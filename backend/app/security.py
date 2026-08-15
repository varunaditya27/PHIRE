"""
Security and compliance utilities: encryption at rest, request auth,
audit-logging hooks.

Responsibilities (to implement):
- Enforce that no patient health data leaves the local network (no
  outbound calls to third-party APIs from this process).
- Field-level encryption/decryption helpers for sensitive columns
  (see utils/encryption.py for the primitives).
- Request-level audit trail hooks (who accessed what patient data, when) —
  see services/audit_logger.py for the actual log sink.
"""
