# Branching policy

The project uses **only two maintained branches**:

| Branch | Purpose |
| --- | --- |
| `main` | Stable, maintainer-approved source; do not push experimental work here. |
| `dev` | Ongoing development, security fixes, and locally tested changes. |

## Workflow

1. Make and test changes locally.
2. Commit directly to `dev` after local validation.
3. When the maintainer approves a promotion, update `main` from the tested `dev` state.
4. Keep both branches; do not create feature, hotfix, release, or temporary branches.
5. Do not publish a GitHub Release, deploy, or start GitHub-hosted execution without explicit permission.

## GitHub-hosted execution

The maintainer has requested **no GitHub Actions or other GitHub-hosted execution**. The currently checked-in workflow has automatic triggers on `main` pushes, version tags, and pull requests. **Before any push or promotion to `main`**, disable that workflow or remove its automatic triggers without triggering an unwanted run. Commits to `dev` do not match its existing push trigger, and pull requests are not part of this project workflow.

## Obsolete branches

The previous `release/0.4.3-beta-local-validation` and `security/portrait-redirect-validation` branches are obsolete. Their work is preserved in `dev` and/or `main`; they should be deleted after verification.
