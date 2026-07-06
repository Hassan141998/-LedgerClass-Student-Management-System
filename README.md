# LedgerClass — Student Management System

A Flask + Bootstrap 5 student management system with role-based access control
(Admin / Staff), built to run identically on a local machine and on Vercel
serverless, backed by Neon Postgres.

## Project structure

```
your-project-folder/
├── api/
│   └── index.py          # Flask app, models, routes (Vercel entry point)
├── templates/
│   ├── layout.html
│   ├── dashboard.html
│   ├── students.html
│   ├── student_form.html
│   ├── students_report.html
│   └── login.html
├── static/
│   ├── css/style.css
│   └── js/main.js
├── main.py                # Local dev entry point — run this in PyCharm
├── vercel.json
├── requirements.txt
├── .env.example
└── .gitignore
```

## Run locally in PyCharm

1. **Open the project folder** in PyCharm (`File -> Open` -> select `your-project-folder`).

2. **Create a virtual environment** (PyCharm usually prompts you automatically):
   - `File -> Settings -> Project -> Python Interpreter -> Add Interpreter -> Add Local Interpreter -> Virtualenv`
   - Or from the terminal inside PyCharm:
     ```bash
     python -m venv .venv
     # Windows
     .venv\Scripts\activate
     # macOS/Linux
     source .venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Set up your `.env` file** — copy `.env.example` to `.env` and fill
   in a Neon `DATABASE_URL` if you want to develop against Postgres instead of
   the default local SQLite file:
   ```bash
   cp .env.example .env
   ```
   If you skip this step, the app automatically uses a local SQLite database
   (`local.db`) — no setup required.

5. **Run `main.py`**:
   - Right-click `main.py` in the Project pane -> **Run 'main'**
   - Or from the terminal:
     ```bash
     python main.py
     ```
   - The app starts at **http://127.0.0.1:5000**

6. **Log in** with the default seeded admin account:
   - Username: `admin`
   - Password: `admin123`

   The database tables and this admin user are created automatically the
   first time the app starts (via `init_db()` in `api/index.py`), so there's
   no manual migration step.

> To configure the run in PyCharm explicitly: `Run -> Edit Configurations -> +
> -> Python`, set **Script path** to `main.py`, **Working directory** to the
> project root, then Run/Debug as usual.

## Deploying to Vercel with Neon Postgres

1. **Create a Neon database** at [neon.tech](https://neon.tech) and copy the
   connection string from the dashboard (Connection Details).

2. **Push this project to a GitHub repo**, then import it in Vercel
   (`Add New -> Project -> Import Git Repository`).

3. **Set environment variables** in the Vercel project settings:
   - `DATABASE_URL` → your Neon connection string (either `postgres://` or
     `postgresql://` prefix works — the app normalizes it automatically)
   - `SECRET_KEY` → a long random string

4. **Deploy.** Vercel reads `vercel.json`, which routes all requests to
   `api/index.py` via the `@vercel/python` runtime and serves `/static/*`
   directly. Tables and the default admin user are created automatically on
   first request via the `init_db()` call.

5. **Log in** with `admin` / `admin123` and change the password by adding a
   new admin user (or update `password_hash` directly in Neon's SQL editor)
   — there's no in-app "change password" flow in this build, by design of
   the spec above; extend `api/index.py` if you'd like one.

## Features implemented

- **Auth & RBAC**: session-based login/logout; `Admin` role required for
  add/edit/delete; both roles can view dashboard, students, and reports.
- **Dashboard**: total student count, breakdown by program (with bar chart),
  5 most recently added students.
- **Students directory**: search by name/roll number, filter by program and
  semester, server-side pagination (10 per page).
- **Add / Edit student**: unified form template, server-side validation,
  graceful handling of duplicate roll number (unique constraint) errors.
- **Delete student**: Bootstrap modal confirmation before submitting.
- **Print report**: `/students/report` renders a bare, print-optimized page
  (respects current search/filter) and calls `window.print()` on load.
- **Client-side JS**: required-field and phone-format checks before submit,
  delete-confirmation modal wiring, responsive sidebar toggle.

## Notes on the default admin account

For security, change the seeded password before using this in production.
The simplest way locally: open a Python shell in the project with the venv
active and run:

```python
from api.index import app, db, User
with app.app_context():
    u = User.query.filter_by(username="admin").first()
    u.set_password("your-new-password")
    db.session.commit()
```
