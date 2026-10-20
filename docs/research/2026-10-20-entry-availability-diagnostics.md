# API26 entry availability diagnostics

The entry collector now preserves the last attempted page number, HTTP status
and a validated two-ASCII-digit JSON API result code in `last_response`.
`availability_status` distinguishes a failed request from an empty but
unconfirmed response. Neither state proves that no race exists.

The existing `collection_status`, validation errors, pagination rules and
entry admission remain unchanged. Only a fully validated capture produces an
entry snapshot. These additive diagnostics do not authorize collection,
inference, training, future registration or automatic retries.

## Evidence categories

The mapping uses the error table on the official
[API26 entry-sheet service page](https://www.data.go.kr/data/15058677/openapi.do),
reviewed on 2026-10-20 at approximately 19:36 UTC. This is a documentation
review, not evidence that any of these errors occurred on the live service.

| Observed evidence | `availability_status` |
| --- | --- |
| Complete validated entry snapshot | `entries_observed` |
| Valid pages but no entries for the requested race | `empty_unconfirmed` |
| JSON API code 20, 30 or 31 | `authentication_or_permission_error` |
| JSON API code 22 | `daily_rate_limited` |
| JSON API code 23 | `per_second_rate_limited` |
| JSON API code 29 | `ip_access_denied` |
| JSON API code 01, 04 or 05 | `upstream_error` |
| JSON API code 10 or 12 | `request_or_service_error` |
| Other unsuccessful JSON API code | `unclassified_api_error` |
| HTTP 401 or 403 | `http_access_denied` |
| HTTP 429 | `http_rate_limited` |
| Other rejected HTTP status | `http_error` |
| Timeout or other HTTP transport exception | `transport_error` |
| Malformed body, unsupported encoding/envelope or failed validation | `invalid_or_unverified_response` |

HTTP access denial alone does not identify an invalid credential. HTTP 429
does not identify the daily or per-second quota. `empty_unconfirmed` includes
both zero rows and an API response containing other races but not the requested
one; neither establishes unpublished status or an official no-race decision.
Publication status needs separate affirmative source evidence.

## Preservation and limits

Diagnostics reset before every page request. Failure on page 2 cannot inherit
the HTTP/API success of page 1. If no response arrives, the current page's HTTP
status and API code remain null. Successful validated pages retain their exact
original bytes, SHA256, collection time and sanitized request parameters.
A pagination failure still has no complete entry snapshot or completion time.

Credential-bearing request URLs, exception strings, arbitrary API messages and
malformed result-code strings are not persisted. The existing credential-echo
guard runs before extracting the API code. Failed bodies are not newly archived
by this change; `last_response` is safe diagnostic metadata, not a complete
error-body provenance record. The manifest still supplies the capture attempt's
start time, not an invented successful completion time.

This collector requests JSON. XML gateway error bodies remain unclassified
invalid JSON; matching digits inside arbitrary XML/text is deliberately not
used as authentication or quota evidence. No redirects or retry loops were
added. Unknown or conflicting responses remain blocked for admission.

## Verification

Mock-transport tests exercise documented API codes, unknown/malformed codes,
successful emptiness, HTTP 401/403/429/503, multi-page failure, timeouts, XML,
credential echo and complete pagination. They assert request counts, safe
persisted metadata and absence of a complete snapshot after failure. They do
not make live authenticated API calls or exercise the saved A24/B34 models.

Local verification: 62 entry-collector tests passed; the combined entry, race
identity, PDF, schedule and synthetic condition-forward regression suite passed
413 tests. Ruff lint and formatting checks passed. Existing CI includes this
collector in the separate Race Card PDF Tests workflow.
