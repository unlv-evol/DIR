# Reproducibility

A reproducible run should record at least:

- dataset/case manifest version
- Git commit
- configuration version
- model and model version, where applicable
- retrieval parameters
- input artifact identifiers
- output artifact identifiers
- timestamp
- checksums for important frozen artifacts

Frozen datasets should not be silently overwritten.

For reconstruction experiments, record enough metadata to reproduce the exact safe input package and pipeline configuration without exposing sealed evaluation information.
