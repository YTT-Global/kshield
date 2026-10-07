"""Regression tests for the graph-aware access control engine (M2/M4).

Run:  SQLITE_FALLBACK=true python -m pytest tests/test_access_control.py -v
"""
from app.engine.graph_builder import build_repo_graph
from app.engine.access_control import check_access_control


def _findings(code, filename="routes.py"):
    g = build_repo_graph([(filename, code)])
    return check_access_control(g.routes)


class TestUnrelatedDependencyGap:
    # This is the specific bug M2 fixes: ast_rules.py treats any Depends() as
    # a guard. These tests lock in that a DB-session-only dependency does NOT
    # count as authentication.

    def test_db_session_only_dependency_still_flagged(self):
        code = """
from fastapi import Depends
@router.post("/scan")
async def scan(db=Depends(get_db_session)):
    pass
"""
        r = _findings(code)
        assert len(r) == 1
        assert r[0]["anomaly_type"] == "Broken Access Control"
        assert "get_db_session" in r[0]["description"]

    def test_no_dependency_at_all_flagged(self):
        code = "@router.post('/x')\nasync def x(): pass\n"
        r = _findings(code)
        assert len(r) == 1


class TestGenuineGuardsNotFlagged:
    def test_signature_auth_dependency_not_flagged(self):
        code = """
from fastapi import Depends
@router.get("/profile")
async def profile(user=Depends(get_current_user)):
    pass
"""
        assert _findings(code) == []

    def test_decorator_dependencies_auth_not_flagged(self):
        code = """
from fastapi import Depends
@router.post("/admin/reset", dependencies=[Depends(require_auth)])
async def reset(): pass
"""
        assert _findings(code) == []

    def test_jwt_named_guard_not_flagged(self):
        code = "@router.get('/x')\nasync def x(user=Depends(verify_jwt_token)): pass\n"
        assert _findings(code) == []

    def test_public_health_path_exempt(self):
        code = "@router.get('/health')\nasync def health(): pass\n"
        assert _findings(code) == []

    def test_public_docs_path_exempt(self):
        code = "@router.get('/docs')\nasync def docs(): pass\n"
        assert _findings(code) == []

    def test_tenant_context_dependency_not_flagged(self):
        # Real bug found in the ChatSync pilot: get_tenant_context parses a
        # real JWT and raises 401 on failure — genuine auth — but "tenant"
        # wasn't in the keyword list, so it read as an unrecognized dependency.
        code = "@router.patch('/{bot_id}')\ndef update_bot(bot_id: str, tenant=Depends(get_tenant_context)): pass\n"
        assert _findings(code) == []

    def test_body_level_signature_verification_counts_as_guard(self):
        # Real bug found in the retail-quick-commerce pilot: a Razorpay
        # webhook calls verify_webhook_signature(body, signature) in its own
        # body — a webhook can never carry Depends(get_current_user) since
        # it's called by a third party's servers, not a logged-in user, but
        # it can still be genuinely protected via signature verification.
        code = """
@router.post("/payments/webhook")
async def razorpay_webhook(request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=400)
"""
        assert _findings(code) == []

    def test_unrelated_body_call_does_not_count_as_guard(self):
        # Confirms the fix above is scoped to signature/hmac-shaped calls,
        # not "any function call in the body suppresses the finding".
        code = """
@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request):
    body = await request.form()
    bot = await get_bot_config(None)
    return await generate_reply(bot, body)
"""
        r = _findings(code)
        assert len(r) == 1
        assert r[0]["anomaly_type"] == "Broken Access Control"


class TestSeverityLadder:
    def test_get_no_sensitivity_is_medium(self):
        code = "@router.get('/widgets')\nasync def widgets(): pass\n"
        r = _findings(code)
        assert r[0]["severity"] == "MEDIUM"

    def test_mutation_no_sensitivity_is_high(self):
        code = "@router.post('/comments')\nasync def comments(): pass\n"
        r = _findings(code)
        assert r[0]["severity"] == "HIGH"

    def test_get_with_sensitivity_escalates_to_high(self):
        code = "@router.get('/admin/users')\nasync def list_users(): pass\n"
        r = _findings(code)
        assert r[0]["severity"] == "HIGH"

    def test_mutation_with_sensitivity_escalates_to_critical(self):
        code = "@router.delete('/admin/users/{id}')\nasync def delete_user(id: str): pass\n"
        r = _findings(code)
        assert r[0]["severity"] == "CRITICAL"

    def test_payment_route_is_critical(self):
        code = "@router.post('/payment/charge')\nasync def charge(): pass\n"
        r = _findings(code)
        assert r[0]["severity"] == "CRITICAL"

    def test_sensitive_but_guarded_route_not_flagged_regardless_of_severity(self):
        code = """
from fastapi import Depends
@router.get("/admin/users")
async def list_users(user=Depends(get_current_user)):
    pass
"""
        assert _findings(code) == []
