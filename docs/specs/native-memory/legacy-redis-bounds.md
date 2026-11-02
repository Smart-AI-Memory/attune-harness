# Legacy Redis reply and connection bounds

Implementation design, November 2, 2026. Baseline: `7aad051`.

## Behavior

Bound each accepted legacy reply to 1 MiB of canonical JSON encoded as UTF-8,
including its authority, hydration stamp, operation metadata and nested items.
Check cumulative serialized item bytes before retaining each item, then check the
complete packet. Refuse the whole reply with an actionable unavailable result;
do not truncate records or present an incomplete result as success. redis-py may
already have allocated the raw server reply. This change does not bound that
allocation or introduce a total-operation deadline.

The host owns `socket_timeout`, `socket_connect_timeout`, `decode_responses`,
`encoding` and `encoding_errors`. Refuse these URL query names, including encoded,
repeated and empty forms, before creating a client. Keep UTF-8 strict decoding and
the existing connect/socket waits. Preserve database selectors and existing TLS
options. Legacy retry and health-check options remain supported; per-attempt
socket waits do not promise a total-operation bound. The native generation route
retains its stricter URL admission, final packet check and generation recheck.

## Cases and disposable probes

Accept exact-boundary packets and ordinary database/TLS configuration. Refuse
one-byte overflow, multibyte expansion, oversized node/search/digest/related
results, nested edges and authority metadata. Stop retaining results when their
cumulative size crosses the bound. Invalid JSON values refuse cleanly. Exercise
URL precedence with the actual pinned redis-py client without opening a socket;
assert rejected options never reach the client factory.

The baseline disposable probe used redis-py 5.3.1 and synthetic data, with zero
network calls. A node with a 1,048,576-character description returned a
1,049,133-byte canonical packet. `Redis.from_url` replaced a two-second socket
wait with zero, a one-second connect wait with 500 seconds, and accepted a
percent-encoded timeout key. A duplicate empty/nonempty timeout selected the
nonempty value. URL decoding options replaced host defaults. Database 2 and
`ssl_cert_reqs=required` retained the host waits.

## Alternatives

- Reject a final-size-only guard: it retains every decoded item before refusal.
- Reject the native route's database-only URL allowlist for legacy users: it
  would remove existing TLS configuration without an approved compatibility case.
- Keep transport allocation and total-operation supervision separate: neither is
  established by packet accounting or existing socket timeout arguments.
