# ListenLab — Interactive Podcast Listening & Vocabulary Platform

A web app for Technical English listening practice. Play a podcast, follow the
transcript as it scrolls with the audio, and click any highlighted vocabulary
word to see its Persian/English meaning, part of speech, notes, and examples.

The repository already includes three *Reply All* episodes (audio, transcript
and vocabulary list) in the `datasets/` folder, so the app works right after
setup.

---

## Tech stack

| Part | Technology |
|---|---|
| Backend | Python, FastAPI, SQLite |
| Frontend | React, TypeScript, Vite, Tailwind CSS |

---

## Requirements

Install these first:

* **Python 3.11+** — https://www.python.org/downloads/ (tick "Add Python to PATH")
* **Node.js 20+** (includes npm) — https://nodejs.org/

No database server is needed; SQLite is created automatically.

---

## Installation (once)

Open a terminal in the project folder (PowerShell or CMD on Windows, any
terminal on Linux/macOS).

**Windows (PowerShell or CMD)**

```
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt

cd frontend
npm install
npm run build
cd ..
```

(In PowerShell, if activation is blocked, run
`Set-ExecutionPolicy -Scope Process Bypass` first.)

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd frontend
npm install
npm run build
cd ..
```

> On Ubuntu/Debian you may first need: `sudo apt install python3-venv`

---

## Run the app

The backend serves the built frontend, so a single server is enough.
Run it from the `backend` folder (with the virtual environment activated):

**Windows**

```
cd backend
python -m uvicorn app.main:app --port 8000
```

**Linux / macOS**

```bash
cd backend
python3 -m uvicorn app.main:app --port 8000
```

Then open **http://127.0.0.1:8000** in your browser.
The three episodes are imported automatically the first time the server starts.
Stop the app with `Ctrl+C`.

> If you change the frontend code, run `npm run build` again (inside
> `frontend`) and refresh the page.

---

## Using the player

* **Space** play/pause · **← / →** seek 5 s · **↑ / ↓** volume
* The transcript scrolls automatically and keeps the current line at the top
  (scroll manually to look around; auto-scroll resumes after a few seconds)
* Click a transcript line to jump to it
* Hover or click a dotted-underlined word to see its meaning

---

## Troubleshooting

* **Port already in use** — close the other terminal still running the app (or use `--port 8001`).
* **Page looks outdated or shows a blank page** — run `npm run build` inside `frontend`, then refresh with `Ctrl+F5`.
* **`python` / `npm` not found** — reinstall and make sure it is added to PATH, then reopen the terminal.
* **Reset the data** — stop the app, delete `backend/data/app.db`, and start it again.
