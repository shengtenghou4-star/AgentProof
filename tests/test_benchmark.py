from agentproof.benchmark import CASES, run_benchmark, wilson_interval


def test_benchmark_detects_all_built_in_cases():
    result = run_benchmark()
    assert len(CASES) >= 35
    assert result["accuracy"] == 1.0
    assert result["correct"] == result["cases"]
    assert result["false_accept_rate"] == 0.0
    assert result["naive_trust_baseline"]["false_accept_rate"] == 1.0
    assert result["by_category"]["gaming"]["accuracy"] == 1.0
    assert result["by_category"]["routing"]["cases"] >= 8


def test_wilson_interval_is_bounded():
    low, high = wilson_interval(35, 35)
    assert 0 < low < high <= 1
    assert wilson_interval(0, 0) == (0.0, 0.0)
