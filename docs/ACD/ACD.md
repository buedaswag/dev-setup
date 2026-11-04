# Developing software with Agents

Based on Bryan’s Agentic CD.

I'm summarizing his content, definitely reccomend opening all the links and reading the articles.

## Starting point - how we are developing

https://beyond.minimumcd.org/docs/agentic-cd/getting-started/learning-curve/

![alt text](image.png)

We’re learning how to write software with agents

One agent at a time:

1. Write desired outcome + hypothesis + spec
    - https://beyond.minimumcd.org/docs/optimize/hypothesis-driven-development/
    - tldr: **“We believe [change] will produce [outcome] because [reason].”**
2. Loop:
   - ATDD basic paragraph - https://beyond.minimumcd.org/docs/optimize/small-batches/#atdd-connecting-scenarios-to-daily-integration
    - tldr:
        1. Pick one BDD scenario.
        2. Write the acceptance test first.
        3. Write just enough code to pass.
        4. Refactor.
        5. Commit and integrate.
        6. Repeat.
3. Continue until feature satisfies spec
4. Review against desired outcome + hypothesis

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
TODO (me): explore whats a minimal way to get this set up, in a waz thats compatible w the loop above.

### Agent Delivery Contract or spec (now it gets interesting, and HAS NOTHING TO DO WITH AI!!)

TODO (me): instead of going through both articles in paralel (one contains the examples, the other the prompts to crreate the example sections, merge the two and. put them here)
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
- Story or scenario too big? See [Slicing strategies](#slicing-strategies)

### Slicing strategies

**CONCERN:** how do we enforce that the batches of work stay small?

https://beyond.minimumcd.org/docs/foundations/work-decomposition/

- tldr: when a story feels too big, apply one of these strategies:
  - By workflow step - implement one step of a multi-step process
  - By business rule - implement one rule at a time
  - By data variation - handle one data type first
  - By operation - implement CRUD operations separately
  - By performance - get it working first, optimize later
  - By platform - support one platform first
  - Happy path first - implement the success case first
- TODO (me): read through the article with some time and go into it. Find a tldr for vertical slicing and INVEST too.

(see loop above in Starting point - how we are developing)
"How to structure agent sessions so context stays manageable, commits stay small, and the pipeline stays green" - https://beyond.minimumcd.org/docs/agentic-cd/architecture/small-batch-sessions/
- Tldr: we implement one BDD scenario at a time (see bellow - Agent Delivery Contract or spec)


## Lessons learned from applying this in practice

- Work slicing was hard. The spec got way too big: ~250 lines, and it took 2 to 3 hours to build instead of the 15 minutes Bryan mentions.
- pair programming is tables stakes: this will result in massive code changes, so build the spec with your colleague.
    - TODO (me): add at least a sectioon about pair programming etiquete?

## References

- Overview of the ACD workflow
  - Section - The ACD workflow in https://beyond.minimumcd.org/docs/agentic-cd/
- Bryan’s talk at devopsdays Dallas, Texas https://www.youtube.com/watch?v=8u_FVTRtqrw

## Next up:

- DONE review what i have against what claude gave me
- Try it out
  - Create a new repo and feature request
  - Write the feature
  - Document learnings
- Improve this documentation
  - Missing at least a quick mention to TDD
  - Work decomposition needs a tldr + some good/bad examples from our team context
    - https://beyond.minimumcd.org/docs/foundations/work-decomposition/
