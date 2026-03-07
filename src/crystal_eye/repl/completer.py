from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

if TYPE_CHECKING:
    from crystal_eye.repl.shell import CrystalEyeShell


class CrystalEyeCompleter(Completer):
    """Context-aware tab completion for the Crystal Eye REPL."""

    COMMANDS = [
        "setup", "set", "show", "campaign",
        "start", "stop", "creds", "export",
        "clear", "help", "exit",
    ]
    SET_KEYS = [
        "campaign", "template", "host", "port", "max_attempts",
        "redirect_url", "verbose", "use_https", "enable_2fa",
    ]
    CAMPAIGN_ACTIONS = ["list", "create", "delete"]
    EXPORT_FORMATS = ["csv", "json"]

    def __init__(self, shell: CrystalEyeShell) -> None:
        self.shell = shell

    def _campaign_names(self, prefix: str):
        from crystal_eye.config import get_state_dir

        campaigns_root = get_state_dir() / "campaigns"
        if campaigns_root.is_dir():
            for entry in campaigns_root.iterdir():
                if entry.is_dir() and entry.name.startswith(prefix):
                    yield Completion(entry.name, start_position=-len(prefix))

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        words = text.split()

        if len(words) <= 1:
            prefix = words[0] if words else ""
            for cmd in self.COMMANDS:
                if cmd.startswith(prefix):
                    yield Completion(cmd, start_position=-len(prefix))

        elif words[0] == "set" and len(words) == 2:
            prefix = words[1]
            for key in self.SET_KEYS:
                if key.startswith(prefix):
                    yield Completion(key, start_position=-len(prefix))

        elif words[0] == "set" and len(words) == 3 and words[1] == "template":
            prefix = words[2]
            for name in self.shell.template_registry.list_names():
                if name.startswith(prefix):
                    yield Completion(name, start_position=-len(prefix))

        elif words[0] == "set" and len(words) == 3 and words[1] == "campaign":
            prefix = words[2]
            yield from self._campaign_names(prefix)

        elif words[0] == "set" and len(words) == 3 and words[1] in ("verbose", "use_https", "enable_2fa"):
            prefix = words[2]
            for val in ["true", "false"]:
                if val.startswith(prefix):
                    yield Completion(val, start_position=-len(prefix))

        elif words[0] == "campaign" and len(words) == 2:
            prefix = words[1]
            for action in self.CAMPAIGN_ACTIONS:
                if action.startswith(prefix):
                    yield Completion(action, start_position=-len(prefix))

        elif words[0] == "campaign" and len(words) == 3 and words[1] == "delete":
            prefix = words[2]
            yield from self._campaign_names(prefix)

        elif words[0] == "export" and len(words) == 2:
            prefix = words[1]
            for fmt in self.EXPORT_FORMATS:
                if fmt.startswith(prefix):
                    yield Completion(fmt, start_position=-len(prefix))

        elif words[0] == "help" and len(words) == 2:
            prefix = words[1]
            for cmd in self.COMMANDS:
                if cmd.startswith(prefix):
                    yield Completion(cmd, start_position=-len(prefix))
