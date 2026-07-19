from agentproof.benchmark import CASES
from agentproof.benchmark_variants import EXTENDED_CASES, expand_cases, run_extended_benchmark


def test_extended_benchmark_has_at_least_300_cases():
    assert len(CASES) >= 38
    assert len(EXTENDED_CASES) >= 300
    assert len({case.name for case in EXTENDED_CASES}) == len(EXTENDED_CASES)


def test_extended_benchmark_preserves_oracles():
    result = run_extended_benchmark()
    assert result["cases"] == len(EXTENDED_CASES)
    assert result["accuracy"] == 1.0
    assert result["false_accepts"] == 0
    assert result["seed_cases"] == len(CASES)
    assert result["variants_per_seed"] == 8


def test_expansion_rejects_non_positive_variant_count():
    try:
        expand_cases(variants_per_case=0)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("expected ValueError")
