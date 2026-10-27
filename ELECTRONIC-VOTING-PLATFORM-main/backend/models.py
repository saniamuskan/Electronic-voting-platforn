from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class Voter(db.Model):
    __tablename__ = "voters"

    id = db.Column(db.Integer, primary_key=True)
    voter_reference = db.Column(
        db.String(100), unique=True, nullable=False
    )
    is_eligible = db.Column(
        db.Boolean, nullable=False, default=True
    )
    credential_issued = db.Column(
        db.Boolean, nullable=False, default=False
    )


class VotingCredential(db.Model):
    __tablename__ = "voting_credentials"

    id = db.Column(db.Integer, primary_key=True)
    credential_hash = db.Column(
        db.String(64), unique=True, nullable=False
    )
    is_used = db.Column(
        db.Boolean, nullable=False, default=False
    )


class Ballot(db.Model):
    __tablename__ = "ballots"

    id = db.Column(db.Integer, primary_key=True)
    encrypted_vote = db.Column(
        db.LargeBinary, nullable=False
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )