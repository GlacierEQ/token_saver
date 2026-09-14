"""Versioned handoff manifest for optional Work Amplification compositions.

The manifest does not represent provider-token savings or model quality. It
binds a compact transport artifact to a source digest, a declared byte budget,
and an explicit lossiness label so consumers cannot silently inflate its claim.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping


MANIFEST_SCHEMA = "glaciereq.token-saver.work-amplification-manifest.v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{7,64}$")
_LOSSINESS = frozenset({"reversible_pointer", "lossy_selection"})


class ManifestValidationError(ValueError):
    """Raised when a composition manifest is internally inconsistent."""


@dataclass(frozen=True)
class SourceReference:
    canonical_uri: str
    sha256: str
    bytes_in: int
    bytes_out: int

    @classmethod
    def from_pointer(cls, pointer: Any) -> "SourceReference":
        return cls(
            canonical_uri=str(pointer.canonical_uri),
            sha256=str(pointer.sha256),
            bytes_in=int(pointer.bytes_in),
            bytes_out=int(pointer.bytes_out),
        )


@dataclass(frozen=True)
class WorkAmplificationManifest:
    source: SourceReference
    source_revision: str
    declared_byte_budget: int
    lossiness: str
    schema: str = MANIFEST_SCHEMA

    @classmethod
    def from_pointer(
        cls,
        pointer: Any,
        *,
        source_revision: str,
        declared_byte_budget: int,
        lossiness: str = "reversible_pointer",
    ) -> "WorkAmplificationManifest":
        manifest = cls(
            source=SourceReference.from_pointer(pointer),
            source_revision=source_revision,
            declared_byte_budget=declared_byte_budget,
            lossiness=lossiness,
        )
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if self.schema != MANIFEST_SCHEMA:
            raise ManifestValidationError("MANIFEST_SCHEMA_UNSUPPORTED")
        if not _SHA256_RE.fullmatch(self.source.sha256):
            raise ManifestValidationError("SOURCE_SHA256_INVALID")
        if self.source.canonical_uri != f"sha256://{self.source.sha256}":
            raise ManifestValidationError("SOURCE_URI_MISMATCH")
        if self.source.bytes_in < 0 or self.source.bytes_out < 0:
            raise ManifestValidationError("SOURCE_BYTES_NEGATIVE")
        if not _REVISION_RE.fullmatch(self.source_revision):
            raise ManifestValidationError("SOURCE_REVISION_INVALID")
        if self.declared_byte_budget <= 0:
            raise ManifestValidationError("BYTE_BUDGET_INVALID")
        if self.source.bytes_out > self.declared_byte_budget:
            raise ManifestValidationError("BYTE_BUDGET_EXCEEDED")
        if self.lossiness not in _LOSSINESS:
            raise ManifestValidationError("LOSSINESS_UNSUPPORTED")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema": self.schema,
            "source": asdict(self.source),
            "source_revision": self.source_revision,
            "declared_byte_budget": self.declared_byte_budget,
            "lossiness": self.lossiness,
            "truth_boundary": (
                "This manifest binds a compact transport artifact to a source digest and "
                "declared byte budget. It does not establish provider-token savings, model "
                "quality, retrieval success, remote durability, or external execution authority."
            ),
        }


def validate_manifest(payload: Mapping[str, Any]) -> WorkAmplificationManifest:
    """Validate an untrusted composition payload and return its typed form."""
    try:
        source_payload = payload["source"]
        source = SourceReference(
            canonical_uri=str(source_payload["canonical_uri"]),
            sha256=str(source_payload["sha256"]),
            bytes_in=int(source_payload["bytes_in"]),
            bytes_out=int(source_payload["bytes_out"]),
        )
        manifest = WorkAmplificationManifest(
            source=source,
            source_revision=str(payload["source_revision"]),
            declared_byte_budget=int(payload["declared_byte_budget"]),
            lossiness=str(payload["lossiness"]),
            schema=str(payload["schema"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ManifestValidationError("MANIFEST_MALFORMED") from exc
    manifest.validate()
    return manifest
