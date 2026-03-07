# Crystal Eye

A modern, open-source phishing simulation CLI for cybersecurity professionals. I built this because tools like SEToolKit are outdated, clunky, and don't reflect how modern login pages actually look. Crystal Eye gives you pixel-perfect replicas, a clean interactive shell, real-time credential capture, 2FA relay support, and campaign-based organization — all in a single Python tool.

## Features

- **Pixel-perfect templates** — The Facebook template is built from the real page source, not a rough approximation
- **Interactive REPL shell** — Tab completion, rich formatting, real-time credential panels
- **2FA relay capture** — Victim enters login, sees a real-looking 2FA page, enters their code — you get both
- **Campaign management** — Every engagement gets its own isolated campaign with its own database, certs, and exports
- **Configurable attempt flow** — Set how many login rounds before redirecting to the real site
- **Export** — Dump captured credentials to CSV or JSON
- **HTTPS support** — Auto-generate self-signed certs per campaign
- **Setup wizard** — Walk through the full config in 30 seconds, or use `set` for manual control

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (strongly recommended)

## Installing uv

I **really** recommend using uv. It's fast, handles everything, and just works. Here's how to install it on common systems:

```bash
# Arch Linux (pacman)
sudo pacman -S uv

# Arch Linux (paru/yay)
paru -S uv

# Debian / Ubuntu
sudo apt install pipx && pipx install uv

# Fedora
sudo dnf install uv

# macOS (Homebrew)
brew install uv

# Universal (curl)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation

```bash
git clone https://github.com/yourusername/crystal-eye.git
cd crystal-eye
uv sync
```

That's it. All dependencies are handled automatically.

## Quick Start

Launch Crystal Eye:

```bash
uv run crystal-eye
```

You'll see the banner and a legal disclaimer — type `yes` to accept. Then you're in the shell.

The fastest way to get running is the setup wizard:

```
crystal-eye > setup
```

It walks you through everything: campaign name, template, port, HTTPS, 2FA, and starts the server for you.

## Usage Guide

### Campaigns

Everything in Crystal Eye is organized by campaign. Credentials, certs, exports — all scoped to the campaign directory under `~/.crystal-eye/campaigns/<name>/`.

```
crystal-eye > set campaign my-pentest
crystal-eye > campaign list
crystal-eye > campaign delete old-test
```

### Configuration

Use `set` to configure individual settings. Type `help set` to see all available keys.

```
crystal-eye > set campaign my-pentest
crystal-eye > set template facebook
crystal-eye > set port 443
crystal-eye > set use_https true
crystal-eye > set enable_2fa true
crystal-eye > set max_attempts 2
crystal-eye > set redirect_url https://www.facebook.com/
```

| Key | Description | Default |
|-----|-------------|---------|
| `campaign` | Set or create a campaign by name | — |
| `template` | Phishing template to use | — |
| `port` | Server listen port | `8080` |
| `host` | Listen address | `0.0.0.0` |
| `max_attempts` | Login rounds before redirect | `2` |
| `redirect_url` | Where to send victim after capture | Set by template |
| `enable_2fa` | Show fake 2FA page and capture codes | `false` |
| `use_https` | Use HTTPS with auto-generated self-signed cert | `false` |
| `verbose` | Verbose server logging | `false` |

Use `show` at any time to see the full current configuration.

### Starting the Server

```
crystal-eye > start
```

This requires a campaign and template to be set. The server runs in the background — your shell stays interactive. Navigate to `http://localhost:8080` (or whatever port you set) and you'll see the phishing page.

### How the Capture Flow Works

**Without 2FA** (`enable_2fa false`, `max_attempts 2`):

1. Victim enters email + password → you capture it, they see "password incorrect"
2. Victim tries again → you capture it, they get redirected to the real site

**With 2FA** (`enable_2fa true`, `max_attempts 2`):

1. Victim enters email + password → you capture it, they see the 2FA page
2. Victim enters their 2FA code → you capture it, they see "information doesn't match" error
3. Victim enters email + password again → captured, shown 2FA page again
4. Victim enters 2FA code again → captured, redirected to the real site

This gives you multiple credential + 2FA code pairs, and the experience feels realistic to the victim because real Facebook sometimes does reject valid 2FA codes.

### Viewing Credentials

Credentials appear in your shell in real-time as they're captured. You can also view them anytime:

```
crystal-eye > creds
```

### Exporting

```
crystal-eye > export csv
crystal-eye > export json
```

Files are saved to `~/.crystal-eye/campaigns/<name>/exports/`.

### Stopping

```
crystal-eye > stop
crystal-eye > exit
```

`exit` will stop the server automatically if it's still running.

### All Commands

| Command | Description |
|---------|-------------|
| `setup` | Interactive setup wizard |
| `set <key> <value>` | Change a config value |
| `show` | Display current configuration |
| `campaign list` | List all campaigns |
| `campaign create <name>` | Create a new campaign |
| `campaign delete <name>` | Delete a campaign and all its data |
| `start` | Start the phishing server |
| `stop` | Stop the server |
| `creds` | View captured credentials |
| `export <csv\|json>` | Export credentials |
| `clear` | Clear the screen |
| `help [command]` | Show help |
| `exit` | Save and quit |

## Templates

Templates live in the `templates/` directory. Each template is a folder with:

```
templates/facebook/
├── manifest.json    # Template metadata (name, fields, redirect URL)
├── login.html       # Login page
├── error.html       # "Wrong password" page
├── 2fa.html         # Two-factor auth page
└── static/          # CSS, images, favicon, etc.
```

Currently included: **Facebook** (2025 design, pixel-perfect).

Adding a new template is straightforward — create the folder, write the HTML/CSS, define the manifest, and it's automatically discovered on next launch.

## Project Structure

```
crystal-eye/
├── src/crystal_eye/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration model
│   ├── banner.py            # ASCII art + legal disclaimer
│   ├── repl/                # Interactive shell
│   │   ├── shell.py         # REPL loop (prompt_toolkit)
│   │   ├── commands.py      # All command handlers
│   │   ├── completer.py     # Tab completion
│   │   └── wizard.py        # Setup wizard
│   ├── server/              # Phishing server
│   │   ├── app.py           # FastAPI app factory
│   │   ├── routes.py        # Credential capture routes
│   │   ├── runner.py        # Threaded uvicorn runner
│   │   └── tls.py           # Self-signed cert generation
│   ├── templates/           # Template discovery + rendering
│   ├── db/                  # SQLite storage (per-campaign)
│   ├── display/             # Rich panels and tables
│   └── export/              # CSV/JSON export
├── templates/               # Phishing page templates
│   └── facebook/
└── tests/
```

## Architecture

The REPL runs on the main thread using `prompt_toolkit`. The phishing server (FastAPI + uvicorn) runs in a daemon thread with its own asyncio event loop. Credentials are captured on the server thread, saved to SQLite (thread-safe with WAL mode), and displayed in the REPL in real-time using Rich panels with `patch_stdout`.

## Legal Disclaimer

This tool is for **authorized security testing and educational purposes only**. You must have explicit written permission before using this tool against any target. Unauthorized use of this tool to capture credentials is illegal and unethical. I am not responsible for any misuse.

## License

MIT
