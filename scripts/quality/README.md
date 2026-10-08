# 데이터 품질 점검 스크립트

`docs/quality/`의 보고서 결과를 다시 계산하는 스크립트다. 모두 데이터를 읽기만 한다. 레포 루트에서 실행한다.

필요한 것: Python 3.12, numpy, scipy (레포 `requirements.txt`). 원본 PDB 대조 단계는 인터넷 연결이 필요하다.

`<작업 폴더>`는 중간 결과와 원본 PDB를 둘 임시 폴더다. 원본 PDB 파일(수백 MB)은 Git에 올리지 않는다.

## Day 1: 결측·중복·불일치 (C-01 ~ C-14)

```bash
python scripts/quality/day1_check.py .
```

C-12 의심 지점을 원본 PDB 번호와 대조:

```bash
python scripts/quality/c12_suspects.py . <작업 폴더>            # suspects.json
python scripts/quality/fetch_pdb.py <작업 폴더> <작업 폴더>/suspects.json
python scripts/quality/c12_classify.py <작업 폴더>              # c12_result.json
```

평가 데이터는 `c12_suspects.py . <작업 폴더> test`로 같은 순서를 따른다.

## Day 2: 비정상 값 (A-01 ~ A-08)

```bash
python scripts/quality/day2_abnormal_stats.py . <작업 폴더>/abn.json      # 분포, 기준 후보
python scripts/quality/day2_hits.py . <작업 폴더>                         # 원본 대조할 샘플 목록
python scripts/quality/fetch_pdb.py <작업 폴더> <작업 폴더>/a05_hits.json <작업 폴더>/hits_067.json
python scripts/quality/day2_a05_verify.py . <작업 폴더>/pdb <작업 폴더>/a05_hits.json
python scripts/quality/day2_a06_verify.py . <작업 폴더>/pdb <작업 폴더>/hits_067.json <작업 폴더>/a06_verified.json
python scripts/quality/day2_shape_verify.py . <작업 폴더>/pdb <작업 폴더>/c12_result.json <작업 폴더>/rest.json
python scripts/quality/day2_extended_verify.py . <작업 폴더>/pdb <작업 폴더>/rest.json <작업 폴더>/ext.json
```

`day2_shape_verify.py`는 Day 1의 `c12_result.json`이 있어야 한다. `day2_extended_verify.py`가 대조하는 원본 PDB 일부는 `fetch_pdb.py`에 `rest.json`을 넘겨 받는다.

## Day 3: 수정 확인 · 평가 데이터 · 추가 점검

`docs/quality/day3-*.md`의 결과를 다시 계산한다. 데이터 버전 `797d114`(PR #5) 기준.

1차 문제 추적 (옛 ID → 원본 domain → 새 ID). 먼저 위 Day 1 C-12 단계를 학습은 `<작업 폴더>`, 평가는 `<작업 폴더>/test`에 돌려 둔다:

```bash
python scripts/quality/day3_track.py . 44e28e4 <작업 폴더>
```

끊긴 지점이 실제로 결합된 이웃인지 원본에서 측정 (D-01, N-01):

```bash
python scripts/quality/day3_boundary.py . <작업 폴더>                                   # D-01 삽입 코드 경계
python scripts/quality/day3_boundary.py . <작업 폴더> "연속인데 끊김 (설명 불가)"          # N-01
```

평가 데이터에 Day 1·2 전 항목 실행. 평가 파일을 학습 파일 자리에 놓은 임시 폴더를 만들어, 위 Day 1·2 명령의 `.` 자리에 넘긴다:

```bash
python scripts/quality/day3_test_view.py . <평가용 폴더>
python scripts/quality/day1_check.py <평가용 폴더>
python scripts/quality/day2_hits.py <평가용 폴더> <작업 폴더>/test
```

이웃 간격이 정상 범위 밖인 쌍의 모양(altloc) 섞임 판정 (P-30 잔여):

```bash
python scripts/quality/day3_altloc_mix.py flags . <작업 폴더>/mix test
python scripts/quality/fetch_pdb.py <작업 폴더>/mix <작업 폴더>/mix/adjacent_flags.json
python scripts/quality/day3_altloc_mix.py check . <작업 폴더>/mix test
```

50% 기준 아래 알라닌 부분 채움 후보:

```bash
python scripts/quality/day3_ala_runs.py .
```

2026-10-04 `797d114` 데이터로 실행해 보고서 수치(D-01 학습 31곳·평가 7곳, 모양 섞임 11곳·8개 구조, A 8개 이상 연속 학습 3·평가 2 등)가 같게 나오는 것을 확인했다.

`day2_extended_verify.py`는 1차 데이터의 ID가 코드에 들어 있어 `797d114` 데이터에서는 실행되지 않는다.

## Day 4: 품질 보고서 2차 (전수 점검)

`docs/quality/day4-*.md`의 결과를 다시 계산한다. 데이터 버전 `cb2f530`(PR #11) 기준. 점검 순서는 `docs/quality/day4-quality-template.md`를 따른다.

학습·평가 모두 위 Day 1 · Day 2 · Day 3 명령을 다시 돌린다(평가는 `day3_test_view.py`로 만든 폴더 사용). 모양 섞임은 학습에도 적용한다:

```bash
python scripts/quality/day3_altloc_mix.py flags . <작업 폴더>/mix_train train
python scripts/quality/fetch_pdb.py <작업 폴더>/mix_train <작업 폴더>/mix_train/adjacent_flags.json
python scripts/quality/day3_altloc_mix.py check . <작업 폴더>/mix_train train
```

번호 규칙으로 끊긴 자리 전체의 실제 결합 (D-02):

```bash
python scripts/quality/day3_boundary.py . <작업 폴더> "번호 건너뜀" "번호 역행" "삽입코드 역순" "삽입코드 건너뜀"
```

비정상 값 기준에 처음 걸린 샘플 찾기 (A 신규 판정). 학습·평가 작업 폴더에 `rest.json`, `hits_067.json`이 있어야 한다:

```bash
python scripts/quality/day4_new_hits.py . <작업 폴더> <작업 폴더>/test
```

데이터 버전 간 분할 변화 (E-05):

```bash
python scripts/quality/day4_split_diff.py . 797d114
```

학습·평가 누출과 공개 파일 점검 (E-04 서열 포함, E-06 거의 같은 서열, E-07 같은 특징값, E-08 같은 PDB 항목, R-01 공개 파일):

```bash
python scripts/quality/day4_leak_checks.py .
```

2026-10-07 `cb2f530` 데이터로 실행해 보고서 수치(처음 걸린 샘플 0건, 분할 이동 1,194 / 1,188, 서열 포함 21쌍 · 거의 같은 서열 11쌍 · 평가 30개, 모양 섞임 학습 43곳 · 평가 1곳, 실제 결합 학습 481 · 평가 105 등)가 같게 나오는 것을 확인했다. `verify_dataset.py`는 pandas가 필요하다.

## Day 4 배포 점검

`docs/quality/day4-release-*.md`의 데이터 쪽 결과를 다시 계산한다. 기준 문서는 웹사이트 레포 `docs/participant-release-candidates.md`, 데이터 버전 `23760e7`(PR #13).

```bash
python scripts/quality/day4_release_checks.py .
```

공개 파일과 zip 안쪽(중첩 zip 포함)의 평가 입력·정답·분할·평가 ID·원본 domain 이름, metadata의 seed·분할 비율, 예제, CSV 열·NPZ 키, ID 순서와 라벨·Public/Private의 관계, zip 메타데이터, 파일 크기, 공개 통계를 점검한다. 2026-10-08 실행에서 보고서 수치(ID 순서 p = 0.107 · 0.319 · 0.407, 파일 시간 1종류, 공개 통계로 맞힌 평가 개수 0/20 등)가 같게 나오는 것을 확인했다. 웹사이트 쪽 항목(공개 API, 오류 안내, 채점 격리)은 이 스크립트 범위 밖이다.

## 주의

- `c12_suspects.py`, `day2_hits.py`는 원본 domain 이름을 쓰기 위해 `data/private/id_mapping.csv`를 읽는다. 출력 JSON에 원본 domain 이름이 들어가므로 작업 폴더는 공유하지 않는다.
- 2026-10-03 커밋 `44e28e4` 데이터로 처음부터 다시 실행해 보고서의 수치(C-12 버그 372곳·7개 구조, A-05 오류 3쌍, A-06 17개 등)가 같게 나오는 것을 확인했다.
