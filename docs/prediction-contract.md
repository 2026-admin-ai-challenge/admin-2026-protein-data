# 예측 출력 계약 초안 (Day 1 산출물)

담당: 윤성 · 기준일 2026-10-02 · 계약 버전 `0.2.0-draft`

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
| 평가 ID 형식 | `TEST_000001` … `TEST_005393` (`TEST_%06d`) | `scripts/prepare_dataset.py:70` |
| 학습 ID 형식 | `TRAIN_000001` … `TRAIN_021568` (`TRAIN_%06d`) | `scripts/prepare_dataset.py:69` |
| 라벨 의미 | CATH Architecture `C.A` 문자열 | `docs/starter-guide.md`, `prepare_dataset.py:40` — `df["class"] + "." + df.architecture` |
| 라벨 개수 | 20개 | `docs/dataset.md` |
| 평가 건수 | 5,393 (Public 1,618 / Private 3,775) | `docs/dataset.md` |
| 점수 | 허용 클래스 전체 대상 Macro F1, `zero_division=0` | `scripts/baseline.py` 의 `f1_score(..., average="macro")` |
| 분할 | 클래스별 Public 30 / Private 70 seeded shuffle | `docs/dataset.md` |

## 2. 출력 파일 형식

```
id,label
TEST_000001,3.30
TEST_000002,1.10
...
TEST_005393,2.40
```

- UTF-8 텍스트 CSV. 쉼표 구분. 헤더 필수.
- 첫 줄은 정확히 `id,label`. 대소문자·철자·순서까지 일치해야 한다.
- 추가 컬럼 금지. 확률·점수 컬럼은 현재 계약에서 받지 않는다 (미결정 `open_2`).
- 평가 입력의 모든 ID가 **정확히 한 번씩** 있어야 한다. 누락·중복·초과 모두 거절.
- 라벨은 허용 클래스 20개 문자열 중 하나. 빈 값·결측 표현 금지.
- 줄바꿈은 LF/CRLF 모두 허용. BOM 은 경고만 내고 통과시킨다.
- 파일 크기 상한은 임시로 10 MiB. 5,393행 × 약 18바이트면 100 KiB 미만이다.

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

`E901`·`E902` 는 **운영 측 설정 오류**다. 참가자 잘못이 아니므로
`ValidationOutcome.operator_fault` 가 `True` 이고, 제출 횟수 차감 정책(Q4)에서
반드시 제외해야 한다. 전체 코드 표는 [ERROR_CODES.md](prediction-errors.md) 에 있다.

## 5. 설계상 지킨 세 가지

**첫 오류에서 멈추지 않는다.** 팀당 제출이 대회 전체 10회뿐이다. 한 번
실패할 때마다 고칠 거리를 최대한 돌려줘야 한다. 모든 행을 끝까지 보고
코드별로 모아서 보고하되, 예시는 코드당 20건으로 제한해 5,393행짜리
응답이 되지 않게 한다.

**숨김 평가 ID를 참가자에게 흘리지 않는다.** `docs/dataset.md` 가 적어 둔 대로
CATH 원본이 공개 자료여서 평가 ID·서열이 노출되면 정답 역추적이 쉬워진다.
그래서 **누락 ID(`E401`)는 개수만 알려주고 실제 ID는 운영 로그에만 남긴다.**
반대로 참가자가 보낸 값(알 수 없는 ID, 잘못된 라벨)은 그대로 되돌려 준다.
자기가 쓴 값이라 노출 위험이 없고, 그게 있어야 고칠 수 있다.

**표준 라이브러리만 쓴다.** 형식 검증기는 pandas 로 만들면 안 된다. pandas 는
형식 오류를 조용히 교정한다 — 바로 3.1 의 `"1.10" → 1.1` 이 그 예다.
`csv` 모듈로 원문을 그대로 읽어야 어긴 것을 어겼다고 판정할 수 있다.
부수 효과로 채점 작업자가 pandas 버전에 상관없이 같은 판정을 내린다.

## 6. 아직 확정되지 않은 것

여기 있는 값을 임의로 확정하지 않는다. 계약 JSON 의 `undecided` 블록과 같은 내용이다.

| 키 | 질문 | 영향 |
| --- | --- | --- |
| `Q2` | 채점 컨테이너의 출력 경로·파일명 | `output.path` 가 임시값 `output/predictions.csv` |
| `Q4` | 형식 오류를 10회에 차감할지 | 운영 측 오류(`E901`/`E902`) 제외 처리 필요 |
| `Q8` | 20개 클래스 문자열 확정 | 클래스 목록을 코드에 넣지 못함 (아래 참조) |
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

## 7. 데이터 의존성 (현재 막힌 지점)

릴리스 [`dataset-2026-10-02`](https://github.com/2026-admin-ai-challenge/admin-2026-protein-data/releases/tag/dataset-2026-10-02)
의 **첨부 파일이 0개**다. README 와 릴리스 노트가 약속한
`admin-dataset-2026-10-02.zip` (82,257,921 bytes, SHA-256 `a9a29937...`) 이
업로드되지 않았다. `gh api .../releases/tags/dataset-2026-10-02` 의 `assets` 가
빈 배열이다.

그래서 실제 20개 클래스 문자열과 5,393개 평가 ID를 확보하지 못했다.
검증기는 그 둘을 주입받는 구조라 **코드·테스트·예제는 완성 상태**이고,
파일이 올라오면 다음 두 줄로 실제 데이터에 붙는다.

```powershell
python scripts/make_prediction_examples.py --eval-ids data/private/test.csv `
    --classes-metadata data/public/metadata.json
```

호성에게 요청: 릴리스에 ZIP 을 다시 올리거나, 최소한
`data/public/metadata.json` 과 `data/private/test.csv` 의 `id` 컬럼만이라도
먼저 공유해 주면 Day 2 실데이터 검증을 시작할 수 있다.
