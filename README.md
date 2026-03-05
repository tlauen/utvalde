# utvalde

Statisk versjon av den tidlegare WordPress-sida for utvalde songar.

## Kva som er migrert

- Framside med innhaldsliste per songtype
- Språkfilter
- Live-søk i tittel + tekst
- Mørk modus
- Songsider med metadata + knappar (Skriv ut / Apple Music / Spotify / YouTube)
- 83 publiserte songar frå WordPress-eksporten

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
