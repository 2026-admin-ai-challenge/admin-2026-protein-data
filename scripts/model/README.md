# 모델 비교·평가 코드

`evaluate_models.py`: 8개 모델(Dummy, Logistic Regression, Random Forest, HistGradientBoosting, ExtraTrees, XGBoost, LightGBM, CatBoost)을 `validation_split.csv` 고정 분할, 31개 특징, CPU 2스레드, seed 42로 평가한다.

## 실행

저장소 루트에서 확장 대회 환경(`runtime/requirements-competition.lock.txt`)으로 실행한다. 전체 약 9분(대부분 CatBoost).

    .venv-competition\Scripts\python.exe scripts\model\evaluate_models.py

- 일부 모델만: `--models logistic_regression catboost`
- 학습시간 반복 횟수: `--repeats 3` (기본값)
- 다른 모델의 예측 파일(`id, y_true, y_pred`)만 같은 기준으로 평가: `--predictions 파일.csv`

## 결과 (`results/eval/`)

- `summary.csv`: 모델별 7개 지표 + 예측 시간 + 모델 크기
- `per_class/`: 20개 클래스별 precision, recall, f1, support, predicted_count
- `confusion/`: Confusion Matrix (행 = 실제, 열 = 예측)
- `predictions/`: 검증 예측 `id, y_true, y_pred`
- `run_info.json`: 패키지 버전, seed, 라벨 순서, 모델 설정, 데이터 커밋

분석 결과는 `docs/model/README.md` 참고.