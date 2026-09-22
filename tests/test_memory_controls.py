"""The strict content gate refuses what the sanitizer would change, in the adapter's words."""
# qualify: platform

import pytest

from attune_harness.memory_controls import REFUSAL, findings, guard, strict


@pytest.mark.parametrize("text,name", [
    ("sk-ant-" + "A1b2" * 24, "anthropic_api_key"),
    ("api_key: sk-" + "a" * 42, "openai_api_key"),
    ("AKIA" + "Q" * 16, "aws_access_key"),
    ("ghp_" + "x" * 36, "github_token"),
    ("xoxb-1234567890-abc", "slack_token"),
    ("sk_live_" + "Z" * 24, "stripe_key"),
    ("api_key = " + "A1b2" * 6, "generic_api_key"),
    ('password = "hunter22"', "password"),
    ("-----BEGIN RSA PRIVATE KEY-----", "private_key"),
    ("postgres://user:pass@db.example/app", "database_url"),
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
    ("MRN: 1234567", "mrn"),
])
def test_personal_data_that_would_be_rewritten_refuses(text, name):
    assert name in findings(text)[1]
    assert not strict("content", text)


def test_plain_prose_and_low_severity_shapes_pass():
    for text in ("Quartz retention policy: keep audit logs ninety days.", "sk-ant-" + "a" * 100,  # no digit, no upper case
                 "token eyJhbGciOi.eyJzdWIiOi.abc", "bearer abcdefghijklmnopqrstuvwxyz"):
        assert strict("content", text), text
    assert not strict("content", "") and not strict("content", None)


def test_guard_walks_text_metadata_values_and_keys_with_the_adapters_labels():
    guard("fine", {"path": "a/b.md", "nested": {"list": ["ok", {"deep": "fine"}]}})
    with pytest.raises(ValueError, match=REFUSAL):
        guard("api_key = " + "A1b2" * 6, {})
    with pytest.raises(ValueError, match=REFUSAL):
        guard("fine", {"note": "reach me at someone@example.com"})
    with pytest.raises(ValueError, match=REFUSAL):
        guard("fine", {"nested": [{"deep": "MRN: 1234567"}]})
    # The label is part of the candidate, as the adapter builds it: a metadata key named like a
    # password followed by "=" and a quoted value is what the password pattern sees.
    with pytest.raises(ValueError, match=REFUSAL):
        guard("fine", {"password": '"hunter22"'})
