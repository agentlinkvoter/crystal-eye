from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from rich.table import Table

from crystal_eye.display.panels import (
    display_campaigns_table,
    display_config_table,
    display_credentials_table,
)

if TYPE_CHECKING:
    from crystal_eye.repl.shell import CrystalEyeShell

HELP_TEXT = {
    "setup": "Interactive wizard to configure campaign, template, server, and behavior settings.",
    "set": "Set a config value. Usage: set <key> <value>\n"
    "  Keys: template, campaign, host, port, max_attempts, redirect_url, verbose, use_https",
    "show": "Display current configuration.",
    "start": "Start the phishing server with current configuration.",
    "stop": "Stop the running server.",
    "creds": "View captured credentials for the current campaign.",
    "campaigns": "List all campaigns with summary statistics.",
    "delete": "Delete a campaign and all its data. Usage: delete <campaign_name>",
    "export": "Export credentials. Usage: export <csv|json>",
    "clear": "Clear the terminal screen.",
    "help": "Show help. Usage: help [command]",
    "exit": "Stop server if running and quit.",
}


class CommandRegistry:
    """Routes command strings to handler methods."""

    def __init__(self, shell: CrystalEyeShell) -> None:
        self.shell = shell
        self._handlers: dict[str, callable] = {
            "setup": self.do_setup,
            "set": self.do_set,
            "show": self.do_show,
            "start": self.do_start,
            "stop": self.do_stop,
            "creds": self.do_creds,
            "campaigns": self.do_campaigns,
            "delete": self.do_delete,
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
            config.campaign = value
            self.shell.init_campaign_db()
            self.shell.console.print(
                f"[green]campaign[/green] = {value}\n"
                f"[dim]Campaign dir: {config.campaign_dir}[/dim]"
            )
            return

        else:
            setattr(config, key, value)

        self.shell.console.print(f"[green]{key}[/green] = {getattr(config, key)}")

    def do_show(self) -> None:
        display_config_table(self.shell.console, self.shell.config)

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

        if not self._require_campaign():
            return

        # Create or resume campaign in DB
        campaign = self.shell.campaign_repo.get_by_name(config.campaign)
        if campaign is None:
            campaign = self.shell.campaign_repo.create(config.campaign, config.template)
        config._active_campaign_id = campaign.id

        # Get template
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
        self.shell.console.print("[dim]Waiting for connections...[/dim]\n")

    def do_stop(self) -> None:
        if not self.shell.server_runner or not self.shell.server_runner.is_running:
            self.shell.console.print("[yellow]No server is running.[/yellow]")
            return

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

    def do_campaigns(self) -> None:
        """List campaigns by scanning the campaigns directory."""
        from crystal_eye.config import get_state_dir
        from crystal_eye.db.engine import Database
        from crystal_eye.db.repository import CampaignRepository, CredentialRepository

        campaigns_root = get_state_dir() / "campaigns"
        if not campaigns_root.is_dir():
            self.shell.console.print("[dim]No campaigns yet.[/dim]")
            return

        from crystal_eye.db.models import Campaign

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

        display_campaigns_table(self.shell.console, campaigns, cred_counts)

    def do_delete(self, name: str = None) -> None:
        if name is None:
            self.shell.console.print("[yellow]Usage:[/yellow] delete <campaign_name>")
            return

        from crystal_eye.config import get_state_dir

        campaign_dir = get_state_dir() / "campaigns" / name
        if not campaign_dir.is_dir():
            self.shell.console.print(f"[red]Campaign not found:[/red] {name}")
            return

        # Confirm
        try:
            answer = input(f"  Delete campaign '{name}' and all its data? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            self.shell.console.print("\n[dim]Cancelled.[/dim]")
            return

        if answer not in ("y", "yes"):
            self.shell.console.print("[dim]Cancelled.[/dim]")
            return

        # If deleting the active campaign, stop server and clear state
        if self.shell.config.campaign == name:
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

    def do_export(self, fmt: str = "csv") -> None:
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

    def do_help(self, command: str = None) -> None:
        if command:
            text = HELP_TEXT.get(command)
            if text:
                self.shell.console.print(f"\n[bold cyan]{command}[/bold cyan]\n{text}\n")
            else:
                self.shell.console.print(f"[red]Unknown command:[/red] {command}")
            return

        table = Table(show_header=False, border_style="dim", padding=(0, 2))
        table.add_column("Command", style="bold cyan", width=12)
        table.add_column("Description")

        for cmd, text in HELP_TEXT.items():
            table.add_row(cmd, text.split("\n")[0])

        self.shell.console.print()
        self.shell.console.print(table)
        self.shell.console.print()

    def do_exit(self) -> None:
        if self.shell.server_runner and self.shell.server_runner.is_running:
            self.shell.server_runner.stop()
            self.shell.console.print("[yellow]Server stopped.[/yellow]")

        self.shell.config.save()
        if self.shell.db:
            self.shell.db.close()
        self.shell.console.print("[dim]Goodbye.[/dim]")
        sys.exit(0)
