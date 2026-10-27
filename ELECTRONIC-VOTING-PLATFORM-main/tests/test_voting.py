
import pytest
from cryptography.fernet import Fernet

from backend.app import create_app
from backend.models import db, Voter, VotingCredential, Ballot


@pytest.fixture
def client(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": (
            "sqlite:///" + str(tmp_path / "test_voting.db")
        ),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "VOTING_ENCRYPTION_KEY": Fernet.generate_key(),
    })

    with app.app_context():
        db.drop_all()
        db.create_all()

        db.session.add_all([
            Voter(
                voter_reference="voter-1",
                is_eligible=True,
                credential_issued=False,
            ),
            Voter(
                voter_reference="voter-2",
                is_eligible=False,
                credential_issued=False,
            ),
        ])
        db.session.commit()

    with app.test_client() as test_client:
        yield test_client

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "success"


def test_issue_credential(client):
    response = client.post(
        "/api/credentials/issue",
        json={"voter_reference": "voter-1"},
    )

    assert response.status_code == 201
    assert response.json["credential"]


def test_ineligible_voter_cannot_get_credential(client):
    response = client.post(
        "/api/credentials/issue",
        json={"voter_reference": "voter-2"},
    )

    assert response.status_code == 403


def test_credential_cannot_be_issued_twice(client):
    payload = {"voter_reference": "voter-1"}

    first = client.post("/api/credentials/issue", json=payload)
    second = client.post("/api/credentials/issue", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


def test_vote_is_accepted_and_encrypted(client):
    issued = client.post(
        "/api/credentials/issue",
        json={"voter_reference": "voter-1"},
    )
    credential = issued.json["credential"]

    response = client.post(
        "/api/ballots",
        json={
            "credential": credential,
            "vote": {"candidate": "candidate-A"},
        },
    )

    assert response.status_code == 201

    # The test-only endpoint verifies that the ciphertext
    # can be decrypted using the configured test key.
    with client.application.app_context():
        ballot = db.session.query(Ballot).one()
        assert ballot.encrypted_vote != b'{"candidate":"candidate-A"}'
        ballot_id = ballot.id

    decrypted = client.post(
        "/api/ballots/decrypt",
        json={"ballot_id": ballot_id},
    )

    assert decrypted.status_code == 200
    assert decrypted.json["vote"] == {"candidate": "candidate-A"}


def test_credential_cannot_be_reused(client):
    issued = client.post(
        "/api/credentials/issue",
        json={"voter_reference": "voter-1"},
    )
    credential = issued.json["credential"]

    payload = {
        "credential": credential,
        "vote": {"candidate": "candidate-A"},
    }

    first = client.post("/api/ballots", json=payload)
    second = client.post("/api/ballots", json=payload)

    assert first.status_code == 201
    assert second.status_code == 401


def test_invalid_credential_is_rejected(client):
    response = client.post(
        "/api/ballots",
        json={
            "credential": "invalid-credential",
            "vote": {"candidate": "candidate-A"},
        },
    )

    assert response.status_code == 401


def test_missing_vote_is_rejected(client):
    response = client.post(
        "/api/ballots",
        json={"credential": "some-credential"},
    )

    assert response.status_code == 400
