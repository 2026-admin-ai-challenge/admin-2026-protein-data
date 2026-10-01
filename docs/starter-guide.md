# ADMIN structure classification starter kit

기본 Logistic Regression으로 학습 내부 검증과 추론 예제를 실행할 수 있습니다. 목표는 **주어진 서열과 3D 구조의 CATH Architecture (`C.A`) 분류**입니다. `train.csv`의 `label`이 target입니다.

1. `starter_kit.zip`을 새 폴더에 압축 해제합니다. Python 3.12를 권장합니다.
2. `python -m pip install -r requirements.txt`
3. `python baseline.py` 또는 같은 폴더에서 `baseline.ipynb` 실행
4. 생성된 `example_prediction.csv`로 `id,label` 출력 형식을 확인합니다. 이 파일은 제출용이 아닙니다.

베이스라인은 제공된 31개 서열·구조 통계 특징과 StandardScaler + Logistic Regression만 사용합니다. 검증은 제공된 H-group 분할을 씁니다. 전체 train으로 다시 학습한 뒤 학습 데이터에서 복사한 예제 3건을 예측합니다. 숨김 평가 입력은 참가자에게 제공되지 않습니다.

전체 학습 3D 좌표는 별도 `train_structures.zip`으로 제공됩니다. `example_structures.zip`은 Starter Kit에 포함됩니다. `structure-format.md`에 배열 형식이 있습니다.

`label`은 반드시 문자열로 읽으세요 (`dtype=str`). 원본 CATH/PDB 검색을 통해 시험 정답을 복구하거나 사람이 정답을 작성하는 것은 금지합니다. 제공된 입력의 구조적 특징을 계산하고 모델로 학습하는 것은 허용됩니다. 외부 데이터·사전학습 모델 사용 여부는 최종 대회 규칙을 따르세요.

숨김 평가 입력과 정답은 운영 서버 전용입니다. 실제 모델 ZIP 제출 형식은 별도 대회 계약을 따릅니다. 파일 구성과 라이선스는 `structure-format.md`에 있습니다.
> **기존 CSV 제출 프로토타입 안내입니다.** 새 대회의 모델 ZIP 제출과 제공 데이터만 사용 규정으로 갱신해야 합니다.
