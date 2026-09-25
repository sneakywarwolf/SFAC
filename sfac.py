#!/usr/bin/env python3
"""SFAC - Subdomain Finder & Accessibility Checker (single-file edition).

Discovers subdomains from keyless passive sources (and optional DNS
brute-force / external tools), checks which hosts are live over HTTPS then
HTTP, optionally captures screenshots, and writes a precise CSV.

Pure Python: `pip install -r requirements.txt`. No child process is required
for discovery. External tools (subfinder) and the vendored Sublist3r package
are used only when present; the script runs without them.
"""

import argparse
import concurrent.futures as cf
import csv
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import warnings

try:
    import requests
except ImportError:
    sys.exit("Missing dependency 'requests'. Run: pip install -r requirements.txt")

# tqdm is optional; degrade to a no-op wrapper if absent.
try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - trivial fallback
    def tqdm(iterable=None, **_kwargs):
        return iterable if iterable is not None else _NullBar()

    class _NullBar:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def update(self, _n=1):
            pass

# colorama is optional; fall back to empty color codes.
try:
    from colorama import Fore, Style, init as _colorama_init
    _colorama_init()
    C_INFO, C_OK, C_WARN, C_ERR, C_RESET = (
        Fore.CYAN, Fore.GREEN, Fore.YELLOW, Fore.RED, Style.RESET_ALL,
    )
except ImportError:  # pragma: no cover - trivial fallback
    C_INFO = C_OK = C_WARN = C_ERR = C_RESET = ""

# dnspython is optional but strongly recommended (fast, respects records).
try:
    import dns.resolver
    _HAVE_DNSPYTHON = True
except ImportError:
    _HAVE_DNSPYTHON = False

BANNER = r"""
   SSSSS  FFFFFF   AAA    CCCCC
  SS      FF      A   A  CC
   SSS    FFFF    AAAAA  CC
      SS  FF      A   A  CC
  SSSSS   FF      A   A   CCCCC
        Subdomain Finder and Accessibility Checker
        single-file edition
"""

DEFAULT_UA = "Mozilla/5.0 (compatible; SFAC/2.0; +https://github.com/sneakywarwolf/SFAC)"

# Small, generic brute-force wordlist used only when --brute is set.
BRUTE_WORDS = [
    "www", "mail", "ftp", "webmail", "smtp", "pop", "imap", "ns1", "ns2",
    "dns", "mx", "admin", "portal", "vpn", "remote", "api", "dev", "staging",
    "stage", "test", "qa", "uat", "beta", "demo", "app", "apps", "gateway",
    "gw", "proxy", "cdn", "static", "assets", "img", "images", "media",
    "download", "downloads", "files", "docs", "wiki", "blog", "shop", "store",
    "secure", "login", "signin", "auth", "sso", "id", "account", "accounts",
    "dashboard", "panel", "cpanel", "whm", "webdisk", "autodiscover",
    "autoconfig", "m", "mobile", "wap", "git", "gitlab", "jenkins", "ci",
    "jira", "confluence", "internal", "intranet", "corp", "office", "erp",
    "crm", "db", "database", "sql", "mysql", "postgres", "redis", "cache",
    "monitor", "monitoring", "grafana", "kibana", "prometheus", "status",
    "help", "support", "kb", "faq", "news", "events", "careers", "jobs",
    "partner", "partners", "billing", "pay", "payment", "payments", "checkout",
    "cloud", "aws", "azure", "gcp", "k8s", "kube", "docker", "registry",
    "smtp2", "ns3", "ns4", "email", "exchange", "owa", "lync", "video",
    "voip", "sip", "chat", "forum", "community", "old", "new", "v1", "v2",
]


# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
def log(message, level="info"):
    color = {"info": C_INFO, "success": C_OK, "warning": C_WARN,
             "error": C_ERR}.get(level, C_INFO)
    ts = time.strftime("%H:%M:%S")
    print(f"{color}[{ts}] {message}{C_RESET}", flush=True)


# --------------------------------------------------------------------------
# Hostname normalisation and validation
# --------------------------------------------------------------------------
_LABEL_RE = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")


def is_valid_hostname(host):
    """Strict RFC-1123 hostname check (per-label), min two labels."""
    if not host or len(host) > 253:
        return False
    labels = host.split(".")
    if len(labels) < 2:
        return False
    return all(_LABEL_RE.match(label) for label in labels)


def normalize_host(raw):
    """Lowercase, strip scheme/port/path/wildcards/trailing dot. Returns '' if unusable."""
    if not raw:
        return ""
    host = raw.strip().lower()
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.split("/", 1)[0]          # drop path
    host = host.split("@")[-1]            # drop userinfo
    host = host.split(":", 1)[0]          # drop port
    if host.startswith("*."):
        host = host[2:]
    host = host.strip(".")
    return host


def normalize_set(raw_iter, root=None, strict_scope=True):
    """Normalise, validate, dedupe, optionally restrict to the root domain."""
    out = set()
    root = (root or "").lower().strip(".")
    for raw in raw_iter:
        host = normalize_host(raw)
        if not host or not is_valid_hostname(host):
            continue
        if strict_scope and root:
            if host != root and not host.endswith("." + root):
                continue
        out.add(host)
    return out


# --------------------------------------------------------------------------
# Discovery sources (all keyless, each fully optional and defensive)
# --------------------------------------------------------------------------
def _get_json(url, timeout, session):
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def src_crtsh(domain, session, timeout):
    """crt.sh certificate transparency search."""
    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    data = _get_json(url, timeout, session)
    found = set()
    for entry in data:
        for key in ("name_value", "common_name"):
            val = entry.get(key) or ""
            for name in val.split("\n"):
                found.add(name)
    return found


def src_hackertarget(domain, session, timeout):
    """HackerTarget hostsearch (free tier, rate-limited). CSV: host,ip."""
    url = f"https://api.hackertarget.com/hostsearch/?q={domain}"
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    text = resp.text.strip()
    if not text or "error" in text.lower() or "api count exceeded" in text.lower():
        return set()
    return {line.split(",", 1)[0] for line in text.splitlines() if "," in line}


def src_alienvault(domain, session, timeout):
    """AlienVault OTX passive DNS."""
    url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns"
    data = _get_json(url, timeout, session)
    return {rec.get("hostname", "") for rec in data.get("passive_dns", [])}


def src_anubis(domain, session, timeout):
    """Anubis-DB (jldc.me). Returns a JSON array of hostnames."""
    url = f"https://jldc.me/anubis/subdomains/{domain}"
    data = _get_json(url, timeout, session)
    return set(data) if isinstance(data, list) else set()


PASSIVE_SOURCES = {
    "crtsh": src_crtsh,
    "hackertarget": src_hackertarget,
    "alienvault": src_alienvault,
    "anubis": src_anubis,
}


def discover_passive(domain, sources, session, timeout):
    found = set()
    for name in sources:
        func = PASSIVE_SOURCES.get(name)
        if not func:
            log(f"Unknown source '{name}', skipping.", "warning")
            continue
        try:
            log(f"Querying source: {name} ...")
            results = func(domain, session, timeout)
            log(f"  {name}: {len(results)} raw names", "success")
            found |= results
        except Exception as exc:  # each source is best-effort
            log(f"  {name} failed: {exc}", "warning")
    return found


def discover_subfinder(domain, timeout):
    """Use subfinder if it is on PATH. Optional accelerator."""
    exe = shutil.which("subfinder")
    if not exe:
        return set()
    try:
        log("Found subfinder on PATH; running it ...")
        proc = subprocess.run(
            [exe, "-d", domain, "-silent"],
            capture_output=True, text=True, timeout=timeout,
        )
        if proc.returncode != 0:
            log(f"  subfinder exited {proc.returncode}: {proc.stderr.strip()[:200]}", "warning")
            return set()
        return {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    except Exception as exc:
        log(f"  subfinder failed: {exc}", "warning")
        return set()


def discover_sublist3r(domain):
    """Use the vendored Sublist3r package as a library, if present."""
    sub_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Sublist3r")
    if not os.path.isfile(os.path.join(sub_dir, "sublist3r.py")):
        return set()
    try:
        log("Found vendored Sublist3r; running it as a library ...")
        if sub_dir not in sys.path:
            sys.path.insert(0, sub_dir)
        import sublist3r  # noqa: E402
        results = sublist3r.main(
            domain, 30, None, ports=None, silent=True,
            verbose=False, enable_bruteforce=False, engines=None,
        )
        return set(results or [])
    except Exception as exc:
        log(f"  Sublist3r failed: {exc}", "warning")
        return set()


# --------------------------------------------------------------------------
# DNS resolution
# --------------------------------------------------------------------------
def resolve_host(host, timeout=5.0):
    """Return a sorted list of A/AAAA addresses, or [] if it does not resolve."""
    addrs = set()
    if _HAVE_DNSPYTHON:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = timeout
        resolver.timeout = timeout
        for rdtype in ("A", "AAAA"):
            try:
                for rdata in resolver.resolve(host, rdtype):
                    addrs.add(rdata.to_text())
            except Exception:
                continue
    else:
        try:
            for info in socket.getaddrinfo(host, None):
                addrs.add(info[4][0])
        except Exception:
            pass
    return sorted(addrs, key=_ip_sort_key)


def _ip_sort_key(addr):
    try:
        ip = ipaddress.ip_address(addr)
        return (ip.version, int(ip))
    except ValueError:
        return (9, addr)


def brute_force(domain, words, workers, dns_timeout):
    candidates = [f"{w}.{domain}" for w in words]
    found = set()
    log(f"DNS brute-force: {len(candidates)} candidates ...")
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(resolve_host, host, dns_timeout): host for host in candidates}
        with tqdm(total=len(futures), desc="Brute-forcing", unit="name") as bar:
            for fut in cf.as_completed(futures):
                host = futures[fut]
                try:
                    if fut.result():
                        found.add(host)
                except Exception:
                    pass
                bar.update(1)
    log(f"Brute-force resolved {len(found)} names.", "success")
    return found


# --------------------------------------------------------------------------
# HTTP probing
# --------------------------------------------------------------------------
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def extract_title(text):
    match = _TITLE_RE.search(text or "")
    if not match:
        return ""
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return title[:200]


def probe_host(host, cfg):
    """Probe a single host. Returns a full result dict (all CSV fields)."""
    result = {
        "Subdomain": host,
        "Status Code": "N/A",
        "Accessible": "No",
        "Live": "No",
        "Scheme": "",
        "Final URL": "",
        "Title": "",
        "Server": "",
        "IP Addresses": "",
        "Redirected": "",
        "Error": "",
    }

    ips = resolve_host(host, cfg["dns_timeout"])
    result["IP Addresses"] = ";".join(ips)
    if not ips:
        result["Error"] = "DNS resolution failed"
        return result

    schemes = cfg["schemes"]
    last_error = ""
    session = requests.Session()
    session.headers["User-Agent"] = cfg["user_agent"]

    for scheme in schemes:
        url = f"{scheme}://{host}"
        try:
            if cfg["delay"] > 0:
                time.sleep(cfg["delay"])
            resp = session.get(
                url,
                timeout=cfg["http_timeout"],
                allow_redirects=cfg["follow_redirects"],
                verify=cfg["verify_tls"],
            )
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {str(exc)[:120]}"
            continue

        status = resp.status_code
        result["Live"] = "Yes"
        result["Status Code"] = status
        result["Accessible"] = "Yes" if 200 <= status < 300 else "No"
        result["Scheme"] = scheme
        result["Final URL"] = resp.url
        result["Redirected"] = "Yes" if resp.history else "No"
        result["Server"] = resp.headers.get("Server", "")
        ctype = resp.headers.get("Content-Type", "")
        if "html" in ctype.lower() or not ctype:
            result["Title"] = extract_title(resp.text)
        result["Error"] = ""
        return result

    result["Error"] = last_error or "No HTTP response"
    return result


def probe_all(hosts, cfg):
    results = []
    with cf.ThreadPoolExecutor(max_workers=cfg["concurrency"]) as pool:
        futures = [pool.submit(probe_host, h, cfg) for h in hosts]
        with tqdm(total=len(futures), desc="Checking hosts", unit="host") as bar:
            for fut in cf.as_completed(futures):
                results.append(fut.result())
                bar.update(1)
    results.sort(key=lambda r: r["Subdomain"])
    return results


# --------------------------------------------------------------------------
# Screenshots
# --------------------------------------------------------------------------
def build_driver(cfg):
    """Create one reusable headless Chrome driver, or return None with a reason."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        log("selenium not installed; screenshots disabled.", "warning")
        return None

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--ignore-certificate-errors")
    # Chrome refuses to run as root without --no-sandbox. Only relax the
    # sandbox when we actually are root (containers/CI), never otherwise.
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

    chrome_bin = cfg.get("chrome_binary") or os.environ.get("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin

    try:
        driver_path = cfg.get("chromedriver") or os.environ.get("CHROMEDRIVER")
        service = Service(executable_path=driver_path) if driver_path else Service()
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(cfg["http_timeout"])
        return driver
    except Exception as exc:
        log(f"Could not start Chrome for screenshots: {exc}", "error")
        return None


def capture_screenshots(results, folder, cfg):
    targets = [r for r in results if r["Live"] == "Yes" and r["Final URL"]]
    if not targets:
        log("No live hosts to screenshot.", "warning")
        return
    driver = build_driver(cfg)
    if driver is None:
        return
    os.makedirs(folder, exist_ok=True)
    log(f"Capturing screenshots of {len(targets)} live hosts ...")
    try:
        for r in tqdm(targets, desc="Screenshots", unit="shot"):
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", r["Subdomain"])
            path = os.path.join(folder, f"{safe}.png")
            try:
                driver.get(r["Final URL"])
                driver.save_screenshot(path)
                r["Screenshot"] = path
            except Exception as exc:
                log(f"  screenshot failed for {r['Subdomain']}: "
                    f"{type(exc).__name__}", "warning")
                r["Screenshot"] = ""
    finally:
        try:
            driver.quit()
        except Exception:
            pass


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
CSV_FIELDS = [
    "Subdomain", "Status Code", "Accessible", "Live", "Scheme",
    "Final URL", "Title", "Server", "IP Addresses", "Redirected",
    "Error", "Screenshot",
]


def write_csv(results, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, "") for k in CSV_FIELDS})
    log(f"Results written to {path}", "success")


def write_jsonl(results, path):
    with open(path, "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps({k: r.get(k, "") for k in CSV_FIELDS}) + "\n")
    log(f"JSONL written to {path}", "success")


def summarize(results):
    live = sum(1 for r in results if r["Live"] == "Yes")
    ok = sum(1 for r in results if r["Accessible"] == "Yes")
    log(f"Summary: {len(results)} checked | {live} live | {ok} HTTP 2xx",
        "success" if live else "warning")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_config(args):
    if args.https_only:
        schemes = ["https"]
    elif args.http_only:
        schemes = ["http"]
    else:
        schemes = ["https", "http"]
    return {
        "concurrency": max(1, args.concurrency),
        "http_timeout": args.timeout,
        "dns_timeout": args.dns_timeout,
        "schemes": schemes,
        "follow_redirects": not args.no_redirects,
        "verify_tls": args.verify_tls,
        "user_agent": args.user_agent,
        "delay": max(0.0, args.delay),
        "chrome_binary": args.chrome_binary,
        "chromedriver": args.chromedriver,
    }


def gather_subdomains(args, session):
    domain = args.domain.lower().strip(".")
    raw = set()

    if not args.no_passive:
        sources = [s.strip() for s in args.sources.split(",") if s.strip()]
        raw |= discover_passive(domain, sources, session, args.timeout)

    if not args.no_tools:
        raw |= discover_subfinder(domain, args.tool_timeout)
        raw |= discover_sublist3r(domain)

    raw.add(domain)  # always include the apex

    hosts = normalize_set(raw, root=domain, strict_scope=not args.no_scope)

    if args.brute:
        words = BRUTE_WORDS
        if args.wordlist:
            try:
                with open(args.wordlist, encoding="utf-8") as fh:
                    words = [w.strip() for w in fh if w.strip() and not w.startswith("#")]
            except OSError as exc:
                log(f"Cannot read wordlist: {exc}; using built-in list.", "warning")
        hosts |= brute_force(domain, words, args.concurrency, args.dns_timeout)

    return sorted(hosts)


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="SFAC - single-file subdomain finder & accessibility checker.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-D", "--domain", help="Target domain to enumerate.")
    p.add_argument("-t", "--textfile", help="File of subdomains/hosts to check (skips discovery).")
    p.add_argument("-o", "--output", default=f"output_{int(time.time())}.csv",
                   help="Output CSV path.")
    p.add_argument("--jsonl", help="Also write results as JSON Lines to this path.")
    p.add_argument("-s", "--snapshots", nargs="?", const="snapshots", default=None,
                   help="Capture screenshots of live hosts (optional folder name).")
    p.add_argument("-T", "--concurrency", type=int, default=10,
                   help="Worker threads for probing and brute-force.")
    p.add_argument("--timeout", type=float, default=10.0, help="Per-request HTTP timeout (s).")
    p.add_argument("--dns-timeout", type=float, default=5.0, help="DNS resolution timeout (s).")
    p.add_argument("--tool-timeout", type=float, default=180.0,
                   help="Timeout for external tools (subfinder).")
    # discovery controls
    p.add_argument("--sources", default=",".join(PASSIVE_SOURCES),
                   help="Comma-separated passive sources: " + ",".join(PASSIVE_SOURCES))
    p.add_argument("--no-passive", action="store_true", help="Skip passive web sources.")
    p.add_argument("--no-tools", action="store_true", help="Skip subfinder/Sublist3r integration.")
    p.add_argument("--brute", action="store_true", help="Enable DNS brute-force.")
    p.add_argument("--wordlist", help="Custom brute-force wordlist (one label per line).")
    p.add_argument("--no-scope", action="store_true",
                   help="Do not restrict discovered names to the target domain.")
    # probe controls
    p.add_argument("--https-only", action="store_true", help="Probe HTTPS only.")
    p.add_argument("--http-only", action="store_true", help="Probe HTTP only.")
    p.add_argument("--no-redirects", action="store_true", help="Do not follow HTTP redirects.")
    p.add_argument("--verify-tls", action="store_true",
                   help="Verify TLS certs (off by default; recon targets often use self-signed).")
    p.add_argument("--delay", type=float, default=0.0, help="Delay (s) before each request.")
    p.add_argument("--user-agent", default=DEFAULT_UA, help="HTTP User-Agent.")
    # screenshot controls
    p.add_argument("--chrome-binary", help="Path to Chrome/Chromium binary.")
    p.add_argument("--chromedriver", help="Path to chromedriver.")
    p.add_argument("--no-banner", action="store_true", help="Suppress the ASCII banner.")
    return p.parse_args(argv)


def load_hosts_from_file(path, root=None, strict_scope=False):
    with open(path, encoding="utf-8") as fh:
        raw = [line for line in fh]
    return sorted(normalize_set(raw, root=root, strict_scope=strict_scope))


def main(argv=None):
    args = parse_args(argv)
    if not args.no_banner:
        print(C_INFO + BANNER + C_RESET)

    if args.https_only and args.http_only:
        sys.exit("Choose only one of --https-only / --http-only.")

    output = args.output if args.output.endswith(".csv") else args.output + ".csv"
    cfg = build_config(args)

    session = requests.Session()
    session.headers["User-Agent"] = args.user_agent

    if args.textfile:
        if not os.path.isfile(args.textfile):
            sys.exit(f"File not found: {args.textfile}")
        hosts = load_hosts_from_file(args.textfile)
        log(f"Loaded {len(hosts)} valid unique hosts from {args.textfile}")
    elif args.domain:
        hosts = gather_subdomains(args, session)
        log(f"Discovery complete: {len(hosts)} unique in-scope hosts.", "success")
    else:
        sys.exit("Provide -D <domain> or -t <file>. Use -h for help.")

    if not hosts:
        log("No hosts to check.", "warning")
        write_csv([], output)
        return

    if _HAVE_DNSPYTHON is False:
        log("dnspython not installed; using socket resolver (slower, no record types).", "warning")

    results = probe_all(hosts, cfg)

    if args.snapshots:
        capture_screenshots(results, args.snapshots, cfg)

    write_csv(results, output)
    if args.jsonl:
        write_jsonl(results, args.jsonl)
    summarize(results)


if __name__ == "__main__":
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted by user.", "error")
        sys.exit(130)
