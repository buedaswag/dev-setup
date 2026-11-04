# Developing software with Agents

Based on Bryan’s Agentic CD.

I'm summarizing his content, definitely reccomend opening all the links and reading the articles.

## Starting point - how we are developing

https://beyond.minimumcd.org/docs/agentic-cd/getting-started/learning-curve/

![alt text](image.png)

We’re learning how to write software with agents

One agent at a time:

1. Write desired outcome + hypothesis + spec
2. Loop:
   1. start session (write small batch of code)
   2. Review (against spec)
   3. End-session (submit small batch)
3. Continue until feature satisfies spec
4. Review against desired outcome + hypothesis

**CONCERN:** how do we enforce that the batches of code stay small?

- https://beyond.minimumcd.org/docs/foundations/work-decomposition/
- https://beyond.minimumcd.org/docs/agentic-cd/architecture/small-batch-sessions/
- Tldr: we implement one BDD scenario at a time (see bellow - Agent Delivery Contract or spec)

## Foundations

- ATDD basic paragraph - https://beyond.minimumcd.org/docs/optimize/small-batches/#atdd-connecting-scenarios-to-daily-integration
    - tldr:
        1. Pick one BDD scenario.
        2. Write the acceptance test first.
        3. Write just enough code to pass.
        4. Refactor.
        5. Commit and integrate.
        6. Repeat.
- https://beyond.minimumcd.org/docs/optimize/hypothesis-driven-development/
    - tldr: **“We believe [change] will produce [outcome] because [reason].”**

## The minimal artefacts we need to write code

### CLAUDE.md

- What is it?
  - Section - Configuration mechanisms - https://beyond.minimumcd.org/docs/agentic-cd/getting-started/agent-setup/
- Where to keep it?
  - Keep it simple as a start and use a single file at the repo root
  - Or at the claude root file you’re working in multiple terraform repositories for example
    - For example if you work in terraform modules that all have roughly the same structure, and way to test, then specify that here

### hooks

- Use whatever you want (python, bash, go, Tasks, precommit python framework etc), configure them to run on pre/post commit, and pre push

### Skills

- Very cool way to work using agents is shown in section Skills - https://beyond.minimumcd.org/docs/agentic-cd/getting-started/agent-setup/ and complete definition of each skill here - https://beyond.minimumcd.org/docs/agentic-cd/architecture/agent-configuration/#skills
- The minimal ones are
  - Start-session
  - Review
  - end-session

### Agent Delivery Contract or spec (now it gets interesting, and HAS NOTHING TO DO WITH AI!!)

https://beyond.minimumcd.org/docs/agentic-cd/specification/first-class-artifacts/#2-user-facing-behavior

Single .md containing

- Intent description (+ hypothesis)
- User-facing behavior (behavior-driven development - BDD)
- Feature description (architecture decisions, implementation details - the weeds)
- Acceptance criteria (written as observable outcomes, not internal implementation details)
- System constraints
  - Can be derived from some global/project level constraints already defined in claude.md

Example of using AI to write a spec (“If your specification effort for a single change takes more than 15 minutes, the change is too large. Split it.”)

- https://beyond.minimumcd.org/docs/agentic-cd/specification/agent-assisted-specification/
- Im fine with copy pasting the prompts because im learning the why/what/how

## References

- Overview of the ACD workflow
  - Section - The ACD workflow in https://beyond.minimumcd.org/docs/agentic-cd/
- Bryan’s talk at devopsdays Dallas, Texas https://www.youtube.com/watch?v=8u_FVTRtqrw

## Next up:

- review what i have against what claude gave me
- Try it out
  - Create a new repo and feature request
  - Write the feature
  - Document learnings
- Improve this documentation
  - Missing at least a quick mention to TDD
  - Work decomposition needs a tldr + some good/bad examples from our team context
    - https://beyond.minimumcd.org/docs/foundations/work-decomposition/
