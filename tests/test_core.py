import geopandas as gpd
from shapely.geometry import box

from src import export, hierarchy, names_ko


def _gdf(items):
    return gpd.GeoDataFrame(
        {"shapeID": [i[0] for i in items], "shapeName": [i[1] for i in items]},
        geometry=[i[2] for i in items],
        crs=4326,
    )


def test_country_name_ko():
    assert names_ko.country_name_ko("KOR") == "대한민국"
    assert names_ko.country_name_ko("XKX") == "코소보"
    assert names_ko.country_name_ko("ZZZ", "Nowhere") == "Nowhere"


def test_assign_parents_point_and_overlap():
    parents = _gdf([("P1", "West", box(0, 0, 10, 10)), ("P2", "East", box(10, 0, 20, 10))])
    children = _gdf([
        ("C1", "a", box(1, 1, 4, 4)),
        ("C2", "b", box(12, 1, 15, 4)),
        ("C3", "outside", box(30, 30, 31, 31)),
    ])
    result = hierarchy.assign_parents(children, parents)
    assert list(result) == ["P1", "P2", None]


def test_match_names_requires_location_and_name():
    gdf = _gdf([
        ("A", "Sokcho-si", box(0, 0, 1, 1)),
        ("B", "Niigata", box(2, 0, 3, 1)),
        ("C", "Kitui East", box(4, 0, 5, 1)),
        ("D", "Dong-gu [East District]", box(6, 0, 7, 1)),
    ])
    cands = [
        {"ko": "속초시", "en": "Sokcho", "lon": 0.5, "lat": 0.5, "depth": 2},
        {"ko": "니가타현", "en": "Niigata Prefecture", "lon": 2.5, "lat": 0.5, "depth": 1},
        {"ko": "니가타시", "en": "Niigata", "lon": 2.4, "lat": 0.5, "depth": 2},
        {"ko": "키투이현", "en": "Kitui County", "lon": 4.5, "lat": 0.5, "depth": 1},
        {"ko": "동구", "en": "Dong District", "lon": 6.5, "lat": 0.5, "depth": 2},
        {"ko": "엉뚱한곳", "en": "Sokcho", "lon": 6.6, "lat": 0.5, "depth": 2},
    ]
    adm2 = names_ko.match_names(gdf, cands, "ADM2")
    assert adm2["A"] == "속초시"
    assert adm2["B"] == "니가타시"
    assert "C" not in adm2  # 상위 구역 이름으로 잘못 붙지 않는다
    assert adm2["D"] == "동구"
    assert names_ko.match_names(gdf, cands, "ADM1")["B"] == "니가타현"


def _layers():
    gdf = _gdf([("A", "Seoul", box(126.8, 37.4, 127.2, 37.7)), ("B", "Busan", box(128.9, 35.0, 129.3, 35.3))])
    gdf["name_ko"] = ["서울특별시", "부산광역시"]
    return [export.Layer("ADM1", gdf, "#1f4e9c", 1.0, 0.1, labels=True)]


def test_export_formats():
    fig, warning = export.render(_layers(), None, (6, 4), "테스트", "출처")
    assert warning is None
    assert export.figure_bytes(fig, "png", 80)[:8] == b"\x89PNG\r\n\x1a\n"
    assert export.figure_bytes(fig, "pdf")[:5] == b"%PDF-"
    svg = export.figure_bytes(fig, "svg").decode("utf-8")
    assert 'id="ADM1"' in svg and 'id="label-ADM1-0"' in svg


def test_vector_exports():
    import io
    import json
    import zipfile

    layers = _layers()
    data = json.loads(export.geojson_bytes(layers))
    assert data["features"][0]["properties"]["name_ko"] == "서울특별시"
    names = zipfile.ZipFile(io.BytesIO(export.shapefile_zip_bytes(layers, "KOR"))).namelist()
    assert "KOR_ADM1.shp" in names and "KOR_ADM1.dbf" in names
