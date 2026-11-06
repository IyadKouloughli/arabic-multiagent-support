# -*- coding: utf-8 -*-
"""Semantic and Exact Query-Response Cache for Arabic customer tickets.

Implements two core architectural guarantees:
1. Scope Isolation: General FAQs and knowledge inquiries are cached, while order-specific
   or transactional inquiries obligatorily bypass the cache to undergo live database reads.
2. Policy-Linked Invalidation: Cache entries are stamped with the active policy hash,
   automatically invalidating cached resolutions whenever store policies are modified.
"""
import json
import math
import hashlib
import re
from typing import Dict, Any, Optional, List
from pathlib import Path

from src.preprocessing.arabic import preprocess_arabic
from src.config import POLICIES_PATH

# Regular expression detecting Nawras Market order IDs (e.g. NW4241472)
OID_REGEX = re.compile(r"NW\d{7}", re.IGNORECASE)

# Write tools that must never be replayed from cache
WRITE_TOOLS = {
    "cancel_order", "create_return", "issue_refund", "update_address",
    "issue_voucher", "create_warranty_claim", "escalate_to_human"
}

# Informational FAQ, Procedure, Hypothetical and Rule patterns (Arabic, French, English)
FAQ_PATTERNS = [
    r"^(ما\s+|ماذا\s+|ماهي\s+|ما\s+هو\s+|ما\s+هي\s+)(سياسة|شروط|طرق|مدة|حالات|معلومات|إجراء|اجراء|تفعلون|يحدث)",
    r"\b(شروط\s+(و\s*سياسة\s+)?(الإرجاع|الارجاع|الإلغاء|الالغاء|الضمان|الاسترداد))\b",
    r"^(كيف\s+|كيفية\s+|طريقة\s+)(يمكن|يتم|استطيع|أستطيع|طريقة|اتصرف|ألغي|الغي|ارجع|أرجع|استرد|أحصل)",
    r"^هل\s+(يمكن|ينفع|يتم|متاح|يحق|توصلون|تشحنون|عندكم|يوجد|لديكم|في|الاسترداد|الالغاء|الإلغاء|الإرجاع|الارجاع|الضمان)",
    r"\b(لو\s+|إذا\s+|اذا\s+|في\s+حال\s+|عند\s+)(وصلني|تأخر|تاخر|حدث|كان|تلف|ضاع)",
    r"\b(الدول\s+المتاحة|فروع\s+المتجر|مدة\s+التوصيل|طرق\s+الدفع)\b",
    r"^(est[- ]ce (qu\'on|que)|comment|quels?|quelles?|politique|conditions?)\b",
    r"^(how\s+(to|do|can)|what\s+(is|are|happens|if)|can\s+(i|an|the|we)|do\s+you)\b"
]

# Direct first-person action requests (commands or immediate personal claims)
DIRECT_ACTION_REQUESTS = [
    r"^(أريد|اريد|بدي|عاوز|حاب|نبي|ابغى|ابي)\s+(ألغي|الغي|نلغي|استرداد|استرجاع|ارجع|أرجع|ابدل|اغير|أغير)",
    r"\b(الغو|ألغوا|كنسل|الغوه|رجعولي|استردوا|غيروا\s+عنواني)\b",
    r"^(وصلني|جاني|استلمت|لقيت)\s+.*(تالف|مكسور|خربان|ناقص|خاطئ)",
    r"\b(i want to (cancel|return|refund)|cancel my|refund my|i received a damaged)\b",
    r"\b(je veux (annuler|retourner|un remboursement)|annulez|remboursez)\b"
]

# Order and shipment terms across all dialects (MSA, Egyptian, Gulf, Levantine, Algerian, French, English)
ORDER_WORDS = [
    r"\b(طلبي|طلبيتي|طلب|الطلب)\b",
    r"\b(أوردر|اوردر|الأوردر|الاوردر)\b",
    r"\b(كوموند|الكوموند|لاكوموند|لا\s*كوموند)\b",
    r"\b(شحنة|الشحنة|شحنتي)\b",
    r"\b(طرد|الطرد|طردي|كولي|الكولي)\b",
    r"\b(commande|la\s+commande|ma\s+commande)\b",
    r"\b(colis|le\s+colis|mon\s+colis)\b",
    r"\b(order|my\s+order|the\s+order)\b"
]

# Action and state verbs/adjectives indicating specific issues across dialects
ORDER_ACTIONS_AND_STATES = [
    # Status / whereabouts / delays
    r"(وين|فين|وينها|فينها|راهي|راهو|وين\s*صار|شو\s*صار|وصل|وصلت|ما\s*وصل|ما\s*وصلش|ما\s*لحقتش|ما\s*استلمت|تأخر|متأخر|اتأخر|تأخير|retard|late|delay|delayed|track|where)",
    # Actions: cancel, return, refund, change address
    r"(إلغاء|الغاء|كنسل|ألغي|الغي|نلغي|اتلغى|تلغوه|annuler|cancel)",
    r"(إرجاع|ارجاع|استرجاع|رجع|نرجع|رجعولي|retour|return)",
    r"(استرداد|فلوسي|دراهمي|مصاري|سواردي|rembours|refund)",
    r"(تغيير|تعديل|أغير|اغير|ابدل|بدل|غيرت|changer|change)\s+.*(عنوان|adresse|address)",
    r"(تالف|مكسور|خربان|ناقص|خاطئ|damaged|cassé)",
    r"(خصم|سحب)\s+.*(مكرر|مزدوج|مرتين|double)"
]

# Personal / dialect possessive markers
POSSESSIVES = [
    r"\b(طلبي|طلبيتي|شحنتي|طردي)\b",
    r"\b(بتاعي|ديالي|حقي|تبعي|نتاعي|لي)\b",
    r"\b(ma\s+commande|mon\s+colis|my\s+order)\b"
]


class SemanticCache:
    """Caches resolution responses for repetitive Arabic support queries with scope isolation & policy sync."""

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        cache_file: Optional[Path] = None,
        enforce_scope_isolation: bool = True,
        policies_path: Optional[Path] = None
    ):
        self.similarity_threshold = similarity_threshold
        self.cache_file = cache_file
        self.enforce_scope_isolation = enforce_scope_isolation
        self.policies_path = Path(policies_path or POLICIES_PATH)
        self.exact_cache: Dict[str, Dict[str, Any]] = {}
        self.indexed_queries: List[Dict[str, Any]] = []
        self.hits = 0
        self.misses = 0
        self.bypasses = 0
        self.invalidations = 0
        self.current_policy_hash = self._compute_policy_hash()
        self._load()

    def _compute_policy_hash(self) -> str:
        """Compute SHA-256 fingerprint of the current store policy document."""
        if self.policies_path and self.policies_path.exists():
            try:
                with open(self.policies_path, "rb") as f:
                    return hashlib.sha256(f.read()).hexdigest()[:16]
            except Exception:
                pass
        return "v1.0_default"

    def check_and_invalidate_policy_cache(self) -> bool:
        """Checks if the policy definitions have been modified and purges stale cache if so."""
        latest_hash = self._compute_policy_hash()
        if latest_hash != self.current_policy_hash:
            stale_entries = len(self.exact_cache)
            self.invalidate_all(reason=f"Policy version modified ({self.current_policy_hash} -> {latest_hash})")
            self.current_policy_hash = latest_hash
            self.invalidations += stale_entries
            return True
        return False

    def invalidate_all(self, reason: str = "manual"):
        """Purge all cached entries."""
        self.exact_cache.clear()
        self.indexed_queries.clear()
        if self.cache_file and self.cache_file.exists():
            try:
                self.cache_file.unlink()
            except Exception:
                pass

    def is_order_specific(self, query: str) -> bool:
        """Determines whether a query pertains to a specific order/account rather than a general FAQ.
        
        Supports all project language varieties:
        - MSA (Modern Standard Arabic)
        - Egyptian (الأوردر، وصل فين، ما وصلش، اتلغى، عاوز الغي...)
        - Gulf (وين طلبيتي، تكفون، متأخر علي، ابي الغي...)
        - Levantine (شو صار بالطلب، اتأخر كتيير، بدي رجع...)
        - Algerian (وين راهي الكوموند، ما لحقتش، لاكوموند، كولي...)
        - Algerian-French code-switching (etat de ma commande, retardée, colis...)
        - English-Arabic code-switching (where is my order, cancel order, refund...)
        """
        q = query.strip()

        # 1. Any order ID is 100% order-specific
        if OID_REGEX.search(q):
            return True

        # 2. Check for personal possessive markers
        if any(re.search(p, q, re.IGNORECASE) for p in POSSESSIVES):
            return True

        # 3. Direct action requests (e.g. 'عايز الغي', 'وصلني تالف وعايز ابدل')
        if any(re.search(p, q, re.IGNORECASE) for p in DIRECT_ACTION_REQUESTS):
            return True

        # 4. Check if query matches general FAQ / hypothetical rule patterns
        is_faq = any(re.search(p, q, re.IGNORECASE) for p in FAQ_PATTERNS)
        if is_faq:
            # If it has a specific personal reference like 'طلبي' or 'NW123', it was caught by rules 1 & 2
            return False

        # 5. Check if query contains an order word AND an action/state word
        has_order_word = any(re.search(p, q, re.IGNORECASE) for p in ORDER_WORDS)
        has_action_or_state = any(re.search(p, q, re.IGNORECASE) for p in ORDER_ACTIONS_AND_STATES)
        if has_order_word and has_action_or_state:
            return True

        # 6. Standalone actions (e.g. 'عايز الغي', 'كنسل الحجز')
        if has_action_or_state and any(re.search(p, q, re.IGNORECASE) for p in [
            r"(إلغاء|الغاء|كنسل|ألغي|الغي|نلغي|annuler|cancel)",
            r"(إرجاع|ارجاع|استرجاع|استرداد|فلوسي|دراهم|مصاري)",
            r"(تالف|مكسور|خربان|damaged|cassé)",
            r"(خصم|سحب)\s+.*(مكرر|مزدوج|مرتين)"
        ]):
            return True

        return False

    def is_cacheable(self, query: str) -> bool:
        """A query is cacheable only if it is a general knowledge/FAQ inquiry and NOT order-specific."""
        return not self.is_order_specific(query)

    def _load(self):
        if self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        # Only restore items that match current policy hash
                        if item.get("policy_hash") == self.current_policy_hash:
                            self.set(item["query"], item["response"], save=False, force=True)
            except Exception:
                pass

    def _save(self):
        if self.cache_file:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.indexed_queries, f, ensure_ascii=False, indent=2)

    def _tokenize(self, text: str) -> set[str]:
        cleaned = preprocess_arabic(text)
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        return set(cleaned.lower().split())

    def _jaccard_similarity(self, set1: set[str], set2: set[str]) -> float:
        if not set1 or not set2:
            return 0.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    def get(self, query: str, bypass_scope_check: bool = False) -> Optional[Dict[str, Any]]:
        """Look up response from exact or semantic cache.
        
        If enforce_scope_isolation is enabled, order-specific queries obligatorily
        bypass the cache to guarantee real-time database reads.
        """
        # 1. Automatic Policy Invalidation Check
        self.check_and_invalidate_policy_cache()

        # 2. Scope Isolation Check
        if self.enforce_scope_isolation and not bypass_scope_check:
            if self.is_order_specific(query):
                self.bypasses += 1
                self.misses += 1
                return None

        cleaned = preprocess_arabic(query)

        # 3. Exact match
        if cleaned in self.exact_cache:
            entry = self.exact_cache[cleaned]
            if entry.get("policy_hash") == self.current_policy_hash:
                self.hits += 1
                return entry["response"]
            else:
                del self.exact_cache[cleaned]
                self.invalidations += 1

        # 4. Semantic token similarity
        q_tokens = self._tokenize(query)
        best_score = 0.0
        best_match = None

        for item in self.indexed_queries:
            if item.get("policy_hash") != self.current_policy_hash:
                continue

            sim = self._jaccard_similarity(q_tokens, item["tokens"])
            if sim > best_score:
                best_score = sim
                best_match = item["response"]

        if best_score >= self.similarity_threshold and best_match:
            self.hits += 1
            return best_match

        self.misses += 1
        return None

    def set(
        self,
        query: str,
        response: Dict[str, Any],
        save: bool = True,
        force: bool = False
    ):
        """Store query and resolution response in cache, tagged with current policy hash.
        
        Guarantees:
        - Order-specific queries are bypassed and not cached (unless forced).
        - Responses containing write actions (refund, cancellation, etc.) are never cached.
        """
        # Scope Isolation: Do not cache order-specific queries
        if self.enforce_scope_isolation and not force:
            if self.is_order_specific(query):
                self.bypasses += 1
                return

        # Backend Guardrail: Never cache responses that execute write tools
        tool_calls = response.get("tool_calls", [])
        has_write = any(
            isinstance(c, dict) and (c.get("tool") in WRITE_TOOLS or c.get("name") in WRITE_TOOLS)
            for c in tool_calls
        )
        if has_write:
            return

        cleaned = preprocess_arabic(query)
        entry = {
            "response": response,
            "policy_hash": self.current_policy_hash
        }
        self.exact_cache[cleaned] = entry

        tokens = self._tokenize(query)
        self.indexed_queries.append({
            "query": query,
            "cleaned": cleaned,
            "tokens": list(tokens),
            "response": response,
            "policy_hash": self.current_policy_hash
        })
        if save and self.cache_file:
            self._save()

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0

    @property
    def stats(self) -> Dict[str, Any]:
        """Detailed runtime metrics for monitoring and transparency."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "bypasses": self.bypasses,
            "invalidations": self.invalidations,
            "hit_rate": round(self.hit_rate, 4),
            "cached_entries": len(self.exact_cache),
            "current_policy_hash": self.current_policy_hash,
            "enforce_scope_isolation": self.enforce_scope_isolation
        }
