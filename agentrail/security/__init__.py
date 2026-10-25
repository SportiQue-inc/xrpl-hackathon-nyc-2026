"""Security layer: who may call what, whose key signs what, and a tamper-evident record of it.

  secrets    environment / *_FILE secret lookup (Docker and Kubernetes secrets)
  keystore   per-owner key stores; the local store is the demo, KmsKeyStore is the production seam
  devices    the client side: participant keyring, institution vault, approver and login devices
  auth       challenge-signed login and short-lived HS256 access tokens
  rbac       roles and the route policy table; any route without a rule is denied
  cosign     treasury approvals: each approver signs on their own device, nonce + expiry + one per approver
  audit      hash-chained event log, verification and ledger anchoring
  http       CORS allow-list, rate limit, security headers, access audit
  masking    secrets never reach logs or the event stream
"""
