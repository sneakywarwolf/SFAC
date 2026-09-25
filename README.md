# 🕵️ SFAC — Subdomain Finder & Accessibility Checker

> **Created by:** Sneakywarwolf 🐺

Discover subdomains, check which are live, capture screenshots, and export a
precise CSV — from a single self-contained script.

---

## What it does

- **Subdomain discovery** from keyless passive sources (crt.sh, HackerTarget,
  AlienVault OTX, Anubis-DB), with optional DNS brute-force. If `subfinder` is
  on your `PATH` or the vendored `Sublist3r/` package is present, SFAC uses
  them too — but neither is required.
- **Accessibility check** over **HTTPS first, then HTTP**. Any HTTP response
  marks a host **Live**; only `2xx` marks it **Accessible**. The exact status
  code, final URL, redirect flag, page title, `Server` header, and resolved
  IPs are recorded.
- **DNS-aware:** hosts are resolved first, so non-resolving names are labelled
  instead of burning a full HTTP timeout.
- **Scope control:** discovered names are restricted to the target domain by
  default (`--no-scope` to disable).
- **Screenshots** (optional) of live hosts using one reused headless-Chrome
  instance.
- **CSV output**, backward-compatible with the old columns
  (`Subdomain, Status Code, Accessible`) plus richer fields. Optional JSON Lines.

---

## Requirements

- **Python 3.8+**
- `pip install -r requirements.txt` (installs `requests`, `dnspython`, `tqdm`,
  `colorama`, and `selenium`).
- **Screenshots only:** Google Chrome / Chromium. Selenium 4.6+ provisions a
  matching driver automatically; otherwise point SFAC at one with
  `--chromedriver` / `CHROMEDRIVER` and the browser with
  `--chrome-binary` / `CHROME_BIN`.

> `subfinder` (Go) is optional. If present it is used automatically; API keys
> configured for subfinder expand its coverage but are not required.

---

## Install

```bash
git clone https://github.com/sneakywarwolf/SFAC.git
cd SFAC
pip install -r requirements.txt
```

---

## Usage

```bash
# Enumerate + check a domain
python sfac.py -D example.com

# Add DNS brute-force with the built-in wordlist
python sfac.py -D example.com --brute

# Check hosts from a file (skips discovery)
python sfac.py -t subdomains.txt

# Save to a specific CSV, and also JSON Lines
python sfac.py -D example.com -o results.csv --jsonl results.jsonl

# Capture screenshots of live hosts into ./shots
python sfac.py -D example.com -s shots

# More threads, HTTPS only, rate-limited
python sfac.py -D example.com -T 20 --https-only --delay 0.2
```

### Key options

| Flag | Purpose |
|------|---------|
| `-D, --domain` | Target domain to enumerate |
| `-t, --textfile` | File of hosts to check (skips discovery) |
| `-o, --output` | Output CSV path |
| `--jsonl` | Also write JSON Lines |
| `-s, --snapshots [folder]` | Capture screenshots of live hosts |
| `-T, --concurrency` | Worker threads (default 10) |
| `--sources` | Comma-separated passive sources |
| `--no-passive` / `--no-tools` | Skip web sources / external tools |
| `--brute` / `--wordlist` | DNS brute-force (built-in or custom list) |
| `--no-scope` | Do not restrict names to the target domain |
| `--https-only` / `--http-only` | Restrict probe scheme |
| `--no-redirects` | Do not follow HTTP redirects |
| `--verify-tls` | Verify TLS certs (off by default) |
| `--delay` / `--user-agent` | Rate limit / custom UA |

Run `python sfac.py -h` for the full list.

---

## Output

CSV columns:

```
Subdomain, Status Code, Accessible, Live, Scheme, Final URL,
Title, Server, IP Addresses, Redirected, Error, Screenshot
```

- **Accessible** = `Yes` only for HTTP `2xx` (matches legacy behaviour).
- **Live** = `Yes` for any HTTP response (2xx/3xx/4xx/5xx).
- **Error** records why a host failed (e.g. `DNS resolution failed`, a TLS or
  connection error), instead of silently dropping it.

---

## Notes & limitations

- Passive-source coverage depends on those services being reachable and their
  free-tier limits; each source is best-effort and skipped on error.
- TLS verification is **off by default** because recon targets often use
  self-signed or expired certificates; use `--verify-tls` to enforce it.
- Following redirects can send traffic outside the target domain. Use
  `--no-redirects` when your rules of engagement require it.

---

## ⚠️ Disclaimer

For **authorized security testing and educational use only**. Obtain explicit
permission before testing any domain you do not own.

---

## Contact

🔗 **GitHub:** [Sneakywarwolf](https://github.com/sneakywarwolf) · 📧 sneakypentester@gmail.com
