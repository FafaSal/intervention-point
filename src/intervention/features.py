"""Features available to an intervention gate at decision time.

Three groups, all observable without ground truth:
  * text cues   - lexical signals in the request and standing context
  * lookups     - workspace queries about the proposed tool call
  * tf-idf      - word and bigram representation of the request + context
"""
from __future__ import annotations

import re

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

from .scenarios import lookup_features

VAGUE = r"\b(appropriate|whatever|wherever|whoever|however you like|sometime|soon|later|a bit|stuff|unimportant|isn't important|doesn't matter|needs work|better|clean(?: up| out)|fix (?:up|it)|deal with|handle|take care|everyone who|needs it|should have it|old|clearer|terrible)\b"
CONFLICT = r"\b(but|without|while|still|leave .* alone|don't (?:move|change|touch)|keep(?:ing)? it|make sure|where it is)\b"
UNIVERSAL = r"\b(all|every|everything|everyone|whole|entire)\b"
TIME = r"\b(\d{1,2}(:\d{2})?\s?(am|pm)?|\d{1,2}:\d{2})\b"
DAY = r"\b(monday|tuesday|wednesday|thursday|friday|tomorrow|today|next week|this week)\b"
DURATION = r"\b(\d+[- ]minutes?|\d+ ?min|hour|minutes)\b"
PERMANENT = r"\b(permanently|for good|purge|wipe|skip the trash|destroy)\b"
ROLE_REF = r"\b(her|his|their) (manager|boss|lead)\b"

TOOLS = ["search_files", "read_file", "summarize_emails", "mark_email_read", "draft_email", "send_email",
         "forward_email", "share_file", "move_file", "rename_file", "edit_file", "delete_file", "archive_email",
         "delete_email", "schedule_event", "reschedule_event", "cancel_event", "decline_event", "make_payment"]


def text_of(row: dict) -> str:
    return (row["request"] + " " + row.get("context", "")).strip()


def cue_features(row: dict) -> dict:
    req = row["request"].lower(); ctx = row.get("context", "").lower()
    n = lambda p, s: len(re.findall(p, s))
    return {
        "cue_vague": n(VAGUE, req),
        "cue_conflict": n(CONFLICT, req),
        "cue_universal": n(UNIVERSAL, req),
        "cue_time": int(bool(re.search(TIME, req))),
        "cue_day": int(bool(re.search(DAY, req))),
        "cue_duration": int(bool(re.search(DURATION, req))),
        "cue_permanent": int(bool(re.search(PERMANENT, req))),
        "cue_role_reference": int(bool(re.search(ROLE_REF, req))),
        "has_standing_instruction": int(bool(ctx)),
        "standing_blocks_external": int(bool(re.search(r"external|outside", ctx))),
        "n_words": len(req.split()),
    }


def structured(row: dict, use_lookups: bool = True) -> dict:
    f = cue_features(row)
    if use_lookups:
        lk = lookup_features(row)
        tool = lk.pop("tool")
        f.update({f"tool_{t}": int(tool == t) for t in TOOLS})
        f.update(lk)
        # interaction the gate needs for standing instructions: an external send while one is in force
        f["standing_conflict_external"] = int(f["standing_blocks_external"] and lk["any_external"])
    return f


class FeatureBuilder:
    """Fit on training rows only (tf-idf vocabulary and scaling)."""

    def __init__(self, use_lookups=True, use_text=True):
        self.use_lookups, self.use_text = use_lookups, use_text
        self.tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        self.keys = None

    def fit(self, rows):
        if self.use_text:
            self.tfidf.fit([text_of(r) for r in rows])
        self.keys = sorted(structured(rows[0], self.use_lookups).keys())
        S = self._struct(rows)
        self.mu, self.sd = S.mean(0), S.std(0) + 1e-6
        return self

    def _struct(self, rows):
        return np.array([[structured(r, self.use_lookups)[k] for k in self.keys] for r in rows], dtype=float)

    def transform(self, rows):
        S = (self._struct(rows) - self.mu) / self.sd
        parts = [sparse.csr_matrix(S)]
        if self.use_text:
            parts.append(self.tfidf.transform([text_of(r) for r in rows]))
        return sparse.hstack(parts).tocsr()

    def feature_names(self):
        names = list(self.keys)
        if self.use_text:
            names += [f"tfidf:{t}" for t in self.tfidf.get_feature_names_out()]
        return names
