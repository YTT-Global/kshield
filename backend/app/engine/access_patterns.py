PUBLIC_PATHS: frozenset[str] = frozenset([
    "/", "/health", "/healthz", "/health-check", "/healthcheck",
    "/ping", "/pong", "/ready", "/readiness", "/liveness", "/alive",
    "/docs", "/redoc", "/openapi.json", "/openapi.yaml",
    "/metrics", "/status", "/version", "/info",
    "/favicon.ico", "/robots.txt", "/sitemap.xml",
])

MUTATION_METHODS: frozenset[str] = frozenset(["post", "put", "delete", "patch"])
