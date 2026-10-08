# 예측 검증기 연동 시험 결과 (Day 5)

담당: 윤성 · 시행일 2026-10-08 · 데이터 버전 `23760e7` (PR #13)

웹 저장소 `admin-2026-protein-structure-challenge` 의 채점 작업자에 검증기를
넣어 정상·오류 예측이 기대한 판정을 받는지 확인했다.

## 연동 지점

웹팀이 검증기를 복사해 채택했다. 호출 경로는 이렇다.

```
worker.py
  └─ app/scoring/predictions.py :: check(content, ids, classes)
       └─ prediction_validator :: validate_submission_output(...)
```

`worker.py:91` 이 `operator_fault` 로 분기해 운영 측 오류를 팀 책임에서 제외한다.
설계 의도대로 쓰이고 있다.

## 시험 1 — 예제 30건을 작업자에 직접 투입

`tests/fixtures/predictions/` 의 예제를 `check()` 에 그대로 넣고
`EXPECTED.json` 과 비교했다.

```
예제 30건 → 기대대로 30건
참가자 메시지에 예측 파일 값 노출 없음
```

통과해야 하는 5건은 통과했고, 실패해야 하는 25건은 각자의 코드를 냈다.
참가자에게 가는 메시지에 `TEST_999999`·`없는클래스` 같은 예측 파일 값이
섞이지 않는 것도 함께 확인했다.

## 시험 2 — 웹 저장소 테스트 전체

```
tests/test_scoring.py, tests/test_diagnostics.py, tests/test_worker.py
41 passed
```

웹팀이 이미 검증기 연동 테스트를 꼼꼼히 써 뒀다. `E402`·`E401`·`E403`·`E502`
·`E501`·`E203`·`E301`·`E507`·`E504`·`E407`·`E201`·`E106`·`E104`·`E102` 를
각각 확인하고, `test_messages_never_echo_file_values` 가 유출 방지를 강제한다.

## 고친 것 — 이 시험이 잡아낸 설계 실수

처음에는 계약·데이터셋 어긋남 검사(`E903`)를 **제출 검증 경로 안에** 넣었다.
계약의 `expected_rows` 와 주입된 평가 ID 개수를 매번 비교하는 방식이었다.

이 상태로 웹 테스트를 돌리자 **전부 깨졌다.**

```
[E903] 채점기 설정 오류: 계약의 예상 행 수와 주입된 평가 ID 개수가 다릅니다.
```

웹 테스트는 평가 ID를 2건만 주입한다. 계약에는 수천 건이 적혀 있으니 어긋남으로
판정된 것이다. **정당한 호출을 막은 것이고, 검사 위치가 틀렸다.**

어긋남은 제출의 성질이 아니라 **설정의 성질**이다. 그래서 제출 경로에서 빼고
`verify_contract_against_dataset()` 로 분리했다. 작업자 시작 시 한 번, CI 에서
한 번 호출하면 된다.

```python
report = verify_contract_against_dataset(
    contract_path=PREDICTION_CONTRACT,
    eval_ids_csv=PRIVATE_ROOT / "test.csv",
)
if not report.ok:
    raise SystemExit(report.to_json(operator=True))
```

분리 후 다시 돌려 41건 모두 통과했다. 시험을 안 했으면 이 변경이 웹팀 테스트를
전부 깨뜨린 채로 머지됐을 것이다.

## 웹팀에 전달할 것 2건

### 1. 계약 사본이 낡았습니다

| | `expected_rows` | `updated` |
| --- | --- | --- |
| 데이터 저장소 (원본) | 5,330 | 2026-10-08 |
| `apps/api/contract/prediction_contract.json` | **5,387** | 2026-10-04 |

검증기 코드 6개 파일은 원본과 같다. 계약 파일만 데이터 재생성(PR #13)을
따라오지 않았다.

**지금 당장 오판정이 나지는 않습니다.** 판정 기준은 작업자가 넘기는 평가 ID
목록이고, `expected_rows` 는 그 비교에 쓰이지 않기 때문이다. 하지만 두 값이
어긋난 상태를 아무도 모르는 게 문제여서 위의 시작 시점 검사를 만들었다.

### 2. `hint`(조치 안내)를 참가자에게 보여주면 좋겠습니다

현재 `app/scoring/predictions.py` 가 메시지를 이렇게 조립한다.

```python
message = " ".join(f"[{e['code']}] {e['message']} ({e['count']}건)" for e in ...)
```

`code`·`message`·`count` 만 쓰고 `hint` 를 버린다. 예측 파일 값을 되돌려주지
않는 판단은 **웹팀 쪽이 맞다** — 참가자 코드가 숨김 평가 입력을 읽은 뒤 예측을
만들기 때문에, 평가 데이터를 라벨 칸에 담아 두면 그 값이 응답으로 돌아온다.
이 판단에 맞춰 검증기의 `participant_payload()` 기본값도 strict 로 바꿨다.

다만 `hint` 는 검증기에 박힌 **고정 문자열**이다. 참가자 데이터도 평가 데이터도
흘러들어갈 수 없다. 그리고 이게 참가자가 제출을 덜 버리게 하는 부분이다.

```
지금: [E507] 라벨이 숫자로 변환돼 끝자리 0이 사라졌습니다. (5123건)

제안: [E507] 라벨이 숫자로 변환돼 끝자리 0이 사라졌습니다. (5123건)
             조치: pd.read_csv(..., dtype=str) 로 읽고 문자열로 저장하세요.
```

조립하다 빠뜨리지 않도록 `outcome.participant_lines` 를 추가했다. 코드·메시지
·건수·조치 안내를 한 줄로 묶고, 예측 파일에서 온 값은 넣지 않는다.

```python
for line in outcome.participant_lines:
    show_to_participant(line)
```

## 덧붙임 — 결정이 필요한 작은 사항

평가 ID에 공백이 생겼다(5,330건인데 최대 번호 `TEST_005384`, 폐기 54건).
`E403`(평가 입력에 없는 ID)은 strict 모드에서 값을 되돌려주지 않으므로 현재
구성에서는 문제가 없다. 다만 `strict=False` 를 쓰기로 하면, 참가자가 후보 ID를
넣어 보는 방식으로 폐기된 번호를 알아낼 수 있다. 정답은 아니니 심각도는 낮지만,
민준이 PR #14 에서 지적한 "오류 안내가 유출 통로가 되는 문제"와 같은 성질이라
함께 정리하면 좋겠다. **권장: strict 유지.**
