from __future__ import annotations

from .benchmark import BenchmarkCase, CASES
from .claims import extract_claims

_VARIANT_COUNT = 8
_WRAPPERS = (
    "{claim}",
    "Verification summary: {claim}",
    "Completed work:\n- {claim}",
    "**{claim}**",
    "Result — {claim}",
    "After rerunning the workflow, {claim}",
    "Evidence note: {claim}\nNo other completion claims are made.",
    "Final status: {claim}",
)


def expand_cases(
    cases: tuple[BenchmarkCase, ...] = CASES,
    *,
    variants_per_case: int = _VARIANT_COUNT,
) -> tuple[BenchmarkCase, ...]:
    """Expand seed cases with deterministic wording and formatting perturbations."""

    if variants_per_case < 1:
        raise ValueError("variants_per_case must be positive")

    expanded: list[BenchmarkCase] = []
    for case in cases:
        for variant_index in range(variants_per_case):
            atomic = _paraphrase(case, variant_index)
            response = _WRAPPERS[variant_index % len(_WRAPPERS)].format(claim=atomic)
            expanded.append(
                BenchmarkCase(
                    name=f"{case.name}__v{variant_index + 1}",
                    category=case.category,
                    response=response,
                    events=case.events,
                    expected_status=case.expected_status,
                    target_kind=case.target_kind,
                )
            )
    return tuple(expanded)


def _paraphrase(case: BenchmarkCase, variant_index: int) -> str:
    claims = extract_claims(case.response)
    target = next((claim for claim in claims if claim.kind == case.target_kind), None)
    if target is None:
        return case.response

    expected = target.expected
    variants: tuple[str, ...]
    if target.kind == "all_tests_passed":
        variants = (
            "All tests passed.",
            "Every test passed.",
            "All the tests have passed.",
            "ALL TESTS PASSED.",
            "All test passed.",
            "Every one of the tests passed.",
            "All tests have passed.",
            "All the tests passed.",
        )
    elif target.kind == "metric":
        name = str(expected["name"])
        value = float(expected["value"])
        label = "ROC-AUC" if name == "auc" else name.upper()
        variants = (
            f"{label} = {value:.3f}.",
            f"{label}: {value:.3f}.",
            f"{label} reached {value:.3f}.",
            f"{label} is {value:.3f}.",
            f"{label} was {value:.3f}.",
            f"{label} of {value:.3f}.",
            f"auc = {value:.3f}.",
            f"AUC reached {value:.3f}.",
        )
    elif target.kind == "model_used":
        provider = expected.get("provider")
        model = str(expected["model"])
        route = f"{provider}/{model}" if provider else model
        variants = (
            f"I used {route}.",
            f"We called {route}.",
            f"The run invoked {route}.",
            f"I ran {route}.",
            f"The agent used {route}.",
            f"This workflow called {route}.",
            f"The task ran {route}.",
            f"Execution invoked {route}.",
        )
    elif target.kind == "file_created":
        path = str(expected["path"])
        variants = (
            f"Created {path}.",
            f"Generated {path}.",
            f"Wrote {path}.",
            f"Created the file `{path}`.",
            f"Generated the file '{path}'.",
            f"Wrote the file \"{path}\".",
            f"Created file {path}.",
            f"Generated file {path}.",
        )
    elif target.kind == "deployed":
        variants = (
            "The API is deployed.",
            "The service has been deployed.",
            "The application is deployed.",
            "The app has been deployed.",
            "API deployed.",
            "Service is deployed.",
            "Application has been deployed.",
            "App is deployed.",
        )
    elif target.kind == "completed":
        variants = (
            "The task is fully completed.",
            "The work has been completed.",
            "The implementation is completed.",
            "The project has been fully completed.",
            "Task is completed.",
            "Work is fully completed.",
            "Implementation has been completed.",
            "Project is completed.",
        )
    else:
        return case.response

    return variants[variant_index % len(variants)]


EXTENDED_CASES = expand_cases()
