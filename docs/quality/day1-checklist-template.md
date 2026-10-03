# Day 1 문제 기록 양식

결측·중복·서열/구조 불일치를 점검하고 기록하기 위한 양식이다. 원본 데이터는 수정하지 않는다. 문제는 샘플 ID와 재현 방법을 적어 공유한다.

## ① 개요 (점검할 때 채움)

| 항목 | 내용 |
| --- | --- |
| 점검자 | |
| 점검일 | |
| 데이터 버전 | `admin-2026-protein-data` 커밋 |
| 파일 해시 | `data/DATASET_CHECKSUMS.json` 기준 |
| 대상 | 학습 / 평가 중 선택 |
| 근거 문서 | `docs/dataset.md`, `docs/structure-format.md`, `docs/dataset-audit.md`, `scripts/structure_dataset.py`, `scripts/verify_structures.py` |

## ② 표기 규칙

| 칸 | 값 | 뜻 |
| --- | --- | --- |
| 결과 | 통과 | 정상 기준을 만족함 |
| | 이상 | 정상 기준과 다름. ③ 문제 기록에 적음 |
| | 미확인 | 아직 판단할 근거가 없음 |
| 근거 | 감사 | `dataset-audit.md` 결과를 인용함 (날짜 함께 표기) |
| | 직접 | 이번 점검에서 직접 실행함 |

## ③ 점검표

| 번호 | 분류 | 점검 항목 | 대상 파일 | 정상 기준 | 점검 방법 | 결과 | 수치 | 근거 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C-01 | 결측 | CSV 빈칸·NaN | CSV 전체 | 빈칸·공백·NaN/null/None/NA 0개 | 모든 CSV 셀 검사 | | | |
| C-02 | 결측 | 좌표 결측 | `*_structures.zip` | 관측된 Cα(`ca_mask=True`) 40개 이상, coverage 95% 이상, `ca_mask=False` 칸의 `pos`는 [0,0,0], `pos`에 NaN/inf 없음 | NPZ별 `ca_mask` 집계, `np.isfinite(pos)` 확인 | | | |
| C-03 | 결측 | ID 집합 일치 | 학습: `train.csv`, `train_features.csv`, `validation_split.csv`, `train_structures.zip` / 평가: `test.csv`, `test_features.csv`, `test_structures.zip`, `labels.csv` | 대상별 네 파일의 ID 목록이 정확히 같음 | 개수 비교 → ID 차집합 | | | |
| C-04 | 중복 | id 중복 | CSV 전체 | 파일마다 id가 한 번씩 | id 값 중복 검사 | | | |
| C-05 | 중복 | 서열 중복 | `train.csv` / `test.csv` | 같은 서열 0개 | sequence 중복 검사 | | | |
| C-06 | 중복 | 학습/평가 겹침 | 학습 ↔ 평가 | id·서열·원본 domain·H-superfamily 겹침 0 | 집합 교집합 | | | |
| C-07 | 중복 | zip 안 파일 이름 중복 | `*_structures.zip` | 같은 이름의 npz 0개 | 파일 이름 목록 중복 검사 | | | |
| C-08 | 불일치 | 서열 길이 = NPZ 행 수 | CSV ↔ NPZ | NPZ에 배열 5개(`residue_type`, `residue_index`, `segment_index`, `pos`, `ca_mask`)가 모두 있음, 각 배열 길이 = `len(sequence)`, `pos` 모양 (N, 3), `residue_index`가 0부터 N-1까지 빠짐없이 이어짐 | 구조별 비교 | | | |
| C-09 | 불일치 | residue_type = 서열 글자 | CSV ↔ NPZ | 서열은 표준 아미노산 20종만 사용, `ACDEFGHIKLMNPQRSTVWY`로 바꾼 글자열이 sequence와 같음 | 구조별 비교 | | | |
| C-10 | 불일치 | 특징 31개 재계산 | `*_features.csv` ↔ NPZ | 열 이름·순서가 `FEATURE_NAMES`와 같음, 모든 값이 유한함, 다시 계산한 값과 상대 오차 1e-6·절대 오차 1e-7 안에서 일치 | `structure_features()` 재계산 후 `np.allclose(rtol=1e-6, atol=1e-7)` | | | |
| C-11 | 불일치 | 라벨 형식 | 학습: `train.csv` / 평가: `labels.csv` | 문자열로 읽었을 때 20종, `metadata.json`의 `labels`와 같음. 평가는 Public과 Private 양쪽에 20종이 모두 있음 | `dtype={"label": str}`로 읽어 집합 비교 | | | |
| C-12 | 불일치 | segment_index 정합성 | `*_structures.zip` | 첫 칸은 0, 다음 칸과의 차이는 0 또는 1. `structure-format.md` 기준대로 좌표 누락·번호/사슬 불연속·4.5Å 초과일 때만 구간이 바뀜 | 시작값과 증가 폭 확인 → 이웃 두 칸이 모두 좌표 있고 거리 4.5Å 이하인데 구간이 바뀐 곳을 셈 → 연속으로 나오는 길이 확인 → 원본 PDB 번호 대조 | | | |
| C-13 | 불일치 | 서열 길이 범위 | `train.csv` / `test.csv` | 모든 서열 길이가 40 이상 1200 이하 (`dataset.md`, `prepare_dataset.py`) | `sequence.str.len()` 최솟값·최댓값 확인 | | | |
| C-14 | 중복 | 학습 내부 분할 | `validation_split.csv` | 열은 `id`, `fold` 두 개, fold 값은 `fit`과 `validation` 두 가지뿐, 두 fold 사이에 H-superfamily 겹침 0, 두 fold 모두 20개 라벨을 포함 | fold별 H-superfamily 교집합, 라벨 집합 비교 (H-superfamily는 `id_mapping.csv` 필요) | | | |

C-12 점검 코드:

```python
d    = np.linalg.norm(np.diff(pos, axis=0), axis=1)
both = ca_mask[:-1] & ca_mask[1:]
odd  = both & (seg[1:] != seg[:-1]) & (d <= 4.5)   # 거리로 설명 안 되는 끊김
```

## ④ 문제 기록 양식

원본 domain 이름은 이 문서에 적지 않는다. 필요하면 김민준(데이터팀)에게 문의한다.

| 번호 | 샘플 ID | label | 문제 유형 | 내용 | 재현 방법 | 원인 | 넘길 곳 | 상태 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P-xx | | | | | | | | |

### 칸 작성법

| 칸 | 적는 내용 |
| --- | --- |
| 번호 | `P-01`부터 차례로 |
| 샘플 ID | `TRAIN_xxxxxx` 또는 `TEST_xxxxxx` |
| label | 문자열 그대로 (`2.30`, `2.160`) |
| 문제 유형 | 결측 / 중복 / 불일치 중 하나 + 관련 점검 번호(C-xx) |
| 내용 | 무엇이 정상 기준과 다른지, 수치와 함께 |
| 재현 방법 | 같은 결과를 다시 얻는 코드나 명령 |
| 원인 | 확인된 원인. 모르면 "미확인" |
| 넘길 곳 | 판단하거나 고칠 담당자 |
| 상태 | 미확인 → 확인됨 → 전달함 → 해결됨 |

## ⑤ 확인했지만 문제 아님 (메모)

점검했지만 문제가 아니라고 판단한 항목을 적는다. 같은 검사를 다시 하지 않도록 이유를 남긴다.

| 항목 | 확인 내용 | 문제 아님으로 본 이유 |
| --- | --- | --- |
| | | |
