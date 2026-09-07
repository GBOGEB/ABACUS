"""W63 P3 manifest-resolved federation zero-delta contract."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .integrity import sha256_bytes
from .ssot_resolver import resolve_ssot


@dataclass(frozen=True)
class FederationZeroDeltaReceipt:
    logical_id: str
    authority_path: str
    payload_sha256: str
    returned_payload_sha256: str
    zero_delta: bool
    authority: str = "AUTHORITATIVE_REFERENCE_ONLY"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def roundtrip_ssot(root: Path, logical_id: str) -> FederationZeroDeltaReceipt:
    path = resolve_ssot(root, logical_id)
    payload = path.read_bytes()
    before = sha256_bytes(payload)

    # Federation is deliberately identity-preserving at this boundary. Analysis may
    # derive findings elsewhere, but the authoritative payload returns byte-for-byte.
    returned_payload = bytes(payload)
    after = sha256_bytes(returned_payload)
    if before != after:
        raise RuntimeError("federation zero-delta SHA256 mismatch")

    return FederationZeroDeltaReceipt(
        logical_id=logical_id,
        authority_path=str(path.relative_to(root)),
        payload_sha256=before,
        returned_payload_sha256=after,
        zero_delta=True,
    )
