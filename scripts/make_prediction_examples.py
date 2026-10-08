"""정상·오류 예측 예제 생성기 (Day 1·Day 3 산출물).

실제 데이터셋 산출물이 아직 손에 없으므로(릴리스 첨부 누락),
생성 코드에서 확인한 스키마대로 **개발용 고정 픽스처**를 만든다.

- 평가 ID: TEST_%06d  (prepare_dataset.py:70)
- 라벨: 'C.A' 형태 문자열 (prepare_dataset.py:40)
- 예측 파일: id,label CSV (baseline.py 의 to_csv)

여기서 쓰는 클래스 문자열은 **개발용 자리값**이다. 확정된 20개 목록으로
바꿀 때는 `--classes-metadata` 로 실제 metadata.json 을 넘기면 된다.
오류 예제는 코드 하나당 최소 하나씩, 참가자가 실제로 낼 법한 형태로 만든다.

사용:
    python scripts/make_prediction_examples.py                      # 개발용 픽스처로 생성
    python scripts/make_prediction_examples.py --eval-ids data/private/test.csv \
        --classes-metadata data/public/metadata.json    # 실제 데이터로 생성
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))   # allow running this file directly from the repo root

from scripts.prediction_validator.contract import (  # noqa: E402
    load_classes_from_metadata,
    load_eval_ids,
)
from scripts.prediction_validator.errors import SPECS  # noqa: E402

DEV_CLASS_COUNT = 20
DEV_EVAL_COUNT = 24
"""개발용 픽스처 크기. 실제 평가셋은 5,387건이지만 예제는 눈으로 읽을 수 있어야 한다."""

DEV_CLASSES: list[str] = [
    # 'C.A' 형태만 맞춘 개발용 자리값. 확정 목록이 아니다.
    # 끝자리 0이 있는 값("1.10", "2.60")을 일부러 넣어 float 절삭(E507)을
    # 재현할 수 있게 한다.
    "1.10", "1.20", "1.25", "1.40", "1.50",
    "2.10", "2.30", "2.40", "2.60", "2.70",
    "3.10", "3.20", "3.30", "3.40", "3.50",
    "3.60", "3.80", "3.90", "4.10", "6.20",
]


def dev_eval_ids(count: int = DEV_EVAL_COUNT) -> list[str]:
    return [f"TEST_{i:06d}" for i in range(1, count + 1)]


def write_csv(path: Path, rows: list[list[str]], *, newline: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator=newline)
        writer.writerows(rows)


def write_raw(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding, newline="")


def valid_rows(ids: list[str], classes: list[str]) -> list[list[str]]:
    """모든 ID를 정확히 한 번씩, 모든 클래스를 한 번 이상 쓰는 정상 예측."""
    rows = [["id", "label"]]
    for index, sample_id in enumerate(ids):
        rows.append([sample_id, classes[index % len(classes)]])
    return rows


def build(out_dir: Path, ids: list[str], classes: list[str]) -> dict[str, dict]:
    """예제를 생성하고 {경로: {code, ok}} 맵을 돌려준다.

    `code` 는 반드시 나와야 하는 코드, `ok` 는 그 파일이 채점 단계로
    넘어가야 하는지다. 경고만 나는 예제는 code 가 있으면서 ok=true 다.
    """
    valid_dir = out_dir / "valid"
    invalid_dir = out_dir / "invalid"
    expect: dict[str, dict] = {}

    base = valid_rows(ids, classes)
    body = base[1:]

    def ok(name: str, rows: list[list[str]], code: str | None = None, **kw) -> None:
        write_csv(valid_dir / name, rows, **kw)
        expect[f"valid/{name}"] = {"code": code, "ok": True}

    def bad(name: str, code: str, rows: list[list[str]] | None = None,
            raw: str | None = None, **kw) -> None:
        """오류 또는 경고 예제. ok 는 코드 심각도에서 자동으로 정한다."""
        if raw is not None:
            write_raw(invalid_dir / name, raw, **kw)
        else:
            write_csv(invalid_dir / name, rows or [], **kw)
        expect[f"invalid/{name}"] = {
            "code": code,
            "ok": SPECS[code].severity == "warning",
        }

    # --- 정상 -------------------------------------------------------------
    ok("predictions.csv", base)
    ok("predictions_crlf.csv", base, newline="\r\n")

    # 단일 클래스: 경고(E506)만 나고 통과해야 한다.
    ok("predictions_single_class.csv",
       [["id", "label"]] + [[i, classes[0]] for i in ids],
       code="E506")

    # BOM: 경고(W903)만 나고 통과해야 한다.
    bom_text = "﻿" + "\n".join(",".join(r) for r in base) + "\n"
    write_raw(valid_dir / "predictions_bom.csv", bom_text)
    expect["valid/predictions_bom.csv"] = {"code": "W903", "ok": True}

    # --- E1xx 파일 --------------------------------------------------------
    bad("empty.csv", "E102", raw="")
    bad("binary.csv", "E106", raw="id,label\nTEST_000001,\x001.10\n")
    bad("unbalanced_quote.csv", "E105", raw='id,label\n"TEST_000001,1.10\n')

    cp949 = (invalid_dir / "cp949.csv")
    cp949.parent.mkdir(parents=True, exist_ok=True)
    cp949.write_bytes(b"id,label\nTEST_000001,\xb0\xa1\n")
    expect["invalid/cp949.csv"] = {"code": "E104", "ok": False}

    # --- E2xx 헤더 --------------------------------------------------------
    bad("no_header.csv", "E201", body)
    bad("wrong_column_name.csv", "E202", [["ID", "prediction"]] + body)
    bad("index_column.csv", "E203",
        [["", "id", "label"]] + [[str(n), i, l] for n, (i, l) in enumerate(body)])
    bad("column_order.csv", "E204", [["label", "id"]] + [[l, i] for i, l in body])
    bad("duplicate_column.csv", "E205",
        [["id", "label", "label"]] + [[i, l, l] for i, l in body])

    # --- E3xx 행 구조 -----------------------------------------------------
    bad("field_count.csv", "E301",
        raw="id,label\n" + "".join(f"{i},{l}\n" for i, l in body[:-1]) +
            f"{body[-1][0]},{body[-1][1]},extra\n")
    bad("row_count.csv", "E302", [["id", "label"]] + body[:-3])
    bad("blank_row.csv", "E303",
        raw="id,label\n" + f"{body[0][0]},{body[0][1]}\n\n" +
            "".join(f"{i},{l}\n" for i, l in body[1:]))

    # --- E4xx ID ----------------------------------------------------------
    bad("missing_id.csv", "E401", [["id", "label"]] + body[:-1])
    bad("duplicate_id.csv", "E402",
        [["id", "label"]] + body[:-1] + [[body[0][0], body[0][1]]])
    bad("unknown_id.csv", "E403",
        [["id", "label"]] + body[:-1] + [["TEST_999999", classes[0]]])
    bad("empty_id.csv", "E404", [["id", "label"]] + [["", body[0][1]]] + body[1:])
    bad("unpadded_id.csv", "E405",
        [["id", "label"]] + [[i.replace("TEST_", "TEST_").lstrip("TEST_0") or "0", l]
                             for i, l in body])
    bad("int_id.csv", "E405",
        [["id", "label"]] + [[str(n + 1), l] for n, (_, l) in enumerate(body)])
    bad("whitespace_id.csv", "E406",
        [["id", "label"]] + [[f" {i} ", l] for i, l in body])
    bad("train_ids.csv", "E407",
        [["id", "label"]] + [[i.replace("TEST_", "TRAIN_"), l] for i, l in body])

    # --- E5xx 라벨 --------------------------------------------------------
    bad("empty_label.csv", "E501", [["id", "label"]] + [[body[0][0], ""]] + body[1:])
    bad("unknown_label.csv", "E502",
        [["id", "label"]] + [[body[0][0], "Orthogonal Bundle"]] + body[1:])
    bad("label_case.csv", "E503",
        [["id", "label"]] + [[body[0][0], f"  {body[0][1]}  "]] + body[1:])
    bad("label_index.csv", "E504",
        [["id", "label"]] + [[i, str(n % len(classes))] for n, (i, _) in enumerate(body)])
    bad("label_nan.csv", "E505", [["id", "label"]] + [[body[0][0], "nan"]] + body[1:])

    # float 절삭: "1.10" -> "1.1". dtype=str 를 빠뜨린 가장 흔한 실수.
    truncated = [[i, l.rstrip("0") if l.endswith("0") else l] for i, l in body]
    bad("label_float_truncated.csv", "E507", [["id", "label"]] + truncated)

    (out_dir / "EXPECTED.json").write_text(
        json.dumps(expect, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return expect


def write_context(
    out_dir: Path,
    ids: list[str],
    classes: list[str],
    source_ids: str,
    source_classes: str,
) -> None:
    """예제를 만든 조건을 함께 기록한다.

    이게 없으면 테스트가 어떤 클래스·평가 ID로 예제가 만들어졌는지 알 수 없어
    개발용 자리값을 가정하게 된다. 그러면 실데이터로 예제를 다시 만든 순간
    테스트가 엉뚱하게 깨진다.
    """
    (out_dir / "CONTEXT.json").write_text(
        json.dumps(
            {
                "classes": classes,
                "eval_ids": ids,
                "source_classes": source_classes,
                "source_eval_ids": source_ids,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="예측 검증기 예제 생성")
    parser.add_argument("--out", type=Path, default=ROOT / "tests/fixtures/predictions")
    parser.add_argument("--eval-ids", type=Path, default=None,
                        help="실제 평가 ID CSV. 없으면 개발용 TEST_%%06d 픽스처를 쓴다")
    parser.add_argument("--classes-metadata", type=Path, default=None,
                        help="실제 metadata.json. 없으면 개발용 자리값을 쓴다")
    parser.add_argument("--limit", type=int, default=DEV_EVAL_COUNT,
                        help="예제에 담을 ID 개수")
    args = parser.parse_args(argv)

    if args.eval_ids and args.eval_ids.is_file():
        ids = load_eval_ids(args.eval_ids)[: args.limit]
        source_ids = str(args.eval_ids)
    else:
        ids = dev_eval_ids(args.limit)
        source_ids = "개발용 픽스처 (TEST_%06d)"

    if args.classes_metadata and args.classes_metadata.is_file():
        classes = load_classes_from_metadata(args.classes_metadata)
        source_classes = str(args.classes_metadata)
    else:
        classes = DEV_CLASSES
        source_classes = "개발용 자리값 (확정 목록 아님)"

    expect = build(args.out, ids, classes)
    write_context(args.out, ids, classes, source_ids, source_classes)

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(f"평가 ID 출처: {source_ids} ({len(ids)}건)")
    print(f"클래스 출처: {source_classes} ({len(classes)}개)")
    passing = sum(1 for v in expect.values() if v["ok"])
    print(f"생성: {args.out} — 전체 {len(expect)}건 "
          f"(통과해야 하는 예제 {passing}건, 실패해야 하는 예제 {len(expect) - passing}건)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
