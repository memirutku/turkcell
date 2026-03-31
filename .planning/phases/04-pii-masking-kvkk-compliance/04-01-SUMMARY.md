---
phase: 04-pii-masking-kvkk-compliance
plan: 01
subsystem: security
tags: [presidio, spacy, pii, kvkk, turkish-nlp, anonymization]

# Dependency graph
requires:
  - phase: 01-infrastructure-foundation
    provides: FastAPI backend structure, pyproject.toml, config.py
provides:
  - PIIMaskingService with mask() method for Turkish PII detection
  - TcKimlikRecognizer with checksum validation
  - TurkishPhoneRecognizer for +90, 0-prefix, compact formats
  - TurkishIbanRecognizer for compact and spaced IBAN
  - EmailRecognizer configured for Turkish context
affects: [04-02-PLAN, 05-billing-tariff-qa, 07-voice-input-output]

# Tech tracking
tech-stack:
  added: [presidio-analyzer 2.2.362, presidio-anonymizer 2.2.362, spacy 3.8.14, xx_ent_wiki_sm 3.8.0]
  patterns: [PatternRecognizer subclass with validate_result, RecognizerRegistry with supported_languages, NlpEngineProvider for Turkish spaCy]

key-files:
  created:
    - backend/app/recognizers/__init__.py
    - backend/app/recognizers/tc_kimlik_recognizer.py
    - backend/app/recognizers/turkish_phone_recognizer.py
    - backend/app/recognizers/turkish_iban_recognizer.py
    - backend/app/services/pii_service.py
    - backend/tests/test_pii.py
  modified:
    - backend/pyproject.toml
    - backend/app/config.py
    - backend/uv.lock

key-decisions:
  - "Skip load_predefined_recognizers() to avoid English false positives on Turkish text"
  - "RecognizerRegistry must be initialized with supported_languages=['tr'] to match AnalyzerEngine"
  - "TC Kimlik checksum validation via PatternRecognizer.validate_result() works automatically with Presidio"

patterns-established:
  - "PatternRecognizer subclass: class-level PATTERNS and CONTEXT constants, validate_result for checksum"
  - "PIIMaskingService: Presidio AnalyzerEngine + AnonymizerEngine with per-entity OperatorConfig"
  - "Turkish-only registry: no predefined recognizers, only custom Turkish + EmailRecognizer with Turkish context"

requirements-completed: [SEC-01, SEC-02, SEC-05]

# Metrics
duration: 5min
completed: 2026-03-31
---

# Phase 4 Plan 1: PII Recognizers & Masking Service Summary

**Presidio-based PIIMaskingService with TC Kimlik checksum validation, Turkish phone/IBAN/email detection, and 16-test suite**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-31T07:56:51Z
- **Completed:** 2026-03-31T08:02:28Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 9

## Accomplishments
- Installed presidio-analyzer, presidio-anonymizer, spaCy with xx_ent_wiki_sm multilingual NER model
- Created three custom Turkish PII recognizers: TcKimlikRecognizer (with checksum validation), TurkishPhoneRecognizer (3 format patterns), TurkishIbanRecognizer (compact + spaced)
- Built PIIMaskingService wrapping Presidio analyzer+anonymizer with per-entity placeholders ([TC_KIMLIK], [TELEFON], [IBAN], [EMAIL], [ISIM], [PII])
- Added pii_masking_enabled config setting for runtime control
- Comprehensive test suite: 16 tests covering all recognizers, masking service, and SEC-05 security config

## Task Commits

Each task was committed atomically (TDD flow):

1. **Task 1 RED: PII test suite** - `8b1765e` (test) - failing tests for all recognizers and PIIMaskingService
2. **Task 1 GREEN: Recognizers + PIIMaskingService** - `70dc321` (feat) - all implementations, dependencies, config, lint fixes

## Files Created/Modified
- `backend/app/recognizers/__init__.py` - Exports all three recognizer classes
- `backend/app/recognizers/tc_kimlik_recognizer.py` - TC Kimlik No detection with checksum validation
- `backend/app/recognizers/turkish_phone_recognizer.py` - Turkish phone number detection (+90, 0-prefix, compact)
- `backend/app/recognizers/turkish_iban_recognizer.py` - Turkish IBAN detection (compact and spaced)
- `backend/app/services/pii_service.py` - PIIMaskingService wrapping Presidio with Turkish config
- `backend/app/config.py` - Added pii_masking_enabled setting
- `backend/pyproject.toml` - Added presidio-analyzer, presidio-anonymizer, spacy dependencies
- `backend/uv.lock` - Updated lockfile
- `backend/tests/test_pii.py` - 16 tests for PII detection and masking

## Decisions Made
- **Skip predefined recognizers:** Do not call `registry.load_predefined_recognizers()` to prevent English-centric recognizers (US SSN, US phone) from creating false positives on Turkish 11-digit numbers. Only register custom Turkish recognizers + EmailRecognizer with Turkish context words.
- **RecognizerRegistry language config:** Must pass `supported_languages=["tr"]` to RecognizerRegistry constructor to match AnalyzerEngine's supported languages. Default is `["en"]` which causes a ValueError.
- **TC Kimlik validate_result works automatically:** Presidio's PatternRecognizer calls `validate_result()` automatically after regex match -- no need to override `analyze()`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RecognizerRegistry supported_languages mismatch**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** `RecognizerRegistry()` defaults to `supported_languages=["en"]`, but `AnalyzerEngine` was configured with `supported_languages=["tr"]`, causing a ValueError
- **Fix:** Pass `supported_languages=["tr"]` to both `RecognizerRegistry()` in pii_service.py and test helper
- **Files modified:** `backend/app/services/pii_service.py`, `backend/tests/test_pii.py`
- **Verification:** All 16 tests pass, full suite (71 tests) passes
- **Committed in:** 70dc321

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Fix was essential for correct Presidio initialization. No scope creep.

## Issues Encountered
- spaCy model (`xx_ent_wiki_sm`) gets uninstalled when running `uv sync --all-extras` after `uv add`. Re-downloaded after sync. This is a known uv behavior with non-PyPI model packages.

## Known Stubs
None -- all functionality is fully implemented and tested.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PIIMaskingService is ready for integration into ChatService (Plan 02 scope)
- Plan 02 will wire PII masking into ChatService.stream_response(), add log sanitization filter, harden system prompt, and update Dockerfile

## Self-Check: PASSED

- All 9 created/modified files verified present on disk
- Commit 8b1765e (test RED) verified in git log
- Commit 70dc321 (feat GREEN) verified in git log
- All 16 PII tests pass (`uv run pytest tests/test_pii.py -x -v`)
- Full suite 71 tests pass, 2 skipped (`uv run pytest tests/ -v`)
- Ruff lint clean (`uv run ruff check app/recognizers/ app/services/pii_service.py`)

---
*Phase: 04-pii-masking-kvkk-compliance*
*Completed: 2026-03-31*
