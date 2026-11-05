# 2. User-facing behavior

[Back to the full spec](example-spec.md)

**What:** how the system behaves from the user's point of view, written as observable outcomes
in BDD scenarios. An agent can write code that passes the tests and still gets the experience
wrong. This section closes that gap.

**Owner:** humans decide which scenarios exist. The agent writes code to satisfy them, but doesn't
choose them.

## Example

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

## Prompts to refine it

Generate scenarios from the intent:

```
Based on this intent description, generate BDD scenarios in Gherkin
format. Cover the primary success path, key error paths, and edge
cases. For each scenario, explain why it matters.

[paste intent description]
```

Find missing scenarios:

```
Here are the BDD scenarios for this feature. What scenarios are
missing? Consider boundary conditions, concurrent access, failure
modes, and interactions with existing behavior.

[paste scenarios]
```
