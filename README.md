# ListenLab — Interactive Podcast Listening & Vocabulary Platform

A web application for university-level technical English listening classes
(designed for Computer Engineering students). Instructors play a podcast, the
transcript follows along line-by-line, and important vocabulary lights up
inside the text — hover or click any highlighted term for Persian/English
meanings, part of speech, notes, and examples.

Built as a real, usable MVP on top of the **three existing podcast datasets**
already present in this repository.

---

## 1. The three source datasets

The repository ships with three complete Reply All episodes
(*Long Distance* story), kept together in the [`datasets/`](datasets/) folder.
They are the primary test & demo content and are
**read in place — never modified or copied**:

| # | Audio | Transcript | Vocabulary | Duration |
|---|-------|------------|------------|----------|
| 102 | `datasets/102-GLT1346255265.mp3` | `datasets/102_ReplyAll_LongDistance_Pt1_Transcript.docx` | `datasets/102_ReplyAll_LongDistance_Pt1_Vocab.xlsx` | ~46:29 |
| 103 | `datasets/103-GLT7017673177.mp3` | `datasets/103_ReplyAll_LongDistance_Pt2_Transcript.pdf` | `datasets/103_ReplyAll_LongDistance_Pt2_Vocab.xlsx` | ~43:26 |
| 164 | `datasets/164 Long Distance The Real Alex Martin.mp3` (actually **OGG** audio) | `datasets/164_ReplyAll_LongDistance_TheRealAlexMartin_Transcript.pdf` | `datasets/164_ReplyAll_LongDistance_TheRealAlexMartin_Vocab.xlsx` | ~29:39 |

### How the files are associated

The audio → transcript → vocabulary mapping is **not guessed from filenames**.
It is declared explicitly in:

```
backend/seed_manifest.json
```

```json
{
  "podcasts": [
    {
      "sourceKey": "reply-all-102-long-distance-pt1",
      "title": "Reply All #102 — Long Distance (Part 1)",
      "audio": "datasets/102-GLT1346255265.mp3",
      "subtitles": "datasets/102_ReplyAll_LongDistance_Pt1_Transcript.docx",
      "vocabulary": "datasets/102_ReplyAll_LongDistance_Pt1_Vocab.xlsx"
    }
  ]
}
```

Paths are relative to the project root (or absolute). The seed script imports
these entries idempotently — every time the server starts, already-imported
podcasts are skipped.

### Transcript formats

The three transcripts are **DOCX/PDF classroom documents** with plain
timestamps (`0:08`, `45:51`) on their own lines and optional `Speaker N`
labels. The backend parser converts them into normal timed subtitle segments.
Standard `.srt` and `.vtt` files are also fully supported for new uploads.

### Vocabulary spreadsheets

All three workbooks currently share the same headers, but the importer **does
not depend on that**:

| Word / Expression | Base Form | Meaning (Persian) | Meaning (English) | POS | Notes | Example |
|---|---|---|---|---|---|---|

Headers are auto-mapped through a synonym table (including Persian header
names), and the import wizard lets the user remap any column before
confirming. Duplicates, empty rows, and rows without a word are detected and
reported.

---

## 2. Architecture

```
TechnicalEnglishBonusApp/
├── datasets/                  ← the 3 semester episodes (source, read-only)
│   ├── *.mp3                  audio (file 164 is OGG audio mislabeled .mp3)
│   ├── *_Transcript.docx/pdf  classroom transcripts with timestamps
│   └── *_Vocab.xlsx           vocabulary workbooks
│
├── backend/                 FastAPI + SQLite (Python)
│   ├── app/
│   │   ├── main.py          app entry, SPA serving, startup seed
│   │   ├── db.py            SQLite schema (portable to PostgreSQL)
│   │   ├── storage.py       file-storage abstraction (originals in place,
│   │   │                    uploads under backend/data/uploads/)
│   │   ├── routers/         /api/podcasts, /api/uploads, /api/files (Range)
│   │   └── services/
│   │       ├── subtitle_parser.py   srt · vtt · docx · pdf · txt → segments
│   │       ├── excel_parser.py      xlsx → entries + mapping + report
│   │       ├── vocab_matcher.py     segments × vocabulary → annotated parts
│   │       ├── audio_meta.py        duration probing (mutagen)
│   │       ├── podcast_service.py   CRUD + serialization
│   │       └── seed.py              manifest-driven import (idempotent)
│   ├── seed_manifest.json   ← explicit audio/subtitle/vocab association
│   ├── tests/               pytest suite incl. real-dataset integration
│   └── data/                app.db + uploads (created at runtime)
│
└── frontend/                React 19 + TypeScript + Vite + Tailwind v4
    └── src/
        ├── pages/           Dashboard · Player · New (wizard) · Edit
        ├── components/      Layout, cards, transcript, vocab popover, UI kit
        ├── hooks/           useAudioEngine (native <audio>), keyboard shortcuts
        ├── api/client.ts    typed fetch wrapper with friendly errors
        └── types.ts         shared API types
```

### Data flow (matching is UI-independent)

```
subtitle file ──► SubtitleParser ──► SubtitleSegment[]
xlsx file     ──► ExcelImporter  ──► VocabularyEntry[]
                      │
        SubtitleSegment[] × VocabularyEntry[]
                      ▼
              VocabMatcher ──► segments with parts[{t, v?}]
                      ▼
                 React UI (highlight → popover)
```

---

## 3. Requirements

* **Python 3.11+**
* **Node.js 20+** and npm
* No database server needed (SQLite file is created automatically)

Python dependencies (`backend/requirements.txt`):
`fastapi`, `uvicorn`, `python-multipart`, `openpyxl`, `pypdf`, `mutagen`,
`pytest`, `httpx`

---

## 4. Setup

```powershell
# 1) Python environment (once)
python -m venv .venv
.\.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt

# 2) Frontend dependencies (once)
cd frontend
npm install
cd ..
```

### Seed the three datasets (optional — also runs automatically on startup)

```powershell
$env:PYTHONPATH = "$PWD\backend"
python -m app.services.seed          # idempotent
python -m app.services.seed --force  # re-import
```

### Run in development (two terminals)

```powershell
# Terminal 1 — API on http://127.0.0.1:8000
$env:PYTHONPATH = "$PWD\backend"
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend on http://localhost:5173 (proxies /api → :8000)
cd frontend
npm run dev
```

Open **http://localhost:5173**

Or use the helper script (starts both):

```powershell
.\scripts\dev.ps1
```

### Run as a single production-ish server

```powershell
cd frontend
npm run build
cd ..
$env:PYTHONPATH = "$PWD\backend"
python -m uvicorn app.main:app --port 8000
```

Open **http://127.0.0.1:8000** (the backend serves the built SPA).

---

## 5. Tests & checks

```powershell
# Backend unit + integration tests (parsers, matcher, Excel, all 3 real datasets, API)
cd backend
python -m pytest

# Frontend typecheck + lint + build
cd frontend
npm run lint
npm run build        # includes tsc -b (typecheck)
```

Or run everything at once from the repo root:

```powershell
.\scripts\test.ps1
```

The integration tests load the three real audio/transcript/vocabulary files
and assert: audio duration readable, transcript parses into valid ordered
segments within the audio, vocabulary parses, and known vocabulary terms are
matched inside the transcript with correct word boundaries.

---

## 6. Adding a new podcast (no programming required)

1. Start the app → **Add Podcast**
2. **Info** — title, optional description & cover image
3. **Audio** — upload MP3 / WAV / M4A / OGG (duration is detected)
4. **Subtitles** — upload `.srt`, `.vtt`, or a `.txt`/`.docx`/`.pdf`
   transcript that contains timestamps like `0:08` on their own lines
   (a preview + parsing warnings are shown)
5. **Vocabulary** — upload an `.xlsx`; columns are auto-detected, you can
   remap them, and you see a preview + duplicate/empty-row report
   (this step is skippable)
6. **Review** → **Save** — the podcast appears in the library immediately

You can change any file later via **Edit** on the player page.

---

## 7. Using the player

* **Play/Pause** `Space` · **Seek ±5s** `←`/`→` · **Volume** `↑`/`↓`
* Speed: 0.75× / 1× / 1.25× / 1.5× / 2× — subtitle sync stays accurate at
  every speed (it reads the native audio clock, not a timer)
* The transcript highlights the current line and auto-scrolls
  (scrolling manually pauses auto-scroll for a few seconds)
* **Click any transcript line** to jump to its start time
* **Hover** a dotted-underlined word → quick preview card
  **Click** it → pin the full card (Esc or × to close)
* The card toggles **فارسی / English**, and Persian text renders RTL while
  English stays LTR — including inside notes and examples
* **Vocabulary** button opens the full word list for the episode

---

## 8. API overview

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/podcasts` | library list |
| GET | `/api/podcasts/{id}` | detail + segments (annotated) + vocabulary |
| POST | `/api/podcasts` | create (JSON with uploaded file ids) |
| PUT | `/api/podcasts/{id}` | update metadata / replace files |
| DELETE | `/api/podcasts/{id}` | delete |
| GET | `/api/podcasts/{id}/matching-stats` | per-word match counts (debug) |
| POST | `/api/uploads/audio` | upload audio → fileId + duration |
| POST | `/api/uploads/subtitles` | upload srt/vtt/docx/pdf/txt → parse preview |
| POST | `/api/uploads/vocabulary` | upload xlsx → headers + mapping + report |
| POST | `/api/uploads/cover` | upload cover image |
| POST | `/api/podcasts/vocabulary-preview` | re-map/re-parse with custom mapping |
| GET | `/api/files/{id}/content` | file stream (HTTP Range for seeking) |
| GET | `/api/health` | health check |

Interactive docs: http://127.0.0.1:8000/docs

---

## 9. Storage & database notes

* `backend/data/app.db` — SQLite database (delete it + re-run seed to reset)
* `backend/data/uploads/` — files uploaded through the UI
* Original podcast files are referenced **in place** via relative paths and
  are never modified by the app
* The schema (`files`, `podcasts`, `segments`, `vocabulary_entries`) is plain
  SQL and straightforward to migrate to PostgreSQL later
* Environment overrides:
  * `PODCAST_PROJECT_ROOT` — where source files live (default: repo root)
  * `PODCAST_DATA_DIR` — data directory (default: `backend/data`)
  * `PODCAST_DB_PATH` — SQLite path
  * `PODCAST_SEED_MANIFEST` — manifest path

---

## 10. Error handling

Invalid audio, corrupt/unreadable subtitles, timestamp-less transcripts,
malformed Excel files, missing word columns, duplicates, and unsupported
extensions all return short human-readable messages — no stack traces are
exposed to users.
