import base64
import hashlib
import hmac
import json
import os
import secrets
import string
import time
from urllib.parse import urlencode

from flask import Flask, jsonify, redirect, request, session, url_for
from flask import send_from_directory
from flask import Flask
from flask import jsonify, session
from flask_cors import CORS
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from google_auth_oauthlib.flow import Flow
import requests
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from utils import send_otp

app = Flask(__name__)

app.secret_key = "tunu-journal-secret"
print("TUNU API STARTED")
CORS(
    app,
    supports_credentials=True,
    origins=[
        "https://www.tunujournal.com",
        "https://www.submit.tunujournal.com",
        "https://tunujournal.com",
        "https://submit.tunujournal.com",
        "http://127.0.0.1:5500"
    ]
)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tunujournal.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["UPLOAD_FOLDER"] = "uploads/usercontent"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)


app.config['MAIL_SERVER'] = 'mail.tunupublishers.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'noreply@tunupublishers.com'
app.config['MAIL_PASSWORD'] = 'YOUR_EMAIL_PASSWORD'
app.config['MAIL_DEFAULT_SENDER'] = (
    'Tunu Publishers',
    'noreply@tunupublishers.com'
)

mail = Mail(app)



os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_CLIENT_SECRETS_FILE = "client_secret.json"

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

SECRET_KEY = "super-token-secret"


# ---------------- ID GENERATOR ----------------

def gen_id(prefix="ID", length=10):
    chars = string.ascii_letters + string.digits
    return prefix + "-" + "".join(secrets.choice(chars) for _ in range(length))


# ---------------- TOKEN SYSTEM ----------------

def generate_token(user_id, tkv, expires_in=86400):
    payload = {
        "user_id": user_id,
        "tkv": tkv,
        "exp": int(time.time()) + expires_in
    }

    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()

    signature = hmac.new(
        SECRET_KEY.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{payload_b64}::{signature}"


def verify_token(token):
    try:
        payload_b64, signature = token.split("::")

        expected = hmac.new(
            SECRET_KEY.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            return None

        payload = json.loads(
            base64.urlsafe_b64decode(payload_b64.encode()).decode()
        )

        if payload["exp"] < time.time():
            return None
 
        return payload

    except Exception:
        return None


# ---------------- MODELS ----------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(1012), nullable=True)
    name = db.Column(db.String(255))
    tkv = db.Column(db.String(50), default=lambda: gen_id("TK", 10))
    email_method = db.Column(db.Boolean, default=False)
    google_method = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)


class Submission(db.Model):
    id = db.Column(db.String(20), primary_key=True, default=lambda: gen_id("SUB", 10))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(500))
    abstract = db.Column(db.Text)
    pdf_url = db.Column(db.String(500))
    status = db.Column(db.String(50), default="Pending")


with app.app_context():
    db.create_all()


# ---------------- HELPERS ----------------

def get_current_user():
    token = request.headers.get("Authorization")
    if not token:
        token = request.args.get('token')
        
    if not token:
        return None

    payload = verify_token(token)
    if not payload:
        return None

    user = User.query.get(payload["user_id"])
    if not user:
        return None

    if user.tkv != payload["tkv"]:
        return None

    return user


# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return jsonify({"message": "Tunu Journal Smoking"})

@app.errorhandler(Exception)
def handle_error(e):
    import traceback

    print("ERROR:", str(e))
    traceback.print_exc()

    return jsonify({
        "error": str(e),
        "type": str(type(e))
    }), 500

@app.route('/api/register', methods=['POST'])
def api_register():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "error": "No data received"
        }), 400

    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not name or not email or not password:
        return jsonify({
            "error": "All fields are required"
        }), 400

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        return jsonify({
            "error": "Email already registered"
        }), 409

    user = User(
        name=name,
        email=email,
        password=generate_password_hash(password),
        email_method=True,
        google_method=False,
        is_active=True,
        tkv=gen_id("TK", 10)
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "Registered successfully. Redirecting to Login"
    }), 201

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True)
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error':'All fields are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error':'Invalid credentials'}), 401
    
    if user.google_method and not user.email_method or not user.password or user.google_id:
        return jsonify({'error':'Invalid login method; Login using Google'}), 400
    
    if not check_password_hash(user.password, password):
        return jsonify({
            "error": "Invalid credentials"
        }), 401
    
    
    user.tkv = gen_id("TK", 10)
    db.session.commit()

    token = generate_token(user.id, user.tkv)

    payload = {
        "name": user.name,
        "email": user.email,
        "token": token
    }

    # encoded = base64.urlsafe_b64encode(
    #     json.dumps(payload).encode()
    # ).decode()

    return jsonify(payload), 200  
    

@app.route("/google/login")
def login():
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for("callback", _external=True)
    )

    auth_url, _ = flow.authorization_url(prompt="consent")
    return redirect(auth_url)

@app.route('/uploads/usercontent/<filename>')
def get_file(filename):
    download = request.args.get('download')
    filename = secure_filename(filename)    
    if download:
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# GOOGLE CALLBACK
@app.route("/google/callback")
def callback():
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
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
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            tkv=gen_id("TK", 10)
        )
        db.session.add(user)
        db.session.commit()

    user.tkv = gen_id("TK", 10)
    db.session.commit()

    token = generate_token(user.id, user.tkv)

    payload = {
        "name": user.name,
        "email": user.email,
        "token": token
    }

    encoded = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode()

    return redirect(
        f"https://tunujournal.com/dashboard/?params={encoded}"
    )


# CURRENT USER
@app.route("/me")
def me():
    user = get_current_user()

    if not user:
        return jsonify({"error": "invalid token"}), 401

    return jsonify({
        "name": user.name,
        "email": user.email
    })


# SUBMIT
@app.route("/submit", methods=["POST"])
def submit():
    user = get_current_user()

    if not user:
        return jsonify({"error": "invalid token"}), 401

    title = request.form.get("title")
    abstract = request.form.get("abstract")
    file = request.files.get("pdf")

    if not file:
        return jsonify({"error": "pdf required"}), 400

    filename = secure_filename(gen_id('SUB', 20) + ".pdf")
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)

    submission = Submission(
        user_id=user.id,
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


@app.route('/admin/submissions', methods=['GET'])
def get_submissions():
    """Fetches all submissions joined with user email."""
    # Query all submissions
    submissions = Submission.query.all()
    
    # Serialize data
    results = []
    for sub in submissions:
        # Accessing the related user to get the email
        author = User.query.get(sub.user_id)
        email = author.email if author else "Unknown"
        
        results.append({
            "id": sub.id,
            "author_email": email,
            "title": sub.title,
            "status": sub.status,
            "pdf_url": sub.pdf_url
        })
    return jsonify(results)

@app.route('/admin/update/<submission_id>', methods=['POST'])
def update_submission(submission_id):

    data = request.get_json(silent=True) or {}

    new_status = data.get('status')

    if not new_status:
        return jsonify({
            "error": "status is required"
        }), 400

    submission = Submission.query.get(submission_id)

    if not submission:
        return jsonify({
            "message": "Submission not found"
        }), 404

    submission.status = new_status
    db.session.commit()

    return jsonify({
        "message": "Status updated successfully",
        "status": new_status
    }), 200

# MY SUBMISSIONS
@app.route("/my-submissions")
def my_submissions():
    user = get_current_user()

    if not user:
        return jsonify({"error": "invalid token"}), 401

    items = Submission.query.filter_by(user_id=user.id).all()

    return jsonify([
        {
            "id": s.id,
            "title": s.title,
            "status": s.status,
            "pdf_url": s.pdf_url
        }
        for s in items
    ])


# LOGOUT (CLIENT SIDE ONLY)
@app.route("/logout")
def logout():
    return jsonify({"message": "delete token on client"})



@app.route('/send-otp')
def send_otp_route():
    email = "lutancorpinoteam#@gmail.com"

    otp = send_otp(email)

    session['otp'] = otp

    return jsonify({
        "success": True,
        "message": "OTP sent successfully"
    })

if __name__ == '__main__':
    app.run(debug=True)