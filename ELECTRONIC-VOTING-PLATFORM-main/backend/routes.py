
import json

from cryptography.fernet import Fernet
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.models import db, Voter, VotingCredential, Ballot
from backend.security import (
    generate_voting_credential,
    hash_voting_credential,
)

voting_bp = Blueprint("voting", __name__, url_prefix="/api")


def get_encryption_key():
    key = current_app.config.get("VOTING_ENCRYPTION_KEY")

    if not key:
        raise RuntimeError("Voting encryption key is not configured")

    if isinstance(key, str):
        key = key.encode("utf-8")

    return Fernet(key)


@voting_bp.post("/credentials/issue")
def issue_credential():
    data = request.get_json(silent=True) or {}
    voter_reference = data.get("voter_reference")

    if not isinstance(voter_reference, str) or not voter_reference.strip():
        return jsonify(error="Valid voter_reference is required"), 400

    try:
        voter = Voter.query.filter_by(
            voter_reference=voter_reference.strip()
        ).first()

        if voter is None:
            return jsonify(error="Voter not found"), 404

        if not voter.is_eligible:
            return jsonify(error="Voter is not eligible"), 403

        if voter.credential_issued:
            return jsonify(error="Credential already issued"), 409

        credential = generate_voting_credential()
        credential_hash = hash_voting_credential(credential)

        db.session.add(
            VotingCredential(credential_hash=credential_hash)
        )
        voter.credential_issued = True
        db.session.commit()

        return jsonify(credential=credential), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Credential issuance conflict"), 409

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Credential issuance failed")
        return jsonify(error="Internal server error"), 500


@voting_bp.post("/ballots")
def submit_ballot():
    data = request.get_json(silent=True) or {}
    credential = data.get("credential")
    vote = data.get("vote")

    if not isinstance(credential, str) or not credential:
        return jsonify(error="Valid credential is required"), 400

    if not isinstance(vote, dict) or not vote:
        return jsonify(error="A non-empty vote object is required"), 400

    try:
        fernet = get_encryption_key()
        encrypted_vote = fernet.encrypt(
            json.dumps(
                vote,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )

        credential_hash = hash_voting_credential(credential)

        # Consume the credential atomically to prevent reuse.
        result = db.session.execute(
            update(VotingCredential)
            .where(
                VotingCredential.credential_hash == credential_hash,
                VotingCredential.is_used.is_(False),
            )
            .values(is_used=True)
        )

        if result.rowcount != 1:
            db.session.rollback()
            return jsonify(
                error="Invalid or already-used credential"
            ), 401

        db.session.add(Ballot(encrypted_vote=encrypted_vote))
        db.session.commit()

        return jsonify(message="Ballot accepted"), 201

    except RuntimeError:
        db.session.rollback()
        return jsonify(error="Encryption is not configured"), 500

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Ballot submission failed")
        return jsonify(error="Internal server error"), 500
