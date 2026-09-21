# Reproducibility

Protocol v5 uses methodology `dir-tfg-v2` and future screening schema `dir-screening-v4`. Record source CSV checksum, stable case/source IDs, retrieval and parsing status, processability source, methodology/schema versions, validation and freeze versions, split seed/stratum/assignment once defined, code commit, configuration version, source artifact IDs, both temporal anchors and their precision/status/source, historical boundary SHA and references, and checksums for frozen outputs. Record model/version and generation settings at generation time.

Former `dir-screening-v3` manifests and smoke outputs are recoverable from Git history. Preserve their ignored retrieval cache and distinguish old `dir-tfg-v1` contracts from current outputs. Do not silently overwrite frozen or historical outputs. Reproduce SAFE inputs without exposing SEALED future or outcome information. See [the protocol](../protocols/experiment_protocol.md).
