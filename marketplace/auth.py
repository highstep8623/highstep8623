import base64
import hashlib
import json
import hmac
import os
import time
from typing import Dict, Optional

from . import database

SECRET_KEY = os.environ.get("MARKETPLACE_SECRET", "dev-secret-key")
HASH_ITERATIONS = 120_000


def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    if isinstance(salt, str):
        salt = base64.b64decode(salt)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, HASH_ITERATIONS)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def create_user(email: str, password: str, role: str, tier: str) -> int:
    conn = database.get_connection()
    cursor = conn.cursor()
    password_hash = _hash_password(password)
    cursor.execute(
        "INSERT INTO users (email, password_hash, role, tier, is_verified) VALUES (?, ?, ?, ?, 1)",
        (email.lower(), password_hash, role, tier),
    )
    conn.commit()
    return cursor.lastrowid


def verify_password(stored_hash: str, password: str) -> bool:
    salt_b64, hash_b64 = stored_hash.split("$")
    salt = base64.b64decode(salt_b64)
    recomputed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, HASH_ITERATIONS)
    return hmac.compare_digest(base64.b64decode(hash_b64), recomputed)


def generate_token(user_id: int, role: str, ttl_seconds: int = 3600 * 24) -> str:
    header = base64.urlsafe_b64encode(b"{\"alg\":\"HS256\",\"typ\":\"JWT\"}").rstrip(b"=")
    payload_data = f"{{\"sub\":{user_id},\"role\":\"{role}\",\"exp\":{int(time.time()) + ttl_seconds}}}"
    payload = base64.urlsafe_b64encode(payload_data.encode()).rstrip(b"=")
    signing_input = header + b"." + payload
    signature = base64.urlsafe_b64encode(
        hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    ).rstrip(b"=")
    return (signing_input + b"." + signature).decode()


def decode_token(token: str) -> Optional[Dict[str, str]]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_signature = base64.urlsafe_b64encode(
            hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
        ).rstrip(b"=")
        if not hmac.compare_digest(expected_signature, signature_b64.encode()):
            return None
        padded_payload = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(padded_payload.encode())
        payload = json.loads(payload_bytes.decode())
        if payload["exp"] < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def authenticate(email: str, password: str) -> Optional[Dict[str, str]]:
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
    row = cursor.fetchone()
    if row and verify_password(row["password_hash"], password):
        return {"id": row["id"], "role": row["role"], "tier": row["tier"]}
    return None

