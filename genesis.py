import os, sqlite3, json, re
from datetime import date
import feedparser

# ==========================
# Traduzione automatica (robusta)
# ==========================
USE_TRANSLATION = True

try:
    from deep_translator import GoogleTranslator
    def traduci_testo(txt, lang="it"):
        if not USE_TRANSLATION or not txt:
            return txt
        try:
            return GoogleTranslator(source="auto", target=lang).translate(txt)
        except Exception:
            return txt
except Exception:
    def traduci_testo(txt, lang="it"):
        return txt

# ==========================
# CONFIG
# ==========================
DB_PATH       = "genesi.db"
ARCHIVE_PATH  = "archive.json"
OUTPUT_INDEX  = "index.html"
SITEMAP       = "sitemap.xml"
ROBOTS        = "robots.txt"
VERCEL_JSON   = "vercel.json"
SITE_URL      = "https://genesi.vrabo.it"

LANGS = {
    "it": "Italiano",
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "de": "Deutsch",
}

FEEDS = [
    "https://www.sciencedaily.com/rss/fossils_ruins/human_evolution.xml",
    "https://phys.org/rss-feed/tags/human+evolution/",
]

# Marker fissi
COUNTRIES = [
    ("GR","Grecia: Petralona","Il cranio di Petralona ridefinisce l’evoluzione europea.","Nature",40.6,23.0),
    ("ET","Etiopia: Lucy","Lucy rimane simbolo dell’Australopithecus afarensis con nuovi dati.","ScienceDaily",9.1,38.7),
    ("IT","Italia: Neanderthal","Ritrovamenti in Italia centrale mostrano nuove connessioni.","Phys.org",42.5,12.5),
]

# Riconoscimento luoghi
REGION_HINTS = {
    r"\b(etio(pia|pia)|ethiopia|afar|hadar)\b":              ("Etiopia (Afar/Hadar)", 9.1, 38.7),
    r"\b(israele|israel|skhul|levant(e)?)\b":               ("Israele (Skhul/Levant)", 31.8, 35.2),
    r"\b(denisov(a|an)|altai|siberia)\b":                   ("Siberia (Grotta di Denisova)", 51.4, 84.7),
    r"\b(tibet|himalaya|alt(o|a)\s*quota|tibetan)\b":       ("Tibet/Himalaya", 30.0, 90.0),
    r"\b(sud\s*africa|south\s*africa|blombos|sterkfontein)\b": ("Sudafrica", -29.0, 24.0),
    r"\b(kenya|turkana|olorgesa(il|ilie))\b":               ("Kenya (Turkana)", 3.5, 36.0),
    r"\b(tanzania|olduvai|old(u|o)vai)\b":                  ("Tanzania (Olduvai)", -3.0, 35.4),
    r"\b(grecia|greece|petralona)\b":                       ("Grecia (Petralona)", 40.6, 23.0),
    r"\b(italia|italy|grotta)\b":                           ("Italia (siti vari)", 42.5, 12.5),
    r"\b(cina|china|xiahe)\b":                              ("Cina (Xiahe/altro)", 35.0, 103.0),
    r"\b(georgia|dmanisi)\b":                               ("Georgia (Dmanisi)", 41.5, 44.8),
    r"\b(marocco|jebel\s*irhoud)\b":                        ("Marocco (Jebel Irhoud)", 31.95, -4.0),
    r"\b(australia|sahul)\b":                               ("Australia (Sahul)", -25.0, 133.0),
    r"\b(america(s)?|and(es|ini)|amazon(as)?)\b":           ("Americhe", 0.0, -60.0),
}

# ==========================
# LOGO (solo SVG)
# ==========================
LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" width="600" height="600">
  <defs>
    <radialGradient id="bg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#00A2FF" stop-opacity="1"/>
      <stop offset="100%" stop-color="#004080" stop-opacity="1"/>
    </radialGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="12" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <circle cx="300" cy="300" r="280" fill="url(#bg)"/>
  <circle cx="300" cy="300" r="200" fill="none" stroke="#FFFFFF" stroke-width="6" opacity="0.9"/>
  <circle cx="300" cy="300" r="130" fill="none" stroke="#FFFFFF" stroke-width="5" opacity="0.6"/>
  <circle cx="300" cy="300" r="60"  fill="none" stroke="#FFFFFF" stroke-width="4" opacity="0.4"/>
  <path d="M520 300 A220 220 0 0 0 300 80" stroke="#FFFFFF" stroke-width="14" fill="none" stroke-linecap="round" filter="url(#glow)"/>
  <circle cx="300" cy="300" r="18" fill="#FFFFFF" filter="url(#glow)"/>
  <text x="50%" y="560" text-anchor="middle"
        font-family="Orbitron, sans-serif"
        font-size="64" font-weight="800"
        fill="#FFFFFF" letter-spacing="12" filter="url(#glow)">GENESI</text>
</svg>"""

# ==========================
# DB
# ==========================
def init_db(conn):
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS chapters_global
              (date TEXT, lang TEXT, title TEXT, content TEXT, sources TEXT,
              PRIMARY KEY(date, lang))""")
    conn.commit()

def insert_global(conn, date_str, lang, title, content, sources_json):
    conn.execute("INSERT OR REPLACE INTO chapters_global VALUES (?,?,?,?,?)",
                 (date_str, lang, title, content, sources_json))
    conn.commit()

# ==========================
# Feed & geotagging
# ==========================
def fetch_latest_news(max_items=6, lang="it"):
    items, seen = [], set()
    headers = {"User-Agent": "Mozilla/5.0 (GenesiBot)"}
    for url in FEEDS:
        try:
            feed = feedparser.parse(url, request_headers=headers)
            for entry in feed.entries[:max_items]:
                link = getattr(entry, "link", "")
                if not link or link in seen:
                    continue
                seen.add(link)
                raw_title   = getattr(entry, "title", "")
                raw_summary = getattr(entry, "summary", "")
                titolo   = traduci_testo(raw_title, lang)
                summary  = traduci_testo(raw_summary, lang)
                items.append({
                    "title": titolo, "summary": summary, "url": link,
                    "raw_title": raw_title or "", "raw_summary": raw_summary or "",
                })
        except Exception as e:
            print(f"⚠️ Errore feed {url}: {e}")
            continue
    return items

def detect_markers_from_news(news_list, lang="it"):
    markers, seen = [], set()
    for n in news_list:
        text = f"{n.get('raw_title','')} {n.get('raw_summary','')} {n.get('title','')} {n.get('summary','')}".lower()
        matched = False
        for pattern, (label, lat, lon) in REGION_HINTS.items():
            if re.search(pattern, text):
                luogo = traduci_testo(label, lang)
                key = (luogo, n["url"])
                if key not in seen:
                    seen.add(key)
                    markers.append({
                        "code": "",
                        "title": f"<b>{n['title']}</b><br/>{luogo}<br/><a href='{n['url']}' target='_blank' rel='noopener'>🔗 Fonte</a>",
                        "lat": lat, "lon": lon
                    })
                matched = True
                break
        if not matched:
            markers.append({
                "code": "",
                "title": f"<b>{n['title']}</b><br/><i>(Località non specificata)</i><br/><a href='{n['url']}' target='_blank' rel='noopener'>🔗 Fonte</a>",
                "lat": 20.0, "lon": 0.0
            })
    return markers

# ==========================
# MAIN
# ==========================
def main():
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    all_exports = {}

    for lang, langname in LANGS.items():
        news = fetch_latest_news(lang=lang)
        sources = [n["url"] for n in news] if news else []

        header_line = traduci_testo("Oggi, un nuovo capitolo della nostra origine.", lang)
        global_text = f"<p>{header_line} ({today})</p>"

        if news:
            for n in news:
                global_text += (
                    "<details>"
                    f"<summary><h3>{n['title']}</h3></summary>"
                    f"<p>{n['summary']}</p>"
                    f"<p><a href='{n['url']}' target='_blank' rel='noopener'>🔗 Fonte</a></p>"
                    "</details>"
                )
        else:
            global_text += f"<p>{traduci_testo('Nessuna notizia disponibile oggi.', lang)}</p>"

        base_markers = [{"code": c[0], "title": c[1], "lat": c[4], "lon": c[5]} for c in COUNTRIES]
        auto_markers = detect_markers_from_news(news, lang=lang)
        markers      = base_markers + auto_markers

        insert_global(conn, today, lang, "Capitolo Globale", global_text, json.dumps(sources, ensure_ascii=False))

        all_exports[lang] = {
            "date": today,
            "lang": lang,
            "global": global_text,
            "markers": markers,
        }

    # Archivio JSON
    with open(ARCHIVE_PATH, "w", encoding="utf8") as f:
        json.dump(all_exports, f, indent=2, ensure_ascii=False)

    # Logo SVG in root
    with open("genesi_logo.svg", "w", encoding="utf8") as f:
        f.write(LOGO_SVG)

    # ---- HTML index ----
    archive_json = json.dumps(all_exports, ensure_ascii=False)
    buttons_html = "".join([f"<button class='lang' onclick=\"loadLang('{l}')\">{name}</button>" for l, name in LANGS.items()])

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>genesi.vrabo.it – Storia Umana</title>
<meta name="description" content="Ogni giorno un nuovo capitolo della storia umana, multilingua."/>
<link rel="canonical" href="{SITE_URL}"/>
<link rel="icon" href="/favicon.ico" type="image/x-icon"/>

<meta property="og:title" content="GENESI – Storia Umana"/>
<meta property="og:description" content="Capitoli evolutivi aggiornati quotidianamente."/>
<meta property="og:image" content="{SITE_URL}/genesi_logo.svg"/>
<meta property="og:url" content="{SITE_URL}"/>
<meta name="twitter:card" content="summary_large_image"/>

<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
<style>
:root {{ --azure:#007FFF; --dark:#0c0c0f; --light:#fff; --card:rgba(255,255,255,0.06); }}
* {{ box-sizing:border-box }}
body {{ margin:0; font-family: 'Exo 2', system-ui; background:linear-gradient(135deg,var(--dark),#191b20); color:var(--light); text-align:center; }}
header {{ padding:2.2rem 1rem; background:rgba(0,0,0,0.5); backdrop-filter:blur(12px); position:sticky; top:0; z-index:10 }}
header img {{ width:96px; height:auto }}
h1 {{ letter-spacing:10px; font-size:3rem; margin:0.7rem 0 0; font-family:'Orbitron',sans-serif }}
main {{ max-width:1100px; margin:2rem auto; padding:2rem; background:var(--card); border-radius:24px; box-shadow:0 30px 100px rgba(0,0,0,0.5); text-align:left }}
.chapter details {{ margin:1rem 0; padding:1rem 1.2rem; border:1px solid rgba(255,255,255,0.18); border-radius:14px; background:rgba(255,255,255,0.03) }}
.chapter summary {{ cursor:pointer; color:var(--azure); font-weight:700 }}
.chapter a {{ color:var(--azure); text-decoration:none }}
h2.section {{ color:var(--azure); margin:2rem 0 1rem; text-align:center }}
#map {{ height:520px; border-radius:18px; overflow:hidden }}
.lang-switch {{ display:flex; flex-wrap:wrap; gap:.5rem; justify-content:center; margin:0 0 1rem 0 }}
button.lang {{ padding:.45rem .9rem; border:1px solid var(--azure); background:none; color:var(--azure); border-radius:999px; cursor:pointer; font-weight:700 }}
button.lang:hover {{ transform:translateY(-1px); box-shadow:0 6px 22px rgba(0,127,255,.25) }}
.ads {{ margin:2rem auto 0; padding:1rem; background:rgba(255,255,255,0.05); border-radius:12px; text-align:center }}
footer {{ max-width:1100px; margin:2rem auto; color:#bbb; padding:0 1rem 2rem }}
</style>
</head>
<body>
<header>
  <img src="/genesi_logo.svg" alt="GENESI Logo" />
  <h1>genesi.vrabo.it</h1>
</header>

<main>
  <div class="lang-switch">{buttons_html}</div>
  <div id="chapter" class="chapter"></div>
  <h2 class="section">Mappa delle Origini</h2>
  <div id="map"></div>
  <div class="ads">
    <iframe title="ads" src="about:blank" width="728" height="90" style="border:none;max-width:100%"></iframe>
  </div>
</main>

<footer>
  <p>&copy; {today} genesi.vrabo.it — Tutti i diritti riservati</p>
</footer>

<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
<script>
let archive = {archive_json};
const map = L.map('map').setView([20,0], 2);
L.tileLayer('https://{{{{s}}}}.tile.openstreetmap.org/{{{{z}}}}/{{{{x}}}}/{{{{y}}}}.png', {{
  attribution: '&copy; OpenStreetMap contributors'
}}).addTo(map);
function clearMarkers() {{
  map.eachLayer(function(layer) {{
    if (layer instanceof L.Marker) map.removeLayer(layer);
  }});
}}
function loadMarkers(markers) {{
  if (!markers || !markers.length) return;
  const group = [];
  markers.forEach(m => {{
    const mk = L.marker([m.lat, m.lon]).addTo(map).bindPopup(m.title || "", {{ maxWidth: 320 }});
    group.push(mk);
  }});
  try {{
    const g = L.featureGroup(group);
    map.fitBounds(g.getBounds().pad(0.25));
  }} catch(e) {{}}
}}
function loadLang(lang) {{
  const data = archive[lang] || archive["it"];
  document.getElementById("chapter").innerHTML = data.global;
  clearMarkers();
  loadMarkers(data.markers);
}}
loadLang("it");
</script>
</body>
</html>"""
    with open(OUTPUT_INDEX, "w", encoding="utf8") as f:
        f.write(html)

    # vercel.json
    vercel_conf = {
        "cleanUrls": True,
        "rewrites": [
            {
                "source": "/((?!api|.*\\..*).*)",
                "destination": "/index.html"
            }
        ]
    }
    with open(VERCEL_JSON, "w", encoding="utf8") as f:
        f.write(json.dumps(vercel_conf, indent=2))

    conn.close()
    print("✅ GENESI FULL POWER: index.html + genesi_logo.svg unico + mappa dinamica + workflow daily + rewrites OK!")

if __name__ == "__main__":
    main()
