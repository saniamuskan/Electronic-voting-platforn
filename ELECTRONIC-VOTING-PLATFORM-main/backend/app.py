
import os
from cryptography.fernet import Fernet
from flask import Flask, jsonify

from backend.models import db


def _load_voting_encryption_key(instance_dir, configured_key=None):
    if configured_key:
        key = (
            configured_key.encode("utf-8")
            if isinstance(configured_key, str)
            else configured_key
        )
    else:
        key_path = os.path.join(instance_dir, "voting.key")
        try:
            with open(key_path, "xb") as key_file:
                key_file.write(Fernet.generate_key())
        except FileExistsError:
            pass

        with open(key_path, "rb") as key_file:
            key = key_file.read()

    Fernet(key)
    return key


def create_app(test_config=None):
    # Find the root directory of the repository.
    base_dir = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    # Tell Flask where the separate frontend files are located.
    app = Flask(
        __name__,
        template_folder=os.path.join(
            base_dir, "frontend", "templates"
        ),
        static_folder=os.path.join(
            base_dir, "frontend", "static"
        ),
        static_url_path="/static",
    )

    # Keep the prototype database path stable whether this module is
    # imported or run directly.
    instance_dir = os.path.join(base_dir, "instance")
    os.makedirs(instance_dir, exist_ok=True)
    database_path = os.path.join(instance_dir, "voting.db")

    app.config.update(
        SQLALCHEMY_DATABASE_URI=(
            "sqlite:///" + database_path.replace(os.sep, "/")
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    configured_key = os.environ.get("VOTING_ENCRYPTION_KEY")
    if test_config and "VOTING_ENCRYPTION_KEY" in test_config:
        configured_key = test_config["VOTING_ENCRYPTION_KEY"]
    app.config["VOTING_ENCRYPTION_KEY"] = _load_voting_encryption_key(
        instance_dir,
        configured_key,
    )
    if test_config is not None:
        app.config.update(test_config)

    # Connect SQLAlchemy to Flask.
    db.init_app(app)

    # Import models before creating database tables.
    from backend.models import Voter, VotingCredential, Ballot

    with app.app_context():
        db.create_all()

    # Register voting endpoints.
    from backend.routes import voting_bp
    app.register_blueprint(voting_bp)

    @app.get("/")
    def home():
        from flask import render_template
        return render_template("index.html")

    @app.get("/api/health")
    def health_check():
        return jsonify({
            "status": "success",
            "message": "Electronic Voting Platform API is running"
        }), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
