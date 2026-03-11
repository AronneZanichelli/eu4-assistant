# Aronne Zanichelli - Static Bilingual Portfolio (EN/IT)

Professional static portfolio/CV site, optimized for technical applications (junior developer, game dev, digital creative), with English default and Italian toggle.

## Project structure

```text
.
├── index.html
├── style.css
├── script.js
├── README.md
└── assets/
    ├── profile.jpg
    ├── cv_en.pdf
    └── cv_it.pdf
```

## Local test (2-3 steps)

1. Run a local static server:
   ```bash
   python3 -m http.server 8080
   ```
2. Open `http://localhost:8080`.
3. Verify language toggle (EN|IT), theme toggle, form validation, and CV download buttons.

## Publish

### GitHub Pages
1. Push repo to GitHub.
2. Go to **Settings → Pages** and set source to your branch root.
3. Save and open generated URL.

### Netlify
1. Connect the repository in Netlify.
2. Build command: none. Publish directory: `/`.
3. Deploy site and optionally enable Netlify Forms.

## Where to edit content

- Bio and all text translations: `script.js` inside `translations.en.about.bio` and `translations.it.about.bio`.
- Education timeline entries: `index.html` timeline section + labels in `script.js` under `timeline`.
- Portfolio cards and in-progress project description: `script.js` under `portfolio`.

## Contact form integration snippets

### Formspree
```html
<form action="https://formspree.io/f/your-form-id" method="POST">
  <input type="text" name="name" required />
  <input type="email" name="email" required />
  <textarea name="message" required></textarea>
  <button type="submit">Send</button>
</form>
```

### Netlify Forms
```html
<form name="contact" method="POST" data-netlify="true">
  <input type="hidden" name="form-name" value="contact" />
  <input type="text" name="name" required />
  <input type="email" name="email" required />
  <textarea name="message" required></textarea>
  <button type="submit">Send</button>
</form>
```

## CV PDF generation

Two methods are already supported:

1. Direct files in `assets/cv_en.pdf` and `assets/cv_it.pdf` (download buttons are linked).
2. In-browser print mode via `Print / Save as PDF` button (`window.print()` + print CSS in `style.css`).

## Performance notes

- Replace `assets/profile.jpg` with optimized image (`.webp` recommended under 250 KB).
- Keep PDFs lightweight (< 1 MB each).
- Use compressed media for portfolio screenshots/videos.

## EU4 Assistant + Bot design

- Initial design document: `EU4_ASSISTANT_BOT_DESIGN.md`.


## EU4 Assistant + Bot — stato progetto

Vedi `EU4_ASSISTANT_BOT_DESIGN.md` per la progettazione completa v1.0.

| Milestone | Stato |
|---|---|
| M1 — Foundation (config, models, telemetry, parser PoC, CLI) | ✅ Completato |
| M2 — Decision engine + risk alerts + simulated executor | ✅ Completato |
| M3 — ClausewitzTextParser completo + SaveUnzipper + mod autosave | ⏳ In corso |
| M4 — FileWatcher + StateExtractor + GameSnapshot v2 + DLC compat | 🔜 Pianificato |
| M5 — UI PyQt6 + PauseController + hotkey | 🔜 Pianificato |
| M6 — Military logic reale | 🔜 Pianificato |
| M7 — Colonial + Economy logic reale | 🔜 Pianificato |
| M8 — ActionExecutor reale + full-bot UI | 🔜 Pianificato |
| M9 — QA / stabilità / crash hardening | 🔜 Pianificato |
| M10 — Packaging + changelog + docs | 🔜 Pianificato |

Run tests:

```bash
python -m pytest -q
```
