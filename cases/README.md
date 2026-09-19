# Cases

`cases/raw/<case_id>/` contains complete raw historical case packages.
Raw cases may contain future or outcome-revealing information and are
not reconstruction-safe.

Researcher interpretations from the exploratory pilot belong in
`pilot_analysis/`, not in raw case packages or reconstruction inputs.

Study roles such as pilot/development and evaluation belong in
`cases/manifests/` or case metadata, not separate case directories.
A case keeps its stable identity when it participates in a different
study stage.

Temporally admissible reconstruction packages belong under
`safe/reconstruction/<case_id>/`; sealed evaluation packages belong
under `sealed/evaluation/<case_id>/`. See
`docs/repository_structure.md` and `docs/architecture.md` for the
full structure and data flow.
