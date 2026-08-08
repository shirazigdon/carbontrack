import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS
from google.cloud import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get("GCP_PROJECT", "sadot-500108")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "sadot-500108-bachelorette-data")
PREFIX = os.environ.get("STORAGE_PREFIX", "bachelorette-nogah/submissions")
ACCESS_CODE = os.environ.get("ACCESS_CODE", "nogah2026")

CATEGORY_KEYS = {
    "awkward", "funny", "rivals", "firstlove",
    "exes", "nicknames", "places", "quirks",
}
MAX_WORDS_PER_CATEGORY = 60
MAX_WORD_LENGTH = 200
MAX_NAME_LENGTH = 80

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

storage_client = storage.Client(project=PROJECT_ID)


def _clean_text(value, max_len):
    if not isinstance(value, str):
        return ""
    value = re.sub(r"\s+", " ", value).strip()
    return value[:max_len]


@app.route("/", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "bachelorette-nogah-api"})


@app.route("/submit", methods=["POST"])
def submit():
    body = request.get_json(silent=True) or {}
    name = _clean_text(body.get("name", ""), MAX_NAME_LENGTH) or "(בלי שם)"
    raw_words = body.get("words", {})
    if not isinstance(raw_words, dict):
        return jsonify({"ok": False, "error": "invalid words payload"}), 400

    cleaned = {}
    total_words = 0
    for key, arr in raw_words.items():
        if key not in CATEGORY_KEYS or not isinstance(arr, list):
            continue
        words = []
        for w in arr[:MAX_WORDS_PER_CATEGORY]:
            w = _clean_text(w, MAX_WORD_LENGTH)
            if w:
                words.append(w)
                total_words += 1
        if words:
            cleaned[key] = words

    if not cleaned:
        return jsonify({"ok": False, "error": "no words submitted"}), 400

    record = {
        "name": name,
        "words": cleaned,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    blob_name = f"{PREFIX}/{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}.json"
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json.dumps(record, ensure_ascii=False), content_type="application/json")

    logger.info("Stored submission from %s (%d words) at %s", name, total_words, blob_name)
    return jsonify({"ok": True, "words_saved": total_words})


@app.route("/submissions", methods=["GET"])
def submissions():
    code = request.args.get("code", "")
    if code != ACCESS_CODE:
        return jsonify({"ok": False, "error": "invalid code"}), 401

    bucket = storage_client.bucket(BUCKET_NAME)
    merged = {key: [] for key in CATEGORY_KEYS}
    contributors = set()
    submission_count = 0

    for blob in bucket.list_blobs(prefix=PREFIX + "/"):
        if not blob.name.endswith(".json"):
            continue
        try:
            record = json.loads(blob.download_as_text())
        except Exception:
            logger.exception("Failed to read %s", blob.name)
            continue
        submission_count += 1
        contributors.add(record.get("name", "(בלי שם)"))
        for key, words in (record.get("words") or {}).items():
            if key in merged and isinstance(words, list):
                for w in words:
                    merged[key].append({"word": w, "by": record.get("name", "(בלי שם)")})

    return jsonify({
        "ok": True,
        "submission_count": submission_count,
        "contributor_count": len(contributors),
        "contributors": sorted(contributors),
        "words": merged,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
