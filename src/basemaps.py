"""API 키 없이 쓸 수 있는 무료 배경지도 목록."""

from __future__ import annotations

import xyzservices.providers as xyz

NO_BASEMAP = "배경 없음"

DEFAULT_BASEMAP = "Esri World Gray Canvas (밝은 회색)"

# CARTO(Positron 등)는 API 키가 필요해져 제외했다.
BASEMAPS = {
    "OpenStreetMap": xyz.OpenStreetMap.Mapnik,
    "OpenStreetMap Humanitarian": xyz.OpenStreetMap.HOT,
    "OpenTopoMap (지형)": xyz.OpenTopoMap,
    DEFAULT_BASEMAP: xyz.Esri.WorldGrayCanvas,
    "Esri World Street Map": xyz.Esri.WorldStreetMap,
    "Esri World Topo Map": xyz.Esri.WorldTopoMap,
    "Esri World Imagery (위성영상)": xyz.Esri.WorldImagery,
    "Esri World Shaded Relief (음영기복)": xyz.Esri.WorldShadedRelief,
    "Esri NatGeo World Map": xyz.Esri.NatGeoWorldMap,
    NO_BASEMAP: None,
}


def get_provider(name: str):
    return BASEMAPS.get(name)
