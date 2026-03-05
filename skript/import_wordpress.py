#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from html import escape
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
WP_XML = ROOT / "migration/wordpress/torbjrnsutvalde.WordPress.2026-03-05.xml"

NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}

LANG_LABELS = {
    "no": ("Norsk", "🇳🇴"),
    "se": ("Svensk", "🇸🇪"),
    "dk": ("Dansk", "🇩🇰"),
    "ie": ("Irsk", "🇮🇪"),
    "fi": ("Finsk", "🇫🇮"),
    "de": ("Tysk", "🇩🇪"),
    "gb": ("Engelsk", "🇬🇧"),
}


@dataclass
class Song:
    title: str
    slug: str
    content_html: str
    plain_text: str
    songtypes: list[tuple[str, str]]
    languages: list[tuple[str, str]]
    tekstforfattar: str
    komponist: str
    apple_music: str
    spotify: str
    youtube: str


def parse_custom_css(root: ET.Element) -> str:
    for it in root.findall("./channel/item"):
        if it.findtext("wp:post_type", "", NS) != "wp_global_styles":
            continue
        if it.findtext("wp:status", "", NS) != "publish":
            continue
        raw = it.findtext("content:encoded", "", NS) or ""
        try:
            blob = json.loads(raw)
            return blob.get("styles", {}).get("css", "")
        except json.JSONDecodeError:
            return ""
    return ""


def postmeta_values(item: ET.Element) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for m in item.findall("wp:postmeta", NS):
        key = (m.findtext("wp:meta_key", "", NS) or "").strip()
        val = (m.findtext("wp:meta_value", "", NS) or "").strip()
        if not key or key.startswith("_"):
            continue
        out[key].append(val)
    return out


def first_nonempty(values: list[str]) -> str:
    for v in values:
        if v:
            return v
    return ""


def content_to_html(raw: str) -> str:
    raw = (raw or "").strip().replace("\r\n", "\n")
    if not raw:
        return "<p></p>"

    if "<" in raw and ">" in raw:
        return raw

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    html_parts: list[str] = []
    for para in paragraphs:
        lines = [escape(line.rstrip()) for line in para.split("\n")]
        html_parts.append("<p>" + "<br>\n".join(lines) + "</p>")
    return "\n\n".join(html_parts) if html_parts else "<p></p>"


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def load_data() -> tuple[str, str, list[Song], str]:
    root = ET.parse(WP_XML).getroot()
    custom_css = parse_custom_css(root)

    home_title = "Torbjørns utvalde songar"
    home_note = (
        "<p class=\"song-notice\"><em>På små skjermar kan det vere lurt å snu telefonen "
        "for å sjå teksten i riktig breidde.</em></p>"
    )

    songs: list[Song] = []

    for item in root.findall("./channel/item"):
        if item.findtext("wp:post_type", "", NS) != "song":
            continue
        if item.findtext("wp:status", "", NS) != "publish":
            continue

        title = (item.findtext("title", "") or "").strip()
        slug = (item.findtext("wp:post_name", "", NS) or "").strip()
        raw_content = item.findtext("content:encoded", "", NS) or ""
        content_html = content_to_html(raw_content)

        songtypes: list[tuple[str, str]] = []
        languages: list[tuple[str, str]] = []
        for c in item.findall("category"):
            dom = (c.get("domain") or "").strip()
            nicename = (c.get("nicename") or "").strip()
            label = (c.text or "").strip()
            if dom == "songtype":
                songtypes.append((nicename, label or nicename))
            if dom == "sprak":
                languages.append((nicename, label or nicename))

        pm = postmeta_values(item)
        tekstforfattar = first_nonempty(pm.get("tekstforfattar", []))
        komponist = first_nonempty(pm.get("komponist", []))
        apple_music = first_nonempty(pm.get("apple_music", []))
        spotify = first_nonempty(pm.get("spotify", []))
        youtube = first_nonempty(pm.get("youtube", []))

        plain_text = " ".join(
            x for x in [title, tekstforfattar, komponist, strip_tags(content_html)] if x
        )

        songs.append(
            Song(
                title=title,
                slug=slug,
                content_html=content_html,
                plain_text=plain_text,
                songtypes=songtypes,
                languages=languages,
                tekstforfattar=tekstforfattar,
                komponist=komponist,
                apple_music=apple_music,
                spotify=spotify,
                youtube=youtube,
            )
        )

    songs.sort(key=lambda s: s.title.casefold())
    return home_title, home_note + "\n", songs, custom_css


def ensure_dirs() -> None:
    for rel in ["song", "stilar", "data", "skript", "assets/img"]:
        (ROOT / rel).mkdir(parents=True, exist_ok=True)


def render_index(title: str, note_html: str, songs: list[Song]) -> str:
    by_songtype: dict[tuple[str, str], list[Song]] = defaultdict(list)
    for s in songs:
        if s.songtypes:
            for t in s.songtypes:
                by_songtype[t].append(s)
        else:
            by_songtype[("ukjent", "Ukjent")].append(s)

    groups = sorted(by_songtype.items(), key=lambda kv: kv[0][1].casefold())

    all_langs: dict[str, str] = {}
    for s in songs:
        for code, label in s.languages:
            all_langs[code] = label

    lang_buttons = [
        '<button type="button" class="song-language-filter__btn" data-sprak="" aria-pressed="true">Alle språk</button>'
    ]
    for code, label in sorted(all_langs.items(), key=lambda kv: kv[1].casefold()):
        fallback_label, flag = LANG_LABELS.get(code, (label, "🌐"))
        vis_label = label or fallback_label
        lang_buttons.append(
            f'<button type="button" class="song-language-filter__btn" data-sprak="{escape(code)}" aria-pressed="false" title="{escape(vis_label)}">'
            f'<span aria-hidden="true">{flag}</span><span class="sr-only">{escape(vis_label)}</span></button>'
        )

    jump_items = []
    sections = []
    for (slug, label), items in groups:
        jump_items.append(
            f'<li class="song-toc-jump__item" data-songtype="{escape(slug)}"><a href="#songtype-{escape(slug)}">{escape(label)}</a></li>'
        )

        lis = []
        for s in sorted(items, key=lambda x: x.title.casefold()):
            sprak_codes = " ".join(sorted({c for c, _ in s.languages}))
            lis.append(
                f'<li data-sprak="{escape(sprak_codes)}"><a href="song/{escape(s.slug)}/">{escape(s.title)}</a></li>'
            )

        sections.append(
            f'''<section class="song-toc-section" data-songtype="{escape(slug)}">\n<h2 id="songtype-{escape(slug)}">{escape(label)}</h2>\n<ul class="song-toc-list">\n{''.join(lis)}\n</ul>\n</section>'''
        )

    return f'''<!doctype html>
<html lang="nn">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="stilar/hovud.css" />
</head>
<body class="front-page home">
  <main class="wp-site-blocks">
    <article class="entry-content wp-block-post-content">
      <h1>{escape(title)}</h1>
      {note_html}

      <div class="song-search">
        <label class="song-search__label" for="song-live-search">Søk i songtekstar</label>
        <input id="song-live-search" class="song-search__input" type="search" placeholder="Skriv minst 2 teikn…" autocomplete="off" />
        <div class="song-search__hint">Tips: Du kan søke etter både tittel og tekst.</div>
        <div class="song-search__results" aria-live="polite"></div>
      </div>

      <div class="song-language-filter" aria-label="Filtrer etter språk">
        {''.join(lang_buttons)}
      </div>

      <nav class="song-toc-jump">
        <ul>
          {''.join(jump_items)}
        </ul>
      </nav>

      <div class="song-toc">
        {''.join(sections)}
      </div>
    </article>
  </main>

  <button class="to-top" type="button" aria-label="Til toppen">↑</button>
  <button class="dark-toggle" type="button" aria-pressed="false" aria-label="Byt mellom lys og mørk modus">
    <span class="dark-toggle__icon" aria-hidden="true">☾</span>
    <span class="dark-toggle__text">Mørk</span>
  </button>

  <script src="skript/app.js"></script>
</body>
</html>'''


def render_song_page(song: Song) -> str:
    credits: list[str] = []
    if song.tekstforfattar:
        credits.append(f'<span class="song-credit"><strong>Tekst:</strong> {escape(song.tekstforfattar)}</span>')
    if song.komponist:
        credits.append(f'<span class="song-credit"><strong>Melodi:</strong> {escape(song.komponist)}</span>')

    buttons = [
        f'<button type="button" class="song-btn song-btn-small song-btn-print" data-song-print="1" data-title="{escape(song.title)}">🖨 Skriv ut</button>'
    ]
    if song.apple_music:
        buttons.append(
            f'<a class="song-btn song-btn-small" href="{escape(song.apple_music)}" target="_blank" rel="noopener"> Apple Music</a>'
        )
    if song.spotify:
        buttons.append(
            f'<a class="song-btn song-btn-small" href="{escape(song.spotify)}" target="_blank" rel="noopener">Spotify</a>'
        )
    if song.youtube:
        buttons.append(
            f'<a class="song-btn song-btn-small song-btn-youtube" href="{escape(song.youtube)}" target="_blank" rel="noopener">YouTube</a>'
        )

    note = (
        '<p class="song-notice"><em>På små skjermar kan det vere lurt å snu telefonen '
        'for å sjå teksten i riktig breidde.</em></p>'
    )

    return f'''<!doctype html>
<html lang="nn">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(song.title)} | Torbjørns utvalde songar</title>
  <link rel="stylesheet" href="../../stilar/hovud.css" />
</head>
<body class="single-song">
  <main class="wp-site-blocks">
    <article class="entry-content wp-block-post-content">
      <p class="tilbake"><a href="../../">← Tilbake til framsida</a></p>
      {note}
      <h1>{escape(song.title)}</h1>

      <div class="song-meta">
        {'<div class="song-credits">' + ''.join(credits) + '</div>' if credits else ''}
      </div>

      <div class="song-lyrics">{song.content_html}</div>

      <div class="song-actions song-actions-bottom">
        {''.join(buttons)}
      </div>

      <p class="tilbake"><a href="../../">← Tilbake til framsida</a></p>
    </article>
  </main>

  <button class="dark-toggle" type="button" aria-pressed="false" aria-label="Byt mellom lys og mørk modus">
    <span class="dark-toggle__icon" aria-hidden="true">☾</span>
    <span class="dark-toggle__text">Mørk</span>
  </button>

  <script src="../../skript/app.js"></script>
</body>
</html>'''


def write_css(custom_css: str) -> None:
    base_css = '''/* Grunnstil inspirert av WordPress Twenty Twenty-Five */
:root {
  --wp-content-size: 600px;
  --wp-wide-size: 680px;
  --wp-bg: #ffffff;
  --wp-fg: #1a1a1a;
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: Manrope, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--wp-fg);
  background: var(--wp-bg);
  line-height: 1.55;
  padding: 5rem 2rem;
}

.wp-site-blocks {
  max-width: var(--wp-content-size);
  margin: 0 auto;
}

.entry-content h1 {
  font-size: clamp(2rem, 5vw, 3rem);
  line-height: 1.1;
  margin: 2rem 0;
  font-weight: 900;
}

.entry-content h2 {
  font-size: clamp(1.4rem, 3.5vw, 2rem);
  margin-top: 2rem;
}

a {
  text-decoration-thickness: 1px;
  text-underline-offset: .1em;
}

:where(.wp-site-blocks *:focus) {
  outline-width: 2px;
  outline-style: solid;
}

.entry-content p, .entry-content li {
  font-size: 1rem;
}

.tilbake a {
  text-decoration: none;
  font-size: 0.9rem;
}

.song-lyrics p, .song-lyrics li, .song-lyrics pre {
  font-size: 1.2rem;
}

.song-lyrics p {
  white-space: normal;
}

.song-btn {
  padding: .35em .7em;
}

.song-btn-print {
  font: inherit;
}

.sr-only{
  position:absolute;
  width:1px;
  height:1px;
  padding:0;
  margin:-1px;
  overflow:hidden;
  clip:rect(0,0,0,0);
  white-space:nowrap;
  border:0;
}

@media (max-width: 800px) {
  body { padding: 2rem 1rem 3rem; }
}
'''

    (ROOT / "stilar/hovud.css").write_text(base_css + "\n\n" + (custom_css or "") + "\n", encoding="utf-8")


def write_js() -> None:
    js = '''(function () {
  var KEY = "songhefte_theme";

  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    var btn = document.querySelector(".dark-toggle");
    if (!btn) return;
    var dark = theme === "dark";
    btn.setAttribute("aria-pressed", String(dark));
    var icon = btn.querySelector(".dark-toggle__icon");
    var txt = btn.querySelector(".dark-toggle__text");
    if (icon) icon.textContent = dark ? "☀︎" : "☾";
    if (txt) txt.textContent = dark ? "Lys" : "Mørk";
  }

  function initTheme() {
    var saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) {}
    var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    setTheme(saved || (prefersDark ? "dark" : "light"));

    var btn = document.querySelector(".dark-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var now = document.documentElement.getAttribute("data-theme") || "light";
      var next = now === "dark" ? "light" : "dark";
      setTheme(next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
    });
  }

  function initPrint() {
    document.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-song-print]");
      if (!btn) return;
      e.preventDefault();
      window.print();
    });
  }

  function initToTop() {
    var btn = document.querySelector(".to-top");
    if (!btn) return;

    function update() {
      btn.style.display = window.scrollY > 400 ? "inline-flex" : "none";
    }

    window.addEventListener("scroll", update, { passive: true });
    update();

    btn.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  function initSearchAndFilter() {
    var input = document.getElementById("song-live-search");
    var results = document.querySelector(".song-search__results");
    var toc = document.querySelector(".song-toc");
    var jump = document.querySelector(".song-toc-jump");
    var langRoot = document.querySelector(".song-language-filter");

    if (!input || !results || !toc) return;

    var index = [];
    fetch("data/sok-index.json", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (data) { index = Array.isArray(data) ? data : []; })
      .catch(function () { index = []; });

    var activeLang = "";

    function applyLangFilter() {
      var sections = toc.querySelectorAll(".song-toc-section");
      sections.forEach(function (sec) {
        var visible = 0;
        var items = sec.querySelectorAll(".song-toc-list li[data-sprak]");
        items.forEach(function (li) {
          var codes = (li.getAttribute("data-sprak") || "").trim();
          var arr = codes ? codes.split(/\\s+/) : [];
          var show = !activeLang || arr.indexOf(activeLang) !== -1;
          li.style.display = show ? "" : "none";
          if (show) visible += 1;
        });
        sec.style.display = visible ? "" : "none";
        if (jump) {
          var st = sec.getAttribute("data-songtype");
          var jumpItem = jump.querySelector('.song-toc-jump__item[data-songtype="' + st + '"]');
          if (jumpItem) jumpItem.style.display = visible ? "" : "none";
        }
      });
    }

    if (langRoot) {
      langRoot.addEventListener("click", function (e) {
        var btn = e.target.closest("button[data-sprak]");
        if (!btn) return;
        activeLang = btn.getAttribute("data-sprak") || "";
        langRoot.querySelectorAll("button[data-sprak]").forEach(function (b) {
          b.setAttribute("aria-pressed", "false");
        });
        btn.setAttribute("aria-pressed", "true");
        applyLangFilter();
      });
    }

    function renderResults(items, q) {
      if (!q || q.length < 2) {
        results.innerHTML = "";
        toc.style.display = "";
        if (jump) jump.style.display = "";
        if (langRoot) langRoot.style.display = "";
        applyLangFilter();
        return;
      }

      if (!items.length) {
        results.innerHTML = '<div class="song-search__empty">Ingen treff.</div>';
        toc.style.display = "none";
        if (jump) jump.style.display = "none";
        if (langRoot) langRoot.style.display = "none";
        return;
      }

      var html = '<div class="song-search__count">Treff: ' + items.length + '</div><ul class="song-search__list">';
      items.forEach(function (it) {
        html += '<li><a href="' + it.link + '">' + it.title + '</a></li>';
      });
      html += "</ul>";
      results.innerHTML = html;
      toc.style.display = "none";
      if (jump) jump.style.display = "none";
      if (langRoot) langRoot.style.display = "none";
    }

    var timer = null;
    input.addEventListener("input", function () {
      var q = (input.value || "").trim().toLowerCase();
      clearTimeout(timer);
      timer = setTimeout(function () {
        if (q.length < 2) {
          renderResults([], q);
          return;
        }
        var hits = index.filter(function (it) {
          return (it.text || "").toLowerCase().indexOf(q) !== -1;
        }).slice(0, 200);
        renderResults(hits, q);
      }, 120);
    });

    applyLangFilter();
  }

  initTheme();
  initPrint();
  initToTop();
  initSearchAndFilter();
})();
'''
    (ROOT / "skript/app.js").write_text(js, encoding="utf-8")


def write_readme(song_count: int) -> None:
    txt = f'''# utvalde

Statisk versjon av den tidlegare WordPress-sida for utvalde songar.

## Kva som er migrert

- Framside med innhaldsliste per songtype
- Språkfilter
- Live-søk i tittel + tekst
- Mørk modus
- Songsider med metadata + knappar (Skriv ut / Apple Music / Spotify / YouTube)
- {song_count} publiserte songar frå WordPress-eksporten

## Kjelde for migrering

- `migration/wordpress/torbjrnsutvalde.WordPress.2026-03-05.xml`
- `migration/wordpress/sql12_hmg9_webhuset_no.sql`

## Regenerer statiske filer

```bash
python3 skript/import_wordpress.py
```

## Lokal test

```bash
python3 -m http.server 8000
```

Opne `http://localhost:8000/`.
'''
    (ROOT / "README.md").write_text(txt, encoding="utf-8")


def copy_assets() -> None:
    src = ROOT / "migration/wordpress/utvalde/wp-content/uploads/2026/01/tittelbilete.png"
    dst = ROOT / "assets/img/tittelbilete.png"
    if src.exists():
        dst.write_bytes(src.read_bytes())


def main() -> None:
    ensure_dirs()

    title, note_html, songs, custom_css = load_data()

    write_css(custom_css)
    write_js()

    (ROOT / "index.html").write_text(render_index(title, note_html, songs), encoding="utf-8")

    search_index = []
    for s in songs:
        song_dir = ROOT / "song" / s.slug
        song_dir.mkdir(parents=True, exist_ok=True)
        (song_dir / "index.html").write_text(render_song_page(s), encoding="utf-8")
        search_index.append({
            "title": s.title,
            "link": f"song/{s.slug}/",
            "text": s.plain_text,
        })

    (ROOT / "data/sok-index.json").write_text(
        json.dumps(search_index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    write_readme(len(songs))
    copy_assets()

    print(f"Generated {len(songs)} songs.")


if __name__ == "__main__":
    main()
