# -*- coding: utf-8 -*-
"""Semantic and Exact Query-Response Cache for Arabic customer tickets."""
import json
import math
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.preprocessing.arabic import preprocess_arabic


class SemanticCache:
    """Caches resolution responses for repetitive Arabic support queries."""

    def __init__(self, similarity_threshold: float = 0.88, cache_file: Optional[Path] = None):
        self.similarity_threshold = similarity_threshold
        self.cache_file = cache_file
        self.exact_cache: Dict[str, Dict[str, Any]] = {}
        self.indexed_queries: List[Dict[str, Any]] = []
        self.hits = 0
        self.misses = 0
        self._load()

    def _load(self):
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        self.set(item["query"], item["response"], save=False)
            except Exception:
                pass

    def _save(self):
        if self.cache_file:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.indexed_queries, f, ensure_ascii=False, indent=2)

    def _tokenize(self, text: str) -> set[str]:
        cleaned = preprocess_arabic(text)
        return set(cleaned.lower().split())

    def _jaccard_similarity(self, set1: set[str], set2: set[str]) -> float:
        if not set1 or not set2:
            return 0.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    def get(self, query: str) -> Optional[Dict[str, Any]]:
        """Look up response from exact or semantic cache."""
        cleaned = preprocess_arabic(query)
        # 1. Exact match
        if cleaned in self.exact_cache:
            self.hits += 1
            return self.exact_cache[cleaned]

        # 2. Semantic token similarity
        q_tokens = self._tokenize(query)
        best_score = 0.0
        best_match = None

        for item in self.indexed_queries:
            sim = self._jaccard_similarity(q_tokens, item["tokens"])
            if sim > best_score:
                best_score = sim
                best_match = item["response"]

        if best_score >= self.similarity_threshold and best_match:
            self.hits += 1
            return best_match

        self.misses += 1
        return None

    def set(self, query: str, response: Dict[str, Any], save: bool = True):
        """Store query and resolution response in cache."""
        cleaned = preprocess_arabic(query)
        self.exact_cache[cleaned] = response
        tokens = self._tokenize(query)
        self.indexed_queries.append({
            "query": query,
            "cleaned": cleaned,
            "tokens": list(tokens),
            "response": response
        })
        if save and self.cache_file:
            self._save()

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0
