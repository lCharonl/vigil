"""Tests for the watchlist loader helpers (data/watchlist.py)."""

from vigil.detect.data.watchlist import is_allowlisted
from vigil.detect.techniques.names import parse_domain


def test_is_allowlisted_exact_match():
    assert is_allowlisted(parse_domain("cisco.com"), frozenset({"cisco.com"}))


def test_is_allowlisted_subdomain_match():
    name = parse_domain("b08cf4.vpn.sse.cisco.com")
    assert is_allowlisted(name, frozenset({"cisco.com"}))


def test_is_allowlisted_no_match():
    name = parse_domain("cisco-login-secure.com")
    assert not is_allowlisted(name, frozenset({"cisco.com"}))


def test_is_allowlisted_non_apex_entry():
    # some watchlist legitimate_domains are themselves subdomains (e.g. aws.amazon.com)
    name = parse_domain("console.aws.amazon.com")
    assert is_allowlisted(name, frozenset({"aws.amazon.com"}))
    assert not is_allowlisted(parse_domain("amazon.com"), frozenset({"aws.amazon.com"}))
