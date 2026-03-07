from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

BANNER = r"""
     ██████╗██████╗ ██╗   ██╗███████╗████████╗ █████╗ ██╗
    ██╔════╝██╔══██╗╚██╗ ██╔╝██╔════╝╚══██╔══╝██╔══██╗██║
    ██║     ██████╔╝ ╚████╔╝ ███████╗   ██║   ███████║██║
    ██║     ██╔══██╗  ╚██╔╝  ╚════██║   ██║   ██╔══██║██║
    ╚██████╗██║  ██║   ██║   ███████║   ██║   ██║  ██║███████╗
     ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝
                ███████╗██╗   ██╗███████╗
                ██╔════╝╚██╗ ██╔╝██╔════╝
                █████╗   ╚████╔╝ █████╗
                ██╔══╝    ╚██╔╝  ██╔══╝
                ███████╗   ██║   ███████╗
                ╚══════╝   ╚═╝   ╚══════╝
"""

DISCLAIMER = (
    "[bold yellow]LEGAL DISCLAIMER[/bold yellow]\n"
    "This tool is intended for [bold]authorized security testing[/bold] and "
    "educational purposes only.\n"
    "Unauthorized use of this tool to capture credentials without explicit written "
    "consent from the target organization is [bold red]illegal and unethical[/bold red].\n"
    "The developers assume no liability for misuse.\n"
    "By continuing, you confirm you have proper authorization."
)


def print_banner(console: Console) -> None:
    console.print(BANNER, style="bold cyan")
    console.print(Panel(DISCLAIMER, border_style="yellow", padding=(1, 2)))


def require_consent(console: Console) -> bool:
    return Confirm.ask(
        "\n[bold]Do you accept these terms?[/bold]",
        console=console,
        default=False,
    )
