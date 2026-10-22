# Changelog

All notable changes to hermes-antigravity-auth.

## [1.9.1] — 2026-10-22

### Added
- **pi-antigravity Model Grouping Engine**: Full implementation of `Rahularya01/pi-antigravity`'s `grouping.ts` architecture (`antigravity_auth/grouping.py`).
  - Automatic collapsing of runtime variants (`-low`, `-medium`, `-high`, `-extra-low`, `-tiered`, `-agent`) into canonical public model entries (`gemini-3.8-flash`, `gemini-3.5-flash`, `claude-opus-4-6`, `claude-sonnet-4-6`, `gemini-2.5-pro`, `gpt-oss-120b`, `gemini-3.1-flash-image`).
  - Merged agent singletons (`gemini-3-flash-agent` merged as High tier into `gemini-3.5-flash`).
  - Priority display formatting matching `pi-antigravity`: Model ID, Name, Thinking Levels, Context Window, Max Output, Quota Remaining, and Reset Time.
  - Added `--all` flag to `hermes agy models` to inspect raw runtime IDs.
  - Priority registration of grouped public models into Hermes Agent's model picker and provider catalog.

## [1.9.0] — 2026-10-22

### Added
- **Gemini 4 Argon & Flash Generations**: Added support for `gemini-4-argon` (low/medium/high), `gemini-3.8-flash` (low/medium/high/tiered), `gemini-3.7-flash`, and `gemini-3.6-flash`.
- **Wire Thinking Budget Engine**: Full parity with `Rahularya01/pi-antigravity` integer thinkingBudget wire format (-1, 4000, 1000, 0, 10000, 10001, 1024, 8192) including strict Argon 0-budget rejection.
- **Dynamic Model Catalog Discovery**: Added `antigravity_auth/discovery.py` querying `/v1internal:fetchAvailableModels` with 4-hour caching and `hermes antigravity models` CLI command.
- **Live User Quota Summary**: Querying `/v1internal:retrieveUserQuotaSummary` with visual progress bars and human-readable reset times (`hermes antigravity usage`).
- **Native Image Generation**: Added `antigravity_auth/image.py` supporting `gemini-3.1-flash-image` with 10 aspect ratios (1:1, 16:9, etc.), base64 decoding, CLI command `hermes antigravity image`, and Hermes tool `antigravity_generate_image`.

## [1.8.0] — 2026-08-21

### Added
- Single-source packaging metadata via `antigravity_auth/_version.py`.
- Runtime hardening for Antigravity auth diagnostics and wrapper drift detection.
- Clean-install pipeline with source-archive smoke test in CI.
- Selftest smoke command for offline verification.

### Changed
- Enforced canonical Hermes install path and tightened auth diagnostics.
- Hardened quota check state handling.
- Diagnosed installed antigravity wrappers for version drift.

### Fixed
- Hardened Antigravity auth runtime safety.
- Hardened Hermes v0.18 Antigravity routing.

## [1.7.0] — 2026-05-31

### Added
- Package build guard rejects local `antigravity_auth/_credentials.py` so wheels/sdists cannot accidentally include private OAuth client credentials.
- Safe OAuth credential resolver supports environment variables and external `~/.hermes/antigravity-credentials.json` without relying on package-tree secrets.
- Account-manager helper resolves the request-selected account by safe index for response-hook bookkeeping.
- Process file locks serialize account-store writes and `auth.json` read-modify-write updates across Hermes processes.
- Test suite mocks bundled credentials fallback so tests pass reliably in CI checkouts.

### Changed
- GitHub Actions CI now uses Node 24-capable `actions/checkout@v6` and `actions/setup-python@v6`.
- Response hooks apply 403/429 handling to the request-selected account rather than whichever account is current later.
- 429 handling uses reason-aware backoff data from Cloud Code error responses.
- Runtime request headers reuse stored per-account Antigravity fingerprints instead of generating random selected-account fallback headers.
- Provider wrapper installs the interceptor best-effort/idempotently.
- Streaming SSE behavior is documented and tested as passthrough for Hermes' native Cloud Code parser.

### Fixed
- Request authorization now fails closed when account selection cannot provide a token, preventing stale bearer reuse.
- Managed runtime refreshes persist `invalid_grant` cleanup and avoid resurrecting revoked accounts from stale managers.
- Anthropic-style content-array `tool_use` / `tool_result` IDs are preserved during message transforms.
- Nullable JSON Schema fields no longer get removed from `required` solely because they allow `null`.
- Debug logs are written with private permissions and redact additional token/key shapes.
- Existing YAML config files now warn visibly when PyYAML is unavailable.

## [1.6.0] — 2026-05-21

### Added
- 403 handling: shadow-banned/ineligible accounts placed on 24h cooldown with auto-rotation
- Rate limit marking for both header styles (antigravity + gemini-cli) on 429 responses
- Account quota cache: soft threshold rotation before hard rate limits
- `token_watchdog.py`: background daemon for proactive access token refresh

### Changed
- Interceptor rewritten as headers-only httpx event hooks (removed broken `_HttpProxy`)
- Endpoint routing defaults to PROD — daily sandbox rejects free-tier Claude accounts
- Gemini CLI header style only uses PROD endpoint (sandbox endpoints skipped)
- `transform/__init__.py` explicitly exports all submodule symbols

### Fixed
- Account rotation actually skips exhausted accounts (both header styles marked)
- Token refresh persists refreshed tokens to both auth.json and google_oauth.json stores

## [1.5.0] — 2026-05-20

### Added
- Multi-account management with health-score-based rotation
- Dual quota pool tracking (Antigravity + Gemini CLI)
- Device fingerprint generation per account
- `antigravity login`, `antigravity accounts`, `antigravity check` CLI commands
- Hermes provider profile with Antigravity branding in `/model` picker
- Google Search tool registration (`google_antigravity_search`)
- Session recovery: tool_result_missing, thinking_block_order detection

### Changed
- Python port from TypeScript: complete rewrite as pip-installable package
- Stdlib-only (urllib, json, dataclasses) — no heavy framework dependencies

## [1.0.0] — 2026-05-19

### Added
- Initial release: port of opencode-antigravity-auth (NoeFabris)
- PKCE OAuth 2.0 flow for Google Antigravity
- Request/response transformation pipeline (messages, schema, envelope, thinking)
- Claude thinking block stripping and signature handling
- JSON Schema sanitization for Antigravity API compatibility
