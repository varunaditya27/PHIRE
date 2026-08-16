"""
Unit tests for ml/local_only.py's require_localhost — including the exact
bypass cases a prior prefix/substring-based check let through (found via
code review, not hypothetical).
"""

import pytest

from ml.local_only import require_localhost


@pytest.mark.parametrize("uri", [
    "http://localhost:11434",
    "http://127.0.0.1:11434",
    "bolt://localhost:7687",
    "bolt://127.0.0.1:7687",
    "bolt://[::1]:7687",
])
def test_require_localhost_accepts_real_localhost_uris(uri):
    require_localhost(uri)  # must not raise


@pytest.mark.parametrize("uri", [
    "http://evil.com",
    # A prior prefix-based check ("does the host start with
    # 'http://localhost'") let this through, since the string literally
    # starts with that prefix while resolving to a genuinely remote host.
    "http://localhost.attacker.example:11434",
    # A prior substring check ("does 'localhost' appear anywhere in the
    # URI") let this through too.
    "bolt://evil.com/?x=localhost",
    "http://notlocalhost:11434",
])
def test_require_localhost_rejects_bypass_attempts(uri):
    with pytest.raises(ValueError, match="localhost"):
        require_localhost(uri)
