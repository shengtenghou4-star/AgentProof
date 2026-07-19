from agentproof.claims import extract_claims


def test_extracts_atomic_claims():
    claims = extract_claims(
        "All tests passed. AUC reached 0.757. I created model.pkl and used openai/gpt-5.6. The API is deployed."
    )
    assert {claim.kind for claim in claims} == {
        "all_tests_passed",
        "metric",
        "file_created",
        "model_used",
        "deployed",
    }
    metric = next(claim for claim in claims if claim.kind == "metric")
    assert metric.expected == {"name": "auc", "value": 0.757}


def test_deduplicates_repeated_claims():
    claims = extract_claims("AUC is 0.70. AUC was 0.70.")
    assert len(claims) == 1
