"""
Smart Catalog Similarity Classifier
====================================
Replaces hard_classification_override() with k-NN similarity search
over historical BOQ classifications stored in BigQuery.

How it works:
1. At startup: loads all high-confidence past classifications from BQ
2. Builds a TF-IDF matrix on the Hebrew descriptions (char n-grams,
   which handle Hebrew morphology well without stemming)
3. For each new item: finds the k most similar past items and votes
4. If the majority agree (>= MIN_AGREEMENT) → return that category
5. Otherwise → return None (falls through to Vertex AI)

This means:
- Every correct classification the system makes becomes a new training
  example — the catalog grows and improves automatically
- No manual regex needed for new edge cases
- Fast: TF-IDF cosine similarity on in-memory matrix, ~1ms per query
"""

from __future__ import annotations

import logging
import re
import threading
import unicodedata
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("calc-carbon")

# ── Tuning knobs ─────────────────────────────────────────────────────────────
TOP_K = 7           # how many neighbors to check
MIN_AGREEMENT = 0.75 # fraction of neighbors that must agree (e.g. 6/7 ≈ 0.86)
MIN_CONFIDENCE = 0.75  # minimum avg confidence of agreeing neighbors
MIN_SIMILARITY = 0.55  # discard neighbors with cosine sim below this — raised to cut false matches
MIN_CATALOG_SIZE = 50  # don't classify until catalog has this many entries
EXCLUDE_LABEL = "__EXCLUDE__"  # internal label for excluded items

# ── Hebrew text normalisation (matches normalize_text in main.py) ─────────────

_NIQQUD = re.compile(r"[֑-ׇ]")
_MULTI_SPACE = re.compile(r"\s+")

def _normalize(text: str) -> str:
    """Strip niqqud, lower-case, collapse whitespace."""
    text = unicodedata.normalize("NFC", text)
    text = _NIQQUD.sub("", text)
    text = text.lower().strip()
    text = _MULTI_SPACE.sub(" ", text)
    return text


# ── Main classifier ───────────────────────────────────────────────────────────

class CatalogClassifier:
    """
    Thread-safe, lazily-refreshed TF-IDF k-NN classifier over the
    historical BOQ catalog stored in BigQuery.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._matrix = None          # sparse TF-IDF matrix (n_items × n_features)
        self._labels: list[str] = [] # category per row (EXCLUDE_LABEL or category name)
        self._confidences: list[float] = []
        self._texts: list[str] = []  # normalised texts (for debug)
        self._ready = False
        self._item_count = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def fit(self, rows: list[dict]) -> None:
        """
        Build / rebuild the index from a list of catalog rows.

        Each row must have:
            short_text  : str   — the BOQ description
            category    : str   — e.g. "Structural Concrete" or None/""
            confidence  : float — 0–1 (use 1.0 if unknown)
            excluded    : bool  — True if the item was EXCLUDEd
        """
        texts, labels, confidences = [], [], []

        for r in rows:
            raw = r.get("short_text") or r.get("material") or ""
            if not raw or not raw.strip():
                continue

            excluded = r.get("excluded", False) or r.get("is_excluded", False)
            category = r.get("category") or ""
            if excluded or category.upper() in ("EXCLUDE", ""):
                label = EXCLUDE_LABEL
            else:
                label = category

            conf = float(r.get("confidence") or r.get("reliability_score") or 1.0)
            # Only learn from high-confidence examples
            if conf < 0.7 and label != EXCLUDE_LABEL:
                continue

            texts.append(_normalize(raw))
            labels.append(label)
            confidences.append(conf)

        if len(texts) < MIN_CATALOG_SIZE:
            logger.info("CatalogClassifier: only %d rows, skipping fit", len(texts))
            return

        # char n-grams (2-4) work well for Hebrew morphology
        vec = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 4),
            min_df=1,
            sublinear_tf=True,
        )
        matrix = vec.fit_transform(texts)

        with self._lock:
            self._vectorizer = vec
            self._matrix = matrix
            self._labels = labels
            self._confidences = confidences
            self._texts = texts
            self._item_count = len(texts)
            self._ready = True

        logger.info(
            "CatalogClassifier: fitted on %d items, %d features",
            len(texts), matrix.shape[1],
        )

    def classify(
        self,
        text: str,
        top_k: int = TOP_K,
        min_agreement: float = MIN_AGREEMENT,
        min_confidence: float = MIN_CONFIDENCE,
    ) -> tuple[Optional[str], float, str]:
        """
        Classify a single BOQ description.

        Returns:
            (category, confidence, reason)
            category is None  → EXCLUDE
            category is ""    → no confident match found (fall through)
        """
        if not self._ready:
            return "", 0.0, "catalog not ready"

        norm = _normalize(text)
        if not norm:
            return "", 0.0, "empty text"

        with self._lock:
            vec = self._vectorizer
            matrix = self._matrix
            labels = self._labels
            confidences = self._confidences
            texts = self._texts

        query = vec.transform([norm])
        sims = cosine_similarity(query, matrix).ravel()

        # Get top-k indices sorted by similarity
        top_idx = np.argsort(sims)[::-1][:top_k]

        # Filter by minimum similarity threshold
        top_idx = [i for i in top_idx if sims[i] >= MIN_SIMILARITY]

        if not top_idx:
            return "", 0.0, f"no neighbors above sim={MIN_SIMILARITY}"

        # Vote
        from collections import Counter
        votes: Counter = Counter()
        vote_conf: dict[str, list[float]] = {}
        for i in top_idx:
            lbl = labels[i]
            votes[lbl] += 1
            vote_conf.setdefault(lbl, []).append(confidences[i] * sims[i])

        winner, win_count = votes.most_common(1)[0]
        agreement = win_count / len(top_idx)
        avg_conf = float(np.mean(vote_conf[winner]))

        # Debug: top-3 neighbors
        neighbors_dbg = " | ".join(
            f"{texts[i][:40]}→{labels[i]}({sims[i]:.2f})"
            for i in top_idx[:3]
        )

        if agreement < min_agreement:
            return "", 0.0, f"disagreement ({agreement:.0%}): {neighbors_dbg}"

        if avg_conf < min_confidence:
            return "", 0.0, f"low avg_conf ({avg_conf:.2f}): {neighbors_dbg}"

        # Map internal EXCLUDE label back to None
        category = None if winner == EXCLUDE_LABEL else winner
        reason = (
            f"catalog k-NN: {win_count}/{len(top_idx)} neighbors agree "
            f"({agreement:.0%}), avg_conf={avg_conf:.2f} | {neighbors_dbg}"
        )
        return category, avg_conf, reason

    @property
    def size(self) -> int:
        return self._item_count

    @property
    def is_ready(self) -> bool:
        return self._ready


# Singleton — imported and used by main.py
catalog_classifier = CatalogClassifier()
