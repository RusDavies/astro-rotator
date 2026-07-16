# Public Release Checklist

Use this checklist before changing the GitHub repository visibility to public.
Do not publish the repository until every required item is complete.

## Repository Safety

- [ ] Confirm `RusDavies/astro-rotator` is still private before starting the review.
- [ ] Confirm the repository history contains only the sanitized product history.
- [ ] Search all tracked files and history for known private-management markers.
  Replace the placeholder pattern with the private project/channel terms from
  the management repository before running:

  ```bash
  git grep -n -I -i -E '<private-marker-regex>' $(git rev-list --all) -- . || true
  ```

- [ ] Confirm no raw astrophotography frames, downloaded sample archives, generated personal reports, private location/timestamp metadata, API tokens, credentials, or local workspace paths are tracked.
- [ ] Confirm private agent instructions, planning queues, state-tracking files,
  project-management knowledge bases, and internal working logs are absent from
  the public product repository.

## Verification

- [ ] Run the normal local check:

  ```bash
  scripts/check.sh
  ```

- [ ] Run the dependency/security check in an environment with `pip-audit` installed:

  ```bash
  python -m pip install pip-audit==2.10.1
  scripts/security_check.sh
  ```

- [ ] Confirm the latest GitHub Actions `checks` workflow completed successfully on `main`.
- [ ] Review any GitHub Actions annotations. Warnings may be acceptable, but they must be understood and tracked.

## Public Project Hygiene

- [ ] Confirm `README.md` accurately describes current prototype status.
- [ ] Confirm `ROADMAP.md` matches the intended public direction.
- [ ] Confirm `CONTRIBUTING.md` and `SECURITY.md` are present and accurate.
- [ ] Confirm sample-data docs clearly say that third-party/raw datasets must not be redistributed without explicit rights.
- [ ] Confirm the package metadata in `pyproject.toml` points to `https://github.com/RusDavies/astro-rotator`.

## Final Approval

- [ ] Human owner explicitly approves the visibility change.
- [ ] Record the approval in the private management repo before changing visibility.
- [ ] Change repository visibility only after approval:

  ```bash
  gh repo edit RusDavies/astro-rotator --visibility public --accept-visibility-change-consequences
  ```

- [ ] Re-check the repository visibility and latest workflow status after publication.
