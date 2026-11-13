# Spec: Poltergeist & Telemetry Events

Broadcast over WebSocket `/ws/telemetry` as JSON envelopes `{id, type, ts, payload}`.

| type | payload | emitted when |
| --- | --- | --- |
| `hello` | `{message}` | on connect |
| `grave.discovered` | `{branch, status, staleness_days}` | ingestion lists graves |
| `exorcism.started` | `{target}` | refactor loop begins |
| `exorcism.step` | `{attempt, stage}` | analyze/transform/test stage |
| `exorcism.completed` | `{target, ok, attempts, findings}` | loop ends |
| `poltergeist` | `{cause, original, latin, severity}` | test failure or dependency error |

`latin` is a Latin-esque translation of the stack trace, produced by `backend/poltergeist.py`.
The frontend triggers screen shake and phosphor-green to crimson mutation on `poltergeist`.
