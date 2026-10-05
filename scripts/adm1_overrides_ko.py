"""Wikidata에 한국어 레이블이 없는 Level 1 행정구역의 한글 표기 (직접 작성).

data/names_ko/{ISO3}.json의 overrides에 반영한다:
    python scripts/adm1_overrides_ko.py

geoBoundaries 원문에 인코딩이 깨진 명칭이 있어(칠레·포르투갈·세이셸), 영문자·숫자만 남긴 형태로 비교한다.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import gb_api, names_ko  # noqa: E402

OVERRIDES = {
    "AFG": {"Ghanzi": "가즈니주", "Wardak": "와르다크주"},
    "ALB": {"Tiranë": "티라나주"},
    "ARE": {"Umm al-Quwain": "움알쿠와인"},
    "ARG": {"Ciudad Autónoma de Buenos Aires": "부에노스아이레스 자치시"},
    "AUS": {"Other Territories": "기타 준주"},
    "AUT": {"Kärnten": "케른텐주", "Niederösterreich": "니더외스터라이히주", "Oberösterreich": "오버외스터라이히주",
            "Steiermark": "슈타이어마르크주", "Tirol": "티롤주", "Wien": "빈"},
    "AZE": {"Nakhchivan Autonomous Republic": "나히체반 자치공화국", "Contiguous Azerbaijan": "아제르바이잔 본토"},
    "BEL": {"Brussels Hoofdstedelijk": "브뤼셀 수도권 지역", "Vlaams Gewest": "플란데런 지역", "Wallonne Gewest": "왈롱 지역"},
    "BFA": {"Centre": "상트르주", "Boucle du Mouhoun": "부클뒤무운주", "Cascades": "카스카드주", "Centre-Est": "상트르에스트주",
            "Centre-Nord": "상트르노르주", "Centre-Ouest": "상트르우에스트주", "Centre-Sud": "상트르쉬드주", "Est": "에스트주",
            "Hauts-Bassins": "오바생주", "Nord": "노르주", "Plateau Central": "플라토상트랄주", "Sahel": "사헬주",
            "Sud-Ouest": "쉬드우에스트주"},
    "BGD": {"Chittagong": "치타공 디비전"},
    "BHS": {"Acklins": "애클린스", "Biminis": "비미니", "San Salvador": "산살바도르"},
    "BLR": {"Grodno": "흐로드나주", "Mogilev": "마힐료우주"},
    "BRA": {"Pernambuco": "페르남부쿠주", "Tocantins": "토칸칭스주", "Distrito Federal": "연방구"},
    "BWA": {"Chobe District": "초베구"},
    "CAF": {"Nana-Grébizi": "나나그레비지주"},
    "CHE": {"Genève": "제네바주", "Graubünden": "그라우뷘덴주", "Luzern": "루체른주"},
    "CHL": {"Región de Antofagasta": "안토파가스타주", "Región de Arica y Parinacota": "아리카이파리나코타주",
            "Región de Atacama": "아타카마주", "Región de Aysén del Gral.Ibañez del Campo": "아이센주",
            "Región de Coquimbo": "코킴보주", "Región de La Araucanía": "아라우카니아주", "Región de Los Lagos": "로스라고스주",
            "Región de Los Ríos": "로스리오스주", "Región de Magallanes y Antártica Chilena": "마가야네스이데라안타르티카칠레나주",
            "Región de Ñuble": "뉴블레주", "Región de Tarapacá": "타라파카주", "Región de Valparaíso": "발파라이소주",
            "Región del Bío-Bío": "비오비오주", "Región del Libertador Bernardo O'Higgins": "오이긴스주",
            "Región del Maule": "마울레주", "Región Metropolitana de Santiago": "산티아고 수도주"},
    "CHN": {"Guangxi Zhuang Autonomous Region": "광시 좡족 자치구", "Ningxia Ningxia Hui Autonomous Region": "닝샤 후이족 자치구",
            "Xinjiang Uyghur Autonomous Region": "신장 위구르 자치구", "Macau Special Administrative Region": "마카오 특별행정구",
            "Hong Kong Special Administrative Region": "홍콩 특별행정구"},
    "CIV": {"District Autonome D'Abidjan": "아비장 자치구", "District Autonome De Yamoussoukro": "야무수크로 자치구"},
    "CMR": {"Adamaoua": "아다마와주"},
    "COD": {"Upper Uele": "오트우엘레주", "Lower Uele": "바우엘레주", "Sud-Ubangi": "쉬드우방기주", "Central Kasai": "카사이상트랄주"},
    "COL": {"Archipiélago de San Andrés, Providencia y Santa Catalina": "산안드레스 프로비덴시아 산타카탈리나주"},
    "CRI": {"Provincia Heredia": "에레디아주", "Provincia Guanacaste": "과나카스테주", "Provincia Alajuela": "알라후엘라주",
            "Provincia San José": "산호세주", "Provincia Puntarenas": "푼타레나스주", "Provincia Cartago": "카르타고주",
            "Provincia Limón": "리몬주"},
    "CUB": {"Isle of Youth": "후벤투드섬"},
    "CZE": {"Hlavní město Praha": "프라하", "Středočeský kraj": "중앙보헤미아주", "Jihočeský kraj": "남보헤미아주",
            "Plzeňský kraj": "플젠주", "Karlovarský kraj": "카를로비바리주", "Ústecký kraj": "우스티주", "Liberecký kraj": "리베레츠주",
            "Královéhradecký kraj": "흐라데츠크랄로베주", "Pardubický kraj": "파르두비체주", "Kraj Vysočina": "비소치나주",
            "Jihomoravský kraj": "남모라바주", "Olomoucký kraj": "올로모우츠주", "Moravskoslezský kraj": "모라바슬레스코주",
            "Zlínský kraj": "즐린주"},
    "DEU": {"Bayern": "바이에른주", "Niedersachsen": "니더작센주", "Nordrhein-Westfalen": "노르트라인베스트팔렌주",
            "Rheinland-Pfalz": "라인란트팔츠주", "Sachsen": "작센주", "Sachsen-Anhalt": "작센안할트주", "Thüringen": "튀링겐주"},
    "DNK": {"Nordjylland": "노르윌란 지역", "Midtjylland": "미트윌란 지역", "Sjælland": "셸란 지역", "Hovedstaden": "호베드스타덴 지역",
            "Syddanmark": "쉬단마르크 지역"},
    "DOM": {"La Estrelleta": "엘리아스피냐주", "El Seybo": "엘세이보주", "Hermanas": "에르마나스미라발주"},
    "DZA": {"Tipaza": "티파자주"},
    "EGY": {"Minya Governate": "미니아주", "Luxor Governate": "룩소르주"},
    "ESP": {"Canarias": "카나리아 제도", "Ciudad Autónoma de Melilla": "멜리야", "Ciudad Autónoma de Ceuta": "세우타",
            "País Vasco/Euskadi": "바스크 지방", "Comunidad Foral de Navarra": "나바라 지방", "Comunidad de Madrid": "마드리드 지방",
            "Comunitat Valenciana": "발렌시아 지방", "Cataluña/Catalunya": "카탈루냐 지방", "Castilla y León": "카스티야이레온 지방",
            "Illes Balears": "발레아레스 제도", "Principado de Asturias": "아스투리아스 지방"},
    "EST": {"Saare maakond": "사레주", "Pärnu maakond": "패르누주", "Hiiu maakond": "히우주", "Lääne maakond": "래네주",
            "Ida-Viru maakond": "이다비루주", "Harju maakond": "하리우주", "Lääne-Viru maakond": "래네비루주",
            "Tartu maakond": "타르투주", "Valga maakond": "발가주", "Viljandi maakond": "빌랸디주", "Põlva maakond": "폴바주",
            "Järva maakond": "얘르바주", "Rapla maakond": "라플라주", "Võru maakond": "버루주", "Jõgeva maakond": "여게바주"},
    "ETH": {"Hareri": "하라리주", "SNNPR": "남부국가민족인민주"},
    "FIN": {"Finland Proper": "바르시나이스수오미", "Southern Savonia": "에텔래사보", "Northern Savonia": "포흐요이스사보",
            "Tavastia Proper": "칸타해메", "Keski-Pohjanmaa": "케스키포흐얀마", "Åland Islands": "올란드 제도"},
    "FRA": {"Normandie": "노르망디", "Bretagne": "브르타뉴", "Corse": "코르시카"},
    "FSM": {"Kosrae": "코스라에주"},
    "GEO": {"Abkhazia": "압하지야"},
    "GMB": {"Basse": "바세", "Brikama": "브리카마", "Janjanbureh": "잔잔부레", "Kanifing": "카니핑", "Kerewan": "케레완",
            "Kuntaur": "쿤타우르", "Mansakonko": "만사콘코"},
    "GRC": {"Agion Oros": "아토스산", "Macedonia-Thrace": "마케도니아·트라키", "Epirus-Western Macedonia": "이피로스·서마케도니아",
            "Peloponisos-W. Greece & Ionian": "펠로폰네소스·서그리스·이오니아", "Egean": "에게",
            "Thessalia-Central Greece": "테살리아·중앙그리스"},
    "GRD": {"Southern Grenadine Islands": "남부 그레나딘 제도"},
    "HRV": {"Vukovar-Syrmia": "부코바르스리옘주"},
    "HTI": {"Département de l'Ouest": "우에스트주", "Département de la Grande-Anse": "그랑당스주", "Département des Nippes": "니프주",
            "Département du Sud-Est": "쉬데스트주", "Département du Nord": "노르주"},
    "IRN": {"Mazandaran": "마잔다란주"},
    "IRQ": {"An-Najaf": "나자프주", "Babil": "바빌주", "Ninawa": "니네베주", "Dohuk": "다후크주"},
    "ITA": {"Nord-Ovest": "북서부", "Nord-Est": "북동부", "Centro": "중부", "Sud": "남부", "Isole": "도서부"},
    "JAM": {"Saint Ann": "세인트앤 교구"},
    "KAZ": {"South Kazakhstan Region": "남카자흐스탄주"},
    "KEN": {"Trans Nzoia": "트랜스은조이아현", "Bungoma": "붕고마현", "Tharaka": "타라카니시현", "Nyeri": "니에리현",
            "Murang'a": "무랑아현", "Migori": "미고리현", "Kiambu": "키암부현"},
    "KHM": {"Preah Sihanouk": "프레아시아누크주"},
    "KIR": {"Line Islands": "라인 제도"},
    "KWT": {"Al Asimah": "아시마주"},
    "LAO": {"Xaignabouli": "사이냐불리주", "Oudomxay": "우돔사이주", "Xekong": "세콩주"},
    "LBN": {"Beyrouth": "베이루트주", "Liban-Nord": "북부주", "Mont-Liban": "산악레바논주", "Liban-Sud": "남부주",
            "Keserwan-Jbeil": "케세르완즈베일주"},
    "LBY": {"Ash Shati'": "와디알샤티주", "Surt": "수르트주", "Al Marqab": "무르쿠브주",
            "Tajura' wa an Nawahi al Arba": "타주라 및 나와히알아르바주", "Az Zawiyah": "자위야주", "Al Jifarah": "지파라주"},
    "LCA": {"Vieux Fort": "비외포르", "Anse la Raya": "앙스라레", "Gros Islet": "그로이슬레", "Dennery": "데너리", "Micoud": "미쿠",
            "Soufrière": "수프리에르", "Choiseul": "슈아죌", "Laborie": "라보리", "Canaries": "카나리스"},
    "LVA": {"Alūksnes novads": "알룩스네군", "Līvānu novads": "리바니군", "Gulbenes novads": "굴베네군",
            "Ventspils novads": "벤츠필스군", "Valkas novads": "발카군", "Salaspils novads": "살라스필스군",
            "Dienvidkurzemes novads": "남쿠르제메군", "Kuldīgas novads": "쿨디가군", "Saldus novads": "살두스군",
            "Talsu novads": "탈시군", "Tukuma novads": "투쿰스군", "Dobeles novads": "도벨레군", "Jelgavas novads": "옐가바군",
            "Mārupes novads": "마루페군", "Bauskas novads": "바우스카군", "Ogres novads": "오그레군",
            "Aizkraukles novads": "아이즈크라우클레군", "Jēkabpils novads": "예캅필스군", "Ludzas novads": "루자군",
            "Rēzeknes novads": "레제크네군", "Balvu novads": "발비군", "Madonas novads": "마도나군",
            "Smiltenes novads": "스밀테네군", "Cēsu novads": "체시스군", "Valmieras novads": "발미에라군",
            "Ādažu novads": "아다지군", "Ropažu novads": "로파지군", "Siguldas novads": "시굴다군", "Preiļu novads": "프레일리군",
            "Krāslavas novads": "크라슬라바군", "Ķekavas novads": "케카바군", "Olaines novads": "올라이네군",
            "Saulkrastu novads": "사울크라스티군", "Limbažu novads": "림바지군", "Augšdaugavas novads": "아우그슈다우가바군",
            "Varakļānu novads": "바라클라니군"},
    "MCO": {"Monaco": "모나코"},
    "MDA": {"Transnistria": "트란스니스트리아"},
    "MDG": {"Matsiatra Ambony": "오트마치아트라구"},
    "MDV": {"Haa Alif": "하알리프 환초", "Haa Dhaalu": "하달루 환초", "Noonu": "누누 환초", "Shaviyani": "샤비야니 환초",
            "Lhaviyani": "라비야니 환초", "Raa": "라 환초", "Baa": "바 환초", "Alif Alif": "알리프알리프 환초",
            "Alif Dhaalu": "알리프달루 환초", "Meemu": "미무 환초", "Dhaalu": "달루 환초", "Faafu": "파푸 환초", "Thaa": "타 환초",
            "Laamu": "라무 환초", "Gaafu Alif": "가푸알리프 환초", "Gaafu Dhaalu": "가푸달루 환초", "Gnaviyani": "냐비야니 환초",
            "Addu": "아두시", "Kaafu": "카푸 환초", "Vaavu": "바부 환초"},
    "MEX": {"Coahuila de Zaragoza": "코아우일라주", "Distrito Federal": "멕시코시티", "Michoacan de Ocampo": "미초아칸주",
            "Queretaro de Arteaga": "케레타로주", "Veracruz de Ignacio de la Llave": "베라크루스주"},
    "MHL": {"Kwajalein": "콰절린 환초", "Kili": "킬리섬", "Rongelap": "롱겔라프 환초", "Likiep": "리키에프 환초", "Lib": "리브섬",
            "Namu": "나무 환초", "Ailinglaplap": "아일링라플라프 환초", "Ailuk": "아일루크 환초", "Arno": "아르노 환초",
            "Aur": "아우르 환초", "Ebon": "에본 환초", "Enewetak": "에네웨타크 환초", "Jabat": "자바트섬", "Lae": "라에 환초",
            "Mejit": "메지트섬", "Namdrik": "남드리크 환초", "Ujae": "우자에 환초", "Utirik": "우티리크 환초", "Wotho": "워토 환초",
            "Jaluit": "잴루잇 환초", "Mili": "밀리 환초", "Maloelap": "말로엘라프 환초", "Wotje": "워제 환초"},
    "MKD": {"Pelagonia": "펠라고니아 지역", "Southwest": "남서부 지역", "Vardar": "바르다르 지역", "Polog": "폴로그 지역",
            "Southeast": "남동부 지역", "East": "동부 지역", "Skopje": "스코페 지역", "Northeast": "북동부 지역"},
    "MLI": {"Tombouctou": "통북투주"},
    "MLT": {"Saint Lawerence": "산로렌츠", "Gharb": "아르브", "Ghasri": "아스리", "Żebbuġ Gozo": "제부지 (고조)", "Fontana": "폰타나",
            "Rabat Gozo": "라바트 (고조)", "Xgħajra": "슈아이라", "Saint John": "산주안", "Pietà": "피에타", "Mosta": "모스타",
            "Mdina": "임디나", "Mtarfa": "임타르파", "Rabat Malta": "라바트 (몰타)", "Attard": "아타르드", "Xagħra": "샤라",
            "Żebbuġ Malta": "제부지 (몰타)", "Isla": "센글레아", "Bormla": "코스피쿠아", "Saint Lucia's": "산타루치야"},
    "MNE": {"Tivat Municipality": "티바트", "Petnjica Municipality": "페트니차"},
    "MNG": {"Ömnögovi": "음느고비주", "Hovsgel": "흡스굴주"},
    "MUS": {"Black River": "블랙리버구", "St. Brandon": "세인트브랜던 제도"},
    "NAM": {"Cunene": "쿠네네주", "Caprivi": "카프리비주"},
    "NER": {"Tahoua/Agadez": "타우아·아가데즈", "Dossa": "도소주", "Zinder/Diffa": "진데르·디파"},
    "NGA": {"Abuja Federal Capital Territory": "아부자 연방수도지구"},
    "NIC": {"South Atlantic Autonomous Region": "남대서양 자치구"},
    "NIU": {"Tuapa": "투아파", "Namukulu": "나무쿨루", "Hikutavake": "히쿠타바케", "Toi": "토이", "Mutalau": "무탈라우",
            "Lakepa": "라케파", "Liku": "리쿠", "Hakupu": "하쿠푸", "Vaiea": "바이에아", "Avatele": "아바텔레",
            "Tamakautoga": "타마카우토가", "Alofi South": "알로피 남부", "Alofi North": "알로피 북부", "Makefu": "마케푸"},
    "NLD": {"Noord-Holland": "노르트홀란트주", "Zuid-Holland": "자위트홀란트주", "Fryslân": "프리슬란트주",
            "Noord-Brabant": "노르트브라반트주"},
    "NPL": {"Province 1": "코시주", "Province 2": "마데시주"},
    "NZL": {"Chatham Islands Territory": "채텀 제도"},
    "OMN": {"Az Zahirah": "자히라주"},
    "PAN": {"Provincia de Bocas del Toro": "보카스델토로주", "Provincia de Darién": "다리엔주",
            "Comarca Emberá-Wounaan": "엠베라워우난 자치구", "Comarca Guna Yala": "구나얄라 자치구",
            "Provincia de Herrera": "에레라주", "Provincia de Los Santos": "로스산토스주",
            "Comarca Ngäbe-Buglé": "응외베부글레 자치구", "Provincia de Panamá Oeste": "파나마오에스테주",
            "Provincia de Panamá": "파나마주", "Provincia de Veraguas": "베라과스주", "Provincia de Chiriquí": "치리키주",
            "Provincia de Coclé": "코클레주"},
    "PER": {"Municipalidad Metropolitana de Lima": "리마 광역시"},
    "PHL": {"ARMM": "무슬림 민다나오 자치구", "CAR": "코르디예라 행정구", "NCR": "메트로 마닐라", "Calabarzon": "칼라바르손",
            "Mimaropa": "미마로파"},
    "PNG": {"Northern (Oro) Province": "오로주", "West Sepik (Sandaun) Province": "산다운주"},
    "POL": {"Subcarpathian Voivodeship": "포트카르파치에주"},
    "PRK": {"Jagang": "자강도"},
    "PRT": {"Região Autónoma da Madeira": "마데이라 자치지역", "Região Autónoma dos Açores": "아소르스 자치지역",
            "BRAGANÇA": "브라간사현", "ÉVORA": "에보라현", "LISBOA": "리스본현", "SANTARÉM": "산타렝현", "SETÚBAL": "세투발현"},
    "QAT": {"Al Khor and Al Thakhira": "알코르", "Al Sheehaniya": "알샤하니야"},
    "ROU": {"BUCURESTI": "부쿠레슈티"},
    "RUS": {"Republic of Mordovia": "모르도바 공화국", "Khanty-Mansiysk Autonomous Okrug – Ugra": "한티만시 자치구",
            "Republic of Karelia": "카렐리야 공화국", "Moscow Oblast": "모스크바주", "Nenets Autonomous Okrug": "네네츠 자치구",
            "Sakha Republic": "사하 공화국", "Yamalo-Nenets Autonomous Okrug": "야말로네네츠 자치구",
            "Chukotka Autonomous Okrug": "추코트카 자치구"},
    "SAU": {"Hayel Region": "하일주", "Makkah Region": "메카주", "Al Madinah Region": "메디나주", "Al Jawf Region": "자우프주"},
    "SDN": {"Abyei PCA": "아비에이 지역", "Gedaref": "알카다리프주"},
    "SGP": {"NORTH REGION": "북부 지역", "WEST REGION": "서부 지역"},
    "SLB": {"Makira": "마키라울라와주", "Capital Territory (Honiara)": "호니아라"},
    "SLV": {"Departamento de Cuscatlán": "쿠스카틀란주", "Departamento de Usulután": "우술루탄주",
            "Departamento de Ahuachapán": "아우아차판주", "Departamento de Sonsonate": "손소나테주",
            "Departamento de San Miguel": "산미겔주", "Departamento de La Unión": "라우니온주",
            "Departamento de Morazán": "모라산주", "Departamento de La Paz": "라파스주", "Departamento de Santa Ana": "산타아나주",
            "Departamento de Chalatenango": "찰라테낭고주", "Departamento de San Salvador": "산살바도르주",
            "Departamento de Cabañas": "카바냐스주"},
    "SMR": {"Città di San Marino": "산마리노 시"},
    "SOM": {"Hiiraan": "히란주", "Sanaag": "사나그주", "Banadir": "바나디르주", "Togdheer": "토그데르주",
            "Woqooyi Galbeed": "워코이갈베드주", "Sool": "술주"},
    "SRB": {"Syrmia District": "스렘구"},
    "STP": {"Príncipe Province": "프린시페주"},
    "SVN": {"Vzhodna": "동슬로베니아", "Zahodna Slovenija": "서슬로베니아"},
    "SWE": {"Västernorrlands län": "베스테르노를란드주", "Västerbottens län": "베스테르보텐주", "Jämtlands län": "옘틀란드주",
            "Gävleborgs län": "예블레보리주", "Dalarnas län": "달라르나주", "Uppsala län": "웁살라주",
            "Västmanlands län": "베스트만란드주", "Örebro län": "외레브로주", "Värmlands län": "베름란드주",
            "Hallands län": "할란드주", "Skåne län": "스코네주", "Kronobergs län": "크로노베리주", "Blekinge län": "블레킹에주",
            "Kalmar län": "칼마르주", "Jönköpings län": "옌셰핑주", "Stockholms län": "스톡홀름주",
            "Östergötlands län": "외스테르예틀란드주", "Södermanlands län": "쇠데르만란드주", "Norrbottens län": "노르보텐주",
            "Gotlands län": "고틀란드주"},
    "SYC": {"Outer Isla": "외곽 제도", "Baie Saint": "베생트안", "Grand Anse": "그랑당스", "La Digue a": "라디그",
            "Anse Aux P": "앙스오팽", "La Rivière": "라리비에르앙글레즈", "Pointe La": "푸앵트라뤼", "Roche Caïm": "로슈카이만",
            "Saint Loui": "생루이"},
    "SYR": {"Rural Damascus": "리프디마슈크주", "Idleb": "이들리브주", "Ar-Raqqa": "라카주", "Dar'a": "다라주",
            "As-Sweida": "수와이다주"},
    "TCD": {"Ennedi-Ouest": "엔네디우에스트주", "Ennedi-Est": "엔네디에스트주"},
    "TJK": {"Districts of Republican Subordination": "공화국 직할구"},
    "TKM": {"Ahai": "아할주"},
    "TLS": {"Oecusse": "오에쿠시"},
    "TON": {"Ha'apai": "하파이", "Niuas": "니우아스", "Tongatapu": "통가타푸", "Vava'u": "바바우", "'Eua": "에우아"},
    "TTO": {"Tobago": "토바고", "Rio Claro-Mayaro": "리오클라로마야로", "Siparia": "시파리아", "Penal-Debe": "페날데베",
            "Diego Martin": "디에고마틴", "Sangre Grande": "상그레그란데"},
    "TUV": {"Niutao": "니우타오"},
    "TWN": {"Matsu Islands": "마쭈 열도", "Penghu": "펑후현"},
    "TZA": {"Zanzibar South & Central": "잔지바르 중앙남부주", "Zanzibar North": "잔지바르 북부주",
            "Zanzibar Urban/West": "잔지바르 도시서부주"},
    "USA": {"Commonwealth of the Northern Mariana Islands": "북마리아나 제도"},
    "UZB": {"Republic of Karakalpakstan": "카라칼파크스탄 공화국"},
    "VEN": {"Distrito Capital": "수도구", "Dependencias Federales": "연방 속령"},
    "VNM": {"Thừa Thiên Huế": "트어티엔후에성"},
    "XKX": {"District of Prishtina": "프리슈티나구", "District of Mitrovica": "미트로비차구", "District of Peja": "페야구",
            "District of Gjilan": "질란구", "District of Gjakova": "자코바구", "District of Prizren": "프리즈렌구",
            "District of Ferizaj": "페리자이구"},
    "YEM": {"Sanʿaʾ": "사나", "Sanʿaʾ Governorate": "사나주", "‘Adan Governorate": "아덴주", "Ad Dali' Governorate": "달리주",
            "Sa'dah Governorate": "사다주", "Socotra": "소코트라주"},
}


def _skeleton(text: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", text.lower())


def main() -> None:
    total = missing = 0
    for country in gb_api.list_countries():
        iso3 = country["iso3"]
        levels = gb_api.country_levels(iso3)
        if "ADM1" not in levels:
            continue
        gdf = gb_api.load_boundary(levels["ADM1"])
        path = names_ko.NAMES_DIR / f"{iso3}.json"
        store = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        matched = store.get("ADM1", {})
        table = {_skeleton(k): v for k, v in OVERRIDES.get(iso3, {}).items()}
        overrides = store.get("overrides", {})
        for row in gdf.itertuples():
            total += 1
            if row.shapeID in matched or row.shapeName in overrides:
                continue
            ko = table.get(_skeleton(row.shapeName))
            if ko:
                overrides[row.shapeName] = ko
            else:
                missing += 1
                print("미해결", iso3, row.shapeID, row.shapeName, sep="\t")
        if overrides:
            store["overrides"] = overrides
            path.write_text(json.dumps(store, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"Level 1 {total}개 중 한글 명칭 없음 {missing}개")


if __name__ == "__main__":
    main()
