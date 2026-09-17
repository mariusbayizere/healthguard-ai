"""RSA key material for signing and verifying tokens (FR-05-05).

WHY ASYMMETRIC. Under HS256 the signing secret and the verifying secret are one
string, so every component able to check a token is also able to mint one. With
RS256 only the issuer holds the private key; anything else needs the public key,
which is not a secret and can be published.

KEY IDENTITY IS DERIVED, NOT NAMED. A key's `kid` is a truncated SHA-256 of its
public DER. Nobody configures it, so a `kid` cannot come to disagree with the
key it labels, and adding a key to the ring cannot collide with an existing name
unless the keys themselves are identical.

ROTATION, CONCRETELY:

  1. Generate a new pair (`python -m app.core.jwt_keys`).
  2. Move the CURRENT public PEM into `JWT_RETIRED_PUBLIC_KEYS`, and put the new
     private PEM in `JWT_PRIVATE_KEY`. Deploy.
  3. New tokens are signed by the new key. Tokens already issued still verify
     against the retired public key, so nobody is signed out.
  4. After one refresh-token lifetime (`REFRESH_TOKEN_EXPIRE_DAYS`, 7 days) no
     live token can still be using the old key. Remove it from
     `JWT_RETIRED_PUBLIC_KEYS`. Deploy.

A retired key verifies and never signs; that separation is what makes step 3
safe, and it is asserted by a test.

DEVELOPMENT. With no key configured, a pair is generated in memory at start-up
and the fact is logged loudly. Sessions then do not survive a restart, which is
the correct trade for not committing key material (L12). Production refuses to
start without a configured key instead of quietly generating one.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Final

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# 2048 is the floor for RS256 in current guidance. Raising it costs signing time
# on every login; it is a setting only if someone shows a reason.
KEY_SIZE: Final = 2048
PUBLIC_EXPONENT: Final = 65537
KID_LENGTH: Final = 16


@dataclass(frozen=True)
class KeyPair:
    """A signing key and the identity derived from its public half."""

    private_pem: str
    public_pem: str
    kid: str


def kid_for_public_pem(public_pem: str) -> str:
    """A stable short identity for a public key: SHA-256 over its DER form.

    DER rather than the PEM text so that whitespace, line endings or a trailing
    newline cannot produce two identities for one key.
    """
    public_key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(der).hexdigest()[:KID_LENGTH]


def public_pem_for_private_pem(private_pem: str) -> str:
    """Derive the public half, so the two can never be configured inconsistently."""
    private_key = serialization.load_pem_private_key(
        private_pem.encode("utf-8"), password=None
    )
    return (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )


def generate_key_pair() -> KeyPair:
    """A fresh RSA pair. Used for development start-up and by the tests."""
    private_key = rsa.generate_private_key(
        public_exponent=PUBLIC_EXPONENT, key_size=KEY_SIZE
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return KeyPair(
        private_pem=private_pem,
        public_pem=public_pem,
        kid=kid_for_public_pem(public_pem),
    )


def normalise_pem(value: str) -> str:
    """Accept a PEM whose newlines survived an env var as the two characters \\n.

    Docker, systemd and CI secrets all mangle multi-line values differently.
    Rejecting the mangled form would be defensible; repairing it here is kinder
    and cannot be ambiguous, because a literal backslash-n never occurs inside
    base64 PEM content.
    """
    text = value.strip().strip('"').strip("'")
    if "\\n" in text and "\n" not in text:
        text = text.replace("\\n", "\n")
    return text + "\n" if not text.endswith("\n") else text


if __name__ == "__main__":  # pragma: no cover - operator tool
    pair = generate_key_pair()
    print("# kid:", pair.kid)
    print("# Put the private key in JWT_PRIVATE_KEY, keep the public key for")
    print("# JWT_RETIRED_PUBLIC_KEYS when you next rotate.")
    print(pair.private_pem)
    print(pair.public_pem)
