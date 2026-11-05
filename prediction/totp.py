"""
Time-based one-time passwords (TOTP, RFC 6238) with the standard library only.

Works with Google Authenticator, Microsoft Authenticator, Authy, 1Password and other authenticator apps
(add the account with "enter a setup key"). No new dependency, so there is nothing extra to install or audit.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

STEP_SECONDS = 30
DIGITS = 6
ISSUER = "CardioNova Health"
RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"       # no look-alike characters (i, l, o, 0, 1)


def new_secret():
    """160 random bits as base32 (32 characters), the format authenticator apps expect."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _key(secret):
    cleaned = secret.replace(" ", "").upper()
    return base64.b32decode(cleaned + "=" * (-len(cleaned) % 8))


def hotp(secret, counter, digits=DIGITS):
    digest = hmac.new(_key(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(number % (10 ** digits)).zfill(digits)


def totp_at(secret, when=None, digits=DIGITS, step=STEP_SECONDS):
    return hotp(secret, int((time.time() if when is None else when) // step), digits)


def verify(secret, code, now=None, window=1, last_step=0, digits=DIGITS, step=STEP_SECONDS):
    """
    Checks a code against the current time step and `window` steps either side (clock drift).
    Returns the matched time step, or None. A step that is not newer than `last_step` is refused,
    so a code that was already used (or an older one) cannot be replayed.
    """
    code = "".join(ch for ch in str(code) if ch.isdigit())
    if len(code) != digits:
        return None
    current = int((time.time() if now is None else now) // step)
    matched = None
    for candidate in range(current - window, current + window + 1):      # no early exit: constant work
        if hmac.compare_digest(hotp(secret, candidate, digits), code) and candidate > last_step:
            matched = candidate if matched is None else max(matched, candidate)
    return matched


def otpauth_uri(secret, account, issuer=ISSUER):
    label = quote(f"{issuer}:{account}", safe="")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer, safe='')}&algorithm=SHA1&digits={DIGITS}&period={STEP_SECONDS}"


def group(secret, size=4):
    """'ABCDEFGH...' -> 'ABCD EFGH ...' (easier to type by hand)."""
    return " ".join(secret[i:i + size] for i in range(0, len(secret), size))


def new_recovery_codes(count=8):
    """Single-use codes, 12 characters (about 60 bits) each, shown as xxxxxx-xxxxxx."""
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(12))
        codes.append(f"{raw[:6]}-{raw[6:]}")
    return codes


def normalise_recovery_code(code):
    return "".join(ch for ch in str(code).lower() if ch.isalnum())
