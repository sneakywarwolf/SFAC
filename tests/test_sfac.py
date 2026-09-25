"""Unit tests for SFAC's pure-logic helpers (no network required)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sfac  # noqa: E402


def test_is_valid_hostname_accepts_normal():
    assert sfac.is_valid_hostname("www.example.com")
    assert sfac.is_valid_hostname("a.b")
    assert sfac.is_valid_hostname("sub-domain.example.co.uk")


def test_is_valid_hostname_rejects_malformed():
    # These were wrongly accepted by the old v1.7 regex.
    assert not sfac.is_valid_hostname("a..b")
    assert not sfac.is_valid_hostname("-bad.example.com")
    assert not sfac.is_valid_hostname("bad-.example.com")
    assert not sfac.is_valid_hostname("a.b.")       # trailing dot -> empty label
    assert not sfac.is_valid_hostname("singlelabel")
    assert not sfac.is_valid_hostname("")
    assert not sfac.is_valid_hostname("has space.example.com")
    assert not sfac.is_valid_hostname("a" * 64 + ".example.com")  # label too long


def test_normalize_host_strips_noise():
    assert sfac.normalize_host("HTTPS://Www.Example.com:443/path") == "www.example.com"
    assert sfac.normalize_host("*.example.com") == "example.com"
    assert sfac.normalize_host("  api.example.com.  ") == "api.example.com"
    assert sfac.normalize_host("user@mail.example.com") == "mail.example.com"


def test_normalize_set_dedupe_and_scope():
    raw = [
        "WWW.example.com", "www.example.com", "*.api.example.com",
        "evil.com", "sub.example.com/path", "a..b", "example.com",
    ]
    out = sfac.normalize_set(raw, root="example.com", strict_scope=True)
    assert out == {"www.example.com", "api.example.com",
                   "sub.example.com", "example.com"}
    assert "evil.com" not in out          # out of scope
    assert "a..b" not in out              # invalid


def test_normalize_set_no_scope_keeps_others():
    out = sfac.normalize_set(["evil.com", "www.example.com"],
                             root="example.com", strict_scope=False)
    assert "evil.com" in out


def test_extract_title():
    html = "<html><head><TITLE>  Hello   World </TITLE></head></html>"
    assert sfac.extract_title(html) == "Hello World"
    assert sfac.extract_title("<html>no title</html>") == ""
    assert sfac.extract_title("") == ""


def test_ip_sort_key_orders_v4_before_v6():
    key4 = sfac._ip_sort_key("1.2.3.4")
    key6 = sfac._ip_sort_key("::1")
    assert key4 < key6


def test_csv_fields_superset_of_legacy():
    # The original v1.7 CSV columns must still be present, in order.
    legacy = ["Subdomain", "Status Code", "Accessible"]
    assert sfac.CSV_FIELDS[:3] == legacy


if __name__ == "__main__":
    import traceback
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(funcs) - failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
