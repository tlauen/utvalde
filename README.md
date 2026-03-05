# utvalde

Statisk versjon av den tidlegare WordPress-sida for utvalde songar (`/utvalde`).

## Kva nettsida er

`utvalde` inneheld framside med songoversikt og eigne songsider, migrert frå WordPress til statisk HTML.

## Kva som er migrert

- Framside med innhaldsliste per songtype
- Språkfilter
- Live-søk i tittel + tekst
- Mørk modus
- Songsider med metadata + knappar (Skriv ut / Apple Music / Spotify / YouTube)
- 83 publiserte songar frå WordPress-eksporten

## Teknologi

- Statisk HTML/CSS/JavaScript
- Generering frå eksport via Python-skript
- Ingen runtime-backend

## Viktige mapper/filer

- `index.html`: framside
- `song/<slug>/index.html`: songsider
- `data/sok-index.json`: søkeindeks
- `stilar/hovud.css`: stilark
- `skript/app.js`: frontend-logikk
- `skript/import_wordpress.py`: migrerings-/generator-skript
- `tiptap-editor.html`: editor for nye songar
- `assets/`: statiske ressursar

## Regenerer statiske filer

```bash
python3 skript/import_wordpress.py
```

## Lokal test

```bash
python3 -m http.server 8000
```

Opne `http://localhost:8000/`.

## Tiptap-editor for nye songar

Opne `tiptap-editor.html` for å lage nytt innhald.

Editoren lagar fire output-felt:

1. Songside (`song/<slug>/index.html`)
2. Framside-linje (`<li ...>`) i rett songtype-seksjon i `index.html`
3. Søkeobjekt til `data/sok-index.json`
4. Metadata-referanse

## Migreringsdata

Rådata frå WordPress ligg i `migration/` lokalt, men mappa er ignorert i git.

## Lisens

Sjå [LICENSE](LICENSE).
