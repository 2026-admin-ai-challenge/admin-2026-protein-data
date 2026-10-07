# Dataset provenance and structural audit

공개 `metadata.json`의 `samples_per_class`와 `sequence_length`, 공개 분포 그림은 학습 데이터만으로 계산합니다(`distribution_scope: train`). 전체 학습·평가 건수는 유지하지만 평가 클래스별 개수와 길이 분포는 공개 통계에 포함하지 않습니다.

공식 CATH-Plus v4.4 S40 ATOM FASTA, domain PDB archive, classification을 domain ID로 결합합니다. URL·SHA-256은 metadata.json에 기록합니다. 전체 서열 FASTA도 원본 기록으로 보관하지만 이번 입력은 **관측 ATOM 도메인 서열**입니다.

현재 데이터는 2026-10-07에 N-04·N-02·N-05를 반영해 공식 원본에서 다시 생성한 버전입니다. 기준은 PR #11의 `cb2f530`이며, 남은 샘플의 ID와 모든 분할은 기준 버전과 동일합니다. 제외된 ID는 재사용하지 않으므로 번호에 빈칸이 있습니다.

PR #6·#8은 `cb2f530` 이전 분할의 모델 결과입니다. 이번 분할 고정이 그 모델의 과거 학습 이력을 지우지는 않습니다. 비교하려면 현재 데이터로 재학습·재평가해야 합니다. 베이스라인 학습 내부 검증 Macro F1은 0.24853입니다.

비표준 잔기를 포함한 샘플, 길이 40–1200 밖의 샘플, 중복 domain/sequence를 제거합니다. PDB 첫 모델의 ATOM 잔기 순서가 관측 FASTA와 정확히 일치해야 합니다. 근사 alignment는 하지 않습니다. 최소 40개 Cα, coverage 95% 이상을 요구합니다. 기존 검토 33개와 Day 4 모양 혼합 33개, 합계 66개는 운영진 전용 `data/private/quality_exclusions.csv`의 원본 domain ID로 제외합니다. 이웃이 아닌 Cα가 3.0 Å 미만으로 겹치는 구조와 같은 연속 구간의 이웃 Cα 선택이 서로 다른 명시적 altloc인 구조를 제외합니다. 후자는 거리 이상이 없어도 적용하는 보수적 품질 규칙입니다. 공유 blank 좌표와 서로 다른 구간의 altloc는 허용합니다. 대소문자가 다른 chain/domain ID가 macOS에서 충돌하지 않도록 원본 캐시 파일명은 ASCII hex로 인코딩합니다.

구조 대응을 통과한 27,477개 중 기준 배정표의 20개 Architecture를 유지합니다. 최종 **26,669개 / train 21,339 / test 5,330 / 20개 클래스**. 공개 학습 서열 통계는 평균 149.4527, 중앙값 127, 범위 40–1,031입니다. 구조 처리에서 서열 불일치 6,291개, coverage 미달 1개, 수동 제외 66개, 명시적 이웃 altloc 불일치 227개, 비이웃 Cα 충돌 8개, 호환되지 않는 대체 위치 1개를 제외했습니다. 자동 제외 227개 중 이전 최종 데이터에 있던 것은 218개이고 나머지 9개는 대상 클래스 밖입니다.

`data/private/split_assignments.csv`는 `cb2f530`의 원본 domain·H-superfamily·라벨·익명 ID·train/test·Public/Private·fit/validation을 저장합니다. 제외 시 배정표에서 제거하지 않고 활성 데이터에서만 빠지게 합니다. 원본 해시, H-group과 라벨 변경, 미배정 domain은 오류로 중단합니다. 원래 약 80/20·30/70이던 비율은 재균형하지 않습니다. 현재 평가 Public/Private는 1,599/3,731, 학습 fit/validation은 17,072/4,267입니다. 각 클래스 최소 train 20/test 10 및 모든 partition/fold의 클래스 존재를 검사합니다.

N-03: 서로 다른 domain의 부분 서열 겹침은 현행 기준상 허용하며 보고된 평가 30개를 모두 유지했습니다. 완전 중복 서열·domain·H-group의 train/test 중복은 계속 금지합니다. D-02: `segment_index`는 기존 번호·좌표 규칙을 유지하며 물리적인 C–N 결합 판정으로 변경하지 않습니다.

좌표 스키마, 누락 mask, altloc, backbone 단절, 거리 특징 정의는 [structure-format.md](structure-format.md)를 참조하세요. train/test 구조 파일에는 정답·원본 ID·분류 코드·PDB header가 없습니다. 좌표 중심화는 평행이동에만 해당하며 회전은 하지 않습니다. 31개 기본 특징은 회전·평행이동에 불변이고 label을 사용하지 않습니다.

`python scripts/verify_dataset.py`가 모든 공개 파일 hash, ID/서열/domain/H 중복, 정답 partition, 클래스 coverage를 확인합니다. 이어서 **모든 NPZ**의 서열 대응, 좌표·mask, 연속 구간 정보, 특징 재계산, 검증 분할, starter ZIP의 고정 파일 목록을 검사합니다.

`prepare_dataset.py`는 기존 private/labels.csv 덮어쓰기를 거부합니다. `--root work/new-dataset`으로 독립 staging 경로를 지정할 수 있습니다. 기존 대회에 제출이 있으면 데이터 교체를 하지 마세요. 새 대회는 새 DB·데이터를 사용합니다. 이번 PR은 데이터 생성본을 제안하며 웹사이트·채점 서버 배포와 기존 제출 재채점은 포함하지 않습니다. 이미 공개된 학습 파일이 있다면 배포 이력을 운영진이 확인해야 합니다.

공개 원본과 재현 가능한 생성 코드만으로 숨김 정답을 재구성할 수 있습니다. 원본 ID를 숨겨도 서열·구조 검색으로 시험 샘플을 식별할 수 있습니다. 저장소 Private 유지, 정답 검색 금지 규칙, 상위 팀 코드 재현 검증이 필요합니다.

Source: CATH © Orengo Group/UCL, CC BY 4.0. 파생 변경: 관측 서열 정제·구조 대응·Cα 중심화·좌표·특징 계산·클래스 선택·익명화·분할.

대회 전 공개: `/api/resources/baseline`의 baseline_code.zip은 코드·노트북·설명서만 포함합니다. 데이터·특징 표·좌표·시험 정답은 없으며 전체 Starter Kit은 대회 시간 제한을 유지합니다.
