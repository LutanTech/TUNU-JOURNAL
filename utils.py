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