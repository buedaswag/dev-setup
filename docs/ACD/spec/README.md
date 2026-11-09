# Writing the spec

Merged from Bryan's two articles:

- the artifacts and examples: https://beyond.minimumcd.org/docs/agentic-cd/specification/first-class-artifacts/
- the prompts to write them: https://beyond.minimumcd.org/docs/agentic-cd/specification/agent-assisted-specification/

Start with the [full example spec](example-spec.md). Then work through it one section at a time.
Each section has its example and the prompts to refine it:

1. [Intent description](1-intent.md)
2. [User-facing behavior](2-user-facing-behavior.md)
3. [Feature description](3-feature-description.md)
4. [Acceptance criteria](4-acceptance-criteria.md)
5. [System constraints](5-system-constraints.md)

## When sections disagree

The higher one wins:

| Priority | Artifact | Authority |
|----------|----------|-----------|
| 1 (highest) | Intent description | **Defines the why; everything else conforms to it** |
| 2 | User-facing behavior | **Observable outcomes; feeds acceptance criteria** |
| 3 | Feature description | **Architectural constraints; implementation must conform** |
| 4 | Acceptance criteria | **Pipeline-enforced; implementation must pass** |
| 5 | System constraints | **Global; applies to every change** |
| 6 (lowest) | Implementation | **Must satisfy all of the above** |

## Not sure where to start? The discovery loop

Let the agent interview you before anything gets written:

```
I want to build [thing]. Before we write a single line of code, I want
you to act as a Principal Architect. Your goal is to help me write a
self-contained specification that an autonomous agent can execute. Do
not start writing the spec yet. First, interview me to uncover the
technical implementation details, edge cases, and trade-offs I have
not considered.
```

Then turn the interview into a first draft:

```
Based on our discussion, generate the first draft of the specification
document. Structure it as: Intent Description, User-Facing Behavior
(BDD scenarios), Feature Description (architectural constraints),
Task Decomposition, and Acceptance Criteria (including evaluation
design with test cases). Ensure the Task Decomposition follows a
planner-worker pattern where tasks are broken into sub-two-hour chunks.
```

Then stress-test it:

```
Critique this specification. Where would a junior developer or an
autonomous agent get confused? What constraints are still too vague?
What edge cases are missing from the evaluation design?
```

## Validate the whole spec

Once every section is written:

```
Review these four specification artifacts for internal consistency
before implementation begins. Check:
- Clarity: is the intent unambiguous? Could it be read differently by two developers?
- Testability: does every BDD scenario have clear, observable outcomes?
- Scope: does the feature description constrain the implementation to what the intent requires, without over-engineering?
- Terminology: are the same concepts named consistently across all four artifacts?
- Completeness: are there behaviors implied by the intent that have no corresponding BDD scenario?
- Conflict: does anything in one artifact contradict anything in another?
- Hypothesis: if the intent includes a hypothesis, is there a corresponding validation path? Can the predicted outcome be measured after deployment?

[paste all four artifacts]
```
