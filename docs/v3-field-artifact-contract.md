# V3 Field Artifact contract

## Status and claim boundary

This contract describes the local-development Field Artifact and Field Viewer
slice. An `available` field is an accepted reference artifact for the declared
case and runner; it is not material calibration, qualification, or design
authority. The browser never reads raw solver files.

## Field set manifest

The executor publishes declared artifact bytes generically. The Field Set module
interprets `field-set-manifest` with media type
`application/vnd.cmc.field-set-manifest+json`. Its JSON shape is
`cmc.field-set-manifest.v1`:

```json
{
  "version": "cmc.field-set-manifest.v1",
  "field": {
    "id": "displacement",
    "name": "displacement_mm",
    "units": "mm",
    "association": "node",
    "components": 2,
    "xdmf_role": "field/displacement/xdmf",
    "hdf5_role": "field/displacement/hdf5"
  },
  "claim_boundary": "Declared local-development reference evidence; not physical validation.",
  "acceptance_role": "field/displacement/acceptance"
}
```

The XDMF, HDF5, and acceptance roles are mandatory to the Field Set module; the
executor does not infer or hard-code their names. The acceptance record is
`cmc.r0-field-acceptance.v1`, with `accepted` status and the explicit
`mesh_audit: accepted` and `solution: solved` gates. `field/<id>/mesh` is optional source
evidence and is never inferred from a path. The Run Mirror's digest-addressed
records are the only artifact identity.

## Field Artifact interface

```text
field_artifact(run_id) -> FieldArtifactResponse
```

`available` requires terminal `solved` outcome with
`accepted` disposition, a complete manifest, matching artifact
digests, supported 2D triangular topology, node-associated field values, and
declared units. Any non-accepted terminal run is `indeterminate`; missing,
malformed, unsupported, or digest-mismatched evidence is `unavailable`.

The response is versioned as `cmc.field-artifact.v1`. An available response
contains browser-safe positions, triangle indices, declared values/components/
units, and run/case/artifact provenance. It contains no storage key, raw XDMF,
HDF5, or parser-specific reference.

## Field Viewer interface

```text
present(FieldArtifactResponse) -> rendered field state
```

The Field Viewer consumes only `cmc.field-artifact.v1`. It renders geometry,
the declared displacement field, a unit-bearing legend, and provenance when
available. It renders a reasoned state without a contour for `unavailable`,
`indeterminate`, or an unknown payload version.
