# Day 4 생성 수정·재생성 보고서

작성일: 2026-10-07. 기준 데이터: PR #11이 병합된 `cb2f530c266f276d94a03eb63da7c4df56f0339c`. PR #12의 품질 보고서를 생성 코드·원본·실제 산출물과 대조해 N-04, N-02, N-05를 반영했다.

## 적용한 정책

| 항목 | 처리 | 근거 |
| --- | --- | --- |
| N-04 분할 변화 | 수정 | 같은 seed는 입력 변화에 대한 안정성을 보장하지 않는다. 기존 12개 제외만으로 학습→평가 1,194개 이동을 재현했다. |
| N-02 모양 혼합 | 수정 | 보고된 33개/44개 이웃 쌍 모두 공식 CATH domain PDB에서 이웃의 A/B 좌표가 하나씩 미리 선택돼 있었다. 복구할 대체 좌표가 없으므로 제외하며 일반 검사도 추가한다. |
| N-03 부분 서열 겹침 | 허용·참고 | 기존 정책은 exact sequence/domain/H-group 중복을 금지한다. 부분 겹침은 금지하지 않는다. 보고된 평가 30개를 모두 유지한다. |
| D-02 번호 때문에 구간 분리 | 현 규격 유지 | 실제 단절과 번호 기반 구간 경계를 구별한다. 기존 문서는 번호 gap/reversal 등을 끊도록 정의하므로 규격 위반이 아니다. C–N 기반 연결 규격으로 바꾸지 않는다. |
| N-05 평가 통계 공개 | 수정 | metadata와 분포 그림을 학습 전용으로 계산하고 실제 학습 값과 대조한다. |

N-03 포함 관계 21쌍 중 동일 라벨은 4쌍, 추가 근접 11쌍 중 동일 라벨은 3쌍이다. 추가 11쌍의 짧은/긴 길이 비율은 약 12~64%이며 짧은 쪽 기준의 높은 일치율이 전체 domain 동일성을 의미하지 않는다. 따라서 30개를 전부 정답 누출로 단정하거나 일괄 제외하지 않는다.

## N-04: 분할과 ID를 함께 고정

- `data/private/split_assignments.csv`에 기준 버전의 원본 domain, H-superfamily, Architecture, 익명 ID, train/test, Public/Private, fit/validation을 저장한다. 기준 26,920개 전부를 보존하며 제외된 행도 지우지 않는다.
- `split_assignments.json`은 기준 commit, 기준 파일 해시, 배정표 해시와 공식 원본 4개의 해시를 기록한다.
- 생성 시 기존 배정을 따라 활성 샘플만 골라낸다. ID는 재사용하지 않으며 빈 번호가 생겨도 다시 매기지 않는다. class 선택도 기준의 20개로 고정한다.
- 원본 해시·H-group·라벨이 바뀌거나 미배정 domain이 나타나면 중단한다. 자동으로 새로운 subset-sum 조합을 뽑지 않는다.
- 전체 기준 배정표의 H-group 교차, 활성 샘플의 exact sequence/domain/H 중복, 최소 클래스 수와 모든 partition/fold의 클래스 존재를 검사한다.
- 최초 배정표 작성 명령은 `python -m scripts.freeze_split_assignments --root <기준 데이터> --output <새 배정표.csv> --reference <기준 commit>`이다. 기존 배정표는 덮어쓰지 않는다. 이번 PR의 배정표를 재생성 때 그대로 사용하는 것이 기본이다.

비율을 맞추기 위한 재균형은 하지 않는다. 현재 버전 고정은 과거 공개 학습 파일의 노출을 취소하지 않으므로, 운영 데이터 교체와 과거 모델·제출 재평가 여부는 실제 배포 이력을 확인한 뒤 정해야 한다.

## N-02: 확인된 사례 제외와 재발 방지

기존 수동 제외 33개에 Day 4의 학습 32개·평가 1개를 `P-30`으로 추가해 수동 제외는 66개다. 보고서의 33개 원본을 직접 확인했고, 수동 목록을 적용하지 않고 parser에 넣어도 33개 모두 새 일반 검사로 거부되는 것을 확인했다.

`choose_ca_locations()`는 선택한 altloc 글자를 내부에 보관한다. 같은 chain에서 현재 번호·좌표 규칙상 하나의 구간으로 연결될 이웃이 서로 다른 명시적 글자(A/B 등)를 선택하면 `adjacent_altloc_mismatch`로 제외한다. 거리 이상 여부에 의존하지 않으므로 정상 범위 안에 숨은 혼합도 걸러낸다. 공유 blank 위치, 누락 좌표, 다른 chain/구간은 같은 글자를 강제하지 않는다. 대체 좌표가 남은 경우 기존 domain 전체 점유율 선택을 유지한다. 결합이 짧다는 이유만으로 coherent cis 구조를 제외하지 않는다.

이 검사는 **보수적 source 품질 규칙**이다. 모든 글자 불일치가 물리적 좌표 오류라고 독립 확정한 것은 아니다. 반대로 altloc 글자가 원본에서 사라진 경우나 다른 구간에 걸친 혼합은 완전히 판별할 수 없다.

수동 제외 외 자동 검사는 전체 정제 원본 227개에서 불일치를 찾았다. 이 중 기존 최종 데이터에 있던 것은 218개(학습 165, 평가 53), 대상 20개 클래스 밖은 9개다. 추가 218개는 원본의 명시적 글자 불일치 규칙에 따른 보수적 제외이며, 거리 대조로 확인된 Day 4의 33개와 구분한다. 전체 원본 domain별 제외 사유는 운영진 전용 `data/private/structure_rejections.csv`에 기록한다.

## N-05: 공개 분포를 학습 전용으로 제한

- `samples_per_class`, `sequence_length`, 클래스 분포 PNG, 길이 분포 PNG는 모두 train만 사용한다.
- `distribution_scope: train`으로 의미를 명시한다. 전체 train/test 건수는 계속 공개하지만 평가 클래스별 개수와 길이 분포를 계산에 넣지 않는다.
- 공개 클래스별 개수 합계는 21,339. 길이는 평균 149.452739, 중앙값 127, 범위 40~1,031.
- 검증은 공개 통계를 실제 train으로 재계산한다. 기존 전체 데이터 합계 방식은 통과하지 않는다.

## 재생성 결과

| 항목 | 기준 `cb2f530` | 이번 생성본 | 변화 |
| --- | ---: | ---: | ---: |
| 전체 | 26,920 | 26,669 | -251 |
| 학습 | 21,536 | 21,339 | -197 |
| 평가 | 5,384 | 5,330 | -54 |
| 평가 Public | 1,615 | 1,599 | -16 |
| 평가 Private | 3,769 | 3,731 | -38 |
| 학습 fit | 17,229 | 17,072 | -157 |
| 학습 validation | 4,307 | 4,267 | -40 |
| 클래스 | 20 | 20 | 0 |

제외된 251개 = Day 4 수동 33개 + 추가 자동 218개. 남은 샘플의 train/test·Public/Private·fit/validation 변경 0, 익명 ID·domain·H-group 변경 0. 남은 26,669개 NPZ의 좌표·mask·residue·segment 배열은 기준 버전과 모두 정확히 같다. D-02 규칙과 기존 좌표를 변경하지 않고 문제가 있는 샘플을 제거한 결과다.

정제 원본의 구조 대응 통과는 27,477개다. 수동 제외 66, 자동 altloc 불일치 227, 서열 불일치 6,291, coverage 미달 1, 비이웃 충돌 8, 호환되지 않는 altloc 1. 최종 20개 클래스 외의 제외도 이 원본 통계에 포함되므로 최종 데이터 감소 251과 단순 합산하지 않는다.

## 실행과 검증

Python 3.12.14/macOS arm64, `requirements.txt` 고정 버전(numpy 2.5.3, pandas 3.0.6, scipy 1.18.1, matplotlib 3.11.2, scikit-learn 1.9.1, pytest 9.1.1)으로 실행했다.

```bash
python scripts/prepare_dataset.py --root work/new-dataset
python scripts/verify_dataset.py --root work/new-dataset
python -m pytest -q
python -m scripts.audit_dataset
python scripts/baseline.py --output work/example_prediction.csv
```

생성 명령은 이제 체크섬과 DATA_VERSION도 함께 작성한다. raw/source/cache는 Git에서 제외하고 운영진 정책 CSV/JSON은 private에만 보관한다. ZIP의 날짜를 고정해 생성 시간·파일 mtime 때문에 패키지 해시가 흔들리지 않게 했다. 모든 배포 파일과 운영진 정책 파일 23개의 체크섬을 기록한다.

- 전체 테스트 69개 통과. source altloc의 정상 거리 혼합, 공유 blank, 서로 다른 구간, coherent cis, 제외 후 배정/ID 유지, 미배정 domain·H-group 불일치·빈 partition 거부를 포함한다.
- 전체 `verify_dataset` PASS: 좌표/서열/마스크/구간/31개 특징 재계산, 모든 분할, exact/domain/H 중복, Starter Kit 허용 목록, 23개 파일 해시와 버전 검증.
- 원본 FASTA/분류표 전수 감사 PASS: 모든 활성 샘플의 서열·Architecture·H-superfamily 일치, CSV 11개 결측 표기 0.
- PR #11 기준 파일과 survivor 배정 및 모든 NPZ 배열 전수 비교 완료.
- 최종 코드로 fresh staging root에서 다시 전수 생성했다. 두 실행의 생성/정책 파일 23개와 DATA_VERSION이 모두 바이트 단위로 일치한다.
- 베이스라인 학습 내부 검증 Macro F1 0.24853, 예제 예측 3건 생성. 이는 그래프 모델 재학습 결과나 숨김 평가 점수가 아니다.
- Linux `test`/`data-linux` 결과는 PR의 GitHub Actions에서 별도 확인한다.

PR #12의 점검 수치는 수정 전 `cb2f530`의 기록이며 이 보고서가 생성 수정 후 결과다. 웹사이트·채점 서버 배포 및 과거 제출 재채점은 이 PR에 포함하지 않는다.
