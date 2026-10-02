# 로컬 전처리 작업

GitHub Organization: `2026-admin-ai-challenge`

데이터 저장소: https://github.com/2026-admin-ai-challenge/admin-2026-protein-data

웹사이트 저장소: https://github.com/2026-admin-ai-challenge/admin-2026-protein-structure-challenge

현재 프로젝트 폴더는 Git 저장소가 아니므로 작업 브랜치가 없습니다. 데이터 저장소 main 커밋 `ec11c626506e6bd40213fafb48182afbf3eaaa03`에서 데이터 코드·문서·노트북·기존 테스트 등 24개 파일만 GitHub 연결로 가져왔습니다. 웹사이트와 sources/는 수정하지 않았습니다. 원본 파일의 Git blob SHA 검증을 완료했습니다. IMPORT_MANIFEST.json에 경로와 출처를 기록했습니다.

## 실행 환경

독립 `.venv`에 Python 3.12와 requirements.txt의 고정 버전을 설치했습니다. PowerShell에서 이 폴더로 이동한 뒤 실행합니다.

```powershell
# 새 데이터 생성 + 전체 검증 (출력 폴더가 비어 있어야 함)
./run-preprocessing.ps1
# 이미 생성된 데이터 검증만
./run-preprocessing.ps1 -VerifyOnly
# 학습·추론 예제
./.venv/Scripts/python.exe scripts/baseline.py --output example_prediction.csv
```

## 입력과 출력

- 입력: CATH v4.4 S40 공식 FASTA, 관측 서열 FASTA, PDB 압축파일, CATH 분류표. data/raw/에 저장하며 manifest.json에 출처·SHA-256 기록.
- 정제: 표준 아미노산, 길이 40~1200, 서열 중복 제거, 관측 서열과 구조 정확 대응, Cα 좌표 최소 40개·coverage 95% 이상.
- 분할: homologous superfamily 단위로 학습/평가 분리. 평가 public/private 비율 30/70. 분류 대상은 Class.Architecture.
- 공개 출력: train.csv (`id,sequence,label`), train_structures.zip (샘플별 NPZ), train_features.csv (`id`와 특징 31개), validation_split.csv, 예제 입력·출력·특징·구조, Starter Kit, 메타데이터와 분포 이미지.
- 운영진 출력: data/private/test.csv (`id,sequence`), test_structures.zip, test_features.csv, labels.csv (`id,label,partition`), id_mapping.csv, manifest.json.
- NPZ 필드: residue_type, residue_index, segment_index, pos (N×3 float32), ca_mask.

원본 전처리 코드는 기존 출력이 있으면 중단합니다. 재생성은 새 staging root에 수행하세요. private 데이터는 운영진 저장소에 유지합니다. 현재 저장소의 평가 입력 비공개 방식은 이전 대화에서 논의한 일반 CSV 제출 방식과 다르므로, 웹사이트 연동 전 별도 정책 결정이 필요합니다.

실행 로그: preprocessing.log, verification.log, baseline.log. 실행 결과는 RUN_RESULT.json에 기록합니다.
