from flask import Flask, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
from google_auth_oauthlib.flow import Flow
import requests
import os
import string
import secrets

app = Flask(__name__)

app.secret_key = "tunu-journal-secret"

CORS(app, supports_credentials=True, origins=['https://www.tunujournal.com', 'https://tunujournal.com', 'www.tunujournal.com'])

# DATABASE
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tunujournal.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# UPLOADS
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_CLIENT_SECRETS_FILE = "client_secret.json"

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]


# ID GENERATOR
def gen_id():
    chars = string.ascii_letters + string.digits
    return "SUB-" + "".join(secrets.choice(chars) for _ in range(10))


# MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True)
    email = db.Column(db.String(255), unique=True)
    name = db.Column(db.String(255))


class Submission(db.Model):
    id = db.Column(db.String(20), primary_key=True, default=gen_id)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(500))
    abstract = db.Column(db.Text)
    pdf_url = db.Column(db.String(500))
    status = db.Column(db.String(50), default="Pending Review")


with app.app_context():
    db.create_all()


# HOME
@app.route("/")
def home():
    return jsonify({"message": "Tunu Journal API running"})


# GOOGLE LOGIN
@app.route("/login")
def login():
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for("callback", _external=True)
    )

    auth_url, state = flow.authorization_url(prompt="consent")

    session["state"] = state

    return redirect(auth_url)


# GOOGLE CALLBACK
@app.route("/callback")
def callback():
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=session["state"],
        redirect_uri=url_for("callback", _external=True)
    )

    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials

    user_info = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"}
    ).json()

    google_id = user_info["sub"]
    email = user_info["email"]
    name = user_info["name"]

    user = User.query.filter_by(google_id=google_id).first()

    if not user:
        user = User(google_id=google_id, email=email, name=name)
        db.session.add(user)
        db.session.commit()

    session["user_id"] = user.id

    # send back to frontend (CORS friendly flow)
    return jsonify({
        "message": "login successful",
        "user": {
            "name": name,
            "email": email
        }
    })


# CURRENT USER
@app.route("/me")
def me():
    if "user_id" not in session:
        return jsonify({"error": "not logged in"}), 401

    user = User.query.get(session["user_id"])

    return jsonify({
        "name": user.name,
        "email": user.email
    })


# SUBMIT ARTICLE (CORS READY)
@app.route("/submit", methods=["POST"])
def submit():

    if "user_id" not in session:
        return jsonify({"error": "login required"}), 401

    title = request.form.get("title")
    abstract = request.form.get("abstract")
    file = request.files.get("pdf")

    if not file:
        return jsonify({"error": "pdf required"}), 400

    filename = secure_filename(gen_id() + ".pdf")
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)

    submission = Submission(
        user_id=session["user_id"],
        title=title,
        abstract=abstract,
        pdf_url=path
    )

    db.session.add(submission)
    db.session.commit()

    return jsonify({
        "message": "submitted successfully",
        "submission_id": submission.id
    })


# USER SUBMISSIONS
@app.route("/my-submissions")
def my_submissions():

    if "user_id" not in session:
        return jsonify({"error": "login required"}), 401

    items = Submission.query.filter_by(user_id=session["user_id"]).all()

    return jsonify([
        {
            "id": s.id,
            "title": s.title,
            "status": s.status,
            "pdf_url": s.pdf_url
        }
        for s in items
    ])


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return jsonify({"message": "logged out"})


if __name__ == "__main__":
    app.run(debug=True)