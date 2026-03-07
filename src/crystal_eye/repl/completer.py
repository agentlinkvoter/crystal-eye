from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

if TYPE_CHECKING:
    from crystal_eye.repl.shell import CrystalEyeShell


class CrystalEyeCompleter(Completer):
    """Context-aware tab completion for the Crystal Eye REPL."""

    COMMANDS = [
        "setup", "set", "start", "stop", "show",
        "creds", "campaigns", "delete", "export", "clear", "help", "exit",
    ]
    SET_KEYS = [
        "template", "host", "port", "campaign", "max_attempts",
        "redirect_url", "verbose", "use_https", "enable_2fa",
    ]
    EXPORT_FORMATS = ["csv", "json"]

    def __init__(self, shell: CrystalEyeShell) -> None:
        self.shell = shell

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

        elif words[0] == "set" and len(words) == 3 and words[1] == "verbose":
            prefix = words[2]
            for val in ["true", "false"]:
                if val.startswith(prefix):
                    yield Completion(val, start_position=-len(prefix))

        elif words[0] == "set" and len(words) == 3 and words[1] in ("use_https", "enable_2fa"):
            prefix = words[2]
            for val in ["true", "false"]:
                if val.startswith(prefix):
                    yield Completion(val, start_position=-len(prefix))

        elif words[0] == "delete" and len(words) == 2:
            from crystal_eye.config import get_state_dir

            prefix = words[1]
            campaigns_root = get_state_dir() / "campaigns"
            if campaigns_root.is_dir():
                for entry in campaigns_root.iterdir():
                    if entry.is_dir() and entry.name.startswith(prefix):
                        yield Completion(entry.name, start_position=-len(prefix))

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
