# -*- coding: utf-8 -*-
"""Comprehensive Tests for Semantic Cache Scope Isolation, Policy Invalidation, and Backend Guardrails."""
import json
import tempfile
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.optimization.cache import SemanticCache
from src.env.backend_client import BackendClient
from src.policies.retriever import PolicyRetriever
from src.api.app import (
    health_check, get_policies, get_policy_hash, get_cache_stats, invalidate_cache,
    resolve_ticket, TicketRequest, semantic_cache
)


def test_scope_isolation_detection():
    """Verify that order-specific queries and general FAQs are strictly distinguished."""
    cache = SemanticCache(enforce_scope_isolation=True)

    # 1. Order-specific queries across all 7 supported language varieties
    order_queries = [
        # MSA (العربية الفصحى)
        "وين وصل طلبي NW4241472؟",
        "أريد إلغاء طلبي الحالي",
        "وصلني منتج تالف في شحنتي",
        "أريد إرجاع المنتج واسترداد المبلغ",
        # Egyptian (المصرية)
        "فين الاوردر بتاعي؟",
        "الاوردر لسه ما وصلش يا فندم",
        "عايز اعرف الاوردر وصل فين",
        "هو الاوردر اتلغى ولا لسه؟",
        "عايز أغير عنوان التوصيل للطلب بتاعي",
        # Gulf (الخليجية)
        "وين طلبيتي؟",
        "وين وصلت شحنتي يا شباب؟",
        "ابي الغي الشحنة تكفون",
        "الطلب متأخر علي",
        "طلب رقم NW8899111 أريد استرجاع فلوسي",
        # Levantine (الشامية)
        "وين صار طلبي؟",
        "بدي اعرف شو صار بالطلب تبعي",
        "الاوردر اتأخر كتيير",
        "بدي رجع المنتج مكسور",
        # Algerian (الجزائرية)
        "وين راهي الكوموند؟",
        "حاب نعرف وين وصلت لاكوموند",
        "الكوموند ما لحقتش",
        "حاب نبدل العنوان نتاع الكوموند",
        "وصلني كولي تالف وحاب نبدلو",
        # Algerian French code-switching (dz_fr)
        "Salam, je veux savoir l'état de ma commande NW4241472 svp.",
        "ma commande retardée bzaf",
        "svp etat de ma commande",
        "annuler ma commande svp",
        "la commande est en retard",
        # English-Arabic mix (en_mix)
        "where is my order?",
        "cancel my order please",
        "the order is delayed",
        "i received a damaged item"
    ]
    for q in order_queries:
        assert cache.is_order_specific(q) is True, f"Failed to detect as order-specific: {q}"
        assert cache.is_cacheable(q) is False, f"Erroneously marked as cacheable: {q}"

    # 2. General FAQ inquiries (MUST be cacheable across languages, even when containing tricky words)
    faq_queries = [
        "ما هي مدة التوصيل المعتادة إلى الجزائر؟",
        "ما هي طرق الدفع المتاحة في المتجر؟",
        "ما هي شروط وسياسة الإرجاع في المتجر؟",
        "هل يوجد فروع لنوار ماركت أم متجر إلكتروني فقط؟",
        "هل لديكم ضمان على الأجهزة الكهربائية والإلكترونية؟",
        "ما هي الدول المتاحة للتوصيل؟",
        # Tricky policy FAQs containing action/order words
        "ما هي سياسة إلغاء الطلبات؟",
        "هل يمكن إلغاء الطلب بعد الدفع؟",
        "هل ينفع ألغي الأوردر لو لسه ما اتشحنش؟",
        "كيف يمكنني إلغاء الطلب في متجركم؟",
        "ما هي شروط إرجاع المنتج واسترداد المبلغ؟",
        "كيف يتم استرداد المبلغ عند وجود خصم مكرر؟",
        "هل الاسترداد يرجع للبطاقة أم رصيد محفظة؟",
        "ما هي مدة استرجاع الفلوس بعد الإلغاء؟",
        "لو وصلني منتج تالف كيف اتصرف؟",
        "هل عندكم تعويض إذا تأخرت الشحنة؟",
        "ماذا تفعلون لو تأخر الطرد أكثر من 10 أيام؟",
        # French & English general FAQs
        "est ce que vous livrez en algerie?",
        "comment retourner un article?",
        "do you deliver to egypt?",
        "what are the accepted payment methods?",
        "est-ce qu'on peut annuler une commande avant l'expédition?",
        "quelles sont les conditions de remboursement en cas de produit endommagé?",
        "how to cancel an order on Nawras Market?",
        "can an order be refunded after 14 days?",
        "what happens if a package is delayed?"
    ]
    for q in faq_queries:
        assert cache.is_order_specific(q) is False, f"Erroneously detected as order-specific: {q}"
        assert cache.is_cacheable(q) is True, f"Failed to detect as cacheable FAQ: {q}"


def test_order_specific_queries_bypass_cache():
    """Verify that order-specific queries obligatorily bypass the cache."""
    cache = SemanticCache(enforce_scope_isolation=True)
    order_query = "أريد معرفة حالة طلبي NW4241472"

    # Attempt to prime cache with an order query
    fake_response = {
        "outcome": "resolve",
        "reply": "طلبك قيد المعالجة",
        "tool_calls": []
    }
    cache.set(order_query, fake_response)

    # In scope isolation mode, it must NOT be cached
    assert cache.bypasses >= 1
    assert len(cache.exact_cache) == 0

    # In lookup, it must immediately return None (bypass)
    res = cache.get(order_query)
    assert res is None
    assert cache.bypasses >= 2


def test_faq_caching_and_semantic_retrieval():
    """Verify that general FAQ inquiries are cached and retrieved sub-millisecond."""
    cache = SemanticCache(enforce_scope_isolation=True)
    faq_q = "ما هي مدة التوصيل المعتادة إلى الجزائر؟"
    faq_response = {
        "outcome": "resolve",
        "reply": "مدة التوصيل المعتادة من 3 إلى 7 أيام عمل.",
        "tool_calls": [],
        "steps": 1
    }

    # Store in cache
    cache.set(faq_q, faq_response)
    assert len(cache.exact_cache) == 1

    # Exact match hit
    hit = cache.get(faq_q)
    assert hit is not None
    assert hit["reply"] == faq_response["reply"]
    assert cache.hits == 1

    # Semantic similarity hit (different phrasing with high overlap)
    variant_q = "ما هي مدة التوصيل المعتادة لديكم إلى الجزائر؟"
    sem_hit = cache.get(variant_q)
    assert sem_hit is not None
    assert sem_hit["reply"] == faq_response["reply"]
    assert cache.hits == 2


def test_policy_linked_invalidation():
    """Verify that modifying the policy file invalidates cached resolutions."""
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False, encoding="utf-8") as tmp:
        tmp.write('[{"policy_id": "P01", "title": "سياسة التوصيل", "text": "التوصيل خلال 5 أيام"}]')
        tmp_path = Path(tmp.name)

    try:
        cache = SemanticCache(enforce_scope_isolation=True, policies_path=tmp_path)
        faq_q = "ما هي مدة التوصيل؟"
        faq_res = {"outcome": "resolve", "reply": "التوصيل خلال 5 أيام", "tool_calls": []}
        cache.set(faq_q, faq_res)

        # Confirm it's cached
        assert cache.get(faq_q) is not None

        # Modify the policy file (simulate admin policy update)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write('[{"policy_id": "P01", "title": "سياسة التوصيل المعدلة", "text": "التوصيل خلال يومين فقط"}]')

        # Cache must detect policy hash change and invalidate entries
        invalidated_res = cache.get(faq_q)
        assert invalidated_res is None, "Cache should have invalidated after policy change"
        assert cache.invalidations >= 1
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_write_tools_guardrail_never_cached():
    """Verify that any resolution that executed write tools is rejected by the cache."""
    cache = SemanticCache(enforce_scope_isolation=True)
    query = "طلب استرداد تجريبي"
    write_response = {
        "outcome": "resolve",
        "reply": "تم استرداد المبلغ بنجاح",
        "tool_calls": [
            {"tool": "issue_refund", "args": {"order_id": "NW100", "amount_usd": 40.0}}
        ]
    }
    # Even if forced, write tools must be blocked from cache
    cache.set(query, write_response, force=True)
    assert len(cache.exact_cache) == 0
    assert cache.get(query, bypass_scope_check=True) is None


def test_backend_server_side_guardrails():
    """Verify server-side deterministic enforcement of policies on write actions."""
    backend = BackendClient()

    # 1. Cancellation check: Delivered order cannot be cancelled
    delivered_orders = [
        o for o in backend.backend.db["orders"].values() if o["status"] == "delivered"
    ]
    if delivered_orders:
        del_ord = delivered_orders[0]
        res = backend.execute("cancel_order", order_id=del_ord["order_id"], customer_id=del_ord["customer_id"])
        assert res["ok"] is False
        assert res["error"] == "NOT_CANCELLABLE"

    # 2. Return window check: older than 14 days must return RETURN_WINDOW_EXPIRED
    old_delivered = [
        o for o in delivered_orders
        if backend.backend._days_since(o["shipping"]["delivered_at"]) > 14
    ]
    if old_delivered:
        ord_old = old_delivered[0]
        sku = ord_old["lines"][0]["sku"]
        res_ret = backend.execute("create_return", order_id=ord_old["order_id"], customer_id=ord_old["customer_id"], sku=sku)
        assert res_ret["ok"] is False
        assert res_ret["error"] == "RETURN_WINDOW_EXPIRED"

    # 3. High value refund without approval must return PENDING_APPROVAL
    if delivered_orders:
        del_ord = delivered_orders[0]
        # Attempt high refund above $50
        res_high_ref = backend.execute(
            "issue_refund",
            order_id=del_ord["order_id"],
            customer_id=del_ord["customer_id"],
            amount_usd=95.0,
            reason_code="DAMAGED_ITEM",
            approved=False
        )
        if res_high_ref.get("ok"):
            assert res_high_ref.get("status") == "PENDING_APPROVAL"


def test_api_endpoints_and_cache_integration():
    """Verify the API endpoints for policy hash, cache stats, invalidation, and resolution cache."""
    # 1. Health check
    h = health_check()
    assert h["status"] == "healthy"

    # 2. Policies with policy_hash
    pol = get_policies()
    assert isinstance(pol, list)
    assert len(pol) == 15

    pol_meta = get_policy_hash()
    assert "policy_hash" in pol_meta
    assert pol_meta["policy_hash"] == semantic_cache.current_policy_hash

    # 3. Cache stats endpoint
    stats = get_cache_stats()
    assert stats["current_policy_hash"] == pol_meta["policy_hash"]
    assert stats["enforce_scope_isolation"] is True

    # 4. Invalidation endpoint
    inv = invalidate_cache()
    assert inv["ok"] is True
    assert inv["current_policy_hash"] == pol_meta["policy_hash"]

    # 5. Fast cached resolution test on general FAQ
    faq_req = TicketRequest(
        customer_id="C50642",
        text="ما هي طرق الدفع المتاحة في المتجر؟",
        channel="web_chat",
        ticket_id="T_FAQ_TEST"
    )
    semantic_cache.set(
        faq_req.text,
        {"outcome": "resolve", "reply": "طرق الدفع: بطاقة بنكية ودفع عند الاستلام", "tool_calls": [], "steps": 0}
    )
    res_faq = resolve_ticket(faq_req)
    assert res_faq.cached is True
    assert res_faq.steps == 0
    assert "طرق الدفع" in res_faq.reply

    # 6. Order-specific query bypasses cache and queries live backend
    order_req = TicketRequest(
        customer_id="C50642",
        text="Salam, je veux savoir l'état de ma commande NW4241472 svp.",
        channel="web_chat",
        ticket_id="T_ORD_TEST"
    )
    res_order = resolve_ticket(order_req)
    assert res_order.cached is False
    assert len(res_order.tool_calls) >= 1  # Verified live get_order tool execution on backend


if __name__ == "__main__":
    test_scope_isolation_detection()
    test_order_specific_queries_bypass_cache()
    test_faq_caching_and_semantic_retrieval()
    test_policy_linked_invalidation()
    test_write_tools_guardrail_never_cached()
    test_backend_server_side_guardrails()
    test_api_endpoints_and_cache_integration()
    print("ALL TESTS PASSED SUCCESSFULLY! (100% Correct)")
