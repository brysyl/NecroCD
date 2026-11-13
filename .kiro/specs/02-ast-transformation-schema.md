# Spec: AST Transformation Schemas (design-first contract)

All models are Pydantic v2 and live in `backend/models.py`. JSON field names equal Python names.

## Finding
| field | type | notes |
| --- | --- | --- |
| rule | str | e.g. `legacy-import`, `deprecated-call`, `syntax-rot`, `security-risk` |
| severity | `info`/`low`/`medium`/`high`/`critical` | |
| file | str | path relative to repo root |
| line | int | 1-based, 0 if unknown |
| message | str | |
| symbol | str or null | offending import or call name |
| suggestion | str or null | modern replacement |

## TransformPlan
`file: str`, `steps: list[TransformStep]`, where `TransformStep = {kind: "replace-import"|"replace-call"|"generate-router"|"generate-component", target: str, replacement: str|null}`.

## RefactorResult
`file`, `ok: bool`, `original_hash`, `new_source: str|null`, `applied: list[TransformStep]`, `router_source: str|null`, `component_source: str|null`, `attempts: int`, `error: str|null`.

## Telemetry event envelope
`{id, type, ts (ISO-8601 UTC), payload: object}`; types are defined in `03-poltergeist-events.md`.

## Invariants
1. Transformers must preserve formatting (libcst) and be idempotent.
2. Source that fails to parse yields a `syntax-rot` Finding, never an exception.
3. Generated code is tested in the Docker sandbox before a result is `ok`.
