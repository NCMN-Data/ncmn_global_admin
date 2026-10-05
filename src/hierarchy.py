"""상·하위 행정구역 매칭 (geoBoundaries에는 상위 코드가 없어 공간 조인으로 만든다)."""

from __future__ import annotations

import warnings

import geopandas as gpd
import pandas as pd


def assign_parents(children: gpd.GeoDataFrame, parents: gpd.GeoDataFrame) -> pd.Series:
    """각 하위 구역의 상위 shapeID. 찾지 못하면 None.

    1차: 하위 구역의 내부 대표점이 포함된 상위 구역.
    2차: 겹치는 면적이 가장 큰 상위 구역 (level 간 경계가 어긋난 경우).
    """
    result = pd.Series([None] * len(children), index=children.index, dtype=object)
    if children.empty or parents.empty:
        return result

    pts = gpd.GeoDataFrame(geometry=children.geometry.representative_point(), crs=children.crs)
    joined = gpd.sjoin(pts, parents[["shapeID", "geometry"]], predicate="within", how="left")
    joined = joined[~joined.index.duplicated(keep="first")]
    result.update(joined["shapeID"].dropna())

    missing = result[result.isna()].index
    for idx in missing:
        geom = children.geometry.loc[idx]
        with warnings.catch_warnings():
            # 상대 비교만 하므로 경위도 좌표계의 면적 왜곡은 무시한다.
            warnings.simplefilter("ignore", UserWarning)
            areas = parents.geometry.intersection(geom).area
        if len(areas) and areas.max() > 0:
            result.loc[idx] = parents.loc[areas.idxmax(), "shapeID"]
    return result
