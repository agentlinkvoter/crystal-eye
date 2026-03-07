from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console

from crystal_eye.banner import print_banner, require_consent
from crystal_eye.config import CrystalEyeConfig
from crystal_eye.repl.shell import CrystalEyeShell
from crystal_eye.templates.registry import TemplateRegistry


def main() -> None:
    console = Console()

    # Banner and legal disclaimer
    print_banner(console)
    if not require_consent(console):
        console.print("\n[dim]Exiting.[/dim]")
        sys.exit(0)

    console.print()

    # Load or create config
    config = CrystalEyeConfig.load()

    # Discover templates
    templates_dir = Path(config.templates_dir) if config.templates_dir else None
    registry = TemplateRegistry(templates_dir)
    registry.scan()

    template_count = len(registry.list_names())
    console.print(f"[dim]Loaded {template_count} template(s). Type 'help' for commands.[/dim]\n")

    # Launch REPL (DB is initialized per-campaign inside the shell)
    shell = CrystalEyeShell(config=config, template_registry=registry)
    shell.run()
