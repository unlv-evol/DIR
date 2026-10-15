# Stage E

Stage E freezes the authoritative conversation-side records after the Stage D
procedure-validation closure gate. It consumes the final Post-C eligibility
manifest but does not change eligibility or construct new historical evidence.

Run the closure gate, freeze, and independent read-only verification with:

```text
python3 -B pipeline/stage_e/run.py --audit-stage-d
python3 -B pipeline/stage_e/run.py --freeze
python3 -B pipeline/stage_e/run.py --verify
```

The freeze is deterministic and idempotent. Existing identical artifacts are
accepted; an existing record, manifest, or summary with different content is
rejected. Corrections require a new versioned contract and retained prior
records.
