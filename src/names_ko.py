"""국가명·행정구역명 한글 표기.

국가명은 CLDR(Babel), 행정구역명은 Wikidata 한국어 레이블을 사용한다.
행정구역 매칭 결과는 data/names_ko/{ISO3}.json에 저장해 재사용한다.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import pycountry
from babel import Locale
from rapidfuzz import fuzz

from .gb_api import CACHE_DIR, ROOT, fetch

NAMES_DIR = ROOT / "data" / "names_ko"
SPARQL_URL = "https://query.wikidata.org/sparql"
MATCH_THRESHOLD = 85

# pycountry에 없는 geoBoundaries 코드 → CLDR 지역 코드
_ISO3_TO_CLDR = {"XKX": "XK"}
_KO = Locale("ko")

# 명칭 비교 시 무시하는 행정단위 일반명사
_GENERIC = {
    "province", "state", "region", "district", "county", "department", "prefecture",
    "municipality", "city", "governorate", "oblast", "division", "parish", "canton",
    "territory", "area", "council", "metropolitan", "special", "autonomous", "capital",
    "of", "the", "de", "del", "la", "le", "el", "al", "do", "si", "gun", "gu",
}

_QUERY = """SELECT ?item ?ko ?en ?coord ?type WHERE {
  ?c wdt:P298 "%s". %s
  ?item rdfs:label ?ko. FILTER(lang(?ko)="ko")
  ?item wdt:P625 ?coord.
  OPTIONAL{?item rdfs:label ?en. FILTER(lang(?en)="en")}
  OPTIONAL{?item wdt:P31 ?type}
}"""
# (패턴, 국가로부터의 단계, 행정구역임이 보장되는지)
# P150 = 하위 행정구역 포함, P131 = 소속 행정구역
_PATTERNS = (
    ("?c wdt:P150 ?item.", 1, True),
    ("?c wdt:P150/wdt:P150 ?item.", 2, True),
    ("?item wdt:P131 ?c.", 1, False),
    ("?item wdt:P131/wdt:P131 ?c.", 2, False),
)
_ADMIN_CLASS = "Q56061"  # administrative territorial entity
_TYPES_QUERY = "SELECT ?t WHERE { VALUES ?t { %s } ?t wdt:P279* wd:" + _ADMIN_CLASS + " }"


def country_name_ko(iso3: str, fallback: str = "") -> str:
    code = _ISO3_TO_CLDR.get(iso3)
    if code is None:
        country = pycountry.countries.get(alpha_3=iso3)
        code = country.alpha_2 if country else None
    return (_KO.territories.get(code) if code else None) or fallback or iso3


def _has_hangul(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[\W_]+", " ", text.lower()).strip()


def _core(text: str) -> str:
    norm = _norm(text)
    core = " ".join(tok for tok in norm.split() if tok not in _GENERIC)
    return core or norm


def _strip_qualifier(text: str) -> str:
    """'Goseong County, Gangwon' → 'Goseong County', 'Dong-gu [East District]' → 'Dong-gu'"""
    text = re.sub(r"[\[(].*?[\])]", " ", text or "")
    return text.split(",")[0]


def _score(shape_name: str, label: str) -> tuple[float, float]:
    """(일반명사를 뺀 명칭 유사도, 전체 명칭 유사도)"""
    a, b = _strip_qualifier(shape_name), _strip_qualifier(label)
    return fuzz.ratio(_core(a), _core(b)), fuzz.ratio(_norm(a), _norm(b))


def _qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _admin_types(types: set[str]) -> set[str]:
    """주어진 Wikidata 클래스 중 행정구역의 하위 클래스인 것."""
    cache = CACHE_DIR / "wikidata" / "_admin_types.json"
    known: dict[str, bool] = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    todo = sorted(t for t in types if t not in known)
    for i in range(0, len(todo), 200):
        chunk = todo[i : i + 200]
        query = _TYPES_QUERY % " ".join(f"wd:{t}" for t in chunk)
        resp = fetch(SPARQL_URL, method="post", timeout=90, retries=2,
                     data={"query": query, "format": "json"})
        admin = {_qid(r["t"]["value"]) for r in resp.json()["results"]["bindings"]}
        known.update({t: t in admin for t in chunk})
    if todo:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(known), encoding="utf-8")
    return {t for t in types if known.get(t)}


def wikidata_candidates(iso3: str) -> tuple[list[dict], bool]:
    """국가 내 한국어 레이블이 있는 행정구역 항목 [{ko, en, lon, lat, depth}]과 조회 완결 여부."""
    cache = CACHE_DIR / "wikidata" / f"{iso3}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8")), True

    items: dict[str, dict] = {}
    complete = True
    for pattern, depth, trusted in _PATTERNS:
        try:
            resp = fetch(SPARQL_URL, timeout=90, retries=2,
                         params={"query": _QUERY % (iso3, pattern), "format": "json"})
            rows = resp.json()["results"]["bindings"]
        except Exception:
            complete = False
            continue
        for row in rows:
            m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", row["coord"]["value"])
            ko = row["ko"]["value"]
            if not m or not _has_hangul(ko):
                continue
            item = items.setdefault(row["item"]["value"], {
                "ko": ko, "en": row.get("en", {}).get("value", ""),
                "lon": float(m.group(1)), "lat": float(m.group(2)),
                "depth": depth, "trusted": False, "types": set(),
            })
            item["trusted"] |= trusted
            if "type" in row:
                item["types"].add(_qid(row["type"]["value"]))
    try:
        admin = _admin_types(set().union(*(it["types"] for it in items.values())))
    except Exception:
        admin, complete = set(), False
    result = [
        {k: it[k] for k in ("ko", "en", "lon", "lat", "depth")}
        for it in items.values()
        if it["en"] and (it["trusted"] or it["types"] & admin)
    ]
    if complete:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result, complete


def match_names(gdf: gpd.GeoDataFrame, candidates: list[dict], level: str = "ADM1") -> dict[str, str]:
    """shapeID → 한글명. 위치(좌표가 폴리곤 안)와 명칭 유사도가 모두 맞는 항목만 채택한다.

    같은 이름의 상·하위 구역(예: 니가타현/니가타시)은 level에 맞는 단계의 항목을 우선한다.
    """
    result: dict[str, str] = {}
    for row in gdf.itertuples():
        if _has_hangul(row.shapeName):
            result[row.shapeID] = row.shapeName
    if gdf.empty or not candidates:
        return result
    want_depth = 2 if level == "ADM2" else 1

    pts = gpd.GeoDataFrame(
        candidates,
        geometry=gpd.points_from_xy([c["lon"] for c in candidates], [c["lat"] for c in candidates]),
        crs=4326,
    )
    joined = gpd.sjoin(pts, gdf[["shapeID", "shapeName", "geometry"]], predicate="within")
    best: dict[str, tuple] = {}
    for row in joined.itertuples():
        if row.shapeID in result:
            continue
        core, full = _score(row.shapeName, row.en)
        key = (row.depth == want_depth, core, full)
        if core >= MATCH_THRESHOLD and key > best.get(row.shapeID, ((False, -1, -1), ""))[0]:
            best[row.shapeID] = (key, row.ko)
    result.update({sid: ko for sid, (_, ko) in best.items()})

    # 좌표가 폴리곤 밖에 찍힌 경우: 국가 안에서 명칭이 유일하게 일치할 때만 채택
    def key_of(text: str) -> str:
        return _core(_strip_qualifier(text))

    by_name: dict[str, set] = defaultdict(set)
    for c in candidates:
        if c["depth"] == want_depth:
            by_name[key_of(c["en"])].add(c["ko"])
    name_counts = gdf["shapeName"].map(key_of).value_counts()
    for row in gdf.itertuples():
        key = key_of(row.shapeName)
        if row.shapeID not in result and name_counts.get(key, 0) == 1 and len(by_name.get(key, ())) == 1:
            result[row.shapeID] = next(iter(by_name[key]))
    return result


def _load_store(iso3: str) -> dict:
    path = NAMES_DIR / f"{iso3}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_store(iso3: str, store: dict) -> None:
    try:
        NAMES_DIR.mkdir(parents=True, exist_ok=True)
        (NAMES_DIR / f"{iso3}.json").write_text(
            json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
        )
    except OSError:
        pass  # 읽기 전용 배포 환경


def admin_names_ko(iso3: str, level: str, gdf: gpd.GeoDataFrame) -> dict[str, str]:
    """행정구역 shapeID → 한글명. 찾지 못한 구역은 결과에 없다.

    저장 파일의 "overrides"(shapeID 또는 원문 명칭 → 한글명)가 가장 우선한다.
    """
    store = _load_store(iso3)
    if level in store:
        names = dict(store[level])
    else:
        candidates, complete = wikidata_candidates(iso3)
        names = match_names(gdf, candidates, level)
        if complete:
            store[level] = names
            _save_store(iso3, store)
    overrides = store.get("overrides", {})
    for row in gdf.itertuples():
        ko = overrides.get(row.shapeID) or overrides.get(row.shapeName)
        if ko:
            names[row.shapeID] = ko
    return names
