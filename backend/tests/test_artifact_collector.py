import json
from hashlib import sha256
from pathlib import Path

from app.artifact_collector import DeclaredOutputSet, PublicationRefusal, TypedArtifactCollector


class MemoryPublisher:
    def __init__(self) -> None:
        self.published: list[tuple[bytes, str]] = []

    def put_bytes(self, content: bytes, media_type: str):
        from app.run_mirror import ArtifactReceipt

        self.published.append((content, media_type))
        return ArtifactReceipt(sha256(content).hexdigest(), len(content), media_type, "memory")


def _field_outputs(tmp_path: Path) -> DeclaredOutputSet:
    (tmp_path / "field-set.json").write_text(
        json.dumps(
            {
                "version": "cmc.field-set-manifest.v1",
                "field": {
                    "id": "u",
                    "name": "u",
                    "units": "mm",
                    "association": "node",
                    "components": 2,
                    "xdmf_role": "field/u/xdmf",
                    "hdf5_role": "field/u/hdf5",
                },
                "claim_boundary": "reference only",
                "acceptance_role": "field/u/acceptance",
                "pair_map_role": "field/u/pair-map",
            }
        )
    )
    (tmp_path / "field.xdmf").write_text(
        '<Xdmf><Domain><Grid><Topology TopologyType="Triangle"><DataItem Format="HDF">field.h5:/mesh/cells</DataItem></Topology><Geometry GeometryType="XY"><DataItem Format="HDF">field.h5:/mesh/points</DataItem></Geometry><Attribute Name="u" AttributeType="Vector" Center="Node"><DataItem Format="HDF">field.h5:/fields/u</DataItem></Attribute></Grid></Domain></Xdmf>'
    )
    (tmp_path / "field.h5").write_bytes(b"not-a-real-hdf5")
    (tmp_path / "acceptance.json").write_text(
        json.dumps(
            {
                "version": "cmc.r0-field-acceptance.v1",
                "status": "accepted",
                "gates": {"mesh_audit": "accepted", "solution": "solved"},
            }
        )
    )
    (tmp_path / "pairs.json").write_text('{"ordered_element_pairs":[{"id":"pair-1"}]}')
    return DeclaredOutputSet(
        "reference-field/v1",
        tmp_path,
        (
            (
                "field-set-manifest",
                "field-set.json",
                "application/vnd.cmc.field-set-manifest+json",
                None,
            ),
            ("field/u/xdmf", "field.xdmf", "application/x-xdmf+xml", None),
            ("field/u/hdf5", "field.h5", "application/x-hdf5", None),
            (
                "field/u/acceptance",
                "acceptance.json",
                "application/vnd.cmc.r0-field-acceptance+json",
                None,
            ),
            ("field/u/pair-map", "pairs.json", "application/vnd.cmc.opened-crack-pairs+json", None),
        ),
    )


def test_collector_refuses_invalid_reference_evidence_before_any_publication(
    tmp_path: Path,
) -> None:
    publisher = MemoryPublisher()
    result = TypedArtifactCollector(publisher).collect(_field_outputs(tmp_path))

    assert result == PublicationRefusal("invalid_hdf5")
    assert publisher.published == []


def test_collector_refuses_path_traversal_and_undeclared_roles_before_publication(
    tmp_path: Path,
) -> None:
    publisher = MemoryPublisher()
    traversal = DeclaredOutputSet(
        "reference-field/v1", tmp_path, (("field-set-manifest", "../secret", "text/plain", None),)
    )
    undeclared = DeclaredOutputSet(
        "reference-field/v1", tmp_path, (("not-a-role", "x", "text/plain", None),)
    )

    assert TypedArtifactCollector(publisher).collect(traversal) == PublicationRefusal(
        "path_outside_output_root"
    )
    assert TypedArtifactCollector(publisher).collect(undeclared) == PublicationRefusal(
        "undeclared_role"
    )
    assert publisher.published == []
