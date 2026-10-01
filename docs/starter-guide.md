# ADMIN structure classification starter kit

CPU로 첫 제출까지 실행할 수 있는 기본 Logistic Regression입니다. 서열만으로 접힘을 예측하는 과제가 아니라 **주어진 서열과 3D 구조의 Architecture 분류**입니다.

1. `starter_kit.zip`을 새 폴더에 압축 해제합니다. Python 3.12를 권장합니다.
2. `python -m pip install -r requirements.txt`
3. `python baseline.py` 또는 같은 폴더에서 `baseline.ipynb` 실행
4. 생성된 `submission.csv`를 사이트 Submit에 제출합니다.

베이스라인은 제공된 31개 서열·구조 통계 특징과 StandardScaler + Logistic Regression만 사용합니다. GPU, 구조 원본, 구조 ZIP 다운로드 없이 실행됩니다. 검증은 제공된 H-group 분할을 쓰며, 검증 결과는 실제 leaderboard 점수와 다를 수 있습니다. 전체 train으로 다시 학습한 뒤 test 예측을 저장합니다. sample_submission.csv의 label은 형식 예시일 뿐 정답이 아닙니다.

서열과 좌표를 활용하는 방법은 자유롭게 선택하세요. 구조 파일이 필요하면 `train_structures.zip`, `test_structures.zip`을 내려받고 `structure-format.md`를 읽으세요. `structure_features.py`는 기본 특징의 계산 방법을 보여줍니다.

`label`은 반드시 문자열로 읽으세요 (`dtype=str`). 원본 CATH/PDB 검색을 통해 시험 정답을 복구하거나 사람이 정답을 작성하는 것은 금지합니다. 제공된 입력의 구조적 특징을 계산하고 모델로 학습하는 것은 허용됩니다. pretrained 모델은 대회 Rules를 따르고 출처를 기록하세요.

데이터와 이 Starter Kit은 대회 시작부터 종료 시각까지만 내려받을 수 있습니다. 코드만 포함한 별도 공개 베이스라인 ZIP은 대회 전후에도 받을 수 있습니다. 파일 구성·좌표 누락·연속 구간 정보·데이터 출처와 라이선스는 `structure-format.md`에 있습니다.
> **기존 CSV 제출 프로토타입 안내입니다.** 새 대회의 모델 ZIP 제출과 제공 데이터만 사용 규정으로 갱신해야 합니다.
