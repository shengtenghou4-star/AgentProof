# Contributing to AgentProof

AgentProof treats evidence quality as part of the implementation, not an afterthought.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
ruff check src tests
pytest
coverage run -m pytest
coverage report
```

## Change requirements

Every behavior change should include:

1. a test that fails before the change;
2. an explicit evidence boundary;
3. deterministic fixtures where possible;
4. no plaintext secrets, prompts, tool arguments, or model responses unless the feature explicitly requires them;
5. documentation updates when public claims or output schemas change.

## New claim verifier

A new claim kind should define:

- a conservative extraction rule or structured-claim schema;
- the exact runtime event required to verify it;
- verified, partial, unsupported, and contradicted behavior;
- false-positive and negation tests;
- adversarial benchmark cases;
- a reason string that explains the evidence gap in plain language.

## New runtime adapter

Adapters should normalize stable semantic facts instead of copying entire vendor objects. Prefer hashes for prompts, responses, tool arguments, and tool outputs. Preserve provider/model identifiers, run IDs, call IDs, status, timing, and explicit errors when available. Unknown records should remain hashed spans rather than being silently discarded.

## Benchmark discipline

Do not add cases only to raise the headline count. Each seed oracle needs:

- a named threat or honest-control scenario;
- an expected status with a clear rationale;
- deterministic evidence;
- category coverage;
- a statement describing whether it is a new attack type or only a wording/layout perturbation.

Controlled-suite performance must never be described as universal real-world accuracy.

## Pull requests

PR descriptions should state:

- what changed;
- why it changed;
- threat model or failure mode addressed;
- validation performed;
- limitations that remain.

The strict self-audit, benchmark suites, package smoke test, coverage gate, and ClaimForge case study must pass before merge.
