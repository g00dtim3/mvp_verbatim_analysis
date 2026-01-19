# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Streamlit Cloud deployment support
- Comprehensive Streamlit Cloud secrets configuration guide
- Python 3.13 compatibility notes in documentation
- SQL scripts for direct database initialization (`sql/create_tables.sql`, `sql/insert_gida_data.sql`)

### Changed
- **BREAKING**: Updated Python requirement from 3.11+ to **3.13**
- Updated SQLAlchemy from 2.0.23 to **2.0.36** (Python 3.13 support)
- Updated Alembic from 1.13.0 to **1.14.0** (Python 3.13 compatibility)
- Switched from psycopg2-binary to **psycopg[binary] 3.3.2** (psycopg3)
- Updated pandas from 2.1.4 to **2.2.3** (prebuilt wheels for Python 3.13)
- Updated pydantic from 2.14.x to **2.10.3** (Python 3.13 compatible)
- Updated pydantic-settings to **2.7.0** (matches pydantic 2.10.x)
- Updated tiktoken from 0.5.2 to **0.8.0** (prebuilt wheels for Python 3.13)
- Updated langchain to **0.3.14** (Python 3.13 compatible)
- Updated langgraph to **0.2.59** (Python 3.13 compatible)
- Updated openai to **1.58.1** (Python 3.13 compatible)
- Updated scikit-learn to **1.5.2** (Python 3.13 compatible)

### Fixed
- **Critical**: Fixed SQLAlchemy incompatibility with Python 3.13 (AssertionError in util.langhelpers)
- **Critical**: Fixed psycopg driver detection - SQLAlchemy now uses psycopg3 instead of trying to import psycopg2
  - Added automatic URL conversion: `postgresql://` → `postgresql+psycopg://`
  - Updated `src/db/connection.py` to handle driver selection
- Fixed pandas Cython compilation errors on Python 3.13
- Fixed pydantic-core Rust compilation errors on Python 3.13
- Fixed tiktoken Rust compilation errors on Python 3.13
- Security fix: Removed `.env` from git tracking, added comprehensive `.gitignore`

### Documentation
- Updated README.md with Python 3.13 requirements
- Updated IMPLEMENTATION.md with detailed Python 3.13 compatibility table
- Added Streamlit Cloud deployment section to README.md
- Added detailed Supabase secrets configuration guide
- Updated hosting options: Streamlit Cloud / Posit Connect

## [1.0.0] - 2026-01-16

### Added
- Initial MVP implementation complete
- 7 EPICs implemented according to specifications v1.2
- Supabase backend support (dual PostgreSQL/Supabase)
- LangGraph orchestration pipeline
- Streamlit UI with 5 pages (Import, Cleaning, Analysis, Quantification, Exploration)
- GIDA ontology integration (version 2026.01, 22 entities)
- Complete database schema (11 tables)
- 2-pass topic merging (algorithmic + LLM)
- Fuzzy deduplication with RapidFuzz
- Stratified sampling for rapid analysis mode
- Python deterministic quantification with negation handling
- Export functionality (Excel, CSV, Markdown)

### Features
- Import CSV from Brandwatch/Semantiweb/Generic sources
- Configurable text cleaning options
- Fuzzy deduplication (threshold 0.80-0.95)
- LLM-powered thematic analysis (GPT-4 Turbo)
- Rapid mode (750 verbatims) and Full mode (unlimited with chunking)
- Topic merging with fuzzy matching and Jaccard similarity
- Ontology generation (keywords, regex, negations)
- Entity recognition for GIDA reference data
- Interactive exploration with filters
- Multi-format export capabilities

## Version History

- **v1.0.0** (2026-01-16): Initial MVP release with full feature set
- **Unreleased**: Python 3.13 compatibility and Streamlit Cloud deployment support
