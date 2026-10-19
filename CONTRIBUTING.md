# Contributing

Contributions are welcome if they are supported by synthetic or irreversibly
sanitised reproduction cases and preserve the evidence-first gates.

By submitting a pull request or other contribution, you agree that your
contribution is licensed under the repository's MIT License, subject to any
third-party rights you must respect. You confirm that you have the authority to
submit it. Contributors retain the copyrights they own; this is not a
copyright assignment or a contributor licence agreement.

1. Create an issue describing the problem without uploading actual minutes,
   attendance records, personal data or signature images.
2. Add a regression test that fails on the prior behaviour, and a true-positive
   test that confirms the gate was not disabled.
3. Run `python -m pytest tests/ -v` and
   `python skills/ccc-minutes-builder/scripts/preflight.py`.
4. Update `research/failures.md`, the README and documented input contracts.
5. Submit a focused pull request for review. Do not publish a new tag or
   release without the release checklist passing.

External dependencies remain governed by their respective licences, and
source materials in users' workspaces are not contributions to this project.
