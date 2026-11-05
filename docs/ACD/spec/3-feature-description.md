# 3. Feature description (constraint architecture)

[Back to the full spec](example-spec.md)

**What:** the architecture, dependencies and trade-off boundaries the implementation has to stay
within: where the change fits, what it touches, and which constraints are non-negotiable. It's the
context a human developer carries in their head and an agent doesn't have. Split it into:

- **Musts / Must Nots**: hard boundaries
- **Preferences**: soft, the agent can trade them off
- **Escalation triggers**: the agent stops and asks instead of deciding

Non-functional requirements (latency, resilience, security) go here explicitly, because
[acceptance criteria](4-acceptance-criteria.md) are derived from them.

**Owner:** engineering. The agent implements within these constraints and never changes them.

## Example

```markdown
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
```

## Prompt to refine it

Find the architectural decisions to document before implementation starts:

```
Given this intent and these BDD scenarios, what architectural
decisions should I document before implementation begins? Consider
where this change fits in the existing system, what components it
touches, and what constraints an implementer needs to know.

Current system context: [brief architecture description]
```
