# 5. System constraints

[Back to the full spec](example-spec.md)

**What:** non-functional requirements, security policies, performance budgets and org rules that
apply to every change, not just this one. Agents can't infer org norms, so write them down.

Most of these belong in CLAUDE.md. In the spec, only add the ones CLAUDE.md doesn't already cover.

Bryan gives no prompt for this section. It's global, so you write it once and rarely refine it
per change.

## Example

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
