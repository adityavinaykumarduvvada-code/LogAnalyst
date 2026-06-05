import os
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

from src.vector_store import VectorStore
from src.rag_engine import RAGEngine
from src.log_parser import parse_directory
from src.chunker import chunk_entries
from src.uploads import save_uploaded_files

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
FRONTEND_BUILT = os.path.isdir(FRONTEND_DIST)

if FRONTEND_BUILT:
    app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path="")
else:
    app = Flask(__name__)

INDEX_PATH = os.environ.get("INDEX_PATH", "index.pkl")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "data/uploaded_logs")
_store = None
_engine = None


def get_engine():
    global _store, _engine
    if _engine is None:
        if not os.path.exists(INDEX_PATH):
            raise RuntimeError(
                "No index found yet. Upload some log files (or a .zip bundle) "
                "using the upload panel to get started."
            )
        _store = VectorStore.load(INDEX_PATH)
        _engine = RAGEngine(_store)
    return _engine


def rebuild_index_from(dir_path: str):
    global _store, _engine
    entries = parse_directory(dir_path)
    if not entries:
        raise RuntimeError(
            "No recognizable log lines were found in the uploaded file(s)."
        )
    chunks = chunk_entries(entries, strategy="line")
    store = VectorStore()
    store.build(chunks)
    store.save(INDEX_PATH)
    _store = store
    _engine = RAGEngine(store)
    return {
        "entries_indexed": len(entries),
        "chunks_indexed": len(chunks),
        "source_files": sorted({os.path.relpath(e.source_file, dir_path) for e in entries}),
    }


if FRONTEND_BUILT:
    @app.route("/")
    @app.route("/<path:path>")
    def serve_frontend(path=""):
        full_path = os.path.join(FRONTEND_DIST, path)
        if path and os.path.isfile(full_path):
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")
else:
    @app.route("/")
    def index():
        return jsonify({
            "service": "security-log-rag API",
            "frontend": "not built yet - run `npm run dev` inside ./frontend for local development, "
                        "or `npm run build` to have Flask serve it directly",
            "endpoints": ["/api/status", "/api/upload", "/api/query"],
        })


@app.route("/api/status")
def api_status():
    exists = os.path.exists(INDEX_PATH)
    stats = None
    if exists:
        try:
            store = VectorStore.load(INDEX_PATH)
            stats = {
                "chunks_indexed": len(store.chunks),
                "source_files": sorted({os.path.basename(c.source_file) for c in store.chunks}),
            }
        except Exception:
            exists = False
    return jsonify({"index_ready": exists, "stats": stats})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    files = request.files.getlist("files")
    if not files or all((f.filename or "") == "" for f in files):
        return jsonify({"error": "No files were provided"}), 400
    try:
        saved = save_uploaded_files(files, UPLOAD_DIR)
        if not saved:
            return jsonify({"error": "No valid files were uploaded"}), 400
        result = rebuild_index_from(UPLOAD_DIR)
        result["saved_files"] = saved
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/query", methods=["POST"])
def api_query():
    data = request.get_json(force=True)
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    try:
        engine = get_engine()
        result = engine.answer(question)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
