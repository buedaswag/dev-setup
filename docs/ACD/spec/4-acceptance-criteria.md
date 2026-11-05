# 4. Acceptance criteria

[Back to the full spec](example-spec.md)

**What:** concrete expectations that run as deterministic tests. They're the source of truth for
what the code does. There are two parts:

- **Done definition**: observable outcomes that someone who has never seen the code could verify
- **Evaluation design**: test cases with known-good outputs, to catch regressions

The more complete they are, the less room the agent has to write wrong code that still passes.
The tests the agent writes from them must be **decoupled from the implementation** (they check
behavior, not internals) and **faithful to the spec** (no edge cases quietly dropped, no assertions
weakened).

The criteria come from two places: [user-facing behavior](2-user-facing-behavior.md) for the
functional side, and [feature description](3-feature-description.md) for the non-functional side.

Acceptance criteria answer "does the code work?" and run on every commit. The hypothesis answers
"did it achieve its purpose?" and is checked in production after deploy. A change can pass every
criterion and still disprove its hypothesis. That's still a result: the problem wasn't what you
thought it was.

**Owner:** humans define both parts. The agent can write the test code.

## Example

### Done definition

```
1. An authenticated client making 100 requests in one minute receives normal
   responses with rate limit headers showing remaining quota
2. An authenticated client making a 101st request in the same minute receives
   a 429 response with a Retry-After header indicating when the limit resets
3. After the rate limit window expires, the previously limited client can make
   requests again normally
4. A different authenticated client is unaffected by another client's rate
   limit status
5. The rate limit middleware adds less than 5ms to p99 request latency
```

### Evaluation design

```
Test Case 1 (Happy Path): Client sends 50 requests in one minute.
Result: All return 200 with X-RateLimit-Remaining headers counting down.

Test Case 2 (Limit Exceeded): Client sends 101 requests in one minute.
Result: Request 101 returns 429 with Retry-After header.

Test Case 3 (Window Reset): Client exceeds limit, then the window expires.
Result: Next request returns 200.

Test Case 4 (Per-Client Isolation): Client A exceeds limit. Client B sends
a request. Result: Client B receives 200.

Test Case 5 (Latency Budget): Single request with rate limit check.
Result: Middleware adds less than 5ms.
```

## Prompt to refine it

Draft the non-functional criteria from the feature description:

```
Based on this feature description, suggest non-functional acceptance
criteria I should define. Consider latency, throughput, security,
resource usage, and operational requirements. For each criterion,
explain why it matters for this specific change.

[paste feature description]
```
