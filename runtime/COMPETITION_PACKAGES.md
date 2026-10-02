# 대회 공통 라이브러리 기준

Python은 CPython 3.12.14로 유지합니다. 기본 수치 계산 버전을 바꾸지 않고 확장 목록의 의존성을 함께 해결했으며, 정확한 89개 버전은 `requirements-competition.lock.txt`에 기록했습니다. 설치 목록은 실행 환경의 가용 패키지를 뜻합니다. 대회에서 외부 데이터·사전학습 가중치·네트워크 사용을 허용한다는 뜻은 아닙니다. 해당 규정은 별도로 정해야 합니다.

| 용도 | 주요 패키지·고정 버전 |
|---|---|
| 수치·표 데이터 | numpy 2.5.3, pandas 3.0.6, scipy 1.18.1 |
| 기본 머신러닝 | scikit-learn 1.9.1 |
| 부스팅 | xgboost 3.4.1, lightgbm 4.7.0, catboost 1.2.10 |
| 딥러닝 | torch 2.14.1, torchvision 0.29.1, torchaudio 2.11.0 |
| Transformer·학습 보조 | transformers 5.18.0, accelerate 1.15.0, einops 0.8.2 |
| 데이터셋·토큰화 | datasets 5.0.1, tokenizers 0.23.2, huggingface-hub 1.33.0 |
| 모델 저장 | safetensors 0.8.0, joblib 1.6.0, h5py 3.16.0 |
| 단백질·그래프 | biopython 1.88, networkx 3.7 |
| 튜닝 | optuna 5.0.0 |
| 시각화 | matplotlib 3.11.2, plotly 7.1.0, pillow 12.3.0 |
| 설정·진행 표시 | PyYAML 6.0.3, tqdm 4.70.1 |
| HTTP | requests 2.34.2 |

## 설치 및 검사

```powershell
./.venv/Scripts/python.exe -m pip install -r runtime/requirements-competition.lock.txt
./.venv/Scripts/python.exe runtime/check_environment.py --competition
./.venv/Scripts/python.exe -m pip check
```

학습 환경과 서버 검증 환경에 동일한 목록을 제공합니다. 제출 시 새로운 패키지를 자동 설치하지 않습니다. TensorFlow, JAX, PyG, DGL, CUDA 확장은 현재 목록에 포함하지 않습니다. 이런 프레임워크는 참가자 요구와 운영 하드웨어를 확인한 뒤 공통 환경의 별도 버전으로 추가합니다.

Windows에서 해결한 버전 목록을 Linux 서버 환경 검증 완료로 간주하지 않습니다. 특히 torch와 torchvision·torchaudio의 바이너리 조합은 각 운영 이미지에서 확인해야 합니다. GPU 프로필의 CUDA·드라이버·torch 빌드와 이미지 digest는 아직 확정하지 않았습니다.

## 실제 확인 결과

2026-10-02 Windows AMD64·CPython 3.12.14에서 전체 설치, 89개 버전 검사와 `pip check`가 통과했습니다. `smoke_common.py`에서 주요 확장 모듈 21개 import, XGBoost·LightGBM·CatBoost 학습/예측, 작은 BERT의 CPU 순전파, safetensors 저장/로드, 단백질 서열 처리가 모두 통과했습니다. 네트워크로 사전학습 모델을 받지 않았습니다.

로그는 `check-common.log`, `smoke-common.log`, `install-common.log`에 있습니다. 대회 운영 서버 검증 전까지 이 목록은 공통 환경 후보로 관리합니다. Windows 실행에서 Visual C++ 런타임 안내가 출력됐지만 위 실행 검사는 통과했습니다.

확장 패키지 설치 후 기존 전처리 테스트도 9개 모두 통과했습니다(41.68초). 결과는 `regression-common.log`에 기록했습니다.
