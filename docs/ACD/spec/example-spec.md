# Example spec: rate limiting for /api/search

The full Agent Delivery Contract in one file, using Bryan's example from
https://beyond.minimumcd.org/docs/agentic-cd/specification/first-class-artifacts/

Each section has its own doc with the prompts to refine it:

1. [Intent description](1-intent.md)
2. [User-facing behavior](2-user-facing-behavior.md)
3. [Feature description](3-feature-description.md)
4. [Acceptance criteria](4-acceptance-criteria.md)
5. [System constraints](5-system-constraints.md)

Once all sections are written, check them against each other: [Validate the whole spec](README.md#validate-the-whole-spec)

---

## Intent: Add rate limiting to the /api/search endpoint

We are receiving complaints about slow response times during peak hours.
Analysis shows that a small number of clients are making thousands of
requests per minute. We need to limit each authenticated client to 100
requests per minute on the /api/search endpoint. Requests that exceed
the limit should receive a 429 response with a Retry-After header.

**Hypothesis:** We believe rate limiting will reduce p99 latency for
well-behaved clients by 40% because abusive clients currently consume
60% of search capacity.

## User-facing behavior

```gherkin
Scenario: Client exceeds rate limit
  Given an authenticated client
  And the client has made 100 requests in the current minute
  When the client makes another request to /api/search
  Then the response status should be 429
  And the response should include a Retry-After header
  And the Retry-After value should indicate when the limit resets

Scenario: Client within rate limit
  Given an authenticated client
  And the client has made 50 requests in the current minute
  When the client makes a request to /api/search
  Then the request should be processed normally
  And the response should include rate limit headers showing remaining quota
```

## Feature: Rate Limiting for Search API

### Musts

- Rate limit middleware sits between authentication and the search handler
- Rate limit state is stored in Redis (shared across application instances)
- Rate limit configuration is read from the application config, not hardcoded
- Must work correctly with horizontal scaling (3-12 instances)
- Must be configurable per-endpoint (other endpoints may have different limits later)

### Must Nots

- Must not add more than 5ms of latency to the request path
- Must not introduce new external dependencies (Redis client library already in use for session storage)

### Preferences

- Prefer middleware pattern over decorator pattern for request interception
- Prefer sliding window counter over fixed window for smoother rate distribution

### Escalation Triggers

- If Redis is unavailable, stop and ask whether to fail open (allow all requests) or fail closed (reject all requests)
- If the existing auth middleware does not expose the client ID, stop and ask rather than modifying the auth layer

## Acceptance criteria

### Done definition

1. An authenticated client making 100 requests in one minute receives normal
   responses with rate limit headers showing remaining quota
2. An authenticated client making a 101st request in the same minute receives
   a 429 response with a Retry-After header indicating when the limit resets
3. After the rate limit window expires, the previously limited client can make
   requests again normally
4. A different authenticated client is unaffected by another client's rate
   limit status
5. The rate limit middleware adds less than 5ms to p99 request latency

### Evaluation design

- **Test Case 1 (Happy Path):** Client sends 50 requests in one minute.
  Result: All return 200 with X-RateLimit-Remaining headers counting down.
- **Test Case 2 (Limit Exceeded):** Client sends 101 requests in one minute.
  Result: Request 101 returns 429 with Retry-After header.
- **Test Case 3 (Window Reset):** Client exceeds limit, then the window expires.
  Result: Next request returns 200.
- **Test Case 4 (Per-Client Isolation):** Client A exceeds limit. Client B sends
  a request. Result: Client B receives 200.
- **Test Case 5 (Latency Budget):** Single request with rate limit check.
  Result: Middleware adds less than 5ms.

## System constraints

Only what isn't already in CLAUDE.md.

```yaml
system_constraints:
  security:
    - No secrets in source code
    - All user input must be sanitized
    - Authentication required for all API endpoints
  performance:
    - API p99 latency < 500ms
    - No N+1 query patterns
    - Database queries must use indexes
  architecture:
    - No circular dependencies between modules
    - External service calls must use circuit breakers
    - All new dependencies require team approval
  operations:
    - All new features must have monitoring dashboards
    - Log structured data, not strings
    - Feature flags required for user-visible changes
```
