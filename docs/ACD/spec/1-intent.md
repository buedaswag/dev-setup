# 1. Intent description

[Back to the full spec](example-spec.md)

**What:** a self-contained problem statement: what the change should accomplish and why, never how.
An agent, or a new team member, should understand the problem from this alone without asking
anything.

**Include a hypothesis:** "We believe [this change] will result in [this outcome] because [this
reason]." It makes the why testable: after deployment, check whether the outcome happened.

**Owner:** a human writes it. The agent never writes or edits it.

Scenarios describe what the system does, not how it does it. See
[Writing better Gherkin](../ACD.md#references).

## Example

```markdown
## Intent: Add rate limiting to the /api/search endpoint

We are receiving complaints about slow response times during peak hours.
Analysis shows that a small number of clients are making thousands of
requests per minute. We need to limit each authenticated client to 100
requests per minute on the /api/search endpoint. Requests that exceed
the limit should receive a 429 response with a Retry-After header.

**Hypothesis:** We believe rate limiting will reduce p99 latency for
well-behaved clients by 40% because abusive clients currently consume
60% of search capacity.
```

## Prompts to refine it

Find ambiguity:

```
Here is the intent description for my next change. Identify any
ambiguity, unstated assumptions, or missing context that could
lead to an implementation that technically satisfies this description
but does not match what I actually want.

[paste intent description]
```

Sharpen the hypothesis:

```
Review this hypothesis. Is the expected outcome measurable with data
we currently collect? Is the causal reasoning plausible? What
alternative explanations could produce the same outcome without this
change being the cause?

[paste intent description with hypothesis]
```
