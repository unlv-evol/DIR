# Reproducibility

Protocol v5 uses methodology `dir-tfg-v2` and future screening schema `dir-screening-v4`. Record source CSV checksum, stable case/source IDs, retrieval and parsing status, processability source, methodology/schema versions, validation and freeze versions, split seed/stratum/assignment once defined, code commit, configuration version, source artifact IDs, both temporal anchors and their precision/status/source, historical boundary SHA and references, and checksums for frozen outputs. Record model/version and generation settings at generation time.

Keep existing `dir-screening-v3` manifests, smoke outputs, caches, and `dir-tfg-v1` contracts distinguishable and unchanged. Do not silently overwrite frozen or historical outputs. Reproduce SAFE inputs without exposing SEALED future or outcome information. See [the protocol](../protocols/pilot_case_selection_and_extraction.md).
