"""화면용 folium 지도."""

from __future__ import annotations

import html

import folium

from .export import Layer

MAX_SCREEN_LABELS = 400


def build_map(layers: list[Layer], provider=None, bounds=None) -> folium.Map:
    """layers를 배경지도 위에 그린다. bounds는 (minx, miny, maxx, maxy)."""
    fmap = folium.Map(location=[20, 0], zoom_start=2, tiles=None, control_scale=True)
    if provider is not None:
        folium.TileLayer(
            tiles=provider.build_url(),
            attr=provider.html_attribution,
            name=provider.name,
            max_zoom=provider.get("max_zoom", 19),
        ).add_to(fmap)

    for layer in sorted(layers, key=lambda l: l.level, reverse=True):
        if layer.gdf.empty:
            continue
        style = {
            "color": layer.color,
            "weight": layer.linewidth * 1.6,
            "fillColor": layer.color,
            "fillOpacity": layer.fill_alpha,
        }
        folium.GeoJson(
            layer.gdf[["shapeName", "name_ko", "geometry"]].to_json(),
            name=layer.level,
            style_function=lambda _f, style=style: style,
            highlight_function=lambda _f: {"fillOpacity": 0.35},
            tooltip=folium.GeoJsonTooltip(fields=["name_ko", "shapeName"], aliases=["명칭", "원문"]),
        ).add_to(fmap)

        if layer.labels and len(layer.gdf) <= MAX_SCREEN_LABELS:
            size = int(layer.fontsize + 4)
            for pt, name in zip(layer.gdf.geometry.representative_point(), layer.gdf["name_ko"]):
                folium.Marker(
                    [pt.y, pt.x],
                    icon=folium.DivIcon(
                        icon_size=(0, 0),
                        html=(
                            f'<div style="font-size:{size}px;font-weight:600;color:#111;'
                            "white-space:nowrap;transform:translate(-50%,-50%);"
                            'text-shadow:-1px 0 #fff,0 1px #fff,1px 0 #fff,0 -1px #fff;">'
                            f"{html.escape(str(name))}</div>"
                        ),
                    ),
                ).add_to(fmap)

    if bounds is not None:
        minx, miny, maxx, maxy = bounds
        fmap.fit_bounds([[miny, minx], [maxy, maxx]])
    return fmap
