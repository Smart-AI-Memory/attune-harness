"""The strict content gate refuses what the sanitizer would change, in the adapter's words."""
# qualify: platform

import os
from pathlib import Path

import pytest

from attune_harness.memory_controls import REFUSAL, findings, guard, strict


@pytest.mark.parametrize("text,name", [
    ("sk-ant-" + "A1b2" * 24, "anthropic_api_key"),
    ("SK-ANT-" + "A1b2" * 24, "anthropic_api_key"),  # the detector is case-insensitive
    ("api_key: sk-" + "a" * 42, "generic_api_key"),  # the bare sk- token has no digit; the label pattern catches it
    ("xsk-" + "A1b2" * 10, "openai_api_key"),  # no word boundary before sk-
    ("AKIA" + "Q" * 16, "aws_access_key"),
    ("aws_secret_access_key = " + "A" * 40, "aws_secret_key"),
    ("ghp_" + "x" * 36, "github_token"),
    ("xoxb-abcdefgh", "slack_token"),  # any length after the prefix
    ("sk_live_" + "Z" * 24, "stripe_key"),
    ("api_key = " + "A1b2" * 6, "generic_api_key"),
    ("myapikey = " + "A1b2" * 6, "generic_api_key"),  # no word boundary before the label
    ('password = "hunter22"', "password"),
    ('mypassword = "hunter2"', "password"),
    ("Authorization: Basic " + "A" * 20, "basic_auth"),
    ("-----BEGIN RSA PRIVATE KEY-----", "rsa_private_key"),
    ("postgres://user:pass@db.example", "database_url"),
    ('connection_string = "server=x;pw=y"', "connection_string"),
    ('database_url = "x"', "connection_string"),
    ('db_url = "x"', "connection_string"),
])
def test_blocking_secrets_are_detected(text, name):
    assert name in findings(text)[0]
    assert not strict("content", text)


@pytest.mark.parametrize("text,name", [
    ("mail me at someone@example.com", "email"),
    ("ssn 123-45-6789", "ssn"),
    ("call (555) 123-4567 today", "phone"),
    ("card 4111111111111111", "credit_card"),
    ("host 10.0.0.12 answered", "ipv4"),
    ("2001:db8::8a2e:370:7334", "ipv6"),
    ("at 12 Main Street", "address"),
    ("MRN: 1234567", "mrn"),
    ("Patient ID 12345", "patient_id"),
])
def test_personal_data_that_would_be_rewritten_refuses(text, name):
    assert name in findings(text)[1]
    assert not strict("content", text)


def test_what_the_sanitizer_leaves_alone_passes():
    for text in ("Quartz retention policy: keep audit logs ninety days.",
                 "sk-ant-" + "a" * 100,  # bare key with no digit and one case: the detector's slug rule
                 "token eyJhbGciOi.eyJzdWIiOi.abc",  # medium severity, neither blocked nor rewritten
                 "bearer abcdefghijklmnopqrstuvwxyz",
                 "aws_secret_key = " + "A" * 40,  # the detector's label needs "access"
                 "api_key = " + "A1b2./+=" * 4,  # characters outside the detector's key alphabet
                 'password = "hunt er2"',  # the detector refuses whitespace inside the quotes
                 "Basic " + "A" * 16, "basic characterization",  # no authorization prefix, too short
                 "-----BEGIN DSA PRIVATE KEY-----", "postgresql://u:p@h", "amqp://u:p@h",  # not in the detector's lists
                 "version 1.2.3 released 2026-09-22 at 10:45",
                 "", "   "):  # the candidate is label=value, never blank
        assert strict("content", text), text
    assert not strict("content", None) and not strict("content", 7)


def test_guard_walks_text_metadata_values_and_keys_with_the_adapters_labels():
    guard("fine", {"path": "a/b.md", "nested": {"list": ["ok", {"deep": "fine"}]}, "empty": ""})
    with pytest.raises(ValueError, match=REFUSAL):
        guard("api_key = " + "A1b2" * 6, {})
    with pytest.raises(ValueError, match=REFUSAL):
        guard("fine", {"note": "reach me at someone@example.com"})
    with pytest.raises(ValueError, match=REFUSAL):
        guard("fine", {"nested": [{"deep": "MRN: 1234567"}]})
    with pytest.raises(ValueError, match=REFUSAL):
        guard("fine", {"someone@example.com": "a key the scrubber would rewrite"})  # metadata_key branch
    # The label is part of the candidate, as the adapter builds it: a metadata key named like a
    # password followed by "=" and a quoted value is what the password pattern sees.
    with pytest.raises(ValueError, match=REFUSAL):
        guard("fine", {"password": '"hunter22"'})


def test_the_bare_key_rule_is_linear_on_a_long_run():
    import time
    started = time.monotonic()
    assert strict("content", "sk-" + "a" * 200000)
    assert time.monotonic() - started < 1.0


@pytest.mark.skipif(not os.environ.get("ATTUNE_TEST_ADAPTER_ROOT"), reason="ATTUNE_TEST_ADAPTER_ROOT names no adapter checkout")
def test_gate_agrees_with_the_adapters_own_gate(monkeypatch):
    """D19: the same strings through both gates, same verdict. Runs where the adapter checkout exists."""
    monkeypatch.syspath_prepend(str(Path(os.environ["ATTUNE_TEST_ADAPTER_ROOT"]).resolve() / "src"))
    session_stash = pytest.importorskip("attune.memory.session_stash")
    cases = ["SK-ANT-" + "A1b2" * 24, "xsk-" + "A1b2" * 10, "xoxb-abcdefgh", "myapikey = " + "A1b2" * 6,
             'mypassword = "hunter2"', 'connection_string = "server=x;pw=y"', 'database_url = "x"', 'db_url = "x"',
             "2001:db8::8a2e:370:7334", "aws_secret_key = " + "A" * 40, "api_key = " + "A1b2./+=" * 4,
             'password = "hunt er2"', "Basic " + "A" * 16, "basic characterization", "-----BEGIN DSA PRIVATE KEY-----",
             "postgresql://u:p@h", "postgres://a.b:p@h", "amqp://u:p@h", "", "   ", "sk-ant-" + "a" * 100,
             "token eyJhbGciOi.eyJzdWIiOi.abc", "bearer abcdefghijklmnopqrstuvwxyz",
             "Quartz retention policy: keep audit logs ninety days.", "call (555) 123-4567 today",
             "mail someone@example.com", "version 1.2.3 released 2026-09-22 at 10:45", "sk-" + "A1b2" * 10,
             "api_key=" + "A" * 24, "1234567890", "10.0.0.12", "at 12 Main Street Apt 4", "Patient ID 12345",
             "ghp_" + "x" * 36, "-----BEGIN OPENSSH PRIVATE KEY-----"]
    disagreements = []
    for text in cases:
        candidate = "content=" + text
        theirs = session_stash.prepare_strict_content(candidate, max_chars=None) == candidate
        if theirs != strict("content", text):
            disagreements.append((text[:40], theirs))
    assert disagreements == []
