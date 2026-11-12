# Changelog

All notable changes to the Skyscanner AI project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-12

### Sprint 3: Polish, Cleanup, and Long-Term Sustainability (AG-087 to AG-132)
#### Added
- **API Quota & Circuit Breaker**: Resilient stateful circuit breaker (`CLOSED` / `OPEN` / `HALF_OPEN`) and sliding-window quota tracking per external provider in `app/tools/api_quota.py` (`AG-123`, `AG-124`).
- **Shared Test Fixtures**: Comprehensive `backend/tests/conftest.py` with mock LLM client, async HTTP client, and standardized constraint fixtures (`AG-122`).
- **Comprehensive Agent & Cache Tests**: Added unit tests in `test_trip_structuring.py` (`AG-119`), `test_cache.py` (`AG-120`), and `test_tool_router.py` (`AG-121`).
- **Frontend-Backend Contract Tests**: Automated Pydantic vs TypeScript schema validation in `test_schema_contracts.py` (`AG-118`).
- **Frontend Component Specs**: Vitest test coverage across `navbar`, `footer`, `flight-search`, `hotel-search`, and `flight-results` (`AG-116`).
- **E2E Smoke Suite**: Playwright end-to-end smoke tests and configuration in `playwright.config.ts` and `e2e/smoke.spec.ts` (`AG-117`).
- **Multi-Environment DevOps**: Staging service declaration and gated production deploy hooks in `render.yaml` (`AG-125`, `AG-128`).
- **Dependabot Configuration**: Automated weekly dependency updates for npm and pip (`AG-132`).

#### Changed
- **Flight & Transport Realism**: Authentic airline carriers (British Airways, Lufthansa, Emirates) in fallbacks; sanitized hallucinated airline names; destination-aware transit booking URLs with Rome2Rio, SNCF, SmartEX, SBB, and IRCTC (`AG-093`, `AG-099`).
- **Client Lifecycle Management**: Added clean `close()` hooks and FastAPI lifespan management for `httpx` async clients (`AG-130`).
- **Rate Limiting Hardening**: Extended IP rate limiting across all write endpoints under `/api/` and added periodic expired key pruning (`AG-094`, `AG-129`).
- **Orchestrator Improvements**: Even spread day reduction in `_remove_extra_days` preserving trip endpoints; capped narrative token budget to avoid rate limits (`AG-097`, `AG-100`).
- **Frontend Polish & A11y**: Dynamic footer copyright year, interactive dropdowns, mobile-responsive map modal (`max-w-lg sm:max-w-3xl`), `aria-label="Close route map"`, `aria-hidden="true"` on decorative icons, WCAG AA contrast improvement in dark hero, and `no-scrollbar` styling on suggestion chips (`AG-103`, `AG-105`, `AG-106`, `AG-107`, `AG-112`, `AG-113`, `AG-114`, `AG-115`).
- **Safety**: Safe popup navigation handler preventing silent failure when browser popup blockers are active (`AG-111`).
- **Cleanup**: Removed dead `progressInterval` in travel planner, duplicate `getAgodaHotelUrl` method, and duplicate `lucide-angular` package (`AG-101`, `AG-102`, `AG-131`).
- **Model Alignment**: Synchronized `GEMINI_MODEL=gemini-2.0-flash` across `config.py`, `render.yaml`, and `.env.example` (`AG-126`).

---

## [0.3.0] - 2026-11-12

### Sprint 2: Architecture Hardening and Quality Assurance (AG-036 to AG-086)
- Consolidated robust JSON extraction and repair pipelines with multiple fallback passes (`AG-036`, `AG-037`).
- LRU caching and bounded memory stores for airport lookups, tool router, and flight search (`AG-038`).
- Write endpoint rate-limiting and audit logging (`AG-039`, `AG-076`).
- Dark mode CSS variable unification, mobile bottom navigation, and accessible touch targets.
- Comprehensive unit test suites for `DestinationAgent`, `ReviewAgent`, `TokenTracker`, and resilient LLM clients (`AG-077` to `AG-081`).
- CI/CD workflow hardening with Python 3.12, ruff linting, bandit security scanning, and code coverage (`AG-072`, `AG-082`, `AG-083`, `AG-084`).

---

## [0.2.0] - 2026-11-12

### Sprint 1: Core Engine Quality and Multi-Currency Unification (AG-006 to AG-035)
- Automated self-correcting repair loop in `ReviewAgent` (`AG-006`).
- Duration-aware hotel night calculations and 45% budget allocation ceiling (`AG-008`).
- Safe token budget truncation and dynamic IATA airport code resolution (`AG-010`, `AG-012`).
- 140+ city geographic coordinate fallback registry (`AG-013`).
- SSR-safe browser APIs, modal dialog backdrop dismissals, and responsive tab state sharing (`AG-022`, `AG-025`, `AG-032`).

---

## [0.1.0] - 2026-11-12

### Sprint 0: Critical Fixes and Security Hardening (AG-001 to AG-005)
- Removed hardcoded credentials and secured environment variable access (`AG-001`, `AG-005`).
- Fixed hotel night multipliers and eliminated double currency conversion bugs (`AG-002`, `AG-004`).
- Introduced unified single-source-of-truth FX conversion module with live ECB parity fallback (`AG-003`).

