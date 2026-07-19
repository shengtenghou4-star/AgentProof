from agentproof.benchmark import CASES, run_benchmark


def test_benchmark_detects_all_built_in_cases():
    result = run_benchmark()
    assert len(CASES) >= 18
    assert result["accuracy"] == 1.0
    assert result["correct"] == result["cases"]
    assert result["by_category"]["gaming"]["accuracy"] == 1.0
