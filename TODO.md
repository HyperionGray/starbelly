# Remaining TODO Items

This file tracks intentional deferred work that remains after the current cleanup and security implementation pass.

## Security / Robustness

- Add HTML parsing timeouts around expensive parser operations (`starbelly/extractor.py`) to complement the existing body-size limits.
- Add targeted API input validation and request-size limits for policy/schedule endpoints.
- Plan and execute a migration window to retire legacy pickled `old_urls` payloads once all paused jobs have been rewritten to JSON.

## Test Suite Cleanup

- Refactor `integration/test_subscription.py`:
  - Move integration-setup-heavy logic into more focused fixtures.
  - Convert broad TODO header comments into explicit test-scoped notes and/or split tests into smaller units.

## Optional Future Security Enhancements

- Certificate pinning support for high-trust domains.
- Dependency vulnerability scanning automation in CI.
