import hmac
import json
import time
import base64
import hashlib

SECRET_KEY = "your-super-secret-key"


import hmac
import json
import time
import base64
import hashlib

SECRET_KEY = "your-super-secret-key"


def generate_token(user_id, tkv, expires_in=86400):
    payload = {
        "user_id": user_id,
        "tkv":tkv,
        "exp": int(time.time()) + expires_in
    }

    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(
        payload_json.encode()
    ).decode()

    signature = hmac.new(
        SECRET_KEY.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{payload_b64}::{signature}"

def verify_token(user_id, token, version):
    try:
        payload_b64, signature = token.split("::")

        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return False

        payload = json.loads(
            base64.urlsafe_b64decode(payload_b64.encode()).decode()
        )

        if payload["exp"] < time.time():
            return False

        if payload["user_id"] != user_id:
            return False
        
        if payload["tkv"] != version:
            return False

        return True

    except Exception:
        return False


import random
from flask_mail import Message


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp(email):
    otp = generate_otp()

    msg = Message(
        subject="Your Verification Code",
        recipients=[email]
    )

    msg.html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
        <h2>Tunu Publishers</h2>

        <p>Your verification code is:</p>

        <div style="
            font-size:32px;
            font-weight:bold;
            letter-spacing:5px;
            padding:15px;
            background:#f5f5f5;
            text-align:center;
            border-radius:8px;
        ">
            {otp}
        </div>

        <p>This code will expire in 10 minutes.</p>

        <p>If you did not request this code, please ignore this email.</p>
    </div>
    """

    mail.send(msg)

    return otp