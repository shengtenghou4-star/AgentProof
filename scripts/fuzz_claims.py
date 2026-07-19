from __future__ import annotations

import random
import string
import time

from agentproof.claims import extract_claims

SEED = 20260719
CASES = 5000
POSITIVE = (
    ("All tests passed.", "all_tests_passed"),
    ("The API is deployed.", "deployed"),
    ("The project is fully completed.", "completed"),
    ("AUC reached 0.757.", "metric"),
    ("I used openai/gpt-test.", "model_used"),
    ("Created report.json.", "file_created"),
)
NEGATED = (
    "Not all tests passed.",
    "The API is not deployed.",
    "The project is not completed.",
    "I did not use openai/gpt-test.",
    "Failed to create report.json.",
)


def main() -> int:
    randomizer = random.Random(SEED)
    started = time.perf_counter()
    positive_checked = 0
    negative_checked = 0
    for index in range(CASES):
        noise = _noise(randomizer, randomizer.randint(0, 140))
        if index % 3 == 0:
            phrase, expected = POSITIVE[index % len(POSITIVE)]
            text = _wrap(randomizer, phrase, noise)
            kinds = {claim.kind for claim in extract_claims(text)}
            if expected not in kinds:
                raise AssertionError(f"missed {expected}: {text!r}")
            positive_checked += 1
        elif index % 3 == 1:
            phrase = NEGATED[index % len(NEGATED)]
            text = _wrap(randomizer, phrase, noise)
            if extract_claims(text):
                raise AssertionError(f"negated claim was extracted: {text!r}")
            negative_checked += 1
        else:
            extract_claims(noise)

    elapsed = time.perf_counter() - started
    if elapsed > 8.0:
        raise AssertionError(f"claim fuzz run exceeded time budget: {elapsed:.3f}s")
    print(
        {
            "seed": SEED,
            "cases": CASES,
            "positive_checked": positive_checked,
            "negative_checked": negative_checked,
            "elapsed_seconds": round(elapsed, 4),
        }
    )
    return 0


def _noise(randomizer: random.Random, length: int) -> str:
    alphabet = string.ascii_letters + string.digits + string.punctuation + " \n\t"
    return "".join(randomizer.choice(alphabet) for _ in range(length))


def _wrap(randomizer: random.Random, phrase: str, noise: str) -> str:
    wrappers = (
        lambda: phrase + "\n" + noise,
        lambda: noise + "\n" + phrase,
        lambda: f"### Result\n{phrase}\n{noise}",
        lambda: f"- {phrase}\n{noise}",
        lambda: f"> {phrase}\n{noise}",
    )
    return randomizer.choice(wrappers)()


if __name__ == "__main__":
    raise SystemExit(main())
