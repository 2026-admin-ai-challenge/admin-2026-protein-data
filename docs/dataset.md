# Dataset provenance and structural audit

공식 CATH-Plus v4.4 S40 ATOM FASTA, domain PDB archive, classification을 domain ID로 결합합니다. URL·SHA-256은 metadata.json에 기록합니다. 전체 서열 FASTA도 원본 기록으로 보관하지만 이번 입력은 **관측 ATOM 도메인 서열**입니다.

비표준 잔기를 포함한 샘플, 길이 40–1200 밖의 샘플, 중복 domain/sequence를 제거합니다. PDB 첫 모델의 ATOM 잔기 순서가 관측 FASTA와 정확히 일치해야 합니다. 근사 alignment는 하지 않습니다. 최소 40개 Cα, coverage 95% 이상을 요구합니다. 대소문자가 다른 chain/domain ID가 macOS에서 충돌하지 않도록 원본 캐시 파일명은 ASCII hex로 인코딩합니다.

구조 대응을 통과한 27,779개 중, 샘플 50개 이상이며 train/test 및 학습 내부 검증용 H-group 분할이 가능한 상위 20개 Architecture를 선택합니다. 최종 **26,961개 / train 21,568 / test 5,393 / 20개 클래스**. 관측 서열 길이 평균 152.0016, 중앙값 129, 범위 40–1146. 원본 구조 대응 검사에서 6,291개 불일치와 Cα coverage 미달 1개를 제외했습니다. 보수적인 제외 정책이며 누락 좌표를 추정하지 않습니다.

완전한 C.A.T.H를 group으로 쓰고 클래스별 subset-sum으로 test 약 20%를 선택합니다. 각 클래스 최소 train 20/test 10 및 학습 내부 검증 가능성을 요구합니다. 15개 클래스 미만이면 중단합니다. 공개 validation_split.csv에는 TRAIN ID와 fit/validation만 있으며 H-group 코드는 없습니다. 검증 분할에도 계열 중복이 없습니다. 시험 내부 Public/Private는 클래스별 30/70 seeded shuffle이며 모든 클래스가 양쪽에 남습니다. 시험 내부에는 별도 H-group 분리를 적용하지 않습니다.

좌표 스키마, 누락 mask, altloc, backbone 단절, 거리 특징 정의는 [structure-format.md](structure-format.md)를 참조하세요. train/test 구조 파일에는 정답·원본 ID·분류 코드·PDB header가 없습니다. 좌표 중심화는 평행이동에만 해당하며 회전은 하지 않습니다. 31개 기본 특징은 회전·평행이동에 불변이고 label을 사용하지 않습니다.

`python scripts/verify_dataset.py`가 모든 공개 파일 hash, ID/서열/domain/H 중복, 정답 partition, 클래스 coverage를 확인합니다. 이어서 **모든 NPZ**의 서열 대응, 좌표·mask, 연속 구간 정보, 특징 재계산, 검증 분할, starter ZIP의 고정 파일 목록을 검사합니다.

`prepare_dataset.py`는 기존 private/labels.csv 덮어쓰기를 거부합니다. `--root work/new-dataset`으로 독립 staging 경로를 지정할 수 있습니다. 기존 대회에 제출이 있으면 데이터 교체를 하지 마세요. 새 대회는 새 DB·데이터를 사용합니다. 이번 전환은 준비 상태(참가자·제출 0)에서 이전 데이터를 보관하고 진행합니다.

공개 원본과 재현 가능한 생성 코드만으로 숨김 정답을 재구성할 수 있습니다. 원본 ID를 숨겨도 서열·구조 검색으로 시험 샘플을 식별할 수 있습니다. 저장소 Private 유지, 정답 검색 금지 규칙, 상위 팀 코드 재현 검증이 필요합니다.

Source: CATH © Orengo Group/UCL, CC BY 4.0. 파생 변경: 관측 서열 정제·구조 대응·Cα 중심화·좌표·특징 계산·클래스 선택·익명화·분할.

대회 전 공개: `/api/resources/baseline`의 baseline_code.zip은 코드·노트북·설명서만 포함합니다. 데이터·특징 표·좌표·시험 정답은 없으며 전체 Starter Kit은 대회 시간 제한을 유지합니다.
