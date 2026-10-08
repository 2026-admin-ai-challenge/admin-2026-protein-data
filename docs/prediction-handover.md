# 예측 검증기 인계 (Day 6)

담당: 윤성 · 2026-10-08 · 계약 `0.3.0-draft` · 데이터 버전 `23760e7`

6일 계획의 예측 검증 항목을 마무리하고 넘긴다. 이 문서 하나로 "무엇이 있고,
누가 뭘 하고, 뭐가 바뀌면 뭘 고치는지" 를 알 수 있게 썼다.

## 1. 무엇을 하는 코드인가

참가자 모델이 채점 컨테이너에서 낸 답안 파일(`id,label` CSV)이 제출 계약을
지켰는지 **점수 계산 전에** 판정한다.

```
참가자 제출 → 격리 컨테이너 추론 → ★ 검증기 → 정답 대조·점수 → 리더보드
```

안 걸러내면 컬럼 하나 틀린 답안이 그대로 채점으로 가서 점수가 0이 된다.
참가자는 원인을 모르고 제출 기회를 쓴다. 그래서 "무엇이 틀렸고 어떻게 고치는지"
를 돌려주는 것이 이 코드의 목적이다.

## 2. 파일 어디 있나

| 경로 | 내용 |
| --- | --- |
| `scripts/prediction_validator/` | 검증기 본체. 의존성 없음(표준 라이브러리만) |
| `scripts/verify_predictions.py` | 명령줄 진입점 |
| `scripts/make_prediction_examples.py` | 예제 생성 |
| `scripts/make_prediction_error_docs.py` | 오류 코드 표 생성 |
| `contract/prediction_contract.json` | 계약 값. **기계가 읽는 단일 출처** |
| `docs/prediction-contract.md` | 답안 규격과 근거 |
| `docs/prediction-errors.md` | 오류 코드 33개 표 (코드에서 생성) |
| `docs/prediction-integration.md` | 채점 작업자 연동 안내 |
| `docs/prediction-integration-test.md` | Day 5 연동 시험 결과 |
| `tests/test_predictions.py` | 검증 로직 테스트 |
| `tests/test_prediction_worker.py` | 작업자 연동 표면 테스트 |
| `tests/fixtures/predictions/` | 정상·오류 예제 30건 |

```bash
pytest -q tests/test_predictions.py tests/test_prediction_worker.py   # 51 passed
python scripts/verify_predictions.py --list-codes                      # 코드 33개
```

## 3. 현재 상태

| 항목 | 상태 |
| --- | --- |
| 실데이터 검증 | 완료. 클래스 20개·평가 ID 5,330건 주입해 전체 통과 |
| 채점 작업자 연동 | 완료. 웹 저장소가 채택, 예제 30건 전부 기대대로 판정 |
| 계약 확정 | 출력 형식·ID·라벨·점수 확정. 출력 **경로**는 미정(Q2) |
| 테스트 | 데이터 51개 + 웹 41개 통과 |

## 4. 바뀌면 고쳐야 하는 것 — 여기만 보면 된다

### 데이터셋이 재생성되면

평가 건수와 평가 ID 집합이 바뀐다. 두 가지를 한다.

```powershell
# 1. 계약의 expected_rows 를 새 건수로
#    contract/prediction_contract.json → output.expected_rows

# 2. 예제 재생성
python scripts/make_prediction_examples.py --eval-ids data/private/test.csv `
    --classes-metadata data/public/metadata.json

pytest -q tests/test_predictions.py tests/test_prediction_worker.py
```

클래스 목록은 코드에 없다. `metadata.json` 에서 읽으므로 자동으로 따라간다.

빠뜨려도 조용히 넘어가지 않게 두 겹으로 막았다.

- CI: `test_shipped_contract_matches_dataset` 가 계약과 실제 건수를 비교한다
- 런타임: 작업자 시작 시 `verify_contract_against_dataset()` 가 `E903` 으로 멈춘다

### 오류 코드를 고치면

`docs/prediction-errors.md` 는 손으로 쓰지 않는다. `errors.py` 의 `SPECS` 를
고친 뒤 생성한다.

```bash
python scripts/make_prediction_error_docs.py
```

### 출력 경로(Q2)가 확정되면

`contract/prediction_contract.json` 의 `output.path` 한 줄. 작업자 호출 코드는
경로를 인자로 받으므로 영향 없다.

## 5. 다른 저장소의 사본 — 제일 조심할 것

웹 저장소가 검증기와 계약을 **복사해서** 쓴다.

```
admin-2026-protein-structure-challenge/
├── apps/api/prediction_validator/              ← scripts/prediction_validator/
└── apps/api/contract/prediction_contract.json  ← contract/prediction_contract.json
```

**이 저장소가 원본이다.** 여기서 고친 뒤 두 경로를 다시 복사하고, 웹 쪽
`apps/api/prediction_validator/README.md` 의 기준 커밋을 고친다.

2026-10-08 점검에서 계약 사본이 낡아 있었다(사본 5,387 / 실제 5,330). 코드
6개 파일은 동일했다. 그래서 `E903` 과 시작 시점 검사를 만들었다.

> 장기적으로는 복사 대신 한 곳에서 가져가는 방식이 낫다. 팀별 과제 문서가
> "격리 작업자를 별도 저장소로 뺄지는 나중에 결정"으로 남겨 둔 항목과 함께
> 정리하는 것이 맞다고 본다.

## 6. 참가자에게 무엇을 보여주는가 — 정책

**보여주는 것:** 오류 코드, 메시지, 건수, **조치 안내(`hint`)**

**보여주지 않는 것:** 예측 파일에서 온 값(`rows`·`samples`), 누락된 평가 ID

이유: 참가자 코드는 숨김 평가 입력을 읽은 뒤 예측 파일을 만든다. 즉 평가
데이터에서 뽑은 내용을 라벨 칸에 담아 두면 그 값이 응답으로 되돌아온다.
CATH 원본이 공개 자료라 평가 ID·서열이 노출되면 정답 역추적이 쉬워진다
(`docs/dataset.md` 의 경고).

`hint` 는 예외로 반드시 보여준다. 검증기에 박힌 고정 문자열이라 어떤 데이터도
흘러들어가지 않고, 참가자가 제출을 덜 버리게 한다. 작업자가 메시지를 조립하다
빠뜨리지 않도록 `Report.participant_lines()` 로 조립 방식을 한 곳에 뒀다.

```python
if outcome.operator_fault:
    requeue(submission_id)                      # 운영 측 오류: 차감 없음
elif not outcome.ok:
    fail(submission_id, outcome.participant_lines)
else:
    score(outcome)
```

## 7. 이 데이터셋에서 특히 조심할 실패 두 개

### `E507` — 라벨을 숫자로 읽어 끝자리 0이 사라지는 것

클래스 20개 중 **19개가 0으로 끝난다**(`1.25` 만 예외). `dtype=str` 없이 읽으면
`1.10` 이 `1.1` 이 되어 다른 클래스가 된다. 실제 평가 입력으로 재현하니 5,330행
대부분이 조용히 바뀌었다. 형식은 멀쩡해 보이고 점수만 떨어지는 실패다.

**참가자 안내문에 굵게 써야 한다.** 검증기가 잡아주지만 제출 기회를 한 번 쓴다.

### `E407` — 예제 입력으로 연습한 결과를 그대로 제출하는 것

`example_input.csv` 가 학습 데이터 복사본이라 ID가 `TRAIN_` 으로 시작한다.

## 8. 남은 미결정 사항

| 항목 | 현재 |
| --- | --- |
| 출력 경로·파일명 (Q2) | `output/predictions.csv` 임시값 |
| 확률·점수 컬럼 허용 | 현재 `label` 단일 컬럼만 |
| CSV 외 형식 허용 | 현재 CSV 단일 가정 |
| 출력 디렉터리의 다른 산출물 | 검사하지 않음 |

확정된 것은 계약 JSON 의 `decided` 블록에 있다. 제출 20회, 형식 오류 미차감,
클래스 목록 확보, 데이터셋 저장소 배치.

## 9. 넘겨받는 사람이 알아야 할 판단 네 가지

코드를 고칠 때 이 네 가지를 깨지 않도록 한다. 테스트가 지키고 있다.

1. **pandas 를 쓰지 않는다.** 형식 오류를 조용히 교정하므로 형식 검증기로는
   적합하지 않다. `E507` 이 바로 그 예다. 부수 효과로 작업자가 pandas 버전에
   상관없이 같은 판정을 낸다.
2. **첫 오류에서 멈추지 않는다.** 제출이 20회로 한정돼 있으므로 한 번의 실패
   응답에 고칠 거리를 최대한 담는다. 코드당 예시는 20건으로 제한한다.
3. **미확정 값을 추측해 넣지 않는다.** 클래스 목록을 코드에 박지 않은 이유다.
   틀린 목록을 넣으면 모든 제출을 오판정한다.
4. **설정 검사와 제출 검사를 섞지 않는다.** 계약·데이터셋 어긋남을 제출 경로에
   넣었다가 웹팀 테스트를 전부 깨뜨렸다(Day 5 에서 발견). 어긋남은 설정의
   성질이라 시작 시점에 본다.
