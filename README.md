# ADMIN 2026 대회 데이터·베이스라인

## 팀원용 데이터셋 받기

전처리가 완료된 파일 19개를 이 비공개 저장소의 `data/public/`과 `data/private/`에 직접 포함합니다. `main`을 clone하면 데이터를 함께 받습니다. 별도 Release 다운로드나 전처리 재실행은 필요하지 않습니다. 대회 중에는 저장소를 운영진 전용 비공개로 유지하고, 대회 종료 후 평가 정답 공개 여부를 결정한 다음 저장소 공개를 검토합니다.

```bash
git clone https://github.com/2026-admin-ai-challenge/admin-2026-protein-data.git
```

- 학습 21,545개 / 평가 5,387개 / 20개 클래스 (품질 재생성본)
- 학습 및 예제 데이터: `data/public/`
- 운영진 평가 입력·정답·ID 매핑: `data/private/`
- 파일별 체크섬: `data/DATASET_CHECKSUMS.json`

참가자용 배포에는 `data/public/`만 사용합니다. 공식 원본과 중간 캐시, Python 가상환경은 Git에서 제외합니다. 기존 파일 검증은 `./run-preprocessing.ps1 -VerifyOnly`로 수행합니다. 새 데이터를 생성할 때는 기존 파일을 덮어쓰지 않고 `prepare_dataset.py --root <새 폴더>`를 사용합니다.

## Python 실행 환경 기준

자주 사용하는 대회용 라이브러리도 [공통 패키지 목록](runtime/COMPETITION_PACKAGES.md)에 추가했습니다. 정확한 전체 의존성 버전은 `runtime/requirements-competition.lock.txt`로 고정합니다.

공통 CPU 추론 환경 v1은 **CPython 3.12.14**와 현재 실행 검증을 마친 패키지 버전으로 고정합니다. 참가자의 학습·모델 저장·추론과 서버의 모델 로드가 같은 버전을 사용하도록 합니다. 정확한 패키지 목록은 `runtime/requirements-inference.lock.txt`, 설치·변경 규칙과 검증 범위는 [실행 환경 기준](runtime/README.md)을 확인하세요. 서버는 운영진의 공통 이미지를 사용하며 참가자 제출마다 패키지를 임의로 설치하지 않습니다. Linux 운영 이미지 검증과 digest 고정은 운영 적용 전 완료해야 합니다.

## 이번 로컬 작업 및 Windows 실행

GitHub Organization `2026-admin-ai-challenge`의 데이터 전용 저장소 `admin-2026-protein-data`에서 main 커밋 `ec11c626506e6bd40213fafb48182afbf3eaaa03`의 코드·문서·노트북·기존 테스트 24개 파일만 가져왔습니다. 최초 작업 당시 ChatGPT 프로젝트 폴더는 Git 저장소가 아니었으며, 데이터 파일은 별도 `admin-2026-protein-data/` 폴더에 저장했습니다. 이후 해당 데이터 폴더를 Git 저장소에 연결하고 `data/publish-dataset` 브랜치에서 데이터 업로드를 진행합니다. 웹사이트 저장소와 동기화된 `sources/` 파일은 수정하지 않았습니다.

원본 파일의 Git blob 해시는 모두 일치합니다. 출처 목록은 `IMPORT_MANIFEST.json`, 로컬 실행 안내는 `LOCAL_RUN.md`, 실제 실행 결과는 `RUN_RESULT.json`을 확인하세요. 아래 명령은 이 README가 있는 폴더에서 실행합니다.

```powershell
# Python 3.12로 새 환경을 만드는 경우
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt

# 새 데이터 생성 + 전체 검증 (출력 폴더가 비어 있어야 함)
./run-preprocessing.ps1

# 이미 생성된 데이터 검증만
./run-preprocessing.ps1 -VerifyOnly

# 베이스라인 학습 및 예제 추론
./.venv/Scripts/python.exe scripts/baseline.py --output example_prediction.csv
```

2026-10-02 최초 생성에서는 독립 `.venv`에 고정 의존성을 설치했고 공식 원본으로 총 26,961개·20개 클래스, 학습 21,568개·평가 5,393개를 생성했습니다. 당시 전체 데이터의 체크섬·서열/구조 대응·분할 누수·배포 파일 검증을 포함한 기존 테스트 9개가 모두 통과했습니다(41.17초). 당시 베이스라인 검증 Macro F1은 0.24083이었습니다. 이 수치들은 아래 품질 재생성 이전 기록입니다.

`preprocessing.log`는 원본 다운로드·전처리, `verification.log`는 전체 테스트, `baseline.log`는 학습·추론 실행 기록입니다. 상세 결과는 `RUN_RESULT.json`을 확인하세요.

| 파일 | 형식 및 역할 |
|---|---|
| `data/public/train.csv` | `id,sequence,label` 학습 데이터 |
| `data/public/train_features.csv` | `id` + 서열 조성 20개·구조 통계 11개 |
| `data/public/train_structures.zip` | 샘플별 NPZ 구조, 좌표 `pos`는 N×3 float32 |
| `data/public/validation_split.csv` | `id,fold` 학습 내부 fit/validation 분할 |
| `data/private/test.csv` | `id,sequence` 평가 입력 |
| `data/private/labels.csv` | `id,label,partition` 운영진 평가 정답 |
| `data/private/test_features.csv`, `test_structures.zip` | 평가 특징·구조 |
| `data/raw/manifest.json` | 공식 원본 URL·SHA-256·크기 |

현재 코드의 평가 입력 비공개 방식은 일반적인 참가자 `submission.csv` 제출 방식과 차이가 있습니다. 이번 작업은 저장소의 데이터 생성 정책을 유지했으며, 웹사이트 제출 방식 변경은 별도 연동 작업입니다.

[CATH v4.4 S40](https://download.cathdb.info/cath/releases/all-releases/v4_4_0/)을 받아 단백질 도메인의 관측 서열과 Cα 좌표를 검증하고, Architecture 분류용 데이터·31개 기본 특징·Logistic Regression 베이스라인을 생성합니다. 웹사이트와 채점 API는 [별도 저장소](https://github.com/2026-admin-ai-challenge/admin-2026-protein-structure-challenge)에 있습니다.

## 내용

- `scripts/download_cath.py`: 원본 다운로드와 체크섬 기록
- `scripts/prepare_dataset.py`: 정제·구조 대응·분할·배포 파일 생성
- `scripts/verify_dataset.py`, `scripts/verify_structures.py`: 파일, 분할, 좌표, 특징 검증
- `scripts/structure_features.py`: 서열 조성 20개와 구조·거리 통계 11개 특징
- `scripts/baseline.py`, `notebooks/baseline.ipynb`: 학습·예측 예제
- `docs/`: 데이터 출처, 좌표 형식, 참가자 가이드
- `tests/`: 데이터 파이프라인 검증

현재 선택 결과는 26,932개 샘플, 20개 Architecture, 학습 21,545개, 평가 5,387개입니다. PR #4 품질 판정에 따라 원본 구조 오류 21개를 제외하고 좌표 충돌·대체 위치 문제를 검사해 다시 생성했습니다. 공개 CATH 자료와 재현 가능한 생성 코드로 숨긴 평가 정답을 추적할 수 있으므로, 이 저장소는 **운영진 전용 비공개**로 유지해야 합니다.

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

`data/raw/`에는 CATH 원본과 SHA-256 기록(`manifest.json`)이 저장됩니다. `data/public/`에는 참가자용 `train.csv`, `train_structures.zip`, `train_features.csv`, 검증 분할, 학습 샘플 3건에서 복사한 추론 예제가 생성됩니다. `data/private/`에는 서버 전용 `test.csv`, `test_structures.zip`, `test_features.csv`, `labels.csv`, 원본 ID 매핑과 체크섬 기록이 생성됩니다. **`private/` 전체를 참가자 다운로드나 추론 컨테이너에 제공하지 마세요.** 생성된 공개·운영진 데이터는 운영진 공유를 위해 이 비공개 Git 저장소에 포함하며, 원본과 중간 캐시는 제외합니다. `prepare_dataset.py`도 원본이 없으면 다운로드를 먼저 수행하므로 **한 명령으로 생성하려면 이 명령만 실행**해도 됩니다. 기존 정답 파일은 덮어쓰지 않습니다. 대회 중 데이터 교체는 기존 제출 점수의 의미를 바꾸므로 하지 마세요.

웹사이트 저장소와 같은 상위 디렉터리에 이 저장소를 두면 웹사이트의 Docker Compose가 `../admin-2026-protein-data/data`를 API에 읽기 전용으로 연결합니다. 다른 위치라면 웹사이트 `.env`의 `DATA_HOST_DIR`을 설정하세요.

## 현재 구현 상태

전처리는 숨김 평가 입력과 정답을 `data/private/`에 분리합니다. **웹사이트 API는 아직 기존 CSV 제출 프로토타입**을 사용하므로 `test.csv` 다운로드 경로, 추론 작업자, 모델 제출 채점 흐름을 별도로 수정해야 합니다. 데이터 생성본만으로 새 대회가 바로 운영되는 것은 아닙니다.

데이터 생성만으로 외부 자료 사용 여부를 증명할 수 없습니다. 새 대회에는 제공 학습 데이터만 사용하도록 규정하고, 상위 팀의 학습 코드·모델을 재현 검증해야 합니다. 팀별 업무와 운영진 문의사항은 [팀별 남은 과제와 문의사항](https://github.com/2026-admin-ai-challenge/admin-2026-protein-structure-challenge/blob/main/ADMIN_%ED%8C%80%EB%B3%84_%EB%82%A8%EC%9D%80_%EA%B3%BC%EC%A0%9C%EC%99%80_%EB%AC%B8%EC%9D%98%EC%82%AC%ED%95%AD.md)을 참조하세요.
