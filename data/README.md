# CATH competition data

public/: train.csv, train_structures.zip, train_features.csv, validation_split.csv, example_* and metadata.json. 참가자 제공 가능.
private/: test.csv, test_structures.zip, test_features.csv (hidden evaluation inputs), labels.csv (hidden answers and public/private partition), id_mapping.csv (original domain and C.A.T.H), manifest.json; 운영진 전용, Git ignored.
raw/: official CATH downloads and source checksum manifest; Git ignored.

CATH © Orengo Group/UCL, CC BY 4.0. Source: https://www.cathdb.info/download. 본 데이터는 서열 정제, 클래스 선택, 익명화, homology-aware split을 적용한 파생물입니다. 고정 시드 파이프라인과 원본 공개 DB를 이용한 시험 정답 재구성이 가능하므로 대회 규칙을 준수하세요.
