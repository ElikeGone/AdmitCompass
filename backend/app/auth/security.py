"""Password hashing (stdlib scrypt), session tokens and a small in-memory login rate limiter.

scrypt is a memory-hard KDF recommended by OWASP when Argon2id isn't available; using hashlib avoids a new
dependency. Hash format: scrypt$<n>$<r>$<p>$<salt b64>$<hash b64> so parameters can be raised later.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque

SCRYPT_N, SCRYPT_R, SCRYPT_P, DKLEN = 2**14, 8, 1, 32


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=DKLEN, maxmem=64 * 1024 * 1024)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, dk = stored.split("$")
        if algo != "scrypt":
            return False
        calc = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                              dklen=len(base64.b64decode(dk)), maxmem=64 * 1024 * 1024)
        return hmac.compare_digest(calc, base64.b64decode(dk))
    except (ValueError, TypeError):
        return False


# Used to spend the same time on unknown emails as on wrong passwords (no account enumeration via timing).
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def new_token() -> str:
    return secrets.token_urlsafe(32)  # 256 bits


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class LoginLimiter:
    """Failed sign-ins per email and per client IP within a sliding window. In-memory: resets on restart."""

    def __init__(self, max_failures: int = 5, window_s: int = 15 * 60, max_ip_failures: int = 20):
        self.max, self.window, self.max_ip = max_failures, window_s, max_ip_failures
        self._fails: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> deque:
        q = self._fails[key]
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def blocked(self, email: str, ip: str) -> bool:
        now = time.time()
        with self._lock:
            return len(self._recent("e:" + email, now)) >= self.max or len(self._recent("i:" + ip, now)) >= self.max_ip

    def fail(self, email: str, ip: str) -> None:
        now = time.time()
        with self._lock:
            self._recent("e:" + email, now).append(now)
            self._recent("i:" + ip, now).append(now)

    def succeed(self, email: str) -> None:
        with self._lock:
            self._fails.pop("e:" + email, None)

    def reset(self) -> None:
        with self._lock:
            self._fails.clear()
