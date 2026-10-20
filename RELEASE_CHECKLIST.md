# Release gate

Do not tag or publish until every mandatory item is verified on the exact
release commit. Record a URL or command output for each check.

- [ ] Document the **actual copyright holder** in `LICENSE`; do not assume
      that a GitHub handle establishes ownership.
- [ ] Obtain a passing CI run on Python 3.10, 3.11 and 3.12.
- [ ] Obtain a passing `claude plugin validate . --strict` run.
- [ ] Confirm confirmed-only row-source tests fail for suggestions/empty maps.
- [ ] Confirm missing, malformed, unnumbered and duplicate DOCX cases fail.
- [ ] Confirm first-body-mention tests pass and missing titles fail.
- [ ] Confirm PostToolUse fails closed for damaged final files and no recursive
      scan of unrelated project directories.
- [ ] Verify temp media and previews stay within ignored workspaces.
- [ ] Confirm preflight and image-swap tests pass on supported platforms.
- [ ] Run the final gates against at least one **consented, fully sanitised**
      representative document, or explicitly declare that this evidence is
      unavailable and restrict the release to a developer preview.
- [ ] Review README, affiliated organisation disclaimer, third-party notices,
      CONTRIBUTING.md, and security guidance.
- [ ] Get a human review of the release commit and run all release tests again.
- [ ] Rebuild the generic version with `python tools/build_portable.py`
      after any change to the skill or its version; CI fails until you do.
- [ ] Tag `v<version>` on that **verified** commit, where `<version>` is the
      version in `plugins/ccc-minutes-builder/.claude-plugin/plugin.json`
      (currently 0.2.0), and publish release notes.

Tagging is prohibited while ownership is unresolved or CI is unverified.
