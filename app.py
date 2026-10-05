"""NCMN 국가별 행정구역도 다운로드 앱 (Streamlit)."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src import export, gb_api, hierarchy, names_ko
from src.basemaps import BASEMAPS, DEFAULT_BASEMAP, NO_BASEMAP, get_provider
from src.map_view import MAX_SCREEN_LABELS, build_map

LEVEL_LABELS = {"ADM0": "Level 0 (국가)", "ADM1": "Level 1 (광역)", "ADM2": "Level 2 (기초)"}
DEFAULT_STYLE = {
    "ADM0": {"color": "#222222", "linewidth": 1.8, "fill_alpha": 0.0, "fontsize": 12.0},
    "ADM1": {"color": "#1f4e9c", "linewidth": 1.1, "fill_alpha": 0.06, "fontsize": 8.5},
    "ADM2": {"color": "#c0392b", "linewidth": 0.5, "fill_alpha": 0.08, "fontsize": 6.0},
}
UNASSIGNED = "(미분류)"

st.set_page_config(page_title="국가별 행정구역도 다운로드", page_icon="🗺️", layout="wide")


@st.cache_data(show_spinner=False, ttl=24 * 3600)
def get_countries() -> list[dict]:
    countries = gb_api.list_countries()
    for c in countries:
        c["name_ko"] = names_ko.country_name_ko(c["iso3"], c["name"])
    return sorted(countries, key=lambda c: c["name_ko"])


@st.cache_data(show_spinner=False, ttl=24 * 3600)
def get_levels(iso3: str) -> dict[str, dict]:
    return gb_api.country_levels(iso3)


@st.cache_data(show_spinner=False, max_entries=24)
def get_boundary(iso3: str, level: str, simplified: bool = True):
    """표시 명칭(name_ko)과 한글 매칭 여부(matched)가 붙은 경계. 한글은 Level 0·1만 적용한다."""
    gdf = gb_api.load_boundary(get_levels(iso3)[level], simplified=simplified)
    if level == "ADM0":
        country = names_ko.country_name_ko(iso3, gdf["shapeName"].iloc[0])
        gdf["name_ko"], gdf["matched"] = country, True
        return gdf
    if level == "ADM2":  # Level 2는 원문 명칭을 그대로 쓴다.
        gdf["name_ko"], gdf["matched"] = gdf["shapeName"], True
        return gdf
    if simplified:
        names = names_ko.admin_names_ko(iso3, level, gdf)
        matched = set(names)
    else:
        # 명칭 매칭은 단순화본 기준으로 한 번만 수행해 두 해상도가 같은 이름을 쓰게 한다.
        base = get_boundary(iso3, level, True)
        names = dict(zip(base["shapeID"], base["name_ko"]))
        matched = set(base.loc[base["matched"], "shapeID"])
    gdf["name_ko"] = gdf["shapeID"].map(names).fillna(gdf["shapeName"])
    gdf["matched"] = gdf["shapeID"].isin(matched)
    return gdf


@st.cache_data(show_spinner=False, max_entries=24)
def get_parents(iso3: str) -> dict[str, str | None]:
    """ADM2 shapeID → 상위 ADM1 shapeID"""
    adm2, adm1 = get_boundary(iso3, "ADM2"), get_boundary(iso3, "ADM1")
    return dict(zip(adm2["shapeID"], hierarchy.assign_parents(adm2, adm1)))


def unique_labels(gdf: pd.DataFrame) -> dict[str, str]:
    """shapeID → 선택 목록용 표시 이름 (동명 구역은 원문 명칭을 덧붙여 구분)."""
    labels = gdf["name_ko"].where(gdf["matched"], gdf["shapeName"])
    dup = labels.duplicated(keep=False)
    labels = labels.where(~dup, labels + " · " + gdf["shapeName"])
    dup = labels.duplicated(keep=False)
    labels = labels.where(~dup, labels + " #" + (labels.groupby(labels).cumcount() + 1).astype(str))
    return dict(zip(gdf["shapeID"], labels))


# ── 사이드바 ────────────────────────────────────────────────────────────────
st.sidebar.title("🗺️ 행정구역도 다운로드")

try:
    countries = get_countries()
except Exception as exc:
    st.error(f"국가 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.\n\n{exc}")
    st.stop()

iso_list = [c["iso3"] for c in countries]
country_by_iso = {c["iso3"]: c for c in countries}
iso3 = st.sidebar.selectbox(
    "1. 국가 선택",
    iso_list,
    index=iso_list.index("KOR") if "KOR" in iso_list else 0,
    format_func=lambda i: f"{country_by_iso[i]['name_ko']} ({i})",
)
country_ko = country_by_iso[iso3]["name_ko"]

try:
    levels = get_levels(iso3)
except Exception as exc:
    st.error(f"{country_ko}의 행정구역 정보를 불러오지 못했습니다.\n\n{exc}")
    st.stop()
if "ADM0" not in levels:
    st.error(f"{country_ko}의 국가 경계가 제공되지 않습니다.")
    st.stop()

st.sidebar.markdown("**2. 행정구역 level 표시**")
show, show_label = {}, {}
for level in gb_api.LEVELS:
    available = level in levels
    col_a, col_b = st.sidebar.columns([3, 2])
    show[level] = col_a.checkbox(
        LEVEL_LABELS[level] if available else f"{LEVEL_LABELS[level]} – 미제공",
        value=available and level != "ADM2",
        disabled=not available,
        key=f"show_{level}",
    )
    show_label[level] = col_b.checkbox(
        "명칭", value=level == "ADM1", disabled=not available, key=f"label_{level}"
    )
missing = [LEVEL_LABELS[l] for l in gb_api.LEVELS if l not in levels]
if missing:
    st.sidebar.caption(f"이 국가는 {', '.join(missing)} 경계가 제공되지 않습니다.")

with st.spinner(f"{country_ko} 경계를 불러오는 중…"):
    try:
        data = {"ADM0": get_boundary(iso3, "ADM0")}
        for level in ("ADM1", "ADM2"):
            if level in levels and (show[level] or (level == "ADM1" and show["ADM2"])):
                data[level] = get_boundary(iso3, level)
        parents = get_parents(iso3) if "ADM2" in data and "ADM1" in data else {}
    except Exception as exc:
        st.error(f"경계 데이터를 불러오지 못했습니다.\n\n{exc}")
        st.stop()

# 행정구역 선택 (비워 두면 전체)
selected: dict[str, set | None] = {"ADM0": None, "ADM1": None, "ADM2": None}
if "ADM1" in data:
    st.sidebar.markdown("**3. 행정구역 선택** (비워 두면 전체)")
    labels1 = unique_labels(data["ADM1"])
    picked1 = st.sidebar.multiselect(
        LEVEL_LABELS["ADM1"],
        sorted(labels1, key=labels1.get),
        format_func=labels1.get,
        key=f"pick1_{iso3}",
        placeholder="전체",
    )
    selected["ADM1"] = set(picked1) or None
    if "ADM2" in data:
        adm2 = data["ADM2"]
        if selected["ADM1"]:
            adm2 = adm2[adm2["shapeID"].map(parents).isin(selected["ADM1"])]
        labels2 = unique_labels(adm2)
        picked2 = st.sidebar.multiselect(
            LEVEL_LABELS["ADM2"],
            sorted(labels2, key=labels2.get),
            format_func=labels2.get,
            key=f"pick2_{iso3}",
            placeholder="전체" if not selected["ADM1"] else "선택한 Level 1의 하위 전체",
        )
        selected["ADM2"] = set(picked2) or (set(adm2["shapeID"]) if selected["ADM1"] else None)

basemap_name = st.sidebar.selectbox("4. 배경지도", list(BASEMAPS), index=list(BASEMAPS).index(DEFAULT_BASEMAP))
provider = get_provider(basemap_name)

with st.sidebar.expander("선 색상 · 굵기"):
    style = {}
    for level in gb_api.LEVELS:
        col_a, col_b = st.columns([1, 2])
        style[level] = dict(DEFAULT_STYLE[level])
        style[level]["color"] = col_a.color_picker(level, DEFAULT_STYLE[level]["color"], key=f"color_{level}")
        style[level]["linewidth"] = col_b.slider(
            f"{level} 굵기", 0.1, 4.0, DEFAULT_STYLE[level]["linewidth"], 0.1, key=f"width_{level}"
        )


def make_layers(source: dict) -> list[export.Layer]:
    layers = []
    for level in gb_api.LEVELS:
        if not show[level] or level not in source:
            continue
        gdf = source[level]
        if selected[level] is not None:
            gdf = gdf[gdf["shapeID"].isin(selected[level])]
        layers.append(export.Layer(level=level, gdf=gdf, labels=show_label[level], **style[level]))
    return layers


layers = make_layers(data)

# ── 본문 ────────────────────────────────────────────────────────────────────
st.title(f"{country_ko} 행정구역도")

visible = [l for l in layers if not l.gdf.empty]
if visible:
    focus = max(visible, key=lambda l: l.level).gdf if any(selected.values()) else data["ADM0"]
    bounds = focus.total_bounds
else:
    bounds = data["ADM0"].total_bounds
    st.info("표시할 level을 왼쪽에서 선택하세요.")

for layer in visible:
    if layer.labels and len(layer.gdf) > MAX_SCREEN_LABELS:
        st.caption(
            f"{LEVEL_LABELS[layer.level]} 명칭은 {MAX_SCREEN_LABELS}개 이하일 때만 화면에 표시됩니다 "
            f"(현재 {len(layer.gdf):,}개). 내보내기 파일에는 포함됩니다."
        )

st_folium(build_map(layers, provider, bounds), height=600, use_container_width=True, returned_objects=[])

tab_export, tab_names, tab_source = st.tabs(["⬇️ 다운로드", "📋 행정구역 명칭", "ℹ️ 출처 · 라이선스"])

with tab_export:
    if not visible:
        st.info("내보낼 행정구역이 없습니다.")
    else:
        col1, col2, col3 = st.columns(3)
        fmt_label = col1.selectbox("파일 형식", list(export.IMAGE_FORMATS))
        page = col2.selectbox("용지", list(export.PAGE_SIZES))
        dpi = col3.select_slider("해상도 (DPI, PNG)", [100, 150, 200, 300, 400, 600], value=300)
        title = st.text_input("지도 제목 (비우면 생략)", value=f"{country_ko} 행정구역도")
        col4, col5 = st.columns(2)
        with_basemap = col4.checkbox(
            "배경지도 포함", value=provider is not None, disabled=provider is None,
            help="배경지도는 PDF/SVG에서도 이미지로 들어갑니다. 순수 벡터가 필요하면 해제하세요.",
        )
        full_res = col5.checkbox(
            "원본 해상도 경계 사용", value=False,
            help="단순화하지 않은 원본 경계를 사용합니다. 국가에 따라 수십 MB를 내려받아 시간이 걸립니다.",
        )
        fmt = export.IMAGE_FORMATS[fmt_label]
        stem = f"{iso3}_{'_'.join(l.level for l in visible)}"

        if st.button("내보내기 파일 만들기", type="primary"):
            with st.spinner("파일을 만드는 중…"):
                try:
                    source = data
                    if full_res:
                        source = {level: get_boundary(iso3, level, False) for level in data}
                    out_layers = [l for l in make_layers(source) if not l.gdf.empty]
                    credit = "행정경계: geoBoundaries (gbOpen)"
                    use_provider = provider if with_basemap else None
                    if use_provider is not None:
                        credit += f" · 배경지도: {use_provider.attribution}"
                    fig, warning = export.render(
                        out_layers, use_provider, export.PAGE_SIZES[page], title.strip(), credit,
                        bounds=bounds,
                    )
                    st.session_state["export"] = {
                        "stem": stem,
                        "fmt": fmt,
                        "image": export.figure_bytes(fig, fmt, dpi),
                        "preview": export.figure_bytes(fig, "png", 110),
                        "geojson": export.geojson_bytes(out_layers),
                        "shp": export.shapefile_zip_bytes(out_layers, iso3),
                        "warning": warning,
                    }
                except Exception as exc:
                    st.session_state.pop("export", None)
                    st.error(f"내보내기에 실패했습니다.\n\n{exc}")

        result = st.session_state.get("export")
        if result and result["stem"] == stem:
            if result["warning"]:
                st.warning(result["warning"])
            b1, b2, b3 = st.columns(3)
            b1.download_button(
                f"{result['fmt'].upper()} 다운로드", result["image"],
                f"{stem}.{result['fmt']}", export.MIME[result["fmt"]], type="primary",
            )
            b2.download_button("GeoJSON 다운로드", result["geojson"], f"{stem}.geojson", "application/geo+json")
            b3.download_button("Shapefile (zip) 다운로드", result["shp"], f"{stem}_shp.zip", "application/zip")
            st.image(result["preview"], caption="미리보기")

with tab_names:
    rows = []
    adm1_names = dict(zip(data["ADM1"]["shapeID"], data["ADM1"]["name_ko"])) if "ADM1" in data else {}
    for layer in visible:
        if layer.level == "ADM0":
            continue
        for row in layer.gdf.itertuples():
            parent = adm1_names.get(parents.get(row.shapeID), UNASSIGNED) if layer.level == "ADM2" else ""
            rows.append({
                "level": layer.level,
                "상위 (Level 1)": parent,
                "표시 명칭": row.name_ko,
                "한글 여부": "" if layer.level == "ADM2" else ("○" if row.matched else "✕"),
                "원문 명칭": row.shapeName,
            })
    if rows:
        table = pd.DataFrame(rows).sort_values(["level", "상위 (Level 1)", "원문 명칭"])
        missing_ko = (table["한글 여부"] == "✕").sum()
        st.caption("Level 0·1은 한글, Level 2는 원문 명칭으로 표시합니다.")
        if missing_ko:
            st.warning(
                f"Level 1 중 {missing_ko:,}개는 한글 명칭이 없어 원문으로 표시됩니다. "
                f"`data/names_ko/{iso3}.json`의 `overrides`에 추가하면 반영됩니다."
            )
        st.dataframe(table, hide_index=True, width="stretch")
        st.download_button(
            "명칭 표 CSV 다운로드", table.to_csv(index=False).encode("utf-8-sig"),
            f"{iso3}_names.csv", "text/csv",
        )
    else:
        st.info("Level 1 또는 Level 2를 표시하면 명칭 표가 나타납니다.")

with tab_source:
    meta_rows = []
    for level, meta in levels.items():
        gdf = data.get(level)
        rate = f"{gdf['matched'].mean():.0%}" if gdf is not None and level == "ADM1" else "–"
        meta_rows.append({
            "level": LEVEL_LABELS[level],
            "구역 수": meta.get("admUnitCount"),
            "기준 연도": meta.get("boundaryYearRepresented"),
            "출처": meta.get("boundarySource"),
            "라이선스": meta.get("boundaryLicense"),
            "한글 명칭 매칭률": rate,
        })
    st.dataframe(pd.DataFrame(meta_rows), hide_index=True, width="stretch")
    st.caption(
        "행정경계: [geoBoundaries](https://www.geoboundaries.org) gbOpen · "
        "한글 국가명: Unicode CLDR · 한글 행정구역명: Wikidata (CC0). "
        "출력물을 배포할 때는 위 라이선스와 배경지도 제공자의 출처 표기 조건을 확인하세요."
    )
    if basemap_name != NO_BASEMAP:
        st.caption(f"배경지도: {provider.attribution}")
