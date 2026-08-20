"""Tests for the ingestion layer: FixtureSource and the CertStream JSON mapping."""

from datetime import UTC
from pathlib import Path

import pytest

from vigil.ingest.certstream import parse_certstream_message
from vigil.ingest.fixtures import FixtureSource

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "certs.jsonl"


@pytest.mark.asyncio
async def test_fixture_source_yields_all_certs():
    source = FixtureSource(FIXTURES_PATH)
    events = [event async for event in source.stream()]
    assert len(events) == 5


@pytest.mark.asyncio
async def test_fixture_source_preserves_order_and_precert_flags():
    source = FixtureSource(FIXTURES_PATH)
    events = [event async for event in source.stream()]
    assert [e.is_precert for e in events] == [False, True, False, False, True]


@pytest.mark.asyncio
async def test_fixture_source_wildcard_domain_is_untouched():
    source = FixtureSource(FIXTURES_PATH)
    events = [event async for event in source.stream()]
    wildcard_event = events[1]
    assert wildcard_event.domains == ["*.acme-cloud.io", "acme-cloud.io"]


@pytest.mark.asyncio
async def test_fixture_source_idn_domain_is_untouched():
    source = FixtureSource(FIXTURES_PATH)
    events = [event async for event in source.stream()]
    idn_event = events[2]
    assert idn_event.domains == ["xn--80ak6aa92e.com"]


@pytest.mark.asyncio
async def test_fixture_source_events_are_utc():
    source = FixtureSource(FIXTURES_PATH)
    events = [event async for event in source.stream()]
    for event in events:
        assert event.validity_not_before.tzinfo == UTC
        assert event.validity_not_after.tzinfo == UTC


def test_parse_certstream_message_maps_fields():
    message = {
        "message_type": "certificate_update",
        "data": {
            "update_type": "X509LogEntry",
            "cert_index": 42,
            "leaf_cert": {
                "serial_number": "0102",
                "signature_algorithm": "sha256WithRSAEncryption",
                "not_before": 1731000000,
                "not_after": 1738776000,
                "all_domains": ["example.org", "www.example.org"],
                "issuer": {"C": "US", "O": "Let's Encrypt", "CN": "R11"},
            },
            "source": {"name": "Google 'Xenon2026' log"},
        },
    }

    event = parse_certstream_message(message)

    assert event is not None
    assert event.serial_number == "0102"
    assert event.signature_algo == "sha256WithRSAEncryption"
    assert event.issuer_country == "US"
    assert event.issuer_organisation == "Let's Encrypt"
    assert event.issuer_common_name == "R11"
    assert event.domains == ["example.org", "www.example.org"]
    assert event.source == "Google 'Xenon2026' log"
    assert event.cert_index == 42
    assert event.is_precert is False
    assert event.validity_not_before.tzinfo == UTC
    assert event.validity_not_after.tzinfo == UTC


def test_parse_certstream_message_ignores_non_certificate_messages():
    assert parse_certstream_message({"message_type": "heartbeat"}) is None
