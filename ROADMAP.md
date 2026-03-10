# Crystal Eye Roadmap

Planned features and improvements, ordered by priority and feasibility.

## Phase 1 - Core Phishing Enhancements

### Site Cloner
Clone any live website into a ready-to-use phishing template. Point at a URL, and Crystal Eye fetches the HTML, rewrites form actions to POST to your server, downloads CSS/images, and generates a `manifest.json` automatically.

- `clone <url>` command in the REPL
- Auto-rewrite form targets
- Download and localize static assets
- Generate template folder structure

### More Templates
- Google / Gmail
- Microsoft 365 / Outlook
- LinkedIn
- Generic login page

### QR Code Generator
Generate QR codes that point to your phishing page. QR phishing ("quishing") is one of the most effective delivery methods right now.

- `qr` command to generate a QR code image
- Embed campaign tracking in the URL
- Output as PNG or terminal display

---

## Phase 2 - Delivery and Tracking

### Email Sender
Complete the phishing lifecycle by delivering lures directly from Crystal Eye.

- SMTP integration for sending phishing emails
- HTML email templates that match login page branding
- Custom headers, spoofed sender (where authorized)
- Tracking pixel embedding for open tracking

### SMS Delivery
Send SMS lures via Twilio or similar APIs with shortened URLs.

### Campaign Analytics
Real-time stats and tracking to make Crystal Eye professional-grade for pentest deliverables.

- Visit count, submission count, conversion rate
- Geo-IP lookup on captured credentials
- Unique URLs per target for click tracking
- Timeline view of campaign activity

### Report Generation
Export campaign results as a formatted PDF or HTML report suitable for pentest deliverables.

---

## Phase 3 - Evasion and Realism

### Geofencing
Only serve the phishing page to target IP ranges. Show a 404 or redirect to the real site for everyone else.

### Bot Detection
Block crawlers, security scanners, and known sandbox IPs from reaching the phishing page.

### Browser Fingerprinting
Collect additional target information (OS, browser, screen resolution, plugins) alongside credentials.

### SSL with Let's Encrypt
Auto-provision real TLS certificates via ACME for custom domains, so targets don't see self-signed certificate warnings.

### URL Obfuscation
Homograph domain suggestions, subdomain tricks, and URL shortener integration.

---

## Phase 4 - Credential Management

### Credential Validation
After capturing credentials, optionally test them against the target service.

- IMAP/SMTP login test
- OAuth token validation
- API-based checks (where legal and authorized)
- Mark credentials as "valid" or "invalid" in the database

### Improved Credential Viewer
- Filter and search captured credentials
- Sort by campaign, template, date, validation status
- Bulk export with flexible formats

---

## Phase 5 - Multi-Vector Toolkit

Expand beyond phishing into a broader social engineering and offensive security platform.

### Payload Generation
Create reverse shells, HTA files, and macro-enabled documents for authorized penetration testing and CTF use.

### USB Drop Attack Simulator
Generate autorun payloads for USB security awareness testing.

### Wi-Fi Evil Twin
Integrate with `hostapd` for rogue access point and captive portal attacks.

### Network Reconnaissance
Port scanning and service enumeration (wrap nmap or use native sockets).

### Social Engineering Pretext Library
Curated collection of pretexts, email templates, and call scripts for social engineering engagements.

---

## Architecture Vision

As the toolkit grows, modules register their own commands with the REPL:

```
crystal-eye/
  modules/
    phishing/        # current functionality
    cloner/          # site cloner
    mailer/          # email delivery
    recon/           # reconnaissance
    payloads/        # payload generation
```

Each module is self-contained with its own commands, templates, and configuration, keeping the codebase modular and extensible.
