# 배포 점검 보고서 (초안)

`day4-release-template.md`로 현재 공개 파일과 공개 API를 배포 후보 문서와 대조한 결과다. Day 4 업무 "배포 파일 목록에 숨김 평가 자료가 없는지 점검"의 결과다. 파일과 서버 설정은 읽기만 했다.

## ① 개요

| 항목 | 내용 |
| --- | --- |
| 점검자 | 김민준 (데이터팀) |
| 점검일 | 2026-10-08 |
| 기준 문서 | 웹사이트 레포 `docs/participant-release-candidates.md` (PR #9 추가, #10 보완. 취소 PR #11은 머지되지 않아 문서 유지). 문서 스스로 "확정 목록이 아닌 협의용 권장안"이라고 밝힘 |
| 데이터 버전 | `admin-2026-protein-data` 커밋 `23760e7` (PR #13). 학습 21,339 / 평가 5,330 |
| 웹사이트 버전 | `admin-2026-protein-structure-challenge` main (2026-10-08) |
| 점검 대상 | `data/public/` 13개 파일과 zip 3개 안쪽, 웹사이트 공개 API(`PUBLIC_FILES`, `/api/competition`). **배포 ZIP 2개는 아직 만들어지지 않아 점검하지 못함** |
| 재현 | 데이터 쪽 항목(B-04 ~ B-07, B-10, B-11, V-01 ~ V-03, V-08)은 `scripts/quality/day4_release_checks.py`. 웹사이트 항목(B-13, V-09, V-11, V-12)은 코드를 읽어 판단했고 근거 파일 위치를 표에 적음 |

## ② 결론

- **지금 공개 파일에는 숨김 평가 자료가 없다.** 평가 입력·정답·Public/Private 분할·평가 ID·원본 domain 이름 모두 0건이다.
- **공개 API가 `metadata.json`의 seed와 분할 비율을 로그인 없이 내보낸다.** 기준 문서가 공개 금지로 정한 "분할을 재구성할 수 있는 설정·seed"에 해당한다. 위반 1건.
- **기준 문서와 실제가 다른 곳이 3건 있다.** 문서의 숫자가 옛 버전 기준이고, 목록에 없는 공개 파일이 있고, 문서의 배포 형태(ZIP 2개, `sample_*`)가 아직 만들어지지 않았다.
- **ML 대회 취약점 13가지를 점검했다(⑥).** 행·ID 순서, 파일 메타데이터, 채점 환경 격리는 안전하다. 가장 큰 위험은 **공개 CATH 원본으로 평가 정답을 그대로 찾을 수 있다는 점**이고, 지금은 규칙과 수상 후보 재현 검증으로만 막고 있다. 재현 검증 기준은 아직 정해지지 않았다.
- **최종 점검은 배포 ZIP 2개를 만든 뒤 다시 한다.** 기준 문서도 "허용 목록대로 만든 두 ZIP에 비공개 자료가 없는지 확인한 뒤 배포를 확정"하도록 정했다.

## ③ 점검 결과

### 허용 목록 대조

| 번호 | 결과 | 판정 |
| --- | --- | --- |
| B-01 | 기준 트리 중 `data/train.csv`, `train_features.csv`, `train_structures.zip`은 있음. `starter_kit/inference.py`, `train.py`, `sample_input/sample_*`, `environment/`, 발표자료용 `data/README.md`, 배포 ZIP 2개(`admin2026_data.zip`, `admin2026_starter_kit.zip`)는 아직 없음. 지금은 `example_*`, `starter_kit.zip`(baseline 코드 포함)이 그 자리를 대신함 | 점검 불가 (미제작) |
| B-02 | 기준 트리에 없는 공개 파일: `validation_split.csv`, `metadata.json`, `class_distribution.png`, `sequence_length_distribution.png`, `baseline_code.zip`. 이 중 `validation_split.csv`와 `baseline_code.zip`은 기준 문서 7절의 확정 필요 항목. 웹사이트 `PUBLIC_FILES`는 `train`, `train_features`, `train_structures`, `validation_split`, `example_io.zip` 5개를 내려주는데, `example_io.zip`은 데이터 레포에 아직 없음 | 불일치 |
| B-03 | 기준 문서는 학습 NPZ를 21,536개로 적었으나 PR #13 이후 21,339개. 문서의 확인 시점(2026-10-07)이 PR #13 머지 전 | 불일치 |

### 공개 금지 대상

| 번호 | 결과 | 판정 |
| --- | --- | --- |
| B-04 실제 평가 입력 | `test.csv` · `test_features.csv` · `test_structures.zip`이 `data/public/`과 zip 안쪽(중첩 `example_structures.zip` 포함)에 없음. 공개 CSV에 평가 ID 0 | 통과 |
| B-05 숨긴 평가 정답 | `labels.csv` 등 없음. 평가 ID와 라벨 쌍 0 | 통과 |
| B-06 분할 · seed | 공개 파일에 partition 열과 ID별 분할 없음. **단 `metadata.json`에 `seed: 42`와 분할 비율(`train 0.8 / test 0.2 / public_test 0.3 / private_test 0.7`)이 있고, 웹사이트 `/api/competition`이 로그인 없이 이를 그대로 돌려줌** | **위반** |
| B-07 평가 ID · 원본 식별자 | `TEST_` ID 0, 원본 domain 이름 0 (공개 파일, zip 안쪽 코드·문서 전체) | 통과 |
| B-08 scoring 내부 자료 | 공개 경로에 채점 설정·스크립트·결과 없음 | 통과 |
| B-09 운영 전용 자료 | 공개 경로에 비밀정보·원본 캐시 없음. 단 데이터 레포의 `data/README.md`(운영진용, "고정 시드 파이프라인과 원본 DB로 시험 정답 재구성 가능" 문장 포함)는 기준 문서의 발표자료용 `data/README.md`와 다른 파일이므로 배포 때 바꿔 넣지 않도록 주의 | 통과 (주의) |

### 내용 검사

| 번호 | 결과 | 판정 |
| --- | --- | --- |
| B-10 공개 예제 | 예제 3개 모두 학습 샘플, 평가 ID와 겹침 0. 입력(`id,sequence`)에 정답 열 없음. 예제 출력 라벨이 공개 학습 라벨과 같음 | 통과 |
| B-11 CSV 열 · NPZ 키 | `train.csv` `id,sequence,label`, `validation_split.csv` `id,fold`, `example_input.csv` `id,sequence`, `example_output.csv` `id,label`. NPZ 키 5개(`residue_type`, `residue_index`, `segment_index`, `pos`, `ca_mask`)로 규격과 같음 | 통과 |
| B-12 코드 · 문서 · 노트북 | Starter Kit의 `structure-format.md`가 `test.csv` · `test_structures.zip`과 Public/Private를 언급하지만, "서버에만 있다", "validation fold는 숨김 Public/Private 분할이 아니다"라는 설명 문장이라 허용 범위(기준 문서 4절). 노트북 실행 결과 없음(`verify_structures.py`가 검사) | 통과 |
| B-13 공개 API 메타데이터 | `/api/competition`이 `metadata.json`을 `files` 항목만 걸러 반환. seed · 분할 비율(B-06) 외에 CATH 원본 주소·해시, 생성 정책 문장, 제외 건수, 기준 커밋(`split_policy`)도 포함됨. 평가 정답·ID는 없음 | 위반 (B-06과 같은 건) |

### 미확정 항목 (기준 문서 7절)

| 번호 | 항목 | 현재 상태 |
| --- | --- | --- |
| B-14 | 학습 내부 검증 분할 | `validation_split.csv` 제공 중. 유지 여부 미정 |
| B-14 | 예제 묶음 | 웹사이트는 `example_io.zip`, 기준 문서는 `sample_input/`, 데이터 레포는 `example_*` 개별 파일. 이름 미정 |
| B-14 | sample / test 입력 이름 | 서열·구조를 쓰는 코드의 이름 매핑 미정 |
| B-14 | 두 ZIP 다운로드 | ZIP 제작, 웹 API · 화면 전환 미정 |
| B-14 | 코드 전용 사전 배포 | `baseline_code.zip` 별도 제공 여부 미정 |
| B-14 | 패키지 · Python 버전 | evaluator 이미지 검증 전 |

## ④ 문제 기록

| 번호 | 문제 | 위치 | 기준 문서 근거 | 영향 | 조치 (권장) | 담당 | 상태 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B-06 | 공개 API가 seed와 분할 비율을 내보냄 | 데이터 `data/public/metadata.json`의 `seed`, `split`. 웹 `apps/api/app/dataset.py` `public_metadata()` | 3절 "분할을 재구성할 수 있는 설정·seed" 공개 금지 | 분할은 비공개 배정표로 고정됐고 생성 코드도 비공개라 seed만으로 재구성은 어려움. 다만 문서 규칙과 어긋나고, CATH 원본 주소·생성 정책과 합치면 재구성 단서가 됨 | `public_metadata()`가 허용한 항목(라벨 목록, 건수, 학습 통계 등)만 내보내도록 바꾸거나, 공개용 metadata를 따로 만듦 | 웹팀 · 하태영 | 수정 필요 |
| B-03 | 기준 문서의 숫자가 옛 버전 | 웹 `docs/participant-release-candidates.md` 1절 | — | 문서를 보고 판단할 때 혼동 | 21,536 → 21,339로 갱신, 확인 기준 커밋 명시 | 하태영 | 수정 필요 |
| B-02 | 기준 트리에 없는 공개 파일 | `validation_split.csv`, `metadata.json`, PNG 2개, `baseline_code.zip` | 1절 트리, 7절 | 허용 목록이 정해지지 않으면 최종 점검 기준이 없음 | 각 파일을 배포할지 결정해 기준 문서 트리에 반영 | 운영진 · 하태영 | 결정 필요 |
| B-09 | 운영진용 `data/README.md`와 배포용 README 혼동 가능 | 데이터 레포 `data/README.md` | 2절 "발표자료 내용만" | 배포 때 잘못 넣으면 정답 재구성 가능 문장이 공개됨 | 배포 ZIP 제작 때 발표자료용 README를 따로 만들고, 최종 점검에서 확인 | 하태영 | 주의 |

## ⑤ 요약

| 판정 | 건수 | 내용 |
| --- | ---: | --- |
| 통과 | 8 | B-04, B-05, B-07, B-08, B-09(주의), B-10, B-11, B-12 |
| 위반 | 1 | B-06 공개 API의 seed · 분할 비율 (B-13과 같은 건) |
| 불일치 | 2 | B-02 목록에 없는 공개 파일, B-03 문서 숫자 |
| 미확정 | 6 | B-14 기준 문서 7절 항목 |
| 점검 불가 | 1 | B-01 배포 ZIP 미제작 |

지금 공개 파일에는 숨김 평가 자료가 없다. 고칠 것은 공개 API의 seed · 분할 비율 노출 하나다. 배포 ZIP 2개가 만들어지면 이 양식으로 B-01 ~ B-13을 다시 점검한다.

## ⑥ ML 대회 취약점 점검

### 조사한 취약점 유형

공개된 대회 사례와 연구에서 숨김 평가 자료가 새는 경로를 정리했다.

| 유형 | 사례 · 근거 |
| --- | --- |
| 행 순서 · ID 순서 누출 | SETI 대회에서 데이터가 라벨 순서로 처리돼 순서만으로 정답이 드러남 |
| 파일 메타데이터 누출 | SETI 대회의 파일 시간 정보, 해양 동물 음성 대회의 파일 길이·시간 정보로 거의 100% 정확도 |
| 공개 원본 · 유사 샘플 | 단백질 벤치마크에서 서열 유사도만으로 나누면 누출이 남음. 공개 DB로 정답 역추적 |
| 리더보드 탐색 | 반복 제출로 Public 점수를 탐색해 과적합 (Ladder 연구) |
| 오류 메시지 · 로그 | Kaggle은 숨김 데이터로 다시 실행하는 대회에서 상세 오류를 주지 않고 일반 오류 분류만 줌. 오류 제출도 횟수를 차감 |
| 채점 환경 격리 | 제출 코드는 네트워크·파일 접근을 막은 격리 환경에서 실행. 정답은 채점 단계에서만 사용 |
| 운영 자료 노출 | 분할 설정 · seed, 원본 ID 매핑, 저장소 기록 |

### 우리 대회 점검 결과

| 번호 | 취약점 | 확인 방법 | 결과 | 판정 |
| --- | --- | --- | --- | --- |
| V-01 | 행 · ID 순서 누출 | ID 순서를 10구간으로 나눠 라벨과 카이제곱 검정, 이웃 샘플이 같은 라벨인 비율 | 학습 p = 0.107, 평가 p = 0.319, 평가 Public/Private p = 0.407. 이웃 같은 라벨 비율 0.117 · 0.115로 무작위 기대값(0.119 · 0.118)과 같음 | 통과 |
| V-02 | 파일 메타데이터 | 구조 zip 안 파일 시간 · 순서 · 주석 | 시간 1개로 고정, ID 순서대로, 주석 · 추가 정보 0 | 통과 |
| V-03 | 파일 크기 | 압축 크기 ÷ 길이를 클래스별로 비교 | 클래스별 15.2 ~ 21.2바이트로 차이가 있으나, 평가 zip은 배포하지 않고 학습에도 같은 정보가 있어 숨김 자료가 아님 | 통과 |
| V-04 | 중복 · 유사 샘플 | Day 4 E-04 · E-06 | 평가 30개가 학습과 서열이 겹침. PR #13에서 운영진이 허용으로 결정 | 참고 (결정됨) |
| V-05 | **공개 원본 DB로 정답 역추적** | 생성 코드와 참가자 규칙 확인 | **존재.** 평가 서열은 모두 공개 CATH S40 원본 서열과 정확히 같다(생성 규칙상 정확 일치만 사용). 공개 원본의 서열 → 라벨 표는 수 MB라 제출 ZIP(500MB)에 넣을 수 있고, 추론 중 네트워크가 없어도 정답을 맞힐 수 있다. 참가자 규칙(`competition.md` 51행)이 CATH/PDB 조회를 금지하고, 수상 후보는 학습 코드 재현을 받는다(53행). 다만 재현 기준(Q11)과 대응 방침(Q12)은 미정 | **높음, 운영 결정 필요** |
| V-06 | 외부 사전학습 모델 | 규칙 확인 | 외부 가중치 허용 범위가 "추후 공지"(Q6). 단백질 언어 모델은 공개 서열 DB로 학습돼 평가 서열을 이미 봤을 수 있음 | 결정 필요 |
| V-07 | 분할 설정 · seed 공개 | ③ B-06 | 공개 API가 seed · 분할 비율을 내보냄 | 위반 (B-06) |
| V-08 | 평가 분포 통계 | 공개 metadata | PR #13 이후 학습 데이터로만 계산. 빼기로 평가 개수를 맞힐 수 있는 클래스 0/20 | 통과 |
| V-09 | 오류 메시지 · 로그 | 웹 `diagnostics.py`, `scoring/predictions.py`, `common.py` | 참가자에게 예외 값 · 경로 · 소스 · 임의 모듈 이름 · 예측 파일 값은 보여 주지 않음. 남은 통로: **inference.py의 오류 발생 줄 번호**(최대 7자리), 오류 종류, 검사 오류 개수, 시작 · 종료 시각, 성공/실패. 참가자 코드가 평가 입력을 보고 이 값을 고를 수 있어 제출 1회에 수십 비트를 내보낼 수 있다. 팀당 총 10회이고 실패도 기본 차감이며, 정답은 컨테이너에 없어 직접 유출은 안 됨 | 낮음 (줄 번호 표시 제거 권장) |
| V-10 | 리더보드 탐색 | 대회 설정 | Public 30%, 팀당 총 10회 제출이라 탐색 여지가 작음. 최종 순위 방식(Q7)은 미정 | 낮음 |
| V-11 | 채점 환경 격리 | 웹 `evaluators/docker.py` | 네트워크 없음, 읽기 전용, 권한 전부 제거, 일반 사용자, 평가 입력만 읽기 전용 연결, 정답 · 분할 · DB 정보 · Docker 소켓 미전달, 출력 폴더 링크 차단 | 통과 |
| V-12 | 채점 중 패키지 설치 (PR #15, 열림) | PR 본문 | 네트워크가 열리는 설치 단계에는 제출 코드와 평가 입력을 붙이지 않고, 받은 패키지 코드는 네트워크 없는 추론 단계에서만 실행. 설계상 평가 자료 유출 경로 없음. 머지되면 실제 동작 재확인 필요 | 통과 (설계 기준) |
| V-13 | 저장소 · git 기록 | 레포 공개 범위 | 두 레포 모두 비공개. 데이터 레포 git에 평가 정답이 있어 공개 전환 · 참가자 공유 금지(호성 검증 보고서와 같은 내용) | 주의 |

### 권장 조치

| 순서 | 조치 | 대상 | 담당 |
| --- | --- | --- | --- |
| 1 | V-05 대응 방침 확정: 재현 검증 기준(Q11)과 정답 역추적 대응(Q12). 예: 수상 후보의 학습 코드로 모델을 다시 만들어 제출 모델과 예측이 일치하는지 확인 | 운영진 | 운영진 · 데이터팀 |
| 2 | V-07 공개 API에서 seed · 분할 비율 등 내부 설정 제외 | 웹 `public_metadata()` 또는 공개용 metadata | 웹팀 · 하태영 |
| 3 | V-09 참가자 오류 안내에서 "발생 위치 N행" 제거 또는 실패 제출 차감 유지 확인 | 웹 `diagnostics.py`, 운영 설정 `count_failed` | 웹팀 |
| 4 | V-06 외부 사전학습 가중치 허용 범위 확정(Q6) | 대회 규칙 | 운영진 |
| 5 | 배포 ZIP 제작 후 ③과 ⑥을 다시 점검. PR #15가 머지되면 V-12 재확인 | — | 김민준 |

### 한계

- 웹사이트는 코드와 문서를 읽어 판단했다. 실제 서버에 접속하거나 공격 제출을 만들어 시험하지는 않았다.
- V-09의 "수십 비트"는 화면에 보이는 값의 경우의 수로 어림한 값이다.
- 공개 CATH 원본을 직접 내려받아 대조하지는 않았다. V-05는 생성 규칙(정확 일치만 사용)과 문서(`docs/dataset.md` 21행, 검증 보고서 3절 5번)로 판단했다.

### 참고 자료

- [Kaggle Competitions Documentation (leakage)](https://www.kaggle.com/docs/competitions)
- [Kaggle Code Competitions - Errors & Debugging Tips](https://www.kaggle.com/code-competition-debugging)
- [Position: AI Competitions Provide the Gold Standard for Empirical Rigor in GenAI Evaluation (SETI · 음성 대회 누출 사례)](https://arxiv.org/pdf/2505.00612)
- [Leakage and the reproducibility crisis in machine-learning-based science](https://www.sciencedirect.com/science/article/pii/S2666389923001599)
- [Climbing a shaky ladder (리더보드 탐색)](https://ar5iv.arxiv.org/html/1706.02733)
- [Reducing overfitting in challenge-based competitions](https://ar5iv.arxiv.org/html/1607.00091)
- [Revealing data leakage in protein interaction benchmarks](https://arxiv.org/pdf/2404.10457)
- [SandboxEval: Towards Securing Test Environment for Untrusted Code](https://arxiv.org/pdf/2504.00018)
- [Keeping 100k battles of untrusted agent code in their lane](https://lambda.ai/blog/keeping-100k-battles-of-untrusted-agent-code-in-their-lane)
