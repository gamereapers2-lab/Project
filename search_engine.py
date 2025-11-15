"""
Composite text search engine for JSON files.
- Index JSON files under a directory
- Extract sentences from text fields
- Supports exact, keywords, and fuzzy search
"""

import os
import json
import re
from difflib import SequenceMatcher
from collections import defaultdict

SENT_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')

class SearchEngine:
    def __init__(self):
        self.index = []
        self.by_file = defaultdict(list)

    # ----- Indexing -----
    def index_json_dir(self, dirpath, recursive=False):
        files = []
        if recursive:
            for root, _, filenames in os.walk(dirpath):
                for fn in filenames:
                    if fn.lower().endswith(".json"):
                        files.append(os.path.join(root, fn))
        else:
            for fn in os.listdir(dirpath):
                if fn.lower().endswith(".json"):
                    files.append(os.path.join(dirpath, fn))
        for fp in files:
            self._index_single_json(fp)

    def _index_single_json(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        text_candidates = []

        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str):
                    text_candidates.append(v)
            if "items" in data and isinstance(data["items"], list):
                for it in data["items"]:
                    if isinstance(it, dict):
                        for kk, vv in it.items():
                            if isinstance(vv, str):
                                text_candidates.append(vv)
        elif isinstance(data, list):
            for it in data:
                if isinstance(it, str):
                    text_candidates.append(it)
                elif isinstance(it, dict):
                    for kk, vv in it.items():
                        if isinstance(vv, str):
                            text_candidates.append(vv)

        if not text_candidates:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw = f.read()
                if raw:
                    text_candidates.append(raw)
            except Exception:
                pass

        for text in text_candidates:
            sentences = self._split_sentences(text)
            for s in sentences:
                s_clean = s.strip()
                if not s_clean:
                    continue
                idx = len(self.index)
                tokens = self._tokenize(s_clean)
                self.index.append({"file": filepath, "sentence": s_clean, "tokens": tokens})
                self.by_file[filepath].append(idx)

    # ----- Helpers -----
    def _split_sentences(self, text):
        return SENT_SPLIT_RE.split(text)

    def _tokenize(self, text):
        tokens = re.findall(r'\w+', text.lower())
        return set(t for t in tokens if len(t) > 1)

    def _jaccard(self, a_set, b_set):
        if not a_set or not b_set:
            return 0.0
        return len(a_set & b_set) / len(a_set | b_set)

    def _sequence_ratio(self, a, b):
        return SequenceMatcher(None, a, b).ratio()

    def _fuzzy_score(self, query, sentence):
        q_tokens = self._tokenize(query)
        s_tokens = sentence["tokens"]
        token_score = self._jaccard(q_tokens, s_tokens)
        seq_score = self._sequence_ratio(query.lower(), sentence["sentence"].lower())
        return 0.65 * token_score + 0.35 * seq_score

    # ----- Search APIs -----
    def search_exact(self, phrase):
        phrase_l = phrase.strip().lower()
        results = []
        for doc in self.index:
            if phrase_l in doc["sentence"].lower():
                results.append({"file": doc["file"], "sentence": doc["sentence"], "score": 1.0})
        return results

    def search_keywords_same_sentence(self, keywords):
        kset = set(k.strip().lower() for k in keywords if k.strip())
        results = []
        for doc in self.index:
            if kset.issubset(doc["tokens"]):
                results.append({"file": doc["file"], "sentence": doc["sentence"], "score": 1.0})
        return results

    def search_fuzzy(self, query, top_n=10, min_score=0.25):
        scored = []
        for doc in self.index:
            score = self._fuzzy_score(query, doc)
            if score >= min_score:
                scored.append({"file": doc["file"], "sentence": doc["sentence"], "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_n]
