# Controlled resilience configuration

This directory defines bounded **local-development** experiments.  They do not
run in hosted CI and they do not mutate OpenTofu state, volumes, or images.

The current runner is intentionally configuration-only:

```sh
bun scripts/resilience-orchestrate.mjs plan
bun scripts/resilience-orchestrate.mjs status v3-backend-pause
```

`run <id> --execute` validates the explicit intent and then refuses because
the semantic probe/recovery driver is not implemented yet.  It cannot inject a
fault accidentally.  Add that driver only with public monitor, physics-app,
and Run Mirror probes plus independent cleanup.

`ml-resilience.v1` is deferred until Slice 7.  No current experiment gates the
ML rig from becoming functional.
