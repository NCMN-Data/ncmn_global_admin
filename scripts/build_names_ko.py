"""Level 1 한글 행정구역 명칭 사전(data/names_ko/{ISO3}.json)을 일괄 생성한다.

한글명을 찾지 못한 구역은 표준출력에 "MISS<TAB>ISO3<TAB>shapeID<TAB>원문" 형식으로 남긴다.

사용법:
    python scripts/build_names_ko.py            # 전체 국가
    python scripts/build_names_ko.py KOR JPN    # 지정 국가만
    python scripts/build_names_ko.py --force KOR  # 기존 결과를 지우고 다시 매칭
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import gb_api, names_ko  # noqa: E402


def main(argv: list[str]) -> None:
    force = "--force" in argv
    targets = [a.upper() for a in argv if not a.startswith("--")]
    targets = targets or [c["iso3"] for c in gb_api.list_countries()]
    for iso3 in targets:
        try:
            levels = gb_api.country_levels(iso3)
            if force:
                path = names_ko.NAMES_DIR / f"{iso3}.json"
                if path.exists():
                    store = json.loads(path.read_text(encoding="utf-8"))
                    path.write_text(
                        json.dumps({"overrides": store.get("overrides", {})}, ensure_ascii=False, indent=1),
                        encoding="utf-8",
                    )
                (gb_api.CACHE_DIR / "wikidata" / f"{iso3}.json").unlink(missing_ok=True)
            if "ADM1" not in levels:
                print(iso3, names_ko.country_name_ko(iso3), "ADM1 없음", sep="\t", flush=True)
                continue
            gdf = gb_api.load_boundary(levels["ADM1"])
            names = names_ko.admin_names_ko(iso3, "ADM1", gdf)
            print(iso3, names_ko.country_name_ko(iso3), f"ADM1 {len(names)}/{len(gdf)}", sep="\t", flush=True)
            for row in gdf.itertuples():
                if row.shapeID not in names:
                    print("MISS", iso3, row.shapeID, row.shapeName, sep="\t", flush=True)
        except Exception as exc:
            print(iso3, f"실패: {exc}", sep="\t", flush=True)
        time.sleep(1)  # Wikidata 질의 간격


if __name__ == "__main__":
    main(sys.argv[1:])
