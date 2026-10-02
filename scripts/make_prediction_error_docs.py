"""오류 코드 표를 코드에서 생성한다 (docs/ERROR_CODES.md).

표를 손으로 쓰면 코드와 어긋난다. SPECS 를 단일 출처로 삼는다.

    python scripts/make_prediction_error_docs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from scripts.prediction_validator.errors import SPECS  # noqa: E402

GROUPS = [
    ("E1", "파일·인코딩", "파일 자체를 열거나 읽을 수 없는 경우. 이후 검사를 진행하지 않는다."),
    ("E2", "헤더·스키마", "컬럼 구성 문제. id/label 위치를 특정할 수 없으면 행 검사로 넘어가지 않는다."),
    ("E3", "행 구조", "행 단위 형태 문제."),
    ("E4", "ID", "평가 ID 집합과의 대조."),
    ("E5", "라벨", "허용 클래스와의 대조."),
    ("E9", "채점기·운영", "참가자 잘못이 아닌 운영 측 설정 문제와 공통 경고."),
    ("W9", "채점기·운영", None),
]

HEADER = """# 오류 코드 표

담당: 윤성 · **이 파일은 `scripts/make_prediction_error_docs.py` 가 생성한다. 직접 고치지 말고
`scripts/prediction_validator/errors.py` 의 `SPECS` 를 고친 뒤 다시 실행하세요.**

- `등급 = error` 는 채점 불가. 점수를 계산하지 않고 제출을 실패로 기록한다.
- `등급 = warning` 은 채점 가능. 점수를 계산하고 경고를 함께 기록한다.
- `평가셋노출` 표시가 있는 코드의 예시 값은 숨김 평가 ID다.
  **참가자 응답에 넣지 않는다.** `Finding.to_participant()` 가 자동으로 제외한다.
- `운영측` 표시가 있는 코드는 참가자 잘못이 아니다. 제출 횟수 차감(Q4)에서 제외한다.

"""

FOOTER = """
## 등급별 처리 요약

```python
outcome = validate_submission_output(...)

if outcome.ok:
    score_submission(outcome)              # 경고가 있어도 채점한다
elif outcome.operator_fault:
    requeue(submission_id)                 # 횟수 차감 없이 재시도 (E901/E902)
else:
    fail(submission_id, outcome.participant_response)   # 형식 오류
```

참가자에게는 `outcome.participant_response` 만 보낸다.
`outcome.operator_detail` 은 운영 로그 전용이다.
"""


def main() -> int:
    lines = [HEADER]

    for prefix, title, note in GROUPS:
        codes = [c for c in SPECS if c.startswith(prefix)]
        if not codes:
            continue
        if note is not None:
            lines.append(f"## {prefix}xx {title}\n")
            lines.append(f"{note}\n")
        lines.append("| 코드 | 등급 | 메시지 | 조치 안내 | 비고 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for code in codes:
            spec = SPECS[code]
            flags = []
            if spec.leaks_eval_set:
                flags.append("평가셋노출")
            if code in {"E901", "E902"}:
                flags.append("운영측")
            lines.append(
                f"| `{code}` | {spec.severity} | {spec.message} | {spec.hint} | "
                f"{', '.join(flags) or '—'} |"
            )
        lines.append("")

    lines.append(f"\n총 {len(SPECS)}개 코드"
                 f" (error {sum(1 for s in SPECS.values() if s.severity == 'error')},"
                 f" warning {sum(1 for s in SPECS.values() if s.severity == 'warning')}).\n")
    lines.append(FOOTER)

    out = ROOT / "docs" / "prediction-errors.md"
    out.write_text("\n".join(lines), encoding="utf-8")

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"생성: {out} ({len(SPECS)}개 코드)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
