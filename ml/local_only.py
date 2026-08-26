"""
Enforces PHIRE's local-only network boundary for every client that talks
to a local service (Ollama, Neo4j): the connection must actually resolve
to localhost, not just have "localhost" appear somewhere in its URI.

One shared implementation, not one ad hoc check per caller — a prior
per-file version used str.startswith()/substring checks (e.g. "does the
host start with 'http://localhost'"), which a hostname like
"http://localhost.attacker.example" satisfies while resolving to a
genuinely remote host. Found via code review, not hypothetical: this
would have silently defeated the privacy boundary on a misconfigured
OLLAMA_HOST/NEO4J_URI env var, for a project whose core invariant is "no
cloud APIs, no external LLM calls, ever."
"""

from urllib.parse import urlparse

_ALLOWED_HOSTNAMES = {"localhost", "127.0.0.1", "::1"}


def require_localhost(uri: str) -> None:
    """Raise ValueError unless uri's actual hostname is localhost/127.0.0.1/::1.

    Parses the URI and checks its hostname component specifically —
    the only correct way to do this, since prefix/substring checks on the
    raw string are bypassable by a hostname or query string that merely
    contains "localhost" without the connection actually going there.
    """
    hostname = urlparse(uri).hostname
    if hostname not in _ALLOWED_HOSTNAMES:
        raise ValueError(f"Only a localhost URI is permitted, got: {uri!r}")
