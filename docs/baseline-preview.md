# ADMIN · 대회 전 공개 베이스라인

이 ZIP에는 **코드와 설명서만** 있습니다. 실제 학습·시험 데이터, 특징 표, 정답, 구조 좌표는 포함하지 않습니다. 대회 전에 환경을 설치하고 코드를 살펴볼 수 있습니다.

1. 이 ZIP을 새 폴더에 압축 해제합니다. Python 3.12를 권장합니다.
2. `python -m pip install -r requirements.txt`로 환경을 준비합니다. GPU는 필요 없습니다.
3. 대회 시작 후 사이트 Data에서 **Starter Kit**을 내려받아 별도 폴더에 압축 해제합니다. 그 키트에는 코드와 필요한 CSV가 모두 들어 있습니다.
4. Starter Kit 폴더에서 `python baseline.py` 또는 `baseline.ipynb`를 실행합니다.
5. 생성된 `submission.csv`를 사이트에 제출합니다.

코드를 미리 수정했다면 별도로 보관하세요. 수정한 코드를 계속 쓰려면 대회 시작 후 train.csv, test.csv, train_features.csv, test_features.csv, validation_split.csv를 같은 폴더에 놓으면 됩니다. 대회 시작 전에는 실제 데이터가 없으므로 학습을 실행할 수 없습니다.

과제: 제공된 관측 아미노산 서열과 실험 3D 구조에서 CATH Architecture를 분류합니다. 베이스라인은 제공될 31개 서열 조성·구조 통계 특징 + StandardScaler + Logistic Regression입니다. `structure_features.py`에서 특징 정의를 볼 수 있습니다. `structure-format.md`에는 좌표 mask와 NumPy 파일 로딩 방법이 있습니다.

대회 시작 후 학습·시험 구조 파일을 별도로 받을 수 있습니다. 제공된 입력을 어떻게 활용할지는 자유롭게 선택하세요. 실제 CATH/PDB 정답 조회는 금지합니다. 데이터 사용 규칙과 출처는 사이트 Rules 및 structure-format.md를 확인하세요.
> **기존 CSV 제출 프로토타입 안내입니다.** 새 대회 참가자에게 공개하기 전에 모델 ZIP 제출 형식으로 갱신해야 합니다.
