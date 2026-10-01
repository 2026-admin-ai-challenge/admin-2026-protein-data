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

원본은 **CATH 공식 v4.4 S40 배포본**에서 받습니다. `s40.atom.fa`는 관측된 잔기 서열, `s40.pdb.tgz`는 3D 구조, `domains.txt`는 C.A.T.H 분류표입니다. `s40.fa`도 출처 확인용으로 함께 받습니다. `label`은 분류표의 **Class.Architecture (`C.A`)**이며 3D 좌표는 입력입니다.

```bash
cd admin-2026-protein-data
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_cath.py      # 공식 원본만 data/raw/에 다운로드
python scripts/prepare_dataset.py    # 서열·3D 전처리 후 학습/평가 파일 생성
python scripts/verify_dataset.py     # 결과 검증
```

`data/raw/`에는 CATH 원본과 SHA-256 기록(`manifest.json`)이 저장됩니다. `data/public/`에는 참가자용 `train.csv`, `train_structures.zip`, `train_features.csv`, 검증 분할, 학습 샘플 3건에서 복사한 추론 예제가 생성됩니다. `data/private/`에는 서버 전용 `test.csv`, `test_structures.zip`, `test_features.csv`, `labels.csv`, 원본 ID 매핑과 체크섬 기록이 생성됩니다. **`private/` 전체를 참가자 다운로드나 추론 컨테이너에 제공하지 마세요.** 생성물은 모두 Git에서 제외합니다. `prepare_dataset.py`도 원본이 없으면 다운로드를 먼저 수행하므로 **한 명령으로 생성하려면 이 명령만 실행**해도 됩니다. 기존 정답 파일은 덮어쓰지 않습니다. 대회 중 데이터 교체는 기존 제출 점수의 의미를 바꾸므로 하지 마세요.

웹사이트 저장소와 같은 상위 디렉터리에 이 저장소를 두면 웹사이트의 Docker Compose가 `../admin-2026-protein-data/data`를 API에 읽기 전용으로 연결합니다. 다른 위치라면 웹사이트 `.env`의 `DATA_HOST_DIR`을 설정하세요.

## 현재 구현 상태

전처리는 숨김 평가 입력과 정답을 `data/private/`에 분리합니다. **웹사이트 API는 아직 기존 CSV 제출 프로토타입**을 사용하므로 `test.csv` 다운로드 경로, 추론 작업자, 모델 제출 채점 흐름을 별도로 수정해야 합니다. 데이터 생성본만으로 새 대회가 바로 운영되는 것은 아닙니다.

데이터 생성만으로 외부 자료 사용 여부를 증명할 수 없습니다. 새 대회에는 제공 학습 데이터만 사용하도록 규정하고, 상위 팀의 학습 코드·모델을 재현 검증해야 합니다. 팀별 업무와 운영진 문의사항은 [팀별 남은 과제와 문의사항](https://github.com/2026-admin-ai-challenge/admin-2026-protein-structure-challenge/blob/main/ADMIN_%ED%8C%80%EB%B3%84_%EB%82%A8%EC%9D%80_%EA%B3%BC%EC%A0%9C%EC%99%80_%EB%AC%B8%EC%9D%98%EC%82%AC%ED%95%AD.md)을 참조하세요.
