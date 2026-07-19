from agentproof.benchmark import run_benchmark


def test_builtin_benchmark_is_self_consistent():
    result = run_benchmark()
    assert result["cases"] >= 8
    assert result["accuracy"] == 1.0
