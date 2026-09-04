# DC Gaming Linktree — Handoff / Working Doc

**Canonical working document.** Update this whenever a decision is made or work
lands, so we never re-litigate settled choices.

- **Repo:** `pxlhierarchy/dc-gaming-linktree`
- **Local path:** `C:\Users\chungus\Documents\dcgaminglinks`
- **Working branch:** `working-changes` (branched from `main` @ `6232606`)
- **Last updated:** 2026-09-03 (donate link added; Vercel-ready, committed)

---

## 1. How to run it

```bash
# from the repo root
venv/Scripts/python.exe -m flask run --debug --host 0.0.0.0 --port 5000
```

| Target | URL |
| --- | --- |
| Desktop | http://localhost:5000 |
| Phone (same Wi-Fi) | http://10.0.0.32:5000 |
| Admin | http://localhost:5000/admin/login |

Auto-reload is on — edit a template, CSS, or `app.py` and refresh.

**Admin credentials (local only):** `admin` / `admin`
Set `ADMIN_PASSWORD` and `SECRET_KEY` in `.env` before any deploy. See `.env.example`.

**Environment:** Python 3.14.6. The original pins (`Pillow==10.0.0`,
`psycopg2-binary==2.9.9`) have no 3.14 wheels, so `requirements.txt` was
loosened and `psycopg2-binary` is now conditional. Pillow was dropped —
nothing imported it.

**Database:** local SQLite at `instance/linktree.db` (gitignored). Delete the
file and restart to reset from scratch.

```bash
venv/Scripts/python.exe seed_demo.py --reset   # reseed demo gear
```

---

## 2. Bugs found and fixed (2026-09-03)

Verified against a running server — every item below was reproduced before the
fix and re-tested after.

### Blockers — the app would not start

| # | Problem | Fix |
| --- | --- | --- |
| 1 | `url_for('gear', _external=True)` ran at import time in `init_db()`. `url_for` needs a request context → `RuntimeError` on startup. | Seed literal paths instead. |
| 2 | The `except` handling that error called `traceback.format_exc()`, but `traceback` was never imported → `NameError` masked the real error and killed the process. | `import traceback` at module level. |
| 3 | `app.run()` sat at line 529 with `/admin/preferences` and the `inject_preferences` context processor defined **below** it. Run directly, `app.run()` blocks and those never register. | Moved `app.run()` to the bottom; all routes register first. |

### Admin dashboard crashed on every load

| # | Problem | Fix |
| --- | --- | --- |
| 4 | `admin.html` called `url_for('logout')` — the endpoint is `admin_logout`. Jinja raised `BuildError`, a broad `try/except` swallowed it, and you got bounced home with a generic "Error loading admin dashboard". | Corrected the endpoint; removed the exception-swallowing wrapper so real errors surface. |
| 5 | "Manage Gear" linked to the **public** `/gear` page, not `/admin/gear`. | Proper admin nav with both destinations. |

### Security

| # | Problem | Fix |
| --- | --- | --- |
| 6 | `/debug/db` was **public with no auth**. It leaked table names and hash prefixes, and if no admin existed it *created one with the password `admin123`* — anyone hitting the URL could seize the site. | Route deleted. |
| 7 | The login handler printed password hashes to logs on every failed attempt. | Removed; logs the username only. |
| 8 | `SECRET_KEY` fell back to the literal `'your-secret-key-here'`. A known key means forgeable session cookies. | Falls back to `os.urandom(32)`. |

### Dead / broken code

| # | Problem | Fix |
| --- | --- | --- |
| 9 | `init_db.py` and `add_initial_links.py` both did `from models import User` — there is no `models.py`. Neither could ever run. | Both deleted, replaced by `seed_demo.py`. |
| 10 | `base.html` loaded `/static/script.js`, which does not exist → 404 on every admin page. | Removed; real shared JS now lives in `static/admin.js`. |
| 11 | Root-level `index.html`, `gear.html`, `styles.css` were stale duplicates of the real files in `templates/` and `static/`. | Deleted. |
| 12 | `templates/login.html` was orphaned (nothing rendered it). | Deleted. |

---

## 3. Mobile & desktop work

**The gear page was the worst offender.** `.gear-item` was a fixed flex row
with a 150px image, leaving ~120px for text on a 360px phone, and there was no
breakpoint for it at all. It now stacks vertically below 600px and goes
side-by-side above.

Also done:

- Fluid `clamp()` typography throughout, replacing a single 600px breakpoint.
- `100dvh` so mobile browser chrome hiding/showing doesn't cause a jump.
- `env(safe-area-inset-*)` padding for the iPhone notch and home indicator.
- 48px minimum touch targets on every link, button and input.
- 16px form inputs — anything smaller makes iOS Safari zoom the page on focus.
- Hover effects gated behind `@media (hover: hover) and (pointer: fine)`, so
  they don't stick after a tap on touch devices.
- `overflow-wrap: anywhere` on headings — Press Start 2P has no hyphenation and
  a long single word otherwise blows out the layout at 320px.
- Admin tables reflowed from a 4-column horizontal scroll into stacked cards
  below 768px (`.table-stack`, labels driven by `data-label`).
- Keyboard focus rings and a skip link — the site previously had neither.
- `prefers-reduced-motion`, `prefers-contrast` and print styles.

**Breakpoints:** base (mobile-first) → 600px → 900px. Keep to these three.

---

## 3b. Visual identity (2026-09-03)

### Typography — pixel fonts are gone

Press Start 2P and VT323 carried the era but were genuinely hard to read at
any length. Replaced with a pair that keeps the 90s feel *and* is legible:

| Role | Face | Why |
| --- | --- | --- |
| Display | **Titan One** | Chunky, rounded, bubbly — 90s cartridge-label energy, and readable at a glance |
| Body | **Rubik** | Geometric with slightly rounded corners; holds up at small sizes on a phone |

Both are on Google Fonts and load in `base.html` and `admin_base.html`.
Body size went 18px → 17px (Rubik has a larger x-height than VT323, so it
reads bigger at a smaller number). Display sizes went **up** substantially —
Press Start 2P had to be tiny to fit; Titan One doesn't.

### Palette — DKC jungle, not generic dark mode

| Token | Value | Role |
| --- | --- | --- |
| `--bg` | `#0F1A12` | Deep night-jungle green. Green-biased, not flat grey. |
| `--surface` | `#18271A` | Cards |
| `--border` | `#35492E` | 3px borders |
| `--accent` | `#F5B921` | **Banana yellow** — headings, icons, buttons |
| `--accent-ink` | `#2A1D02` | Dark text that sits *on* yellow |
| `--hot` | `#D93B2B` | DK-tie red, used sparingly (warnings only) |
| `--wood` | `#8A5325` | Barrel wood, used on the ROM callout shadow |
| `--vine` | `#6FA83C` | Prices |
| `--text` | `#F5F1E3` | Warm off-white, not clinical |

**Yellow replaced red as the primary accent** because it has far better
contrast on dark green — a legibility decision as much as a thematic one. Red
is now reserved for one thing at a time.

These values are stored in the `Preferences` row *and* as model defaults, so a
reset doesn't reintroduce the old red.

### 90s devices

- **Hard blurless offset shadows** (`4px 4px 0`) — the era's house style, and
  it reads as deliberate rather than a soft modern drop shadow.
- **Press physics:** cards lift up-left on hover (shadow grows) and sink
  down-right on `:active` (shadow shrinks).
- **3px borders** throughout instead of 1–2px.
- **Hard text shadow** on the site title, the way box art set display type off
  its ground.
- A faint vine-green radial wash at the top of `body` — depth behind the
  cut-out characters at no image cost.

### Artwork

| File | Placement | Notes |
| --- | --- | --- |
| `static/images/kongs.png` | source only | Cut-out Kong art with real alpha (corners are alpha 0). Not referenced by any template — it is an input to `build_hero.py`. |
| `static/images/logo.png` | source only | The original red DC monogram. Already transparent; kept untouched. |
| `static/images/logo-gold.png` | Gear header, admin brand, favicon | Generated. Logo recoloured to the accent. |
| `static/images/hero.png` | `og:image` only | Generated. Kong art with the gold logo composited in. **Rejected as the home hero** — kept because it makes a good social share card. |
| `static/images/snes-dkc.jpg` | New Runner Setup hero | SNES + all three DKC boxes + DK barrel mug. Full alt text. |

### `build_hero.py` — regenerates the hero

```bash
venv/Scripts/python.exe build_hero.py
```

Re-run after replacing either source image. What it does, and why:

- **Recolours the logo by interpolating black → gold on the red channel.** The
  source is a flat red fill (255,49,49) with a flat black outline, so the red
  channel alone says how far a pixel sits between outline and fill. Lerping by
  `r/255` recolours the fill, keeps the outline black, and leaves every
  antialiased edge smooth — no halo, no keying artefacts.
- **Finds the placement automatically** rather than hardcoding coordinates: it
  searches the alpha channel for the largest fully-transparent rectangle in the
  upper centre. That gap is `x 140-345, y 0-220` — dead centre between the two
  ropes and above the DK/Diddy high-five. Replace the art and it re-solves.
- **Adds a hard offset shadow** (the logo's own silhouette at 45% black, offset
  5px) to match the site's blurless-shadow language.
- **Quantises the colour channels only, then restores the original 8-bit
  alpha.** Quantising RGBA directly folds alpha into the palette and leaves a
  visible grey halo of banding around the characters' soft edges — this was
  tried, looked bad, and is the reason the code splits the channels.

Hero is ~223KB. Full-RGBA was 239KB and a naive RGBA quantise got it to 57KB
but with the halo, so the size win was rejected in favour of clean edges.

Sources were `unnamed.png` and `images.jfif` in Downloads. The `.jfif` is a
plain JPEG — renamed to `.jpg` so browsers and tooling handle it predictably.

### Background — current

Two earlier attempts were rejected: the **composited hero** (logo set into the
Kong art) and then the **faded Kong backdrop**. Current answer is a full-bleed
DKC wallpaper.

**Two images, switched on width:**

| Viewport | Image | Why |
| --- | --- | --- |
| ≥ 600px | `wallpaper.jpg` (2016×1134, 131KB) | DKC sunset scene. 16:9. |
| < 600px | `background-mobile.jpg` (668×459, 48KB) | DK / Diddy / Squawks. Near-square, so it survives a portrait crop. |

The 16:9 wallpaper looked wrong on phones: under `cover` on a tall screen it
crops to a thin vertical slice and the scene falls apart. Keyed on **width, not
a device check**, so a phone turned landscape goes back to the 16:9 wallpaper —
which is the shape that suits it.
- Painted by `.page-art`, an empty `aria-hidden` div, **`position: fixed;
  inset: 0`**. Deliberately *not* `background-attachment: fixed` on the body —
  iOS Safari handles that badly (jitter, silent fallback to scrolling); a fixed
  element is solid everywhere.
- The scrim is the **first background layer on the same element**, so there is
  no second node to keep in sync.

```css
--scrim-top: rgba(12, 20, 14, 0.72);      /* desktop */
--scrim-bottom: rgba(12, 20, 14, 0.88);
--scrim-top-sm: rgba(12, 20, 14, 0.82);   /* mobile */
--scrim-bottom-sm: rgba(12, 20, 14, 0.90);
```

**These are the dials.** Raise the alpha to push the art back, lower it to let
more through.

**The mobile image needs a heavier scrim, and this was measured, not guessed.**
It is far brighter — mean `rgb(160,127,33)` against the wallpaper's
`rgb(91,61,33)`, with pure white highlights. At the desktop scrim the gold
accent lands at **4.25:1 and fails AA**, so mobile runs at 0.82/0.90.

Contrast at each worst case (text and gold over the brightest pixel, under the
*lighter* top scrim):

| | `--text` `#F5F1E3` | `--accent` `#F5B921` |
| --- | --- | --- |
| Desktop @ 0.72 | 8.22:1 pass | 5.24:1 pass |
| Mobile @ 0.82 | 9.66:1 pass | 6.16:1 pass |
| *Mobile @ 0.72* | *6.67:1 pass* | *4.25:1 **fail*** |

**Known limitation:** `background-mobile.jpg` is only 668×459. On a tall phone
`cover` upscales it roughly 1.8× and crops to the middle ~32% (DK's face, which
frames acceptably). The heavy scrim hides most of the softness, but a
larger source would be better if one turns up.

Cards keep an opaque `--surface`, so the wallpaper shows through in the header
area and the gutters but never behind body copy.

`kongs.png` and `hero.png` are now unused by any page; `hero.png` is still the
`og:image` social card. The site description line stays removed from the home
page.

### Type scale reduced (2026-09-03)

Everything was running large. Roughly a 10-15% reduction across the board,
keeping the same proportions:

| | Before | After |
| --- | --- | --- |
| Body | 17px (18px ≥900px) | 16px (17px ≥900px) |
| `.link-label` | `clamp(1rem, 3.6vw, 1.2rem)` | `clamp(0.88rem, 3vw, 1rem)` |
| `.link-icon` | 1.2rem | 1.02rem |
| `.profile-name` | `clamp(1.9rem, 8vw, 3rem)` | `clamp(1.5rem, 6vw, 2.25rem)` |
| `.profile-mark` | `clamp(140px, 40vw, 210px)` | `clamp(104px, 28vw, 150px)` |
| Card gap | 0.75rem | 0.6rem |

Gear, guide steps and buttons came down in step so the scale stays consistent
across pages. **`min-height: var(--tap)` (48px) on links and buttons was left
alone** — the text got smaller, the touch targets did not.

The title's text shadow changed from a `--bg`-coloured offset to black, since
it now sits over artwork rather than a flat ground.

---

## 4. Architecture decisions (settled — don't revisit without cause)

- **Two template shells.** `base.html` = public pages (no Bootstrap, own CSS).
  `admin_base.html` = admin (Bootstrap 5.3). Previously `index.html` and
  `gear.html` were standalone documents duplicating the whole `<head>`.
- **Bootstrap 5.3 dark mode via CSS variables** (`--bs-body-bg` etc.) rather
  than fighting each component with overrides.
- **`position` column** on `Link` and `Gear` for stable manual ordering,
  replacing "newest first". `/admin/links/reorder` exists and works; the
  drag-and-drop UI is not built yet.
- **Preferences are global**, read from the first user, so public visitors get
  the owner's theme. The old context processor only ran for logged-in users, so
  preferences never affected the public site at all.
- **Toasts, not `alert()`.** `static/admin.js` exposes `Admin.toast`,
  `Admin.postJSON`, `Admin.busy`. `postJSON` reads the body as text first, so a
  500 returning an HTML error page gives a real message instead of an opaque
  JSON parse error.
- **Error pages:** shared `templates/error.html` for 404 and 500.

---

## 5. Current state

### Routes

| Route | Auth | Purpose |
| --- | --- | --- |
| `/` | public | Link list |
| `/setup-emulator` | public | How to play DKC on a PC (emulator + ROM) |
| `/track/<id>` | public | Count link click → redirect |
| `/api/links` | public | JSON link list |
| `/healthz` | public | Health check |
| `/admin/login`, `/admin/logout` | — | Auth |
| `/admin` | required | Links + Preferences tabs |
| `/admin/links/add\|edit\|delete\|reorder` | required | Link CRUD |
| `/admin/preferences` | required | GET / POST site theme |

### Data

**Links — live, 7 total** (Donate added 2026-09-03) (order = position on the page):

| # | Title | URL |
| --- | --- | --- |
| 1 | Set Up Emulator | `/setup-emulator` |
| 2 | YouTube | https://youtube.com/@dcgaming6898 |
| 3 | Twitch | https://twitch.tv/dcgaming708 |
| 4 | X / Twitter | https://x.com/isaac708 |
| 5 | speedrun.com | https://www.speedrun.com/users/deviantcode |
| 6 | DKC Speedrunning Wiki | https://dkcspeedruns.com/Main_Page |
| 7 | Donate | https://www.paypal.com/donate/?hosted_button_id=42YKZUXLBFFQ2 |

Discord and the old placeholder Twitter link were removed.

Links are managed by `set_links.py` — edit the `LINKS` list and re-run it. It
adds, updates, reorders and removes to match, so that file is the source of
truth rather than hand-editing the database.

```bash
venv/Scripts/python.exe set_links.py
```

Internal links (`/`-prefixed) render with the `--featured` highlight so they
read as destinations on this site rather than outbound social links.

Gear was removed on 2026-09-03 — see section 8.

## 6. Open items / next up

**In progress**
- [ ] Merge `working-changes` and push, then import the repo on Vercel.
- [ ] Attach Postgres, set `SECRET_KEY` + `ADMIN_PASSWORD`, run `init-db`.

**Decided, not built**
- [ ] Drag-and-drop link reordering (backend endpoint already exists).
- [ ] CSRF protection. Flask-WTF was in the original requirements but never
      wired up; admin POSTs are currently unprotected.

**Ideas — not committed**
- [ ] Click-analytics view in admin (data is already collected).
- [ ] Scheduled/expiring links for drops and events.
- [ ] The `.banner` CSS component exists but no template uses it — could become
      an announcement bar driven by Preferences.

**Removed, pending your input**
- The three social icons at the bottom of the home page were
  `<a href="#">` (gamepad / trophy / dice) pointing nowhere. Dropped for now —
  supply real destinations to bring them back.
- The gear feature. See section 8; recoverable from git history.

---

## 7. Set Up Emulator page (`/setup-emulator`)

A first-party page at `templates/setup_emulator.html`, linked first on the home
page. Six numbered steps — the numbering is real sequence, not decoration.

**Renamed and reframed 2026-09-03.** Was "New Runner Setup" at
`/getting-started`. The page is not about turning someone into a speedrunner —
it is about showing anyone how to play the game. Speedrunning is now the
optional next step at the end, and the leaderboard rules are explicitly marked
"only if you later want to submit a run" rather than presented as the point.

1. What you need (emulator + ROM)
2. Install Snes9x — links https://www.snes9x.com/
3. Set up your controls
4. What a ROM file is
5. Getting the right DKC ROM
6. Where to go next

**Editorial decisions made here:**

- **The target version is called out in its own highlighted block:**
  *Donkey Kong Country (USA), Revision 1.0* — the original unpatched release.
  Later revisions patched out tricks runs depend on, so the version matters.
- **No ROM is linked or named to a host.** The page explains what a ROM is and
  that searching the exact release name plus `.sfc` is how people find them.
  **Cartridge-dumping and the legality aside were cut on request** (2026-09-03)
  — readers just want to download a ROM, and the detour got in the way.
- **No checksum value is written down.** A wrong hash is worse than none, so the
  page tells the reader to get the correct CRC32/SHA-1 from the DKC wiki and
  verify their file against it. `File → ROM Information` in Snes9x is noted as
  the in-app check.
- **Snes9x instructions stay at menu level** (`Options → Input Configuration`,
  `File → Open ROM`) rather than asserting specific hotkeys, which vary between
  builds.
- **Leaderboard rules are deferred to the board**, not asserted — boards differ
  on accepted emulator versions and some categories don't take emulator runs.
  Save states are flagged as practice-only.

Styles live at the end of `static/styles.css` under "Guide pages".

---

## 8. Gear feature — REMOVED (2026-09-03)

Removed on request. Deleted: the `Gear` model, `/gear`, `/gear/<id>/click`,
every `/admin/gear*` route including the Amazon `fetch` endpoint, the
product-link helpers (ASIN parsing, URL canonicalisation, scraping),
`templates/gear.html`, `templates/admin_gear.html`, `seed_demo.py`, the gear
CSS blocks, the admin import-bar styles, the Gear nav tab, and the six demo
product images.

**All of it is recoverable** — it is in the history at `6232606..fef0e04` on
`working-changes`. Do not rebuild it from scratch if it comes back.

**Watch out:** `setup_emulator()` was defined *between* the two gear routes, so
the first removal pass took it out too and `/setup-emulator` 404'd. It has been
restored. Any similar bulk removal should re-check the route list afterwards.

The old `gear` table may still exist in a pre-existing local SQLite file. It is
unused and harmless; delete `instance/linktree.db` for a clean slate.

---

## 9. Vercel deployment

Full step-by-step is in `README.md`. The decisions behind it:

| File | Role |
| --- | --- |
| `api/index.py` | Entrypoint. Re-exports the Flask app; Vercel's Python runtime picks up a module-level `app` as a WSGI callable. Inserts the repo root on `sys.path`, which is not there by default. |
| `vercel.json` | Rewrites all paths to that function, bundles `templates/` and `static/` via `includeFiles`, sets cache and security headers. |
| `.vercelignore` | Keeps venv, `instance/`, `.env`, `HANDOFF.md` and local tooling out of the bundle. |

**Guards that fail loudly rather than silently misbehaving** (`VERCEL=1` is set
by Vercel in all its environments):

- **No `SECRET_KEY` on serverless → refuses to boot.** Each request may hit a
  different instance; a per-process random key would sign every session
  differently, so logins would appear to work and then randomly drop. That is
  far worse to debug than a startup error.
- **No `DATABASE_URL` on serverless → refuses to boot.** The filesystem is
  read-only and discarded between invocations, so SQLite silently loses
  everything.

Local development is unaffected: it still falls back to a random key and
SQLite, and self-bootstraps on first run.

**Schema creation is manual on serverless.** `db.create_all()` at import would
run reflection queries on every cold start. Run once, from your machine,
pointed at the production database:

```bash
DATABASE_URL="postgresql://..." ADMIN_PASSWORD="..."   venv/Scripts/python.exe -m flask --app app init-db
DATABASE_URL="postgresql://..." venv/Scripts/python.exe set_links.py
```

Other production settings: `pool_pre_ping` and `pool_recycle: 280` so a
serverless pooler dropping a connection does not surface as a 500.

**`psycopg2-binary` is deliberately unpinned from a Python-version marker.** It
was `python_version < "3.14"` (so it would install on Vercel's 3.12 but skip on
this machine's 3.14). 2.9.12 now ships 3.14 wheels, so the marker is gone — it
would have silently dropped the Postgres driver if Vercel's default Python
moved up.

### Bug found during this work

`init_db()` called `db.session.rollback()` in its `except` block from *outside*
the `with app.app_context()` block, so any real failure was replaced by
"Working outside of application context". Same masking pattern as the original
`traceback` bug. The handler now sits inside the context.

---

## 10. Conventions

- Mobile-first CSS; only add breakpoints at 600px and 900px.
- Comments explain **why**, not what.
- Admin fetch calls go through `Admin.postJSON` for consistent error handling.
- Every user-facing string in templates, not hardcoded in Python.
- Nothing is committed or pushed unless explicitly asked. `main` is untouched.
