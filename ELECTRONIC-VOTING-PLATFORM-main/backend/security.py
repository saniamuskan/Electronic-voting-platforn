import hashlib
import secrets


def generate_voting_credential():
    """Generate a cryptographically secure random credential."""
    return secrets.token_urlsafe(32)


def hash_voting_credential(credential):
    """Calculate the SHA-256 digest of a voting credential."""
    if not isinstance(credential, str) or not credential:
        raise ValueError("A non-empty credential is required")

    return hashlib.sha256(
        credential.encode("utf-8")
    ).hexdigest()