Project Overview

The Electronic Voting Platform aims to provide a secure way for eligible voters to participate in an electronic election. The system is designed to support voter eligibility checks, voting credential management, ballot submission, and protection against unauthorised or repeated voting.

Key Features:
Voter Eligibility: Validates voter eligibility before voting credentials are issued.
Anonymous Voting: Designed to separate voter identity from submitted ballot records.
Credential Management: Supports secure issuance and verification of voting credentials.
Duplicate Voting Prevention: Prevents the same voting credential from being used to submit multiple ballots.
Input Validation: Validates incoming requests and rejects invalid submissions.
Secure Backend Processing: Applies appropriate security controls to voting operations.
Automated Testing: Supports testing of backend functionality and security-related scenarios.



Programming language: Python
Backend framework: [Flask / FastAPI / other framework]
Database: [SQLite / PostgreSQL / other database]
Testing: [pytest / unittest / other testing framework]
Version control: Git and GitHub
Development environment: Visual Studio Code

Prerequisites

Install the software required by the project:

Python 3.10 or another version supported by the project.
Git.
pip.
The dependencies specified by the project.
Install dependencies

the project contains a requirements.txt file:

pip install -r requirements.txt
Run the application

Use the startup command appropriate for the framework and configuration in the repository. For example, if the project uses Flask and exposes app from backend/app.py:

run "@'
>> from backend.app import app
>> from backend.models import db, Voter
>> 
>> with app.app_context():
>>     reference = "voter-demo-003"
>>     if Voter.query.filter_by(voter_reference=reference).first() is None:
>>         db.session.add(Voter(voter_reference=reference))
>>         db.session.commit()
>>     print(f"Use this voter reference: {reference}")
>> '@ | python -"
>>
run this with new voter id(there were 3 previous voter ids,1,2 and 3)

run the main file:
python -m flask --app backend.app run

Check the application's actual entry point before using this command.

Testing

Run the tests using the framework configured in the project.
