from app.provenance_closure import DeclaredArtifactRoot, ProvenanceClosureVerifier
from app.reference_corpus import CorpusCurator, CorpusMember, CorpusRefusal, CorpusRequest


def _member(case_id: str, digest: str) -> CorpusMember:
    return CorpusMember(
        case_id=case_id,
        field_set_digest=digest,
        accepted=True,
        problem_card_digest="r0-card",
        mesh_pair_digest="opened-pairs",
        material_digest="elastic-material",
    )


def test_curator_refuses_the_existing_single_accepted_field_as_not_a_case_split() -> None:
    result = CorpusCurator().freeze(
        CorpusRequest("r0-elastic/v1", (_member("edge-cracked-plate-v1", "a"),))
    )

    assert result == CorpusRefusal("insufficient_independent_cases")


def test_curator_freezes_a_full_case_split_and_closure_verifies_each_declared_edge() -> None:
    corpus = CorpusCurator().freeze(
        CorpusRequest(
            "r0-elastic/v1",
            (
                _member("r0-elastic-displacement-e180-v1", "a"),
                _member("r0-elastic-displacement-e200-v1", "b"),
                _member("r0-elastic-displacement-e220-v1", "c"),
            ),
        )
    )
    assert not isinstance(corpus, CorpusRefusal)
    assert {member.split for member in corpus.members} == {"train", "held-out"}

    closure = ProvenanceClosureVerifier().verify(
        DeclaredArtifactRoot(
            "model-release",
            {
                "model-release": ("corpus-receipt", "recipe"),
                "corpus-receipt": ("field-set:a", "field-set:b", "field-set:c"),
                "field-set:a": (),
                "field-set:b": (),
                "field-set:c": (),
                "recipe": (),
            },
            {
                "model-release": "model-release",
                "corpus-receipt": "reference-corpus",
                "field-set:a": "reference-field",
                "field-set:b": "reference-field",
                "field-set:c": "reference-field",
                "recipe": "training-recipe",
            },
            {
                key: "a" * 64
                for key in (
                    "model-release",
                    "corpus-receipt",
                    "field-set:a",
                    "field-set:b",
                    "field-set:c",
                    "recipe",
                )
            },
        )
    )

    assert closure.root_digest
