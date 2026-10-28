
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
        "SECRET_KEY": "unit-test-secret-key",
        "DEMO_VOTER_PASSWORD": "test-voter-password",
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


def issue_as_voter(client, voter_reference):
    login = client.post("/api/auth/login", json={
        "voter_reference": voter_reference,
        "password": "test-voter-password",
    })
    if login.status_code != 200:
        return login
    return client.post("/api/credentials/issue", json={}, headers={
        "X-CSRF-Token": login.json["csrf_token"]
    })


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "success"


def test_issue_credential(client):
    response = issue_as_voter(client, "voter-1")

    assert response.status_code == 201
    assert response.json["credential"]


def test_ineligible_voter_cannot_get_credential(client):
    response = issue_as_voter(client, "voter-2")

    assert response.status_code == 401


def test_credential_cannot_be_issued_twice(client):
    first = issue_as_voter(client, "voter-1")
    second = issue_as_voter(client, "voter-1")

    assert first.status_code == 201
    assert second.status_code == 409


def test_vote_is_accepted_and_encrypted(client):
    issued = issue_as_voter(client, "voter-1")
    credential = issued.json["credential"]

    response = client.post(
        "/api/ballots",
        json={
            "credential": credential,
            "vote": {"candidate": "candidate-A"},
        },
    )

    assert response.status_code == 201

    # Verify encryption inside the test only. No decrypt API is exposed.
    with client.application.app_context():
        ballot = db.session.query(Ballot).one()
        assert ballot.encrypted_vote != b'{"candidate":"candidate-A"}'
        plaintext = Fernet(client.application.config["VOTING_ENCRYPTION_KEY"]).decrypt(ballot.encrypted_vote)
        assert plaintext == b'{"candidate":"candidate-A"}'


def test_credential_cannot_be_reused(client):
    issued = issue_as_voter(client, "voter-1")
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


def test_anonymous_issuance_blocked(client):
    response = client.post("/api/credentials/issue", json={"voter_reference": "voter-1"})
    assert response.status_code == 401


def test_wrong_demo_password_blocked(client):
    response = client.post("/api/auth/login", json={"voter_reference": "voter-1", "password": "wrong"})
    assert response.status_code == 401


def test_issuance_csrf_required(client):
    response = client.post("/api/auth/login", json={"voter_reference": "voter-1", "password": "test-voter-password"})
    assert response.status_code == 200
    assert client.post("/api/credentials/issue", json={}).status_code == 403


@pytest.mark.parametrize("vote", [
    {"candidate": "candidate-Z"},
    {"candidate": 123},
    {"candidate": "candidate-A", "extra": "bad"},
    {"preferences": [1, 2, 3]},
    {},
])
def test_invalid_vote_does_not_consume_credential(client, vote):
    credential = issue_as_voter(client, "voter-1").json["credential"]
    bad = client.post("/api/ballots", json={"credential": credential, "vote": vote})
    assert bad.status_code == 400
    good = client.post("/api/ballots", json={"credential": credential, "vote": {"candidate": "candidate-A"}})
    assert good.status_code == 201


def test_session_lifetime_configured(client):
    from datetime import timedelta

    assert client.application.config["PERMANENT_SESSION_LIFETIME"] == timedelta(minutes=15)
    assert client.application.config["SESSION_REFRESH_EACH_REQUEST"] is False

    login = client.post("/api/auth/login", json={
        "voter_reference": "voter-1",
        "password": "test-voter-password",
    })
    assert login.status_code == 200

    with client.session_transaction() as sess:
        assert sess.permanent is True
        assert sess.get("voter_id") is not None


def test_logout_requires_csrf(client):
    login = client.post("/api/auth/login", json={
        "voter_reference": "voter-1",
        "password": "test-voter-password",
    })
    assert login.status_code == 200

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 403


def test_valid_logout_clears_session(client):
    login = client.post("/api/auth/login", json={
        "voter_reference": "voter-1",
        "password": "test-voter-password",
    })
    assert login.status_code == 200

    token = login.json["csrf_token"]
    logout = client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": token},
    )
    assert logout.status_code == 200

    rejected = client.post(
        "/api/credentials/issue",
        json={},
        headers={"X-CSRF-Token": token},
    )
    assert rejected.status_code == 401
