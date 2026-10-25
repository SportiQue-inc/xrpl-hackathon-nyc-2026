"""PREIMAGE-SHA-256 crypto-conditions (RFC draft used by XRPL escrows) for a 32-byte key.

The data key K is the preimage. Publishing K in EscrowFinish pays the contributor and,
at the same moment, gives the research institution the key to open the bundle."""
import hashlib
import os


def new_key() -> bytes:
    return os.urandom(32)


def fulfillment_hex(key: bytes) -> str:
    assert len(key) == 32
    return ("A0228020" + key.hex()).upper()


def condition_hex(key: bytes) -> str:
    return ("A0258020" + hashlib.sha256(key).hexdigest() + "810120").upper()


def key_from_fulfillment(fulfillment: str) -> bytes:
    f = fulfillment.upper()
    if not (f.startswith("A0228020") and len(f) == 8 + 64):
        raise ValueError("not a 32-byte PREIMAGE-SHA-256 fulfillment")
    return bytes.fromhex(f[8:])
