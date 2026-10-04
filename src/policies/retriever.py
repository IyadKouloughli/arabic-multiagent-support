# -*- coding: utf-8 -*-
"""Arabic Policy Document Retriever for RAG."""
import json
import re
import math
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import POLICIES_PATH
from src.preprocessing.arabic import preprocess_arabic


def normalize_arabic(text: str) -> str:
    """Preprocess Arabic text by removing diacritics and tatweel while keeping original letter forms."""
    text = preprocess_arabic(text)
    # Remove punctuation for word tokenization without modifying letter forms
    text = re.sub(r"[^\w\s]", " ", text)
    return text.lower().strip()


class PolicyRetriever:
    """Retrieves Arabic company policies (P01-P15) with citations."""

    def __init__(self, policies_path: Optional[Path] = None):
        path = policies_path or POLICIES_PATH
        with open(path, "r", encoding="utf-8") as f:
            self.policies: List[Dict[str, Any]] = json.load(f)
        self.by_id: Dict[str, Dict[str, Any]] = {p["policy_id"]: p for p in self.policies}
        self._build_index()

    def _build_index(self):
        """Index policy documents for BM25 retrieval."""
        self.doc_tokens = []
        self.df = {}
        self.doc_len = []
        self.n_docs = len(self.policies)

        for p in self.policies:
            content = f"{p['title']} {p['title_en']} {p['text']}"
            tokens = normalize_arabic(content).split()
            self.doc_tokens.append(tokens)
            self.doc_len.append(len(tokens))
            for token in set(tokens):
                self.df[token] = self.df.get(token, 0) + 1

        self.avg_dl = sum(self.doc_len) / max(1, self.n_docs)

    def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific policy by its ID (e.g. 'P01')."""
        return self.by_id.get(policy_id.upper())

    def get_all_policies(self) -> List[Dict[str, Any]]:
        """Return all available policies."""
        return list(self.policies)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """BM25 search over policy documents."""
        q_tokens = normalize_arabic(query).split()
        if not q_tokens:
            return self.policies[:top_k]

        k1 = 1.5
        b = 0.75
        scores = []

        for idx, p in enumerate(self.policies):
            score = 0.0
            tokens = self.doc_tokens[idx]
            dl = self.doc_len[idx]
            counts = {}
            for t in tokens:
                counts[t] = counts.get(t, 0) + 1

            for qt in q_tokens:
                if qt in counts:
                    doc_freq = self.df.get(qt, 1)
                    idf = math.log((self.n_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
                    tf = counts[qt]
                    score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / self.avg_dl)))
            scores.append((score, p))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [p for score, p in scores[:top_k]]

    def format_for_prompt(self, policies: List[Dict[str, Any]]) -> str:
        """Format a list of policies with citation identifiers for prompt injection."""
        lines = []
        for p in policies:
            lines.append(f"[{p['policy_id']}] {p['title']} ({p['title_en']}):\n{p['text']}")
        return "\n\n".join(lines)
