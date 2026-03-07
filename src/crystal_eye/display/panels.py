from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from crystal_eye.config import CrystalEyeConfig
from crystal_eye.db.models import Campaign, Credential


def display_credential_panel(console: Console, credential: Credential) -> None:
    """Display a captured credential as a rich panel."""
    lines = []
    for key, value in credential.fields.items():
        lines.append(f"  [bold white]{key:<12}[/bold white] {value}")
    lines.append("")
    lines.append(f"  [dim]Template[/dim]    {credential.template}")
    lines.append(f"  [dim]IP[/dim]          {credential.source_ip}")
    lines.append(f"  [dim]Time[/dim]        {credential.captured_at:%H:%M:%S}")

    content = "\n".join(lines)
    panel = Panel(
        content,
        title="[bold green]Credential Captured[/bold green]",
        border_style="green",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)


def display_config_table(console: Console, config: CrystalEyeConfig) -> None:
    """Display current configuration as a rich table."""
    table = Table(
        show_header=False,
        show_edge=False,
        box=None,
        padding=(0, 2),
        expand=True,
    )
    table.add_column("Key", style="bold cyan", width=16, no_wrap=True)
    table.add_column("Value")

    table.add_row("Campaign", config.campaign or "[dim]not set[/dim]")
    table.add_row("Template", config.template or "[dim]not set[/dim]")
    table.add_row("Host", config.host)
    table.add_row("Port", str(config.port))
    table.add_row("HTTPS", "Yes" if config.use_https else "No")
    table.add_row("Max Attempts", str(config.max_attempts))
    table.add_row("Redirect URL", config.redirect_url or "[dim]from template[/dim]")
    table.add_row("2FA Capture", "Yes" if config.enable_2fa else "No")
    table.add_row("Verbose", "Yes" if config.verbose else "No")
    table.add_row("Tunnel", config.tunnel or "[dim]none[/dim]")
    if config.token:
        masked = config.token[:4] + "..." + config.token[-4:] if len(config.token) > 8 else "****"
        table.add_row("Token", masked)
    elif config.tunnel == "ngrok":
        table.add_row("Token", "[red]not set[/red]")
    table.add_row("Campaign Dir", str(config.campaign_dir) if config.campaign_dir else "[dim]n/a[/dim]")

    console.print()
    console.print(Panel(table, title="[bold]Configuration[/bold]", border_style="cyan", expand=True))


def display_credentials_table(console: Console, credentials: list[Credential]) -> None:
    """Display credentials in a table."""
    if not credentials:
        console.print("[dim]No credentials captured yet.[/dim]")
        return

    table = Table(border_style="dim", padding=(0, 1))
    table.add_column("#", style="dim", width=4)
    table.add_column("Time", width=10)
    table.add_column("Template", width=12)

    # Get all unique field names across all credentials
    field_names: list[str] = []
    for cred in credentials:
        for key in cred.fields:
            if key not in field_names:
                field_names.append(key)
    for name in field_names:
        table.add_column(name.capitalize(), max_width=40)
    table.add_column("IP", width=16)

    for i, cred in enumerate(credentials, 1):
        row = [str(i), f"{cred.captured_at:%H:%M:%S}", cred.template or ""]
        for name in field_names:
            row.append(cred.fields.get(name, ""))
        row.append(cred.source_ip)
        table.add_row(*row)

    console.print()
    console.print(table)


def display_campaigns_table(
    console: Console,
    campaigns: list[Campaign],
    cred_counts: dict[int, int],
) -> None:
    """Display campaigns in a table."""
    if not campaigns:
        console.print("[dim]No campaigns yet.[/dim]")
        return

    table = Table(border_style="dim", padding=(0, 1))
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="bold")
    table.add_column("Template")
    table.add_column("Created")
    table.add_column("Creds", justify="right")
    table.add_column("Status")

    for i, camp in enumerate(campaigns, 1):
        count = cred_counts.get(camp.id, 0)
        status = "[green]active[/green]" if camp.is_active else "[dim]inactive[/dim]"
        table.add_row(
            str(i),
            camp.name,
            camp.template,
            f"{camp.created_at:%Y-%m-%d %H:%M}",
            str(count),
            status,
        )

    console.print()
    console.print(table)
