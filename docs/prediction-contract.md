# 예측 출력 계약 초안 (Day 1 산출물)

담당: 윤성 · 최초 기준일 2026-10-02 · 데이터 건수 갱신 2026-10-04 · 계약 버전 `0.2.0-draft`

이 문서는 **참가자 모델의 추론 결과 파일**이 지켜야 하는 형식과, 그것을 어기는
모든 경우를 정한다. 기계가 읽는 값은 `contract/prediction_contract.json` 에 있고
이 문서는 그 근거와 판단을 적는다. 둘이 어긋나면 JSON 이 기준이다.

## 1. 근거

추측하지 않고 데이터 저장소
[`2026-admin-ai-challenge/admin-2026-protein-data`](https://github.com/2026-admin-ai-challenge/admin-2026-protein-data)
커밋 `80c6405` 의 코드에서 직접 확인했다.

| 항목 | 확정값 | 근거 |
| --- | --- | --- |
| 출력 컬럼 | `id,label` (이 순서) | `scripts/baseline.py` — `pd.DataFrame({"id": ..., "label": ...}).to_csv(output, index=False)` |
| 평가 ID 형식 | `TEST_[0-9]{6}` (제외된 ID의 빈 번호를 허용; 실제 ID 목록은 test.csv 기준) | `scripts/prepare_dataset.py` |
| 학습 ID 형식 | `TRAIN_000001` … `TRAIN_021545` (`TRAIN_%06d`) | `scripts/prepare_dataset.py` |
| 라벨 의미 | CATH Architecture `C.A` 문자열 | `docs/starter-guide.md`, `prepare_dataset.py:40` — `df["class"] + "." + df.architecture` |
| 라벨 개수 | 20개 | `docs/dataset.md` |
| 평가 건수 | 5,330 (Public 1,599 / Private 3,731) | `docs/dataset.md` |
| 점수 | 허용 클래스 전체 대상 Macro F1, `zero_division=0` | `scripts/baseline.py` 의 `f1_score(..., average="macro")` |
| 분할 | 클래스별 Public 30 / Private 70 seeded shuffle | `docs/dataset.md` |

## 2. 출력 파일 형식

```
id,label
TEST_000001,3.30
TEST_000002,1.10
...
```

평가 ID는 `TEST_` + 6자리지만 **연속이 아니다.** 데이터 정제에서 제외된 샘플의
번호가 공백으로 남는다(2026-10-08 기준 5,330건, 최대 번호 `TEST_005384`).
번호를 직접 만들지 말고 평가 입력 파일의 `id` 를 그대로 쓴다.

- UTF-8 텍스트 CSV. 쉼표 구분. 헤더 필수.
- 첫 줄은 정확히 `id,label`. 대소문자·철자·순서까지 일치해야 한다.
- 추가 컬럼 금지. 확률·점수 컬럼은 현재 계약에서 받지 않는다 (미결정 `open_2`).
- 평가 입력의 모든 ID가 **정확히 한 번씩** 있어야 한다. 누락·중복·초과 모두 거절.
- 라벨은 허용 클래스 20개 문자열 중 하나. 빈 값·결측 표현 금지.
- 줄바꿈은 LF/CRLF 모두 허용. BOM 은 경고만 내고 통과시킨다.
- 파일 크기 상한은 임시로 10 MiB. 5,330행 × 약 18바이트면 100 KiB 미만이다.

## 3. 이 데이터셋에서 특히 조심할 실패 두 가지

### 3.1 `label` 을 숫자로 읽어 끝자리 0이 사라지는 경우 → `E507`

라벨이 `"1.10"`, `"2.60"` 처럼 **숫자로 보이는 문자열**이다. `dtype=str` 없이
읽으면 pandas 가 float 으로 바꿔 `1.1` 이 되고, 저장하면 `"1.1"` 이 된다.
`"1.1"` 과 `"1.10"` 은 서로 다른 클래스다. 점수가 0에 가깝게 나오는데
형식 오류로는 안 보이는, 가장 찾기 어려운 실패다.

`docs/starter-guide.md` 가 이미 "`label`은 반드시 문자열로 읽으세요 (`dtype=str`)"
라고 경고하는 것도 이 때문이다. 검증기는 이 경우를 `E502`(알 수 없는 라벨)로
뭉개지 않고 `E507` 로 따로 짚고 원래 값까지 알려준다.

### 3.2 예제 입력으로 연습한 뒤 그대로 제출하는 경우 → `E407`

`example_input.csv` 는 학습 데이터에서 복사한 3건이라 ID가 `TRAIN_` 으로
시작한다 (`prepare_dataset.py` 의 `make_example`). 추론 코드가 평가 입력 대신
예제 입력 경로를 읽으면 예측 ID가 전부 `TRAIN_...` 이 된다. 이때
"평가 입력에 없는 ID"라고만 말하면 참가자가 원인을 찾기 어렵다.
전용 코드와 안내문을 둔다.

## 4. 오류 등급

| 등급 | 뜻 | 채점 작업자 동작 |
| --- | --- | --- |
| `error` | 채점할 수 없다 | 점수 계산하지 않고 제출을 실패로 기록 |
| `warning` | 채점 가능하지만 참가자가 알아야 한다 | 점수 계산 진행, 경고를 함께 기록 |

`E901`·`E902`·`E903` 은 **운영 측 설정 오류**다. 참가자 잘못이 아니므로
`ValidationOutcome.operator_fault` 가 `True` 이고, 제출 횟수 차감에서 반드시
제외해야 한다. 형식 오류를 차감하지 않는 것은 확정됐지만(웹 저장소 PR #6),
운영 측 오류는 그와 별개로 어떤 정책에서도 차감 대상이 아니다. 전체 코드 표는 [ERROR_CODES.md](prediction-errors.md) 에 있다.

## 5. 설계상 지킨 세 가지

**첫 오류에서 멈추지 않는다.** 팀당 제출이 대회 전체 20회로 한정돼 있다.
한 번 실패할 때마다 고칠 거리를 최대한 돌려줘야 한다. 모든 행을 끝까지 보고
코드별로 모아서 보고하되, 예시는 코드당 20건으로 제한해 5,330행짜리
응답이 되지 않게 한다.

**숨김 평가 ID를 참가자에게 흘리지 않는다.** `docs/dataset.md` 가 적어 둔 대로
CATH 원본이 공개 자료여서 평가 ID·서열이 노출되면 정답 역추적이 쉬워진다.
그래서 **누락 ID(`E401`)는 개수만 알려주고 실제 ID는 운영 로그에만 남긴다.**

처음에는 "참가자가 보낸 값은 자기가 쓴 것이라 되돌려 줘도 안전하다"고 보고
알 수 없는 ID·잘못된 라벨을 그대로 응답에 담았다. **이 판단을 바꿨다.**
참가자 코드는 숨김 평가 입력을 읽은 뒤 예측 파일을 만든다. 즉 평가 데이터에서
뽑은 내용을 라벨 칸에 담아 두면 그 값이 응답으로 되돌아온다. 웹 저장소의
`app/scoring/predictions.py` 가 같은 결론에 먼저 도달했고, 거기에 맞춰
`participant_payload()` 의 기본값을 strict 로 바꿨다. 예측 파일에서 온 값
(`rows`·`samples`)은 기본적으로 내보내지 않는다.

**대신 `hint`(조치 안내)는 반드시 내보낸다.** 이 모듈에 박힌 고정 문자열이라
참가자 데이터도 평가 데이터도 흘러들어갈 수 없다. 이게 빠지면 참가자는 무엇이
틀렸는지만 알고 어떻게 고치는지는 모르게 되어, 한정된 제출 기회를 그만큼 더
쓴다. 작업자가 메시지를 직접 조립하다 빠뜨리지 않도록
`Report.participant_lines()` 로 조립 방식을 한 곳에 뒀다.

**표준 라이브러리만 쓴다.** 형식 검증기는 pandas 로 만들면 안 된다. pandas 는
형식 오류를 조용히 교정한다 — 바로 3.1 의 `"1.10" → 1.1` 이 그 예다.
`csv` 모듈로 원문을 그대로 읽어야 어긴 것을 어겼다고 판정할 수 있다.
부수 효과로 채점 작업자가 pandas 버전에 상관없이 같은 판정을 내린다.

## 6. 아직 확정되지 않은 것

여기 있는 값을 임의로 확정하지 않는다. 계약 JSON 의 `undecided` 블록과 같은 내용이다.

| 키 | 질문 | 영향 |
| --- | --- | --- |
| `Q2` | 채점 컨테이너의 출력 경로·파일명 | `output.path` 가 임시값 `output/predictions.csv` |
| ~~`Q4`~~ | ~~형식 오류를 차감할지~~ | **확정**: 차감하지 않음 (웹 PR #6). 운영 측 오류도 제외 |
| ~~`Q8`~~ | ~~20개 클래스 문자열 확정~~ | **확보**: `metadata.json` 의 `labels` 를 주입해 사용 |
| `open_1` | CSV 외 형식 허용 여부 | 현재 CSV 단일로 가정 |
| `open_2` | 확률·점수 컬럼 허용 여부 | 현재 `label` 단일 컬럼만 허용 |
| `open_3` | 출력 디렉터리에 다른 산출물 허용 여부 | 현재 검사하지 않음 |

### 클래스 목록을 코드에 넣지 않은 이유

실제 20개 문자열은 데이터셋 산출물(`data/public/metadata.json` 의 `labels`)
안에만 있다. 추측해서 적으면 틀렸을 때 **모든 제출을 오판정**하므로,
검증기는 클래스 목록을 런타임에 주입받고 주입이 없으면 참가자 파일을
탓하지 않고 `E901`(운영 측 설정 오류)로 보고한다.
`contract/classes.txt` 는 의도적으로 플레이스홀더 상태이며, 그 상태가
유지되는지 테스트(`test_shipped_class_list_is_placeholder`)가 지키고 있다.

### 문서 간 상충 (운영진 확인 필요)

| | 디렉팅 문서 | 팀별 과제 문서 / 6일 계획 |
| --- | --- | --- |
| 제출 ZIP 압축 크기 | "초기 제안 **200 MiB**", 해제 후 500 MiB 별도 | "**확정** 압축 ZIP 최대 500 MB" |
| ZIP 구성 | `inference.py` / `model/` / `submission.json` | `inference.py` / `requirements.txt` / `model/` |

ZIP 구성은 특히 확인이 필요하다. 공통 패키지 문서가 "제출 시 새로운 패키지를
자동 설치하지 않습니다"라고 했으므로 `requirements.txt` 를 받더라도 설치하지
않는 참고 파일이다. 그렇다면 필수로 둘 이유가 있는지, `submission.json` 과
둘 중 무엇이 진짜 필수인지 정해야 한다.

## 7. 데이터셋이 바뀔 때 함께 고칠 것

데이터셋은 품질 점검 결과에 따라 재생성된다(PR #5, #11, #13). 재생성되면
평가 건수와 평가 ID 집합이 바뀌므로 아래를 함께 맞춘다.

| 바뀌는 것 | 고칠 곳 |
| --- | --- |
| 평가 건수 | `contract/prediction_contract.json` 의 `output.expected_rows` |
| 평가 ID 집합 | 예제 재생성 (아래 명령) |
| 클래스 목록 | 코드에 없음. `metadata.json` 에서 읽으므로 자동 반영 |

```powershell
python scripts/make_prediction_examples.py --eval-ids data/private/test.csv `
    --classes-metadata data/public/metadata.json
pytest -q tests/test_predictions.py tests/test_prediction_worker.py
```

빠뜨려도 조용히 넘어가지 않게 두 겹으로 막아 둔다.

- `tests/test_predictions.py::test_shipped_contract_matches_dataset` 가 CI 에서
  계약과 실제 평가 입력 건수를 비교한다.
- 그래도 새면 채점 중에 `E903`(계약·데이터셋 어긋남)이 **참가자 파일을 보기
  전에** 운영 측 오류로 멈춘다. 어긋난 계약으로 내린 판정은 신뢰할 수 없다.

### 다른 저장소의 계약 사본

웹 저장소가 검증기와 계약을 복사해서 쓴다
(`apps/api/prediction_validator/`, `apps/api/contract/prediction_contract.json`).
**이 저장소가 원본이다.** 여기서 고친 뒤 양쪽 경로를 다시 복사하고 웹 쪽
`prediction_validator/README.md` 의 기준 커밋을 고친다.

사본이 낡으면 `expected_rows` 가 실제 데이터와 어긋나므로 위의 `E903` 이
채점 시점에 잡아낸다. 2026-10-08 점검에서 실제로 어긋난 상태를 발견했다
(사본 5,387 / 실제 5,330).
