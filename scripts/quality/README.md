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

## 주의

- `c12_suspects.py`, `day2_hits.py`는 원본 domain 이름을 쓰기 위해 `data/private/id_mapping.csv`를 읽는다. 출력 JSON에 원본 domain 이름이 들어가므로 작업 폴더는 공유하지 않는다.
- 2026-10-03 커밋 `44e28e4` 데이터로 처음부터 다시 실행해 보고서의 수치(C-12 버그 372곳·7개 구조, A-05 오류 3쌍, A-06 17개 등)가 같게 나오는 것을 확인했다.
