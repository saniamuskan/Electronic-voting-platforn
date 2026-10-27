# ELECTRONIC-VOTING-PLATFORM
SECURE ELCTRONIC VOTING PLATFORM - G50

The backend creates and reuses a local Fernet key at `instance/voting.key`
when `VOTING_ENCRYPTION_KEY` is not set. Keep this file safe and do not delete
or regenerate it while encrypted ballots need to remain readable. For
deployments, configure `VOTING_ENCRYPTION_KEY` with a securely managed Fernet
key instead of relying on the local development key.
