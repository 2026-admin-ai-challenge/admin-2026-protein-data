# 데이터 검증 보고서

대상: 2026-10-07 N-04·N-02·N-05 재생성 데이터. 생성 기준과 검증 세부는 [Day 4 생성 수정 보고서](quality/day4-generation-resolution.md).

| 항목 | 결과 |
| --- | --- |
| 학습 / 평가 / 클래스 | 21,339 / 5,330 / 20 |
| 평가 Public / Private | 1,599 / 3,731 |
| fit / validation | 17,072 / 4,267 |
| 기준 버전 대비 활성 샘플 분할·ID 변경 | 0 |
| 기준 버전 대비 활성 NPZ 배열 차이 | 0 |
| 공개 분포 | 학습 전용, metadata와 실제 train 일치 |
| 구조·특징·서열·mask·segment 전수 검증 | PASS |
| exact sequence/domain/H train/test 중복 | 0 |
| Starter Kit·baseline code 허용 목록 | PASS |
| 원본 FASTA·분류표 전수 감사 | PASS |
| CSV 결측 표기 | 0 (11개 생성/감사 CSV; 정책 CSV는 별도 검사) |
| 체크섬 | 공개·운영진 파일 23개, DATA_VERSION 연계 PASS |
| 전체 테스트 | 69 passed (Python 3.12.14, 고정 requirements.txt) |
| 새 staging root 재생성 재현성 | 23개 파일 및 DATA_VERSION 바이트 단위 일치 |

`verify_dataset.py`는 기준 배정표와 provenance hash까지 대조한다. 생성은 fresh staging root만 허용하고 원본 파일 해시가 기준과 다르면 중단한다. 정책 배정표는 운영진 전용이며 참가자 ZIP에 포함되지 않는다.

좌표 coverage 95% 정책은 유지한다. 현재 학습 188개 구조/194개 잔기, 평가 61개 구조/61개 잔기에 좌표 누락이 있고 mask로 명시한다. Linux 검증은 CI의 `data-linux` job에서 같은 전체 검사를 수행한다.
