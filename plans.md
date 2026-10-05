국가별 행정구역도 download App 개발

## 요구사항

1. streamlit을 이용해서 국가선택시 세계지도에 국가를 표기 - geoBoundaries API이 활용하기

2. 국가 선택시 행정구역 level 0 - level 1 - level 2 까지 선택가능하도록 제시

3. 각 level별 행정구역의 명칭을 매칭해서 2번의 level을 선택시 지도에 표시 (표시는 check box로 보이거나 안보이게 option 제공)

4. 최종 선택된 행정구역은 png, pdf, 일러스터 파일 등 다양한 옵션으로 다운이 가능하도록 기능제공

5. 배경 Map은 다양한 무료 배경을 이용할 수 있도록 옵션제공

## 확정 사항

- 행정구역은 level 2(ADM2)까지만 지원한다. ADM3 이상은 제공되더라도 다루지 않는다.
- 배포는 GitHub 저장소와 연계해 Streamlit Community Cloud로 공개한다 (개발 완료 후 진행).
- 국가명(level 0)과 level 1 행정구역 명칭은 모든 국가에 대해 한글로 표시한다. level 2는 원문(영문) 명칭을 그대로 쓴다.

## 개발계획

### 데이터 (geoBoundaries API)

- 엔드포인트: `https://www.geoboundaries.org/api/current/gbOpen/{ISO3}/{ADM0|ADM1|ADM2|ALL}/`
- 화면 표시는 단순화본(`simplifiedGeometryGeoJSON`), 내보내기는 원본(`gjDownloadURL`)을 사용한다.
- ADM2가 없는 국가가 있으므로 국가별로 제공되는 level만 선택지에 노출한다.
- level마다 출처·라이선스가 다르므로 앱과 출력물에 표기한다.
- 피처에 상위 행정구역 코드가 없으므로 ADM1–ADM2 관계는 공간 조인으로 만든다.

### 한글 명칭 (level 0·1)

- 국가명: CLDR(Babel) 한국어 지역명을 ISO 코드로 매칭한다.
- level 1 행정구역명: Wikidata 한국어 레이블을 국가별로 조회해 위치(좌표가 폴리곤 안에 있는지)와 영문 명칭 유사도로 매칭한다.
- Wikidata로 채워지지 않은 level 1 명칭은 한글 표기를 직접 작성해 `overrides`에 넣는다.
- 결과는 `data/names_ko/{ISO3}.json`에 저장해 저장소에 포함하고, `overrides`를 우선 적용한다.
- level 2는 변환하지 않고 원문 명칭으로 표시한다.

### 기술 스택

| 영역 | 선택 |
|---|---|
| UI | Streamlit |
| 인터랙티브 지도 | folium + streamlit-folium |
| 공간 처리 | geopandas, shapely |
| 배경지도 | xyzservices (API 키가 필요 없는 무료 타일: OpenStreetMap, OpenTopoMap, Esri. CARTO는 키가 필요해 제외) |
| 내보내기 | matplotlib + contextily → PNG / PDF / SVG, GeoJSON / Shapefile |
| 한글 폰트 | 저장소에 포함한 나눔고딕 (OFL) |

### 구조

```
app.py                  Streamlit 진입점
src/gb_api.py           geoBoundaries 메타데이터/GeoJSON 조회, 캐시
src/names_ko.py         국가·행정구역 한글 명칭
src/hierarchy.py        ADM1–ADM2 공간 조인
src/basemaps.py         배경지도 목록
src/map_view.py         folium 지도 구성
src/export.py           PNG/PDF/SVG 및 벡터 데이터 내보내기
scripts/build_names_ko.py   한글 명칭 사전 일괄 생성
tests/                  단위 테스트
```

### 단계

| 단계 | 내용 | 완료 기준 |
|---|---|---|
| 1 | 환경 구성, API 클라이언트, 캐시 | 임의 국가의 메타데이터와 GeoJSON을 불러옴 |
| 2 | 국가 선택(한글)과 세계지도 하이라이트 | 국가를 고르면 지도에 표시되고 확대됨 |
| 3 | level 선택, 계층 매칭, 한글 명칭, 체크박스 | ADM1 선택 시 하위 ADM2만 나열, 레이어 on/off 동작 |
| 4 | 배경지도 옵션 | 배경을 바꾸면 화면과 출력물에 모두 반영 |
| 5 | 내보내기 | 출력 파일이 Illustrator에서 level별 그룹으로 열림 |
| 6 | 테스트, 예외 처리, README | ADM2 없는 국가와 대용량 국가에서도 정상 동작 |
| 7 | GitHub 연계 Streamlit Community Cloud 배포 | 공개 URL에서 동작 |

### 위험 요소

- 대용량 국가의 ADM2 원본은 수십 MB이므로 화면은 단순화본만 사용한다.
- level 간 출처가 달라 경계가 어긋날 수 있으며, 매칭 실패 단위는 "미분류"로 표시한다.
- 배경 타일은 PDF/SVG에서도 래스터로 포함된다. 순수 벡터는 "배경 없음"으로 내보낸다.
