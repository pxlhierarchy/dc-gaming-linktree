# DC Gaming Linktree

A small Flask link-in-bio site: link list with click tracking, an admin
dashboard, and a "Set Up Emulator" guide page.

---

## Local development

```bash
python -m venv venv
venv/Scripts/python.exe -m pip install -r requirements.txt   # macOS/Linux: venv/bin/python
venv/Scripts/python.exe -m flask run --debug --host 0.0.0.0 --port 5000
```

Open http://localhost:5000. Admin is at `/admin/login`.

Copy `.env.example` to `.env` and set at least:

```
SECRET_KEY=<a long random string>
ADMIN_PASSWORD=<your password>
```

Locally the app uses SQLite (`instance/linktree.db`) and creates the tables and
an `admin` user on first run. Delete that file to start over.

Links are managed by `set_links.py` — edit the `LINKS` list and re-run it:

```bash
venv/Scripts/python.exe set_links.py
```

---

## Deploying to Vercel

### 1. Push to GitHub

```bash
git add -A
git commit -m "Prepare for Vercel"
git push -u origin main
```

### 2. Add a Postgres database

**This step is not optional.** Serverless filesystems are read-only and thrown
away between invocations, so SQLite cannot be used on Vercel — the app refuses
to start without `DATABASE_URL` rather than silently losing your data.

In the Vercel dashboard: **Storage → Create Database → Neon (Postgres)**, then
connect it to the project. Vercel injects `DATABASE_URL` automatically.

### 3. Import the repo

Vercel dashboard → **Add New → Project** → pick the repo. It reads
`vercel.json`; no framework preset or build command is needed.

### 4. Set environment variables

**Settings → Environment Variables**, for all environments:

| Name | Value |
| --- | --- |
| `SECRET_KEY` | A long random string. Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD` | The admin password to seed |

`SECRET_KEY` must be set and must stay stable. Each request can be served by a
different instance, so a rotating key would sign every session differently and
logins would appear to work and then randomly drop. The app refuses to boot
without it.

### 5. Create the schema, once

The app does **not** create tables on serverless — `db.create_all()` would run
reflection queries on every cold start. Run it once from your machine, pointed
at the production database:

```bash
# Copy DATABASE_URL from the Vercel dashboard (Storage -> your database)
DATABASE_URL="postgresql://..." ADMIN_PASSWORD="..." \
  venv/Scripts/python.exe -m flask --app app init-db
```

Then load your links into it:

```bash
DATABASE_URL="postgresql://..." venv/Scripts/python.exe set_links.py
```

`init-db` only sets a password when it *creates* the admin user. To rotate it
on a database that already exists:

```bash
DATABASE_URL="postgresql://..." ADMIN_PASSWORD="a-real-password"   venv/Scripts/python.exe -m flask --app app set-admin-password
```

### 6. Deploy

Push to `main`, or hit **Deploy**. Check `/healthz` returns `{"status":"ok"}`,
then log in at `/admin/login`.

---

## How it fits together on Vercel

- `api/index.py` re-exports the Flask app; Vercel's Python runtime picks up the
  module-level `app` as a WSGI callable.
- `vercel.json` rewrites every path to that function and bundles `templates/`
  and `static/` via `includeFiles`, plus cache and security headers.
- `.vercelignore` keeps the venv, the local SQLite file, `.env` and the local
  tooling scripts out of the deployment.

## Project layout

```
app.py                  Flask app: models, routes, bootstrap
api/index.py            Vercel entrypoint
set_links.py            Source of truth for the link list
build_hero.py           Regenerates the og:image from source art
templates/              base + admin_base shells, pages
static/                 styles.css, admin.css, admin.js, images
vercel.json             Vercel routing, bundling, headers
HANDOFF.md              Working doc: decisions, fixes, open items
```

## Admin

`/admin/login`, username `admin`, password from `ADMIN_PASSWORD`. The dashboard
manages links and site preferences (title, description, colours).
