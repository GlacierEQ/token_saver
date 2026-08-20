import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pure_pointer import externalize
from token_saver_work import (
    MANIFEST_SCHEMA,
    ManifestValidationError,
    WorkAmplificationManifest,
    validate_manifest,
)


def test_pointer_manifest_round_trip_is_versioned_and_bounded(tmp_path):
    pointer = externalize("verified source " * 100, tmp_path, label="work")
    manifest = WorkAmplificationManifest.from_pointer(
        pointer,
        source_revision="67ae5ac0a2d90bf2ebf95d74a34986a89ba768bf",
        declared_byte_budget=pointer.bytes_out,
    )

    payload = manifest.to_dict()
    recovered = validate_manifest(payload)

    assert payload["schema"] == MANIFEST_SCHEMA
    assert recovered.source.sha256 == pointer.sha256
    assert recovered.lossiness == "reversible_pointer"
    assert "provider-token savings" in payload["truth_boundary"]


def test_manifest_rejects_unbounded_or_inconsistent_payload(tmp_path):
    pointer = externalize("verified source", tmp_path, label="work")
    manifest = WorkAmplificationManifest.from_pointer(
        pointer,
        source_revision="67ae5ac0a2d90bf2ebf95d74a34986a89ba768bf",
        declared_byte_budget=pointer.bytes_out,
    ).to_dict()

    manifest["declared_byte_budget"] = 0
    with pytest.raises(ManifestValidationError, match="BYTE_BUDGET_INVALID"):
        validate_manifest(manifest)

    manifest["declared_byte_budget"] = pointer.bytes_out
    manifest["source"]["canonical_uri"] = "sha256://not-the-digest"
    with pytest.raises(ManifestValidationError, match="SOURCE_URI_MISMATCH"):
        validate_manifest(manifest)
