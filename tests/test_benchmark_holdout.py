from agentproof.benchmark_holdout import HOLDOUT_CASES, run_holdout_benchmark


def test_holdout_suite_has_over_one_thousand_cases():
    assert len(HOLDOUT_CASES) == 1216
    assert len({case.name for case in HOLDOUT_CASES}) == len(HOLDOUT_CASES)


def test_holdout_suite_has_zero_false_accepts():
    result = run_holdout_benchmark()
    assert result["cases"] == 1216
    assert result["accuracy"] == 1.0
    assert result["false_accepts"] == 0
