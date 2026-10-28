"""Create a disposable eligible voter for a local demonstration."""
import sys
from backend.app import create_app
from backend.models import db, Voter

def main():
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        raise SystemExit("Usage: python -m backend.seed_demo DEMO_REFERENCE")
    ref = sys.argv[1].strip()
    app = create_app()
    with app.app_context():
        voter = Voter.query.filter_by(voter_reference=ref).first()
        if voter is not None:
            print(f"Existing voter: {ref}; credential issued: {bool(voter.credential_issued)}")
            return
        db.session.add(Voter(voter_reference=ref, is_eligible=True, credential_issued=False))
        db.session.commit()
        print(f"Created eligible demonstration voter: {ref}")

if __name__ == "__main__":
    main()
