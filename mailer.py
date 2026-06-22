import random
from flask_mail import Message
from app import mail


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