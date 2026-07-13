import re
import math

# Named-token patterns — matched before entropy to avoid duplicate findings.
# Any line that matches here is CRITICAL; entropy scan is skipped for that line.
SIGNATURE_REGEX: dict[str, str] = {
    # VCS / CI tokens
    "GitHub Classic PAT":       r"ghp_[a-zA-Z0-9]{36}",
    "GitHub Fine-grained PAT":  r"github_pat_[a-zA-Z0-9_]{82}",
    "GitHub OAuth":             r"gho_[a-zA-Z0-9]{36}",
    "GitHub Actions":           r"ghs_[a-zA-Z0-9]{36}",
    "GitHub Refresh":           r"ghr_[a-zA-Z0-9]{36}",
    "GitLab PAT":               r"glpat-[a-zA-Z0-9\-_]{20,}",
    # Cloud providers
    "AWS Access Key":           r"AKIA[0-9A-Z]{16}",
    "AWS Secret Key":           r"(?i)aws.{0,10}secret.{0,10}['\"][a-zA-Z0-9+/]{40}['\"]",
    "Google API Key":           r"AIza[0-9A-Za-z\-_]{35}",
    "Google Service Account":   r'"type"\s*:\s*"service_account"',
    "Azure SAS Token":          r"sig=[a-zA-Z0-9%]{30,}",
    # Payment / comms
    "Stripe Secret Key":        r"sk_live_[a-zA-Z0-9]{24,}",
    "Stripe Test Key":          r"sk_test_[a-zA-Z0-9]{24,}",
    "Stripe Publishable Key":   r"pk_live_[a-zA-Z0-9]{24,}",
    "SendGrid API Key":         r"SG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43}",
    "Twilio Account SID":       r"AC[a-f0-9]{32}",
    "Twilio Auth Token":        r"(?i)twilio.{0,10}['\"][a-f0-9]{32}['\"]",
    "Mailgun API Key":          r"key-[a-zA-Z0-9]{32}",
    # AI APIs
    "OpenAI API Key":           r"sk-[a-zA-Z0-9]{20}T3BlbkFJ[a-zA-Z0-9]{20}",
    "OpenAI Project Key":       r"sk-proj-[a-zA-Z0-9_\-]{50,}",
    "Anthropic API Key":        r"sk-ant-[a-zA-Z0-9_\-]{93,}",
    "HuggingFace Token":        r"hf_[a-zA-Z0-9]{34}",
    # Package registries
    "npm Token":                r"npm_[a-zA-Z0-9]{36}",
    "PyPI Token":               r"pypi-[a-zA-Z0-9_\-]{30,}",
    # Messaging
    "Slack Bot Token":          r"xoxb-[0-9]{11,13}-[0-9]{11,13}-[a-zA-Z0-9]{24}",
    "Slack User Token":         r"xoxp-[0-9]{11,13}-[0-9]{11,13}-[a-zA-Z0-9]{24}",
    "Discord Bot Token":        r"[MN][a-zA-Z0-9]{23}\.[a-zA-Z0-9\-_]{6}\.[a-zA-Z0-9\-_]{27}",
    # Keys / certs
    "Private Key Block":        r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
    "Generic Assignment":       r"(?i)(api[_-]?key|secret[_-]?key|auth[_-]?token|private[_-]?key|access[_-]?token)\s*=\s*['\"][a-zA-Z0-9_\-\+=\/]{20,}['\"]",
}

# Strings matching these patterns are NOT secrets — skip entropy check
_ALLOWLIST_RE: list[re.Pattern] = [
    re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I),  # UUID
    re.compile(r"^[0-9a-f]{32}$", re.I),    # MD5 hex
    re.compile(r"^[0-9a-f]{40}$", re.I),    # SHA-1 hex
    re.compile(r"^[0-9a-f]{64}$", re.I),    # SHA-256 hex
    re.compile(r"^[0-9a-f]{128}$", re.I),   # SHA-512 hex
    re.compile(r"^\d+\.\d+\.\d+"),          # semver (1.2.3 / 1.2.3-rc1)
    re.compile(r"^[A-Za-z0-9+/]{1,4}={0,2}$"),  # very short base64 — not a secret
    re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*([.-][a-zA-Z0-9_]+)+$"),  # qualified names / URLs
]

_ENTROPY_THRESHOLD = 4.8
_MIN_SECRET_LENGTH = 24


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in (s.count(ch) for ch in set(s)))


def _is_allowlisted(literal: str) -> bool:
    return any(p.match(literal) for p in _ALLOWLIST_RE)


def analyze_entropy_and_secrets(code_data: str) -> list:
    findings: list = []
    lines = code_data.splitlines()

    for idx, line in enumerate(lines, 1):
        regex_matched = False

        # 1. Named-pattern (signature) check — CRITICAL; suppresses entropy for this line
        for name, pattern in SIGNATURE_REGEX.items():
            if re.search(pattern, line):
                findings.append({
                    "line_number": idx,
                    "anomaly_type": "Hardcoded Secret",
                    "severity": "CRITICAL",
                    "description": f"{name} detected. Hardcoded credentials are exposed in source history.",
                    "code_snippet": line.strip(),
                })
                regex_matched = True
                break  # one finding per line is enough

        if regex_matched:
            continue

        # 2. Entropy scan — only runs when no named pattern matched
        literals = re.findall(r"['\"]([a-zA-Z0-9_\-\+=\/]{%d,})['\"]" % _MIN_SECRET_LENGTH, line)
        for literal in literals:
            if _is_allowlisted(literal):
                continue
            score = _shannon_entropy(literal)
            if score > _ENTROPY_THRESHOLD:
                findings.append({
                    "line_number": idx,
                    "anomaly_type": "High Entropy Credential",
                    "severity": "HIGH",
                    "description": (
                        f"High-entropy string (Shannon score {score:.2f} > {_ENTROPY_THRESHOLD}). "
                        f"Likely an API key, bearer token, or secret. Move to an environment variable."
                    ),
                    "code_snippet": line.strip(),
                })
                break  # one entropy finding per line

    return findings
