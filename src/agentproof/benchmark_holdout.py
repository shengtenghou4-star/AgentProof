from __future__ import annotations

from .benchmark import BenchmarkCase, CASES, run_benchmark

_PREFIXES = (
    "",
    "Final answer:\n",
    "Verification report:\n",
    "Execution summary:\n",
    "Evidence-backed result:\n",
    "Status update:\n",
    "### Result\n",
    "### Completion statement\n",
)
_SUFFIXES = (
    "",
    "\nEnd of report.",
    "\nNo additional claims are asserted.",
    "\nEvidence is attached separately.",
)
_CONTAINERS = (
    "{claim}",
    "- {claim}",
    "* {claim}",
    "> {claim}",
    "**{claim}**",
    "`{claim}`",
    "({claim})",
    "[status] {claim}",
)


def build_holdout_cases(
    cases: tuple[BenchmarkCase, ...] = CASES,
) -> tuple[BenchmarkCase, ...]:
    """Create 1,216 deterministic layout perturbations from controlled seed oracles."""

    output: list[BenchmarkCase] = []
    for case in cases:
        variant = 0
        for prefix in _PREFIXES:
            for suffix in _SUFFIXES:
                container = _CONTAINERS[variant % len(_CONTAINERS)]
                response = prefix + container.format(claim=case.response) + suffix
                output.append(
                    BenchmarkCase(
                        name=f"{case.name}__holdout_{variant + 1:02d}",
                        category=case.category,
                        response=response,
                        events=case.events,
                        expected_status=case.expected_status,
                        target_kind=case.target_kind,
                    )
                )
                variant += 1
    return tuple(output)


def run_holdout_benchmark() -> dict[str, object]:
    result = run_benchmark(build_holdout_cases())
    result["benchmark"] = "AgentProofBench-layout-holdout-v0.1"
    result["seed_cases"] = len(CASES)
    result["variants_per_seed"] = len(_PREFIXES) * len(_SUFFIXES)
    result["scope"] = (
        "Deterministic formatting and context perturbations over controlled seed oracles; "
        "not an estimate of unknown real-world attack coverage."
    )
    return result


HOLDOUT_CASES = build_holdout_cases()
