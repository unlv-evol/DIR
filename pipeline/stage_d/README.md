# Stage D

Stage D draws a reproducible PA/PN-stratified sample from the final eligible
population and prepares two blinded, initially blank human-review packages.
It validates Stage C conversation extraction only. It does not validate or
expose Post-C reconstruction results.

Run, in order:

```text
python3 pipeline/stage_d/run.py --check-config
python3 pipeline/stage_d/run.py --generate-sample
python3 pipeline/stage_d/run.py --prepare-review
python3 pipeline/stage_d/run.py --validate
```

The fixed integer seed is `20261005`. Case IDs are sorted lexicographically in
each stratum. Domain-separated SHA-256 derivations from that one seed initialize
the PA draw, PN draw, and final blinded review-order shuffle. Each draw uses
Python's seeded `random.Random.sample` without replacement.

The internal manifest records the configured Git remote and repository-relative
evidence paths. After review, commit, and push, the checkpoint commit SHA can be
combined with those values; files do not attempt to contain their own commit.
