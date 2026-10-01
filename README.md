# ADMIN 2026 대회 데이터·베이스라인

[CATH v4.4 S40](https://download.cathdb.info/cath/releases/all-releases/v4_4_0/)을 받아 단백질 도메인의 관측 서열과 Cα 좌표를 검증하고, Architecture 분류용 데이터·31개 기본 특징·Logistic Regression 베이스라인을 생성합니다. 웹사이트와 채점 API는 [별도 저장소](https://github.com/2026-admin-ai-challenge/admin-2026-protein-structure-challenge)에 있습니다.

## 내용

- `scripts/download_cath.py`: 원본 다운로드와 체크섬 기록
- `scripts/prepare_dataset.py`: 정제·구조 대응·분할·배포 파일 생성
- `scripts/verify_dataset.py`, `scripts/verify_structures.py`: 파일, 분할, 좌표, 특징 검증
- `scripts/structure_features.py`: 서열 조성 20개와 구조·거리 통계 11개 특징
- `scripts/baseline.py`, `notebooks/baseline.ipynb`: 학습·예측 예제
- `docs/`: 데이터 출처, 좌표 형식, 참가자 가이드
- `tests/`: 데이터 파이프라인 검증

현재 선택 결과는 26,961개 샘플, 20개 Architecture, 학습 21,568개, 평가 5,393개입니다. 공개 CATH 자료와 재현 가능한 생성 코드로 숨긴 평가 정답을 추적할 수 있으므로, 이 저장소는 **운영진 전용 비공개**로 유지해야 합니다.

## 대회 전 생성

Python 3.12 환경에서 실행합니다. 구조 원본 압축파일은 약 818 MiB이며, 데이터 생성과 전체 검증에는 추가 디스크 공간과 시간이 필요합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_cath.py
python scripts/prepare_dataset.py
python scripts/verify_dataset.py
```

`data/raw/`에는 CATH 원본, `data/public/`에는 참가자 제공용 파일, `data/private/`에는 숨긴 정답과 원본 ID 매핑이 저장됩니다. 생성물은 모두 Git에서 제외합니다. `prepare_dataset.py`는 기존 정답 파일이 있으면 덮어쓰기를 거부합니다. 대회 중 데이터 교체는 기존 제출 점수의 의미를 바꾸므로 하지 마세요.

웹사이트 저장소와 같은 상위 디렉터리에 이 저장소를 두면 웹사이트의 Docker Compose가 `../admin-2026-protein-data/data`를 API에 읽기 전용으로 연결합니다. 다른 위치라면 웹사이트 `.env`의 `DATA_HOST_DIR`을 설정하세요.

## 현재 구현 상태

현재 파이프라인은 기존 **CSV 예측 제출 프로토타입**에 맞춰 `test.csv`와 `test_features.csv`를 참가자에게 배포합니다. 새 규칙인 **저장된 모델 제출 → 공개하지 않은 평가 입력으로 격리 추론 → 채점**에 맞게 배포 파일과 채점 연동을 수정해야 합니다. 지금 생성물을 그대로 새 대회의 최종 평가셋으로 배포하지 마세요.

데이터 생성만으로 외부 자료 사용 여부를 증명할 수 없습니다. 새 대회에는 제공 데이터만 사용하도록 규정하고, 상위 팀의 학습 코드·모델을 재현 검증해야 합니다. 자세한 과제는 [개발 디렉팅 문서](https://github.com/2026-admin-ai-challenge/admin-2026-protein-structure-challenge/blob/main/ADMIN_%EB%8C%80%ED%9A%8C_%EA%B0%9C%EB%B0%9C_%EB%94%94%EB%A0%89%ED%8C%85.md)를 참조하세요.
