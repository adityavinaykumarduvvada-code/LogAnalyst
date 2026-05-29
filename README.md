# Log Analyst — Verifiable RAG

An AI security log analyst that answers questions about your logs using
Retrieval-Augmented Generation, and — unlike most RAG demos — actually
**verifies** that the answer is grounded in real, unaltered evidence
before you see it.

## Why "verifiable"?

Plain RAG systems retrieve some text, hand it to an LLM, and trust
whatever citations the model produces. That's not good enough for
security work, where a false positive (or a fabricated citation) wastes
an analyst's time, and a missed true positive is worse.

This project adds a verification layer on top of retrieval + generation:

1. **Hashing at ingest** — every log line is SHA-256 hashed the moment
   it's parsed. Every retrieval chunk carries that hash.
2. **Strict citation prompting** — the model is instructed to cite every
   claim with `[n]` pointing at a specific numbered source, and to say
   "not enough evidence" rather than guess.
3. **Post-hoc verification** (`src/verifier.py`) — after the model
   answers, the code (not the model) checks:
   - Every `[n]` citation actually refers to a chunk that was retrieved
     (catches invented sources).
   - Each cited chunk's hash still matches its original — an integrity
     check that would catch tampering between indexing and querying.
   - Every claim-shaped sentence has *some* citation — sentences that
     look factual but have no citation are flagged as unsupported
     rather than silently trusted.
4. A **trust score** (0–1) summarizes these checks, shown alongside
   every answer.

## Architecture

```
data/sample_logs/*.log
        │
        ▼
  log_parser.py     — regex-based parsing of SSH/firewall/web logs
        │              into normalized LogEntry objects (+ hash)
        ▼
  chunker.py         — groups entries into retrievable Chunks
        │              (line-level by default; window mode available)
        ▼
  vector_store.py     — TF-IDF + cosine similarity index (fully local,
        │              no model download; includes a small security-
        │              term synonym expansion for recall)
        ▼
  rag_engine.py       — retrieves top-k chunks, builds a strict citation
        │              prompt, calls Gemini
        ▼
  verifier.py         — checks citation validity, hash integrity, and
        │              claim coverage on the model's answer
        ▼
  app.py               — Flask API + serves the browser UI
```

### Why TF-IDF instead of a neural embedding model?
It's fully offline (no model download), transparent (you can see
exactly which terms drove a match), and effective for log text, which
is dense with exact-match tokens like IPs, usernames, and status codes.
The tradeoff is it only matches vocabulary that's literally present, so
`src/vector_store.py` includes a small, readable synonym table (e.g.
"brute force" → "failed password invalid user attempt") to bridge
common security terminology without giving up transparency. Swapping in
a real embedding model later is a contained change, isolated to that
one file.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then add your GEMINI_API_KEY
```

## Usage

### 1. Run the app
The web UI is a small React app (`frontend/`) that talks to the Flask
backend as a JSON API. Run both, in two terminals:
```bash
# terminal 1 - backend API
python app.py                 # http://localhost:5000

# terminal 2 - frontend
cd frontend
npm install                    # first time only
npm run dev                    # http://localhost:5173
```
Open http://localhost:5173.

### 2. Add your logs
Everything is added through the upload panel — drag and drop, or click
to browse. It accepts individual log files (`.log`/`.txt`/`.csv`/`.json`)
or a `.zip` bundle of many logs at once, and re-indexes automatically
the moment you drop something in. Each upload adds to the existing
index rather than replacing it. Zip extraction is protected against
path traversal ("zip slip") — any archive entry that would write
outside the target directory is rejected.

To try it immediately without your own logs, upload the synthetic demo
files in `data/sample_logs/` (a scripted SSH brute-force attempt, a
port scan, and a SQL-injection probe, mixed with benign traffic).

New to React? `frontend/README.md` has a one-day guided tour through
this exact codebase.

### 3. Ask questions
Once the status bar shows "Ready", ask things like:
- "Were there any SSH brute force attempts?"
- "Did any IP attempt SQL injection on the login page?"
- "Summarize suspicious activity from 198.51.100.77"
- "Was there a successful login right after failed attempts from the same IP?"

## Running in production / hosting
See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for building the frontend for
production, running under gunicorn, Docker, and full step-by-step
hosting instructions (a Platform-as-a-Service path, and a full VPS +
nginx + HTTPS path).

## Extending this project
- **New log formats**: add a regex + type to `src/log_parser.py`.
- **Different chunking**: `chunk_entries(..., strategy="window", window=5)`
  groups nearby lines for more context per retrieval.
- **Stronger integrity guarantees**: persist each chunk's hash to a
  separate write-once audit log at ingest time, and compare against
  *that* in `verifier.py` instead of recomputing from the same index
  file — this protects against the index file itself being modified.
- **Swap the LLM**: `rag_engine.py` isolates the single API call; point
  it at any other provider by changing `_get_client`/`answer`.
- **Real-time ingestion**: wrap `log_parser.parse_file` in a file-tailer
  (e.g. watch new lines appended to `/var/log/auth.log`) and re-index
  incrementally.

## Project structure
```
security-log-rag/
├── app.py                    # Flask API + serves the built frontend
├── requirements.txt
├── .env.example
├── src/
│   ├── log_parser.py         # raw logs -> structured, hashed entries
│   ├── chunker.py             # entries -> retrievable chunks
│   ├── vector_store.py        # TF-IDF index + search
│   ├── rag_engine.py          # retrieval + prompting + Gemini call
│   ├── verifier.py            # citation/integrity/coverage checks
│   └── uploads.py             # safe file/zip-bundle upload handling
├── frontend/                  # React UI (see frontend/README.md)
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       └── components/
├── data/sample_logs/          # synthetic demo logs
└── data/uploaded_logs/        # created at runtime by web uploads
```

## Notes
- The sample logs are entirely synthetic — no real IPs, usernames, or
  incidents.
- `GEMINI_API_KEY` is required for the web UI's answer generation;
  uploading and indexing logs needs no key.
- LLM calls use Google's `google-genai` SDK (`src/rag_engine.py`), the
  current unified SDK for the Gemini API.
