from sqlalchemy import inspect

from cryptography.fernet import Fernet

from backend.app import app, _load_voting_encryption_key
from backend.models import db


def test_local_encryption_key_is_persisted(tmp_path):
    key = _load_voting_encryption_key(str(tmp_path))

    assert _load_voting_encryption_key(str(tmp_path)) == key
    Fernet(key)


def test_configured_encryption_key_is_used(tmp_path):
    key = Fernet.generate_key()

    assert _load_voting_encryption_key(str(tmp_path), key) == key
    assert not (tmp_path / "voting.key").exists()


def test_required_database_tables_exist():
    with app.app_context():
        tables = set(inspect(db.engine).get_table_names())

        assert {
            "voters",
            "voting_credentials",
            "ballots"
        }.issubset(tables)


def test_ballots_have_no_direct_voter_reference():
    with app.app_context():
        inspector = inspect(db.engine)

        columns = {
            column["name"]
            for column in inspector.get_columns("ballots")
        }

        assert "encrypted_vote" in columns
        assert "voter_id" not in columns
        assert "voter_reference" not in columns

        foreign_keys = inspector.get_foreign_keys("ballots")
        assert foreign_keys == []