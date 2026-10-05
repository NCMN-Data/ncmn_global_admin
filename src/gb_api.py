"""geoBoundaries(gbOpen) API 클라이언트와 디스크 캐시."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import geopandas as gpd
import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(os.environ.get("NCMN_CACHE_DIR", ROOT / ".cache"))
API = "https://www.geoboundaries.org/api/current/gbOpen"
LEVELS = ("ADM0", "ADM1", "ADM2")
USER_AGENT = "ncmn-global-admin/0.1 (https://github.com/DavidChoi76)"
META_MAX_AGE = 7 * 24 * 3600


def fetch(
    url: str, timeout: int = 120, retries: int = 3, method: str = "get", **kwargs
) -> requests.Response:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.request(
                method, url, timeout=timeout, headers={"User-Agent": USER_AGENT}, **kwargs
            )
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"요청 실패: {url} ({last})")


def _cached_json(name: str, url: str):
    path = CACHE_DIR / "meta" / name
    if path.exists() and time.time() - path.stat().st_mtime < META_MAX_AGE:
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        data = fetch(url).json()
    except RuntimeError:
        # 네트워크 오류 시 오래된 캐시라도 사용한다.
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        raise
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def list_countries() -> list[dict]:
    """ADM0 경계가 제공되는 국가 목록 [{iso3, name}]."""
    data = _cached_json("countries.json", f"{API}/ALL/ADM0/")
    seen: dict[str, dict] = {}
    for m in data:
        seen[m["boundaryISO"]] = {"iso3": m["boundaryISO"], "name": m["boundaryName"]}
    return sorted(seen.values(), key=lambda c: c["iso3"])


def country_levels(iso3: str) -> dict[str, dict]:
    """국가에서 제공되는 level(ADM0~ADM2)별 메타데이터."""
    data = _cached_json(f"{iso3}.json", f"{API}/{iso3}/ALL/")
    if isinstance(data, dict):
        data = [data]
    return {m["boundaryType"]: m for m in data if m.get("boundaryType") in LEVELS}


def _download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(fetch(url, timeout=300).content)
    tmp.replace(path)


def load_boundary(meta: dict, simplified: bool = True) -> gpd.GeoDataFrame:
    """메타데이터 한 건에 해당하는 경계를 GeoDataFrame(shapeID, shapeName, geometry)으로 반환."""
    variants = [(True, meta.get("simplifiedGeometryGeoJSON")), (False, meta.get("gjDownloadURL"))]
    if not simplified:
        variants.reverse()
    last: Exception | None = None
    for is_simple, url in variants:
        if not url:
            continue
        suffix = "_simplified" if is_simple else ""
        path = CACHE_DIR / "geo" / f"{meta['boundaryID']}{suffix}.geojson"
        try:
            if not path.exists():
                _download(url, path)
            gdf = gpd.read_file(path)
        except Exception as exc:  # 손상된 파일은 지우고 다른 해상도로 재시도
            last = exc
            path.unlink(missing_ok=True)
            continue
        return _normalize(gdf, meta)
    raise RuntimeError(f"경계 데이터를 불러오지 못했습니다: {meta.get('boundaryID')} ({last})")


def _normalize(gdf: gpd.GeoDataFrame, meta: dict) -> gpd.GeoDataFrame:
    gdf = gdf.reset_index(drop=True)
    if "shapeName" not in gdf.columns:
        gdf["shapeName"] = meta.get("boundaryName", "")
    gdf["shapeName"] = gdf["shapeName"].fillna("").astype(str)
    if "shapeID" not in gdf.columns or gdf["shapeID"].isna().any() or gdf["shapeID"].duplicated().any():
        gdf["shapeID"] = [f"{meta['boundaryID']}-{i}" for i in range(len(gdf))]
    gdf = gdf[["shapeID", "shapeName", "geometry"]]
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    gdf["geometry"] = gdf.geometry.make_valid()
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(4326).reset_index(drop=True)
