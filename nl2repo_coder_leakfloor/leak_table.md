| task | src | recorded pass/total (sr) | leak_floor pass/total | honest sr | class |
|---|---|---|---|---|---|
| fuzzywuzzy | orig | 39/71 (0.5493) | 1/71 (0.0141) | 0.5352 | partial (floor<rec) |
| google-images-download | orig | 16/30 (0.5333) | 1/30 (0.0333) | 0.5000 | partial (floor<rec) |
| justext | orig | 32/61 (0.5246) | 58/61 (0.9508) | 0.0000 | shadow-zeroed (rec<floor) |
| autorccar | orig | 6/13 (0.4615) | 6/13 (0.4615) | 0.0000 | PURE-LEAK (rec==floor) |
| tsfresh | rerun | 27/317 (0.0852) | 10/317 (0.0315) | 0.0536 | partial (floor<rec) |
| pytz | orig | 16/235 (0.0681) | 232/235 (0.9872) | 0.0000 | shadow-zeroed (rec<floor) |
| databases | rerun | 4/154 (0.0260) | 142/154 (0.9221) | 0.0000 | shadow-zeroed (rec<floor) |
| aiofiles | orig | 5/211 (0.0237) | 1/211 (0.0047) | 0.0190 | partial (floor<rec) |
| python-pytest-cases | rerun | 21/1372 (0.0153) | 21/1372 (0.0153) | 0.0000 | PURE-LEAK (rec==floor) |
| pysondb-v2 | orig | 1/96 (0.0104) | 1/96 (0.0104) | 0.0000 | PURE-LEAK (rec==floor) |
