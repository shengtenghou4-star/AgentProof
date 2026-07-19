import pytest

from agentproof.claims import extract_claims


def test_structured_check_claim():
    claims = extract_claims(
        'AGENTPROOF_CLAIM {"kind":"check_succeeded","expected":{"name":"lint","exit_code":0}}'
    )
    assert len(claims) == 1
    assert claims[0].kind == "check_succeeded"
    assert claims[0].expected == {"name": "lint", "exit_code": 0}


def test_negated_completion_language_is_not_extracted():
    text = "Not all tests passed. I did not use openai/gpt-5.6. Failed to create report.json."
    assert extract_claims(text) == []


def test_invalid_structured_claim_fails_closed():
    with pytest.raises(ValueError, match="unsupported structured claim"):
        extract_claims('AGENTPROOF_CLAIM {"kind":"believe_me","expected":{}}')
