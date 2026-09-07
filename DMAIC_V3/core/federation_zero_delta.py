"""W63 P3 manifest-resolved federation zero-delta contract."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .integrity import sha256_bytes
from .ssot_resolver import resolve_ssot

FederationTransport = Callable[[bytes], bytes]


@dataclass(frozen=True)
class FederationZeroDeltaReceipt:
    logical_id: str
    authority_path: str
    payload_sha256: str
    returned_payload_sha256: str
    zero_delta: bool
    boundary: str
    authority: str = "AUTHORITATIVE_REFERENCE_ONLY"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def identity_transport(payload: bytes) -> bytes:
    """Representative byte-preserving federation transport boundary."""
    # Force a real serialization boundary rather than returning the same object.
    return bytes(bytearray(payload))


def roundtrip_ssot(
    root: Path,
    logical_id: str,
    transport: FederationTransport = identity_transport,
) -> FederationZeroDeltaReceipt:
    path = resolve_ssot(root, logical_id)
    payload = path.read_bytes()
    before = sha256_bytes(payload)

    returned_payload = transport(payload)
    if not isinstance(returned_payload, bytes):
        raise TypeError("federation transport must return bytes")
    after = sha256_bytes(returned_payload)
    if before != after:
        raise RuntimeError("federation zero-delta SHA256 mismatch")

    return FederationZeroDeltaReceipt(
        logical_id=logical_id,
        authority_path=str(path.relative_to(root)),
        payload_sha256=before,
        returned_payload_sha256=after,
        zero_delta=True,
        boundary=transport.__name__ if hasattr(transport, "__name__") else "callable_transport",
    )
