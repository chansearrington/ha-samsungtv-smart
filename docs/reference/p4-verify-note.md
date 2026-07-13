# P4 TV-verify note (2026-07-12) — WS auto-reconnect + keepalive

Merged `p4-reconnect` (isolated deploy slot); deployed to Ark.

| Criterion | Result |
|---|---|
| 14 — auto-reconnect / keepalive | ✅ recovery logic unit-tested (backoff capped 60s, cancel-in-close). Live STEADY-STATE verified: reconnect-churn-count=0 over 40s, no doubled-ping errors, both Frames healthy. Destructive recovery test (kill WS/reboot TV → recover <60s) DEFERRED (needs a TV reboot; do in a controlled moment). |
| 15 — tests green, no pyc | ✅ 25/25 passed; 0 pyc |
| 16 — no regression | ✅ clean load; both Frames `on`; no reconnect storm |

Real wiring (from agent): `_receive_loop` L533–606; uses `self._log`, `self._ws`, `self._connected`,
`self._recv_task`; keepalive started in `_connect_once`; reconnect scheduled only on unintentional
drop and cancelled in `close()`.
