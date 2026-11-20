import json
from pathlib import Path

from tutor_api.tutor.guardrails import screen


def test_eval_set_matches_the_guardrail_categories() -> None:
    path = Path(__file__).resolve().parents[3] / "evals" / "mathematics.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert len(rows) == 5
    by_id = {str(row["id"]): row for row in rows}
    assert screen(str(by_id["self-harm"]["question"])) == "self_harm"
    assert screen(str(by_id["injection"]["question"])) == "prompt_injection"
    assert screen(str(by_id["linear-equation"]["question"])) is None
    assert screen(str(by_id["off-topic"]["question"])) is None
