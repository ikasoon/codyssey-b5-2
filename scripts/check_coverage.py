"""coverage JSON에서 라인 80%, 분기 70% 기준을 각각 검사한다."""

import json
from pathlib import Path


def main() -> int:
    """커버리지 비율을 출력하고 기준에 못 미치면 실패한다."""
    totals = json.loads(Path(".cache/coverage.json").read_text())["totals"]
    failed = False
    for name, covered, total, minimum in (
        ("Line", totals["covered_lines"], totals["num_statements"], 80),
        ("Branch", totals["covered_branches"], totals["num_branches"], 70),
    ):
        percent = covered / total * 100 if total else 100.0
        print(f"{name} coverage: {percent:.2f}% (required: {minimum}%)")
        if percent < minimum:
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
