# 데이터 검증 보고서 (분할·누출·무결성)

작성: 김호성 (데이터팀) / 대상: 병합된 `main` 기준(`0f3537c`)의 재생성 데이터

## 1. 데이터 버전

`data/DATA_VERSION.json`이 버전 기준이다. `python scripts/make_data_version.py`로 생성하고, `verify_dataset.py`가 같은 값을 대조한다.

| 항목 | 값 |
| --- | --- |
| 출처 | CATH v4.4 S40, 시드 42 |
| 학습 / 평가 | 21,545 / 5,387 (클래스 20개) |
| 평가 Public / Private | 1,616 / 3,771 |
| 체크섬 | `data/DATASET_CHECKSUMS.json` (공개·비공개 19개 파일) |

## 2. 검사 방법과 결과

실행: `python scripts/verify_dataset.py` (내부에서 `verify_structures`도 실행). 결과: **PASS**.

| 검사 | 내용 | 결과 |
| --- | --- | --- |
| 스키마 | train `id,sequence,label`, test `id,sequence`, 예제 출력 `id,label`, 결측 없음 | 통과 |
| 건수 | metadata `stats`(학습·평가·클래스·클래스별 수)와 실제 파일 대조 | 통과 |
| 해시 | `metadata.json`, `private/manifest.json`, `DATASET_CHECKSUMS.json`의 파일 크기·sha256 | 통과 |
| 누출 | 학습/평가 간 ID·서열·원본 도메인·homologous superfamily 중복 없음 | 통과 |
| 분할 | Public/Private이 서로 겹치지 않고 합이 평가 전체와 같음. 모든 클래스가 양쪽에 포함 | 통과 |
| 예제 | 공개 예제가 학습 샘플의 부분집합이고 평가 ID와 겹치지 않음 | 통과 |
| 배포 금지 | `data/public/`에 test 관련 파일 없음. Starter Kit은 허용 목록만 포함하고 데이터 파일이 공개본과 바이트 단위로 같음 | 통과 |
| 구조 | 좌표·마스크·구간·서열 대응, 특징 재계산, H-group 검증 (학습 21,545, 평가 5,387) | 통과 |

원본 CATH 대조(서열·라벨·H-superfamily 일치)는 `docs/dataset-audit.md`(2026-10-04)의 결과를 따른다. `data/raw`가 필요해 이번에는 재실행하지 않았다.

## 3. 알려진 한계와 운영진 확인 사항

1. **좌표 누락:** 최소 coverage 95% 정책상 학습 195개, 평가 58개 구조에 Cα 좌표 누락이 있다(최저 96.875%, 97.96%). 100% 완전한 데이터가 아니다. 모두 요구하려면 해당 샘플을 제외하고 새 데이터 버전을 만들어야 한다.
2. **private 데이터가 git에 있음:** `data/private/`(평가 입력·정답)가 이 저장소에 커밋돼 있다. 저장소를 참가자에게 공유하거나 공개 전환하지 않아야 하고, collaborator 범위를 확인해야 한다.
3. **CI 범위:** CI는 실제 데이터 테스트(`real_cath_dataset`, `actual_group_split`)를 제외하고 실행한다. 이 보고서의 검사는 데이터가 있는 로컬·서버 환경에서만 실행된다.
4. **실행 환경:** 이번 검사는 Python 3.12.10(패키지는 기준 lock과 동일)에서 실행했다. 기준 3.12.14와 Linux 이미지에서의 재실행은 하지 않았다.
5. **외부 데이터 사용:** 데이터 생성 절차와 CATH 원본이 공개이므로 코드·데이터 검사만으로 외부 자료 사용 여부를 증명할 수 없다. 수상 후보의 학습 코드·모델 재현 검증과 함께 운영해야 한다.

## 4. 데이터 재생성 시 절차

1. 생성 후 `DATASET_CHECKSUMS.json`을 갱신한다.
2. `python scripts/make_data_version.py`를 실행한다.
3. `python scripts/verify_dataset.py`가 PASS인지 확인한다.
4. 이 보고서의 건수와 날짜를 갱신한다.
