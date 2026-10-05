# ncmn_global_admin

국가별 행정구역도(Level 0–2)를 지도에서 확인하고 PNG / PDF / SVG, GeoJSON / Shapefile로 내려받는 Streamlit 앱입니다.
행정경계는 [geoBoundaries](https://www.geoboundaries.org) gbOpen API를 사용하며, 국가명과 Level 1 행정구역명은 한글로 표시합니다.

## 실행

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

## 기능

- 국가 선택 시 세계지도에 해당 국가를 표시하고 확대
- Level 0 / 1 / 2 표시와 명칭 표시를 체크박스로 on/off (국가에 없는 level은 비활성화)
- Level 1을 고르면 그 하위 Level 2만 선택 목록에 표시
- 무료 배경지도 선택 (OpenStreetMap, OpenTopoMap, Esri 계열, 배경 없음)
- PNG / PDF / SVG 내보내기. SVG는 level별로 그룹(`ADM0`, `ADM1`, `ADM2`)이 나뉘어 Illustrator에서 편집하기 쉽습니다.
- GeoJSON / Shapefile, 명칭 표(CSV) 다운로드

## 한글 명칭

- 국가명(Level 0): Unicode CLDR (Babel)
- Level 1 행정구역명: Wikidata 한국어 레이블(좌표가 해당 구역 안에 있고 명칭이 일치하는 항목)에, Wikidata에 없는 구역은
  직접 작성한 한글 표기(`overrides`)를 더했습니다. 전체 국가분이 `data/names_ko/{ISO3}.json`에 들어 있습니다.
- Level 2는 원문 명칭을 그대로 표시합니다.
- 표기를 고치려면 해당 파일의 `overrides`를 수정합니다 (키는 shapeID 또는 원문 명칭).

```json
{ "overrides": { "Trans Nzoia": "트랜스은조이아현" } }
```

geoBoundaries 데이터가 갱신되어 사전을 다시 만들 때:

```bash
.venv/bin/python scripts/build_names_ko.py --force       # 전체 (overrides는 유지)
.venv/bin/python scripts/build_names_ko.py --force KOR   # 일부
.venv/bin/python scripts/adm1_overrides_ko.py            # 직접 작성한 표기 반영, 남은 미해결 구역 출력
```

## 테스트

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests
```

## 라이선스 · 출처

- 코드: MIT (LICENSE)
- 행정경계: geoBoundaries gbOpen — level마다 라이선스가 다르며 앱의 "출처 · 라이선스" 탭에 표시됩니다.
- 한글 행정구역명: Wikidata (CC0)
- 글꼴: 나눔고딕 (SIL OFL, `assets/fonts/OFL.txt`)
- 배경지도: 각 제공자의 출처 표기가 내보내기 파일에 자동으로 들어갑니다.
