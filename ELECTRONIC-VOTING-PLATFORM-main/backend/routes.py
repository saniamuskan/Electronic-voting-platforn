import json
import secrets

from cryptography.fernet import Fernet
from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.models import db, Voter, VotingCredential, Ballot
from backend.security import generate_voting_credential, hash_voting_credential

voting_bp = Blueprint("voting", __name__, url_prefix="/api")
VALID_CANDIDATES = frozenset({"candidate-A", "candidate-B", "candidate-C"})


def get_encryption_key():
    key = current_app.config.get("VOTING_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("Voting encryption key is not configured")
    return Fernet(key.encode("utf-8") if isinstance(key, str) else key)


@voting_bp.post("/auth/login")
def demo_login():
    """Password gate for a demonstration voter; NOT official identity verification."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Invalid request"), 400
    reference, password = data.get("voter_reference"), data.get("password")
    if not isinstance(reference, str) or not reference.strip() or not isinstance(password, str):
        return jsonify(error="Voter reference and password are required"), 400
    configured = current_app.config.get("DEMO_VOTER_PASSWORD", "")
    if not configured:
        return jsonify(error="Demo login is not configured"), 503
    # Demo-only shared secret. Production elections require a trusted identity provider.
    if not secrets.compare_digest(password, configured):
        return jsonify(error="Invalid demo credentials"), 401
    voter = Voter.query.filter_by(voter_reference=reference.strip()).first()
    if voter is None or not voter.is_eligible:
        return jsonify(error="Invalid demo credentials"), 401
    session.clear()
    session["voter_id"] = voter.id
    session["csrf_token"] = secrets.token_urlsafe(32)
    return jsonify(message="Demo voter verified", csrf_token=session["csrf_token"]), 200


@voting_bp.post("/auth/logout")
def logout():
    session.clear()
    return jsonify(message="Logged out"), 200


@voting_bp.post("/credentials/issue")
def issue_credential():
    voter_id = session.get("voter_id")
    csrf = session.get("csrf_token")
    if not isinstance(voter_id, int) or not csrf:
        return jsonify(error="Login required"), 401
    if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), csrf):
        return jsonify(error="Invalid CSRF token"), 403
    try:
        # The conditional UPDATE makes checking eligibility and claiming issuance atomic.
        result = db.session.execute(
            update(Voter).where(
                Voter.id == voter_id,
                Voter.is_eligible.is_(True),
                Voter.credential_issued.is_(False),
            ).values(credential_issued=True)
        )
        if result.rowcount != 1:
            db.session.rollback()
            return jsonify(error="Credential already issued or voter ineligible"), 409
        credential = generate_voting_credential()
        db.session.add(VotingCredential(credential_hash=hash_voting_credential(credential)))
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
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Valid JSON request is required"), 400
    credential, vote = data.get("credential"), data.get("vote")
    if not isinstance(credential, str) or not credential:
        return jsonify(error="Valid credential is required"), 400
    if not isinstance(vote, dict) or set(vote) != {"candidate"} or not isinstance(vote["candidate"], str) or vote["candidate"] not in VALID_CANDIDATES:
        return jsonify(error="A valid candidate selection is required"), 400
    try:
        encrypted_vote = get_encryption_key().encrypt(json.dumps(vote, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        result = db.session.execute(
            update(VotingCredential).where(
                VotingCredential.credential_hash == hash_voting_credential(credential),
                VotingCredential.is_used.is_(False),
            ).values(is_used=True)
        )
        if result.rowcount != 1:
            db.session.rollback()
            return jsonify(error="Invalid or already-used credential"), 401
        db.session.add(Ballot(encrypted_vote=encrypted_vote))
        db.session.commit()
        return jsonify(message="Ballot accepted"), 201
    except RuntimeError:
        db.session.rollback()
        return jsonify(error="Encryption is not configured"), 503
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Ballot submission failed")
        return jsonify(error="Internal server error"), 500
