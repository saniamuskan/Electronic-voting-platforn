# Electronic Voting Platform — Demonstration Prototype

Flask + SQLite + Fernet demonstration of one-use voting credentials and a single-choice ballot. This is not a production voting system or official voter identity verification.

## Run locally (Windows PowerShell)

From this folder, activate an existing virtual environment that has `requirements.txt` installed, then configure a **development-only** password:

```powershell
$env:DEMO_VOTER_PASSWORD = "choose-a-new-private-demo-password"
python -m backend.seed_demo voter-demo-new-001
python -m pytest tests/ -q
python -m backend.app
```

Browse to http://127.0.0.1:5000. Enter a test voter reference already seeded in your local database and the demo password. Use only disposable test data. Do not put the password into source code, screenshots or GitHub.

**Important:** This shared password is only a local demonstration access gate, not personal identity verification. No public deployment is suitable without an actual authentication provider, TLS, rate limiting, secure key management and independent review.

## Cryptography and sensitive files

Ballots are encrypted with Fernet. The application uses `VOTING_ENCRYPTION_KEY` if provided, otherwise stores a locally generated development key in `instance/voting.key`. Keep the key private. `instance/` and `.env` are Git-ignored. A prior shared ZIP contained a key and database; do not publish either again. If exposed, consider both compromised. Rotating a key will prevent decrypting any ballots encrypted under the old key unless those are migrated or deliberately discarded.

## Evidence and testing

`python -m pytest tests/ -q` runs the current code's tests. The prior 53-test count referred to a separate development branch; use the current test output when documenting the integrated system. No decryption HTTP endpoint is exposed. The candidate set for this prototype is A, B and C, with a single-choice ballot.
