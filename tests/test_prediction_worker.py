"""채점 작업자 연동 표면 테스트.

docs/INTEGRATION.md 에 적은 호출 방식이 실제로 동작하는지 확인한다.
문서의 코드 조각이 그대로 돌아가야 한다.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from scripts.prediction_validator import validate_submission_output  # noqa: E402
from scripts.make_prediction_examples import DEV_CLASSES, dev_eval_ids  # noqa: E402

EXAMPLES = ROOT / "tests/fixtures/predictions"
CONTEXT_PATH = EXAMPLES / "CONTEXT.json"


def _context() -> dict:
    """예제를 만든 조건. make_examples.py 가 기록한다."""
    if CONTEXT_PATH.is_file():
        return json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
    return {"classes": DEV_CLASSES, "eval_ids": dev_eval_ids()}


CONTEXT = _context()
CLASSES = CONTEXT["classes"]
EVAL_IDS = CONTEXT["eval_ids"]


@pytest.fixture
def eval_ids_csv(tmp_path) -> Path:
    """평가 입력 파일을 모사한다. 정답 컬럼은 일부러 넣지 않는다."""
    path = tmp_path / "test.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "sequence"])
        for sample_id in EVAL_IDS:
            writer.writerow([sample_id, "MKVLAA"])
    return path


@pytest.fixture
def metadata_json(tmp_path) -> Path:
    path = tmp_path / "metadata.json"
    path.write_text(
        json.dumps({"schema_version": 2, "labels": CLASSES}),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def kw(eval_ids_csv, metadata_json) -> dict:
    return {"eval_ids_csv": eval_ids_csv, "classes_metadata": metadata_json}


def test_valid_submission_passes(kw):
    outcome = validate_submission_output(EXAMPLES / "valid/predictions.csv", **kw)
    assert outcome.ok
    assert not outcome.operator_fault
    assert outcome.error_codes == []
    assert "통과" in outcome.summary_line


def test_classes_read_from_metadata(kw):
    """metadata.json 의 labels 배열에서 클래스를 읽어야 한다."""
    outcome = validate_submission_output(EXAMPLES / "valid/predictions.csv", **kw)
    assert outcome.operator_detail["summary"]["classes_allowed"] == len(CLASSES)


def test_classes_read_from_train_csv(eval_ids_csv, tmp_path):
    """metadata.json 이 없으면 train.csv 의 label 고유값으로도 되어야 한다."""
    train = tmp_path / "train.csv"
    with train.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "sequence", "label"])
        for n, label in enumerate(CLASSES, start=1):
            writer.writerow([f"TRAIN_{n:06d}", "MKVL", label])

    outcome = validate_submission_output(
        EXAMPLES / "valid/predictions.csv",
        eval_ids_csv=eval_ids_csv,
        classes_train_csv=train,
    )
    assert outcome.ok, outcome.error_codes


def test_format_error_is_participant_fault(kw):
    outcome = validate_submission_output(EXAMPLES / "invalid/unknown_label.csv", **kw)
    assert not outcome.ok
    assert not outcome.operator_fault
    assert "E502" in outcome.error_codes
    assert "형식 오류" in outcome.summary_line


def test_missing_class_list_is_operator_fault(eval_ids_csv):
    """클래스 목록을 못 읽으면 참가자를 탓하지 않아야 한다."""
    outcome = validate_submission_output(
        EXAMPLES / "valid/predictions.csv",
        eval_ids_csv=eval_ids_csv,
    )
    assert not outcome.ok
    assert outcome.operator_fault
    assert "E901" in outcome.error_codes
    assert "채점기 설정 오류" in outcome.summary_line


def test_missing_eval_ids_is_operator_fault(metadata_json):
    outcome = validate_submission_output(
        EXAMPLES / "valid/predictions.csv",
        classes_metadata=metadata_json,
    )
    assert outcome.operator_fault
    assert "E902" in outcome.error_codes


def test_shipped_placeholder_classes_trigger_operator_fault(eval_ids_csv):
    """저장소에 들어 있는 플레이스홀더 목록으로는 채점을 시작할 수 없어야 한다."""
    outcome = validate_submission_output(
        EXAMPLES / "valid/predictions.csv",
        eval_ids_csv=eval_ids_csv,
        classes_file=ROOT / "contract" / "classes.txt",
    )
    assert outcome.operator_fault
    assert "E901" in outcome.error_codes


def test_participant_response_hides_eval_ids(kw):
    outcome = validate_submission_output(EXAMPLES / "invalid/missing_id.csv", **kw)
    assert "E401" in outcome.error_codes

    operator = json.dumps(outcome.operator_detail, ensure_ascii=False)
    participant = json.dumps(outcome.participant_response, ensure_ascii=False)

    leaked = [
        finding
        for finding in outcome.operator_detail["findings"]
        if finding["leaks_eval_set"]
    ]
    assert leaked, "E401 이 평가셋 노출 코드로 표시돼야 한다"
    for finding in leaked:
        for sample in finding["samples"]:
            assert sample in operator, "운영 로그에는 남아야 한다"
            assert sample not in participant, f"참가자 응답에 {sample} 가 노출됐다"


def test_warning_only_submission_is_scorable(kw):
    """경고만 있으면 채점으로 넘어가되 경고를 함께 보고해야 한다."""
    outcome = validate_submission_output(
        EXAMPLES / "invalid/whitespace_id.csv", **kw
    )
    assert outcome.ok
    assert "E406" in outcome.warning_codes
    assert "E406" in outcome.codes
    assert "경고" in outcome.summary_line


def test_integration_doc_example_loop(kw):
    """INTEGRATION.md 8절의 예제 순회 코드가 그대로 돌아야 한다."""
    expected = json.loads(
        (EXAMPLES / "EXPECTED.json").read_text(encoding="utf-8")
    )
    for name, want in expected.items():
        outcome = validate_submission_output(EXAMPLES / name, **kw)
        assert outcome.ok == want["ok"], (name, outcome.error_codes)
        if want["code"]:
            assert want["code"] in outcome.codes, (
                name, want["code"], outcome.codes,
            )


def test_outcome_is_json_serializable(kw):
    """DB 에 그대로 저장할 수 있어야 한다."""
    outcome = validate_submission_output(EXAMPLES / "invalid/row_count.csv", **kw)
    assert json.loads(json.dumps(outcome.participant_response, ensure_ascii=False))
    assert json.loads(json.dumps(outcome.operator_detail, ensure_ascii=False))


def test_validator_never_reads_answers(kw, tmp_path):
    """검증기는 정답 파일을 요구하지 않아야 한다.

    labels.csv 를 넘기지 않아도 정상 동작해야 한다. 정답은 점수 계산
    단계에만 필요하고, 검증기는 평가 ID 집합만 알면 된다.
    """
    outcome = validate_submission_output(EXAMPLES / "valid/predictions.csv", **kw)
    assert outcome.ok
    signature = validate_submission_output.__doc__ or ""
    assert "labels.csv" not in signature
