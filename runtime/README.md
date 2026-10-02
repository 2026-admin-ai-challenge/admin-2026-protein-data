# Python 실행 환경 기준 v1

대회 참가자용 확장 목록은 [대회 공통 라이브러리](COMPETITION_PACKAGES.md)와 `requirements-competition.lock.txt`를 기준으로 합니다. 아래 기본 lock은 경량 scikit-learn 추론용이며, 확장 환경은 PyTorch·부스팅·단백질 처리 도구를 추가합니다.

이번 기준은 실제 전처리·베이스라인 실행이 통과한 환경을 기준으로 고정합니다.

| 항목 | 기준 |
|---|---|
| Python | CPython 3.12.14 |
| 추론 방식 | CPU |
| 서버 운영 대상 | Linux x86_64 컨테이너 |
| NumPy | 2.5.3 |
| pandas | 3.0.6 |
| SciPy | 1.18.1 |
| scikit-learn | 1.9.1 |
| threadpoolctl | 3.7.0 |
| 나머지 의존성 | requirements-inference.lock.txt의 정확한 버전 |

## 참가자와 서버가 공유할 규칙

1. 참가자는 같은 Python·패키지 버전으로 학습, 모델 저장, inference.py 검증을 수행합니다. 특히 scikit-learn 모델의 학습·로드 버전을 일치시킵니다.
2. 서버는 운영진이 미리 만든 실행 이미지를 사용합니다. 제출마다 참가자 requirements.txt를 설치하거나 고정 패키지를 변경하지 않습니다.
3. 참가자의 requirements.txt는 사용 환경 확인용입니다. 추가 라이브러리가 필요하면 운영진이 사전 검증해 새 공통 환경 버전을 배포합니다.
4. 기본 경량 lock에는 PyTorch가 없고, 확장 대회 lock에는 PyTorch가 포함됩니다. TensorFlow와 CUDA·GPU 실행 환경은 포함하지 않습니다. GPU 모델을 허용할 경우 해당 환경을 별도로 확정하고 검증해야 합니다.
5. 대회 시작 후 환경을 고정합니다. 변경이 필요하면 버전 이름·변경 내역을 공개하고 기존 제출의 재현성을 검증합니다.

## 설치와 확인

CPython 3.12.14를 준비한 뒤 데이터 저장소 루트에서 실행합니다. 전처리 환경의 requirements.txt와 추론 환경의 lock 파일은 용도가 다릅니다.

```powershell
python -m venv .venv-inference
./.venv-inference/Scripts/python.exe -m pip install -r runtime/requirements-inference.lock.txt
./.venv-inference/Scripts/python.exe runtime/check_environment.py
./.venv-inference/Scripts/python.exe -m pip check
```

Linux에서는 `.venv-inference/Scripts/python.exe` 대신 `.venv-inference/bin/python`을 사용합니다.

## 검증 범위와 다음 단계

Windows x86_64의 CPython 3.12.14에서 버전 검사, 전처리, 기존 테스트 9개, 베이스라인 학습·추론이 통과했습니다. Linux 컨테이너 실행은 아직 검증하지 않았습니다. 패키지 버전 고정만으로 OS·네이티브 라이브러리 차이까지 없어지지는 않습니다.

운영 적용 전에 Linux 이미지 빌드, 동일 모델 추론 검증, 이미지 digest 고정, 패키지 wheel·해시 보관을 완료해야 합니다. 참가자는 최종 배포된 동일 이미지를 사용해 제출을 검증합니다. inference.py의 인자, 파일 경로, 모델 로드와 출력 형식은 다음 단계에서 이 실행 환경에 맞춰 확정합니다.
