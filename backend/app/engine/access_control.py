from app.engine.access_patterns import PUBLIC_PATHS, MUTATION_METHODS
from app.engine.graph_builder import RouteInfo

# Starter list — a name matching any of these is treated as a real auth guard,
# not just "some dependency exists". Deliberately excludes generic words like
# "user" or "session" that show up in unrelated dependencies (get_db_session).
_AUTH_KEYWORDS = (
    "auth", "current_user", "require_auth", "login", "permission",
    "token", "credential", "oauth", "jwt", "authorize", "authenticate",
    "access_control", "verify_user", "tenant", "signature", "hmac",
)

# Path segments that mark a route as touching something worth more than a shrug —
# an unguarded /admin or /payment route is a different kind of problem than an
# unguarded /widgets route, even if both are technically "unauthenticated GET".
_SENSITIVE_PATH_KEYWORDS = (
    "admin", "payment", "billing", "account", "user", "secret", "credential",
    "internal", "config", "export", "delete", "role", "permission", "invoice",
)

# Escalates one step up the ladder when the route also touches sensitive data.
_SEVERITY_ESCALATION = {"MEDIUM": "HIGH", "HIGH": "CRITICAL"}


def _looks_like_auth(name: str, keywords: tuple[str, ...]) -> bool:
    lowered = name.lower()
    return any(keyword in lowered for keyword in keywords)


def _touches_sensitive_data(path: str) -> bool:
    lowered = path.lower()
    return any(keyword in lowered for keyword in _SENSITIVE_PATH_KEYWORDS)


def check_access_control(routes: list[RouteInfo], extra_auth_keywords: tuple[str, ...] = ()) -> list[dict]:
    keywords = _AUTH_KEYWORDS + tuple(extra_auth_keywords)
    findings = []

    for route in routes:
        if route.path in PUBLIC_PATHS:
            continue

        if any(_looks_like_auth(name, keywords) for name in route.guard_names if name):
            continue

        is_mutation = route.method.lower() in MUTATION_METHODS
        severity = "HIGH" if is_mutation else "MEDIUM"

        is_sensitive = _touches_sensitive_data(route.path)
        if is_sensitive:
            severity = _SEVERITY_ESCALATION.get(severity, severity)

        path_hint = f" '{route.path}'" if route.path else ""
        sensitivity_hint = " This route also touches sensitive data." if is_sensitive else ""

        guard_hint = ""
        named_guards = [n for n in route.guard_names if n]
        if named_guards:
            guard_hint = (
                f" It does have a dependency ({', '.join(named_guards)}), "
                f"but that name doesn't look auth-related."
            )

        findings.append({
            "line_number": route.line,
            "anomaly_type": "Broken Access Control",
            "severity": severity,
            "description": (
                f"{route.method} endpoint{path_hint} '{route.handler}' has no authentication guard."
                f"{guard_hint}{sensitivity_hint} Add Depends(get_current_user) or a similarly named auth dependency."
            ),
            "code_snippet": f"def {route.handler}(...):",
            "filename": route.filename,
        })

    return findings
