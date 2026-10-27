import pytest

from backend.security import (
    generate_voting_credential,
    hash_voting_credential,
)


def test_credential_generation():
    credential = generate_voting_credential()

    assert isinstance(credential, str)
    assert len(credential) >= 32


def test_credentials_are_unique():
    credentials = {
        generate_voting_credential()
        for _ in range(1000)
    }

    assert len(credentials) == 1000


def test_credential_hashing():
    credential = generate_voting_credential()
    digest = hash_voting_credential(credential)

    assert len(digest) == 64
    assert digest != credential
    assert digest == hash_voting_credential(credential)


def test_empty_credential_rejected():
    with pytest.raises(ValueError):
        hash_voting_credential("")