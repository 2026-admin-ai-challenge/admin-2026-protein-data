# 채점 작업자 연동 안내 (Day 4 산출물)

대상: 웹·운영 API 팀 (채점 작업자 담당) · 담당: 윤성 · 계약 버전 `0.2.0-draft`

검증기는 **점수를 계산하기 전에** 참가자 모델의 추론 결과가 계약을 지켰는지
확인한다. 점수 계산은 이 검증을 통과한 뒤에만 한다.

## 1. 파이프라인에서의 위치

```
제출 ZIP 접수 → 대기열 → 격리 컨테이너에서 추론 (최대 10분)
                                  ↓  예측 파일만 꺼냄
                         ★ 예측 출력 검증  ← 이 패키지
                                  ↓  통과한 경우에만
                      정답 대조 · Public/Private 점수 계산
                                  ↓
                            DB · 리더보드 갱신
```

**검증기는 컨테이너 밖, 신뢰된 채점기 쪽에서 실행한다.** 허용 클래스 목록과
평가 ID 목록을 읽어야 하는데, 그 파일들을 추론 컨테이너에 넣으면 안 된다
(`ADMIN_대회_개발_디렉팅.md` 4절). 컨테이너에는 평가 입력만 읽기 전용으로 준다.

검증기는 **정답(`labels.csv` 의 `label`)을 읽지 않는다.** 평가 ID 목록만
필요하므로 `data/private/test.csv` 의 `id` 컬럼으로 충분하다. 정답 파일은
점수 계산 단계에만 넘기면 된다.

## 2. 설치

의존성이 없다. 표준 라이브러리만 쓴다 (Python 3.12 기준으로 작성, 3.14 에서도 동작 확인).

```powershell
# 작업자 저장소에 복사하거나
Copy-Item -Recurse scripts/prediction_validator <worker>/
Copy-Item -Recurse contract <worker>/contract

# 또는 경로를 추가해서 import
$env:PYTHONPATH = "prediction-validator/src"
```

## 3. 호출 방법

함수 하나만 쓰면 된다.

```python
from prediction_validator import validate_submission_output

outcome = validate_submission_output(
    prediction_path=container_output / "predictions.csv",
    eval_ids_csv=PRIVATE_ROOT / "test.csv",          # id 컬럼만 사용, 정답 아님
    classes_metadata=PUBLIC_ROOT / "metadata.json",  # labels 배열에서 클래스 읽음
)
```

### 반환값 `ValidationOutcome`

| 필드 | 용도 |
| --- | --- |
| `ok` | `True` 면 채점 단계로 넘긴다 |
| `operator_fault` | `True` 면 **운영 측 설정 오류**다. 제출 횟수를 차감하지 않고 재시도 |
| `participant_response` | 참가자에게 보낼 dict. 그대로 JSON 응답에 넣어도 된다 |
| `operator_detail` | 운영 로그 전용. 누락된 평가 ID가 들어 있다 |
| `error_codes` | `["E401", "E302"]` 같은 코드 목록. DB 인덱싱·집계용 |
| `summary_line` | DB `status_message` 한 줄용 요약 |

### 분기 예시

```python
outcome = validate_submission_output(...)

logger.info("submission=%s %s", submission_id, outcome.summary_line)
db.save_validation_detail(submission_id, outcome.operator_detail)   # 운영 로그

if outcome.operator_fault:
    # E901/E902 — 클래스 목록·평가 ID를 채점기가 못 읽었다.
    # 참가자 잘못이 아니므로 횟수를 돌려주고 다시 대기열에 넣는다.
    db.requeue(submission_id, reason=outcome.error_codes)
    alert_operators(outcome.operator_detail)
    return

if not outcome.ok:
    db.mark_failed(
        submission_id,
        codes=outcome.error_codes,
        response=outcome.participant_response,    # 참가자에게 보이는 부분
    )
    return

public, private = score(outcome, labels_csv=PRIVATE_ROOT / "labels.csv")
db.save_scores(submission_id, public=public, private=private,
               warnings=outcome.participant_response["warnings"])
```

## 4. 참가자에게 보여줄 것과 보여주지 말 것

**반드시 `participant_response` 만 참가자에게 보낸다.**

`operator_detail` 에는 `E401`(누락 ID)의 실제 평가 ID 예시가 들어 있다.
CATH 원본이 공개 자료여서 평가 ID가 노출되면 정답 역추적이 쉬워진다
(데이터 저장소 `docs/dataset.md` 의 경고). `participant_response` 는
`leaks_eval_set=True` 인 코드의 예시·행번호를 자동으로 제거하고 개수만 남긴다.

같은 파일에 대한 두 응답을 비교하면 차이가 보인다.

```json
// participant_response — 개수만
{ "code": "E401", "count": 1,
  "message": "평가 입력에 있는 ID가 예측에 빠졌습니다.", "hint": "..." }

// operator_detail — 실제 ID 포함
{ "code": "E401", "count": 1, "samples": ["TEST_000024"],
  "leaks_eval_set": true }
```

반대로 참가자가 **보낸** 값(알 수 없는 ID, 잘못된 라벨)은 그대로 되돌려 준다.
자기가 쓴 값이라 노출 위험이 없고, 그게 있어야 고칠 수 있다.

## 5. 제출 횟수 차감 (Q4 와 연결)

미결정 사항 Q4("형식 오류·실행 실패·시간 초과를 10회에 포함할까")가
확정되기 전이라도, **운영 측 설정 오류는 어떤 정책에서도 차감 대상이 아니다.**
`operator_fault` 로 그 구분을 코드에서 제공하므로, Q4 가 어떻게 정해지든
작업자 쪽 분기는 위 예시 그대로 두면 된다.

## 6. 점수 계약과의 접점

검증 통과 후 점수 계산은 데이터 저장소 `scripts/baseline.py` 와 같은 방식이어야 한다.

```python
from sklearn.metrics import f1_score

f1_score(y_true, y_pred, labels=sorted(all_allowed_classes),
         average="macro", zero_division=0)
```

`labels=` 에 **허용 클래스 전체**를 넘기는 것이 중요하다. 참가자가 예측하지
않은 클래스도 분모에 들어가야 Macro F1 이 팀 간 비교 가능하다. 검증기는
예측에 쓰이지 않은 클래스를 `W904` 경고로 알려주지만 실패로 보지는 않는다.

Public/Private 분리는 `data/private/labels.csv` 의 `partition` 컬럼을 쓴다.
참가자에게는 Public 점수만 보여준다.

## 7. 명령줄로 확인하기

연동 전 수동 점검이나 CI 에서 쓸 수 있다.

```powershell
python scripts/verify_predictions.py predictions.csv `
    --eval-ids data/private/test.csv `
    --classes-metadata data/public/metadata.json

python scripts/verify_predictions.py predictions.csv ... --json            # 참가자 응답
python scripts/verify_predictions.py predictions.csv ... --json --operator # 운영 상세
python scripts/verify_predictions.py --list-codes                          # 코드 표
```

| 종료 코드 | 뜻 |
| --- | --- |
| 0 | 통과 (경고는 있을 수 있음) |
| 1 | 참가자 출력 형식 오류 |
| 2 | 채점기 설정 오류 — 운영 측 조치 필요 |
| 3 | 사용법 오류 |

## 8. Day 5 연동 시험에 쓸 예제

`tests/fixtures/predictions/` 에 예제 30건이 있고 `tests/fixtures/predictions/EXPECTED.json` 이 각 파일의 기대
결과를 담고 있다. 항목마다 `code`(반드시 나와야 하는 코드)와 `ok`(채점
단계로 넘어가야 하는지)가 있다. 경고만 나는 예제는 `code` 가 있으면서
`ok: true` 다.

```json
{
  "valid/predictions.csv":        { "code": null,   "ok": true  },
  "valid/predictions_bom.csv":    { "code": "W903", "ok": true  },
  "invalid/whitespace_id.csv":    { "code": "E406", "ok": true  },
  "invalid/label_float_truncated.csv": { "code": "E507", "ok": false }
}
```

작업자에 넣어 기대한 결과가 나오는지 확인하면 연동이 끝난다.

```python
import json
expected = json.loads((EXAMPLES / "EXPECTED.json").read_text(encoding="utf-8"))

for name, want in expected.items():
    outcome = validate_submission_output(EXAMPLES / name, ...)
    assert outcome.ok == want["ok"], (name, outcome.error_codes)
    if want["code"]:
        assert want["code"] in outcome.codes, (name, want["code"], outcome.codes)
```

`outcome.codes` 는 오류와 경고를 합친 목록이고, `outcome.error_codes` 는
오류만이다. 통과/실패 판정은 `outcome.ok` 로 본다.

이 순회는 `tests/test_worker_api.py::test_integration_doc_example_loop` 로
테스트에 들어 있어, 문서와 코드가 어긋나면 테스트가 깨진다.

현재 예제는 개발용 픽스처(평가 ID 24건·클래스 20개 자리값)로 만들어져 있다.
실제 데이터셋이 손에 들어오면 아래로 다시 만든다.

```powershell
python scripts/make_prediction_examples.py --eval-ids data/private/test.csv `
    --classes-metadata data/public/metadata.json
```

## 9. 지금 막혀 있는 것

- **데이터셋 릴리스에 첨부 파일이 0개다.** `dataset-2026-10-02` 릴리스가
  약속한 `admin-dataset-2026-10-02.zip` 이 올라와 있지 않아, 실제 클래스
  문자열 20개와 평가 ID 5,393건을 확인하지 못했다. 검증기는 둘 다 주입받는
  구조라 코드는 완성 상태다.
- **출력 경로·파일명이 미정이다 (Q2).** 현재 계약은 `output/predictions.csv`
  를 임시값으로 둔다. 확정되면 `contract/prediction_contract.json` 의
  `output.path` 한 줄만 바꾸면 된다. 작업자 쪽 호출 코드는 경로를 인자로
  받으므로 영향이 없다.
