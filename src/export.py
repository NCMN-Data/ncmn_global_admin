"""선택한 행정구역을 PNG / PDF / SVG 및 벡터 데이터로 내보낸다."""

from __future__ import annotations

import io
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import matplotlib
from matplotlib import patheffects
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from shapely.geometry import box

from .gb_api import ROOT, USER_AGENT

FONT_PATH = ROOT / "assets" / "fonts" / "NanumGothic-Regular.ttf"
IMAGE_FORMATS = {
    "PNG (이미지)": "png",
    "PDF (벡터, Illustrator 호환)": "pdf",
    "SVG (벡터, Illustrator 호환)": "svg",
}
MIME = {"png": "image/png", "pdf": "application/pdf", "svg": "image/svg+xml"}
PAGE_SIZES = {
    "A4 가로": (11.69, 8.27),
    "A4 세로": (8.27, 11.69),
    "A3 가로": (16.54, 11.69),
    "A3 세로": (11.69, 16.54),
    "정사각형 (10in)": (10, 10),
}
MAX_LABELS = 1500


@dataclass
class Layer:
    level: str  # ADM0 / ADM1 / ADM2
    gdf: gpd.GeoDataFrame  # 컬럼: shapeID, shapeName, name_ko, geometry (EPSG:4326)
    color: str
    linewidth: float
    fill_alpha: float = 0.0
    labels: bool = False
    fontsize: float = 8.0


def _font(size: float) -> FontProperties:
    if FONT_PATH.exists():
        return FontProperties(fname=str(FONT_PATH), size=size)
    return FontProperties(size=size)


def render(
    layers: list[Layer],
    provider=None,
    figsize: tuple[float, float] = (11.69, 8.27),
    title: str = "",
    credit: str = "",
    bounds=None,
) -> tuple[Figure, str | None]:
    """지도를 그린 Figure와 (배경지도 실패 시) 경고 문구를 반환한다.

    bounds는 지도 범위 (minx, miny, maxx, maxy; 경위도). 생략하면 전체 layer 범위.
    """
    layers = [layer for layer in layers if not layer.gdf.empty]
    if not layers:
        raise ValueError("내보낼 행정구역이 없습니다.")

    fig = Figure(figsize=figsize)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0.02, 0.04, 0.96, 0.9 if title else 0.94])
    ax.set_axis_off()
    ax.set_aspect("equal")

    projected = [layer.gdf.to_crs(3857) for layer in layers]
    if bounds is not None:
        xmin, ymin, xmax, ymax = gpd.GeoSeries([box(*bounds)], crs=4326).to_crs(3857).total_bounds
    else:
        xmin = min(g.total_bounds[0] for g in projected)
        ymin = min(g.total_bounds[1] for g in projected)
        xmax = max(g.total_bounds[2] for g in projected)
        ymax = max(g.total_bounds[3] for g in projected)
    pad_x, pad_y = (xmax - xmin) * 0.04 or 1000, (ymax - ymin) * 0.04 or 1000
    ax.set_xlim(xmin - pad_x, xmax + pad_x)
    ax.set_ylim(ymin - pad_y, ymax + pad_y)

    warning = None
    if provider is not None:
        try:
            import contextily as cx

            # OSM 등은 앱을 식별하는 User-Agent가 없으면 타일 요청을 거부한다.
            cx.add_basemap(
                ax, source=provider, crs="EPSG:3857", attribution=False, reset_extent=True,
                headers={"user-agent": USER_AGENT},
            )
            ax.images[-1].set_gid("basemap")
        except Exception as exc:
            warning = f"배경지도를 불러오지 못해 배경 없이 내보냈습니다. ({exc})"

    # 하위 level을 먼저 그려 상위 경계선이 위에 오도록 한다.
    order = sorted(range(len(layers)), key=lambda i: layers[i].level, reverse=True)
    for i in order:
        layer, gdf = layers[i], projected[i]
        before = len(ax.collections)
        gdf.plot(
            ax=ax,
            facecolor=to_rgba(layer.color, layer.fill_alpha),
            edgecolor=layer.color,
            linewidth=layer.linewidth,
            aspect=None,
        )
        for coll in ax.collections[before:]:
            coll.set_gid(layer.level)  # SVG에서 level별 그룹(<g id="ADM1">)이 된다.

    halo = [patheffects.withStroke(linewidth=2, foreground="white")]
    for i in sorted(order, key=lambda i: layers[i].level, reverse=True):
        layer, gdf = layers[i], projected[i]
        if not layer.labels or len(gdf) > MAX_LABELS:
            continue
        for n, (pt, name) in enumerate(zip(gdf.geometry.representative_point(), gdf["name_ko"])):
            text = ax.text(
                pt.x, pt.y, name, ha="center", va="center", color="#111111",
                fontproperties=_font(layer.fontsize), path_effects=halo, clip_on=True,
            )
            text.set_gid(f"label-{layer.level}-{n}")

    if title:
        fig.text(0.5, 0.965, title, ha="center", va="center", fontproperties=_font(16))
    if credit:
        fig.text(0.98, 0.015, credit, ha="right", va="bottom", color="#555555", fontproperties=_font(6.5))
    return fig, warning


def figure_bytes(fig: Figure, fmt: str, dpi: int = 300) -> bytes:
    buf = io.BytesIO()
    # PDF는 글자를 편집 가능한 TrueType으로, SVG는 폰트가 없어도 열리도록 윤곽선으로 저장한다.
    with matplotlib.rc_context({"pdf.fonttype": 42, "svg.fonttype": "path"}):
        fig.savefig(buf, format=fmt, dpi=dpi, facecolor="white")
    return buf.getvalue()


def _combined(layers: list[Layer]) -> gpd.GeoDataFrame:
    import pandas as pd

    parts = []
    for layer in layers:
        part = layer.gdf[["shapeID", "shapeName", "name_ko", "geometry"]].copy()
        part.insert(0, "level", layer.level)
        parts.append(part)
    return gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=4326)


def geojson_bytes(layers: list[Layer]) -> bytes:
    return _combined(layers).to_json(ensure_ascii=False).encode("utf-8")


def shapefile_zip_bytes(layers: list[Layer], stem: str) -> bytes:
    """level별 Shapefile을 하나의 zip으로 묶는다 (UTF-8)."""
    buf = io.BytesIO()
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for layer in layers:
            if layer.gdf.empty:
                continue
            gdf = layer.gdf[["shapeID", "shapeName", "name_ko", "geometry"]]
            gdf.to_file(Path(tmp) / f"{stem}_{layer.level}.shp", encoding="utf-8")
        for path in sorted(Path(tmp).iterdir()):
            zf.write(path, path.name)
    return buf.getvalue()
