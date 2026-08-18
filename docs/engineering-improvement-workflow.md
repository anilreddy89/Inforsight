# Engineering Improvement Workflow

## Purpose

This workflow explains how Inforsight records and delivers engineering improvements discovered during implementation, review, testing, or later maintenance. It is intended for defects, latent risks, technical debt, type-safety improvements, test gaps, documentation gaps, and small refactors that do not belong to the currently active feature.

The goal is to preserve useful observations without expanding an active pull request unexpectedly or losing the work after review.

## Core principles

1. GitHub Issues are the operational source of truth for actionable improvements.
2. GitHub Milestones determine the intended release, not the order in which an observation was discovered.
3. `docs/backlog.md` contains phase-level roadmap work, not every local refactor.
4. A completed pull request should not be reopened or rewritten to absorb a later observation.
5. Improvements must have observable acceptance checks before implementation begins.
6. Clean-room, point-in-time, authority, and human-review boundaries apply to maintenance work as they do to features.
7. A release includes an improvement only after its pull request is merged and its issue is closed.

## Sources of improvement observations

An improvement may be identified during:

- Design or implementation.
- Code review or post-merge review.
- Automated test failure or missing-test analysis.
- Static analysis, dependency review, or security review.
- Documentation review.
- Production-like demonstrations using fictional data.
- Work on a later feature that exposes limitations in an earlier design.

Record the observation when it is understood well enough to explain the affected behavior and likely risk. It does not need to have an implementation solution yet.

## Classify the observation

Before creating work, determine what kind of change it represents.

| Classification | Meaning | Typical handling |
| --- | --- | --- |
| Current defect | Existing supported behavior is incorrect or unsafe. | Prioritize based on impact; fix before release when it blocks an acceptance gate. |
| Latent defect | Current paths work, but a plausible extension would violate an invariant. | Create a maintenance issue and schedule before the affected extension. |
| Test gap | Behavior exists but lacks objective verification. | Track with the behavior it protects or as a focused testing issue. |
| Type or tooling improvement | Runtime behavior is correct, but developer feedback or maintainability is weak. | Bundle with closely related maintenance work when the scope remains coherent. |
| Refactor | Internal structure should improve without changing supported behavior. | Require regression tests and a clearly stated nonbehavioral boundary. |
| Documentation gap | The implementation or operating boundary is unclear. | Fix immediately only when small and in scope; otherwise create a documentation issue. |
| Architecture decision | The proposal changes a durable boundary, dependency, or system direction. | Create a decision issue and ADR before implementation. |
| Security or privacy concern | The observation could expose credentials, personal data, authorization failures, or proprietary material. | Do not use a public issue for sensitive details; follow `SECURITY.md`. |

## Decide whether to fix now or track separately

Fix the observation in the active pull request only when all of these conditions hold:

- It is necessary for the pull request's stated acceptance checks.
- It remains within the issue's declared scope.
- The change is small enough to review with the existing work.
- It does not introduce a new contract or architecture decision.
- It can be fully tested before merge.

Create a separate issue when any of these conditions hold:

- The current implementation satisfies its contract, but a future extension may fail.
- The change expands the supported behavior or event taxonomy.
- It requires additional design decisions.
- It would make the active pull request materially larger or harder to review.
- It was discovered after the original pull request merged.
- It should ship in a different milestone.

When uncertain, prefer a focused follow-up issue. A truthful sequence of small changes is easier to review and maintain than an expanding pull request.

## Check for existing work

Before creating an issue:

1. Search open and closed GitHub Issues for the affected component and behavior.
2. Review `docs/backlog.md` for an existing phase-level item.
3. Review relevant ADRs and experiment notes.
4. Add the observation to an existing issue only when its outcome and acceptance checks already cover the work.
5. Cross-link related issues instead of duplicating them.

Do not place sensitive vulnerability details, credentials, customer information, or proprietary material in an issue.

## Create the GitHub issue

Use `.github/ISSUE_TEMPLATE/implementation.yml` for a scoped engineering improvement. Complete every applicable field as follows.

### Title

Use an observable, imperative outcome rather than a vague category.

Good:

```text
[Implementation] Harden repeatable simulator identifiers and callback typing
```

Avoid:

```text
Code cleanup
Fix generator
Technical debt
```

### Outcome

Describe what will be observably different when the issue is complete. Avoid prescribing a large implementation unless the design is already decided.

Include:

- The component affected.
- The protected behavior or invariant.
- Whether supported runtime behavior should remain unchanged.

### Context

Explain:

- How the observation was discovered.
- Whether it is a current defect, latent defect, test gap, or maintainability improvement.
- Why it matters.
- Why it is separate from the original feature.
- Relevant issues, pull requests, schemas, ADRs, or documentation.

### Acceptance checks

Use objective checkboxes. Cover behavior, regression protection, documentation, and repository gates.

Typical checks include:

```markdown
- [ ] The protected invariant is implemented for the documented case.
- [ ] A regression test fails without the fix and passes with it.
- [ ] Existing deterministic or contract behavior remains valid.
- [ ] Relevant documentation is updated.
- [ ] `make check` passes.
- [ ] `git diff --check` passes.
```

Do not use acceptance checks such as "code looks better" or "refactor is complete" without an observable condition.

### Evidence

List what reviewers should expect in the pull request:

- Focused test names and output.
- Full `make check` output.
- Before-and-after examples when useful.
- Static-analysis output when the improvement concerns typing or tooling.
- Documentation or ADR updates.
- Confirmation that deterministic output did or did not change.

### Out of scope

Name adjacent work explicitly. This prevents a maintenance issue from becoming a feature expansion.

Examples:

- New event types or contract fields.
- New default scenarios.
- General refactoring of unrelated identifiers.
- Point-in-time reconstruction.
- Dataset or model changes.

### Dependencies

Record:

- The issue or pull request that introduced the relevant component.
- Work that must merge first.
- Follow-up features that should not proceed until the improvement is complete.
- `None` when there are no dependencies.

### Boundaries

Confirm all repository-boundary checkboxes honestly. If a checkbox cannot be confirmed, stop and resolve the boundary before implementation.

## Labels and priority

Use the repository's available labels. If these labels are not configured, treat the following as recommended categories rather than creating labels without repository-owner agreement:

- `maintenance` for internal hardening and refactoring.
- `technical-debt` for a known maintainability or extension risk.
- `bug` for incorrect supported behavior.
- `testing` for a primarily test-focused gap.
- `documentation` for documentation-only work.
- `security` only for public, nonsensitive security hardening; use private reporting for sensitive details.

Set priority from evidence, not convenience:

| Priority | Use when |
| --- | --- |
| Release blocking | A release acceptance gate, contract, security boundary, or supported workflow is currently broken. |
| High | A likely near-term path can violate an invariant or corrupt output. |
| Normal | The improvement prevents a plausible future problem or materially improves maintainability. |
| Low | The change is beneficial but has no identified near-term consumer or risk. |

## Assign a milestone

Assign the issue to the earliest release that genuinely needs the improvement.

- Use the current milestone when the release should not be considered complete without the change.
- Use a maintenance milestone when the current release is already complete but requires a focused hardening pass.
- Leave the issue unassigned only when there is no credible release target; review unassigned issues during milestone planning.

Do not reopen or rewrite a merged feature pull request. A post-merge improvement receives its own issue, branch, pull request, and completion evidence.

## When to update the repository backlog

Add an item to `docs/backlog.md` when the improvement:

- Represents phase-level work.
- Introduces a durable capability or contract.
- Blocks multiple downstream issues.
- Groups several related improvement issues into a roadmap theme.

Do not add every isolated type annotation, test case, or small refactor. GitHub Issues, labels, and milestones are sufficient for focused maintenance work.

If related work accumulates, add a roadmap-level entry such as:

```markdown
## Cross-cutting engineering improvements

- [ ] Harden repeatable simulator identifiers and static typing.
```

The roadmap checkbox should represent the group, while linked GitHub Issues contain the implementable details.

## Implementation lifecycle

Follow the same lifecycle as feature work:

```text
Observation -> GitHub issue -> Milestone -> Branch -> Tests and implementation
            -> Pull request -> CI and review -> Merge -> Issue closed -> Release notes
```

### Before implementation

1. Confirm the issue has an observable outcome and acceptance checks.
2. Confirm scope and milestone.
3. Create a branch linked to the issue number, for example:

   ```text
   fix/<issue-number>-repeatable-simulator-identifiers
   ```

   Use `feat/` only when the issue adds supported behavior; use `docs/` for documentation-only changes.

4. Capture the failing or missing case with a focused test when practical.

### During implementation

1. Make the smallest coherent change that satisfies the issue.
2. Preserve unrelated user and repository changes.
3. Update tests and documentation with the behavior.
4. Record a generator or contract version change when deterministic public output or a versioned contract intentionally changes.
5. Avoid opportunistic refactors outside the issue.

### Before opening the pull request

Run:

```bash
source .venv/bin/activate
make check
git diff --check
git status --short
git diff --stat
git diff
```

Confirm that generated datasets, caches, credentials, temporary output, and unrelated changes are absent.

### Pull request

The pull request should:

- Summarize the protected behavior or maintainability improvement.
- Explain whether runtime or serialized output changed.
- Include focused and full verification evidence.
- Restate important out-of-scope work.
- Use `Closes #<issue-number>` when merge should close the issue.
- Use the same milestone as the issue.

### After merge

1. Confirm required CI checks passed on the merged revision.
2. Confirm the linked issue closed.
3. Confirm milestone assignment and completion state.
4. Update `docs/backlog.md` only if the issue completes a tracked roadmap item.
5. Update personal progress records separately from tracked repository status.
6. Add a concise release-note entry when the improvement affects users, contributors, reproducibility, contracts, security boundaries, or supported workflows.
7. Do not describe unmerged work as released.

## Release-note guidance

Release notes should explain impact rather than internal mechanics.

Example:

```markdown
### Reliability

- Prevent duplicate synthetic service-contact identifiers when a policy history contains multiple contacts.

### Developer experience

- Add an explicit callback type for simulator event construction.
```

Purely internal changes may be omitted from public release notes when they have no user, contributor, reproducibility, or safety impact. They should still remain traceable through their issue and pull request.

## Example: simulator observations

Suppose review identifies these observations:

1. Service-contact identifiers use a hardcoded secondary index, which is unique today because each policy has at most one contact but would collide if a later scenario added another.
2. The service-contact helper accepts an event-building callback typed as `Any`, even though the callback has a known signature.

Classification:

- The identifier issue is a latent defect.
- The callback annotation is a type-safety improvement.
- Neither invalidates current one-contact scenarios.
- Both affect the same helper and can be reviewed coherently in one maintenance issue.

Suggested issue outcome:

```markdown
Make repeatable simulator entity identifiers safe for multiple events of the same type within one policy, and replace the unbounded service-contact callback type with an explicit callable signature.
```

Suggested acceptance checks:

```markdown
- [ ] Service-contact identifiers use an explicit sequence rather than a hardcoded secondary index.
- [ ] Two service contacts for one policy receive different contract-valid identifiers.
- [ ] Existing deterministic output remains stable unless a generator-version change is explicitly documented.
- [ ] The event-building callback uses a precise callable type.
- [ ] Automated tests cover multiple contacts and identifier uniqueness.
- [ ] Existing schema and deterministic-generation tests pass.
- [ ] `make check` passes.
- [ ] `git diff --check` passes.
```

Suggested out-of-scope boundary:

```markdown
- Adding new service-contact scenarios to the default corpus.
- Changing policy-event or service payload contracts.
- Adding new event types.
- Point-in-time reconstruction.
- General refactoring of unrelated generator identifiers.
```

Because the observations were found after the original generator pull request merged, they should use a new issue and pull request rather than modifying the history of the completed feature.

## Periodic maintenance review

At milestone planning and before a release:

1. Review open maintenance, technical-debt, testing, and documentation issues.
2. Confirm priorities still match current evidence.
3. Assign issues that block the milestone.
4. Close issues that are obsolete, documenting why.
5. Split issues that have grown beyond one reviewable outcome.
6. Confirm deferred issues do not block downstream contracts or acceptance gates.
7. Prepare release notes from merged issues, not from planned work.

An open improvement issue is not a failure. It is evidence that the project distinguishes known limitations from completed behavior and manages them transparently.
