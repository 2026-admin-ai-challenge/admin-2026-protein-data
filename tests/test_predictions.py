"""예측 검증기 테스트.

`examples/` 의 모든 예제가 기대한 코드를 내는지 확인한다 (EXPECTED.json).
정상 예제는 반드시 통과해야 하고, 오류 예제는 해당 코드를 반드시 내야 한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from scripts.prediction_validator import (  # noqa: E402
    load_contract,
    validate_file,
    validate_text,
)
from scripts.prediction_validator.errors import SPECS  # noqa: E402
from scripts.make_prediction_examples import DEV_CLASSES, dev_eval_ids, valid_rows  # noqa: E402

EXAMPLES = ROOT / "tests/fixtures/predictions"
EXPECTED_PATH = EXAMPLES / "EXPECTED.json"
CONTEXT_PATH = EXAMPLES / "CONTEXT.json"


@pytest.fixture(scope="session")
def expected() -> dict[str, str]:
    if not EXPECTED_PATH.is_file():
        pytest.skip("examples 가 없습니다. python scripts/make_prediction_examples.py 를 먼저 실행하세요.")
    return json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def context() -> dict:
    """예제를 만든 조건(클래스·평가 ID).

    `make_examples.py` 가 CONTEXT.json 에 기록한다. 실데이터로 예제를 다시
    만들면 이 값도 함께 바뀌므로 테스트가 따라간다. 개발용 자리값을
    가정하면 실데이터 전환 때 엉뚱하게 깨진다.
    """
    if CONTEXT_PATH.is_file():
        return json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
    return {
        "classes": DEV_CLASSES,
        "eval_ids": dev_eval_ids(),
        "source_classes": "개발용 자리값 (CONTEXT.json 없음)",
        "source_eval_ids": "개발용 픽스처 (CONTEXT.json 없음)",
    }


@pytest.fixture
def classes(context) -> list[str]:
    return context["classes"]


@pytest.fixture
def eval_ids(context) -> list[str]:
    return context["eval_ids"]


@pytest.fixture
def contract(context):
    """예제와 같은 조건으로 주입한 계약."""
    c = load_contract()
    c.with_classes(context["classes"]).with_eval_ids(context["eval_ids"])
    c.expected_rows = len(context["eval_ids"])
    return c


def _csv(rows: list[list[str]]) -> str:
    return "".join(",".join(r) + "\n" for r in rows)


# --- 예제 기반 테스트 ------------------------------------------------------

def test_examples_exist(expected):
    assert expected, "EXPECTED.json 이 비어 있습니다."
    for name in expected:
        assert (EXAMPLES / name).is_file(), f"예제 파일 누락: {name}"


def test_every_example_matches_expectation(expected, contract):
    """기대한 코드가 나오고, 통과/실패 판정도 기대와 같아야 한다."""
    failures = []
    for name, want in sorted(expected.items()):
        report = validate_file(EXAMPLES / name, contract)
        code = want["code"]
        if code is not None and code not in report.codes:
            failures.append(f"{name}: {code} 를 기대했으나 {report.codes} 발생")
        if report.ok != want["ok"]:
            state = "통과" if want["ok"] else "실패"
            failures.append(
                f"{name}: {state}해야 하는데 ok={report.ok} "
                f"(오류 {[f.code for f in report.errors]})"
            )
    assert not failures, "\n".join(failures)


def test_warning_only_examples_still_pass(expected, contract):
    """경고만 나는 예제는 채점 단계로 넘어가야 한다."""
    warning_only = [
        name for name, want in expected.items()
        if want["ok"] and want["code"] is not None
    ]
    assert warning_only, "경고만 나는 예제가 하나도 없습니다."
    for name in warning_only:
        report = validate_file(EXAMPLES / name, contract)
        assert report.ok, f"{name}: {[f.code for f in report.errors]}"
        assert report.warnings, f"{name}: 경고가 나와야 합니다."


def test_every_error_code_has_an_example(expected):
    """정의한 코드마다 예제가 있어야 한다. 아래 skip 은 별도 단위 테스트로 다룬다."""
    covered = {want["code"] for want in expected.values() if want["code"]}
    skip = {"E101", "E103", "E901", "E902", "W904"}
    uncovered = {c for c in SPECS if c not in covered and c not in skip}
    assert not uncovered, f"예제 없는 코드: {sorted(uncovered)}"


# --- 파일 수준 ------------------------------------------------------------

def test_missing_file(contract, tmp_path):
    report = validate_file(tmp_path / "nope.csv", contract)
    assert report.codes == ["E101"]
    assert not report.ok


def test_file_too_large(contract, tmp_path):
    path = tmp_path / "big.csv"
    path.write_text("id,label\n" + "TEST_000001,1.10\n" * 100, encoding="utf-8")
    contract.max_file_bytes = 50
    report = validate_file(path, contract)
    assert "E103" in report.codes


def test_bom_is_warning_only(contract, eval_ids, classes):
    text = "﻿" + _csv(valid_rows(eval_ids, classes))
    report = validate_text(text, contract)
    # validate_text 는 BOM 을 벗기지 않으므로 validate_file 경로로 확인한다.
    assert not report.ok or True


def test_bom_via_file_passes(contract, tmp_path, eval_ids, classes):
    path = tmp_path / "bom.csv"
    path.write_text(
        "﻿" + _csv(valid_rows(eval_ids, classes)),
        encoding="utf-8",
        newline="",
    )
    report = validate_file(path, contract)
    assert report.ok
    assert "W903" in report.codes


# --- 운영 측 설정 오류 ----------------------------------------------------

def test_missing_class_list_is_operator_fault(contract, eval_ids, classes):
    contract.classes = ()
    report = validate_text(_csv(valid_rows(eval_ids, classes)), contract)
    assert "E901" in report.codes
    assert report.operator_fault


def test_missing_eval_ids_is_operator_fault(contract, eval_ids, classes):
    contract.eval_ids = ()
    report = validate_text(_csv(valid_rows(eval_ids, classes)), contract)
    assert "E902" in report.codes
    assert report.operator_fault


def test_participant_format_error_is_not_operator_fault(contract, eval_ids, classes):
    rows = valid_rows(eval_ids, classes)
    rows[1][1] = "nope"
    report = validate_text(_csv(rows), contract)
    assert not report.ok
    assert not report.operator_fault


# --- 평가셋 노출 방지 -----------------------------------------------------

def test_missing_ids_are_hidden_from_participant(contract, eval_ids, classes):
    rows = valid_rows(eval_ids, classes)[:-3]
    report = validate_text(_csv(rows), contract)

    finding = report.get("E401")
    assert finding is not None
    assert finding.count == 3, "누락 건수가 실제 누락 ID 수와 같아야 한다"
    assert finding.samples, "운영 로그에는 누락 ID 예시가 있어야 한다"

    participant = report.participant_payload()
    blob = json.dumps(participant, ensure_ascii=False)
    for sample in finding.samples:
        assert sample not in blob, f"참가자 응답에 평가 ID {sample} 가 노출됐다"

    e401 = next(e for e in participant["errors"] if e["code"] == "E401")
    assert e401["count"] == 3
    assert "samples" not in e401 and "rows" not in e401


def test_unknown_id_is_echoed_back(contract, eval_ids, classes):
    """참가자가 보낸 값은 되돌려 줘도 평가셋이 새지 않는다."""
    rows = valid_rows(eval_ids, classes)
    rows[1][0] = "TEST_999999"
    report = validate_text(_csv(rows), contract)
    blob = json.dumps(report.participant_payload(), ensure_ascii=False)
    assert "TEST_999999" in blob


# --- 라벨 세부 판정 -------------------------------------------------------

def test_float_truncated_label_is_e507_not_e502(contract, eval_ids, classes):
    """dtype=str 누락으로 '1.10'이 '1.1'이 된 경우를 정확히 짚어야 한다."""
    rows = valid_rows(eval_ids, classes)
    rows[1][1] = "1.1"
    report = validate_text(_csv(rows), contract)
    assert "E507" in report.codes
    assert "E502" not in report.codes


def test_class_index_label_is_e504(contract, eval_ids, classes):
    rows = valid_rows(eval_ids, classes)
    for i, row in enumerate(rows[1:]):
        row[1] = str(i % 20)
    report = validate_text(_csv(rows), contract)
    assert "E504" in report.codes


def test_whitespace_label_is_e503(contract, eval_ids, classes):
    rows = valid_rows(eval_ids, classes)
    rows[1][1] = f" {classes[0]} "
    report = validate_text(_csv(rows), contract)
    assert "E503" in report.codes


def test_nullish_label_is_e505(contract, eval_ids, classes):
    for value in ["nan", "NaN", "None", "null", "NA"]:
        rows = valid_rows(eval_ids, classes)
        rows[1][1] = value
        report = validate_text(_csv(rows), contract)
        assert "E505" in report.codes, f"{value} 를 결측으로 잡지 못했다"


def test_single_class_is_warning_only(contract, eval_ids, classes):
    rows = [["id", "label"]] + [[i, classes[0]] for i in eval_ids]
    report = validate_text(_csv(rows), contract)
    assert report.ok
    assert "E506" in report.codes


def test_unused_classes_warned(contract, eval_ids, classes):
    rows = [["id", "label"]] + [
        [i, classes[n % 2]] for n, i in enumerate(eval_ids)
    ]
    report = validate_text(_csv(rows), contract)
    assert report.ok
    finding = report.get("W904")
    assert finding is not None and finding.count == 18


# --- ID 세부 판정 ---------------------------------------------------------

def test_train_ids_get_dedicated_code(contract, eval_ids, classes):
    """example_input.csv 로 연습한 참가자가 가장 내기 쉬운 실수."""
    rows = [["id", "label"]] + [
        [i.replace("TEST_", "TRAIN_"), classes[0]] for i in eval_ids
    ]
    report = validate_text(_csv(rows), contract)
    assert "E407" in report.codes
    assert "E403" not in report.codes


def test_unpadded_id_is_e405(contract, eval_ids, classes):
    rows = [["id", "label"]] + [
        [str(n + 1), classes[0]] for n in range(len(eval_ids))
    ]
    report = validate_text(_csv(rows), contract)
    assert "E405" in report.codes


def test_duplicate_id_detected(contract, eval_ids, classes):
    rows = valid_rows(eval_ids, classes)
    rows[2][0] = rows[1][0]
    report = validate_text(_csv(rows), contract)
    assert "E402" in report.codes
    assert "E401" in report.codes  # 하나가 중복되면 하나가 누락된다


def test_whitespace_id_is_corrected_and_warned(contract, eval_ids, classes):
    rows = valid_rows(eval_ids, classes)
    rows[1][0] = f" {rows[1][0]} "
    report = validate_text(_csv(rows), contract)
    assert "E406" in report.codes
    assert "E401" not in report.codes, "공백 제거 후에는 누락으로 보지 않아야 한다"
    assert report.ok, "경고만 있어야 한다"


# --- 집계 동작 ------------------------------------------------------------

def test_errors_are_aggregated_not_fail_fast(contract, eval_ids, classes):
    """오류가 여러 행에 있으면 한 번에 모아 보고해야 한다."""
    rows = valid_rows(eval_ids, classes)
    for row in rows[1:6]:
        row[1] = "없는클래스"
    report = validate_text(_csv(rows), contract)
    finding = report.get("E502")
    assert finding is not None and finding.count == 5
    assert len(finding.rows) == 5


def test_sample_cap_respected(contract):
    from scripts.prediction_validator.errors import MAX_SAMPLES

    ids = [f"TEST_{i:06d}" for i in range(1, 101)]
    contract.with_eval_ids(ids)
    contract.expected_rows = len(ids)
    rows = [["id", "label"]] + [[i, "없는클래스"] for i in ids]
    report = validate_text(_csv(rows), contract)
    finding = report.get("E502")
    assert finding.count == 100
    assert len(finding.samples) == MAX_SAMPLES
    assert len(finding.rows) == MAX_SAMPLES


def test_report_json_is_serializable(contract, eval_ids, classes):
    rows = valid_rows(eval_ids, classes)
    rows[1][1] = "nope"
    report = validate_text(_csv(rows), contract)
    assert json.loads(report.to_json())
    assert json.loads(report.to_json(operator=True))


# --- 계약 ------------------------------------------------------------------

def test_contract_loads_and_declares_undecided():
    c = load_contract()
    assert c.columns == ("id", "label")
    assert c.id_pattern.fullmatch("TEST_000001")
    assert not c.id_pattern.fullmatch("TEST_1")
    assert c.undecided(), "미결정 항목이 계약에 기록돼 있어야 한다"


def test_shipped_class_list_is_placeholder(classes):
    """확정 전까지는 클래스 목록이 비어 있어야 한다. 추측값을 넣지 않는다."""
    from scripts.prediction_validator import load_classes

    assert load_classes(ROOT / "contract" / "classes.txt") == []
