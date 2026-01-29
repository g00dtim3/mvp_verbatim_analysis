# CLAUDE.md — AI Assistant Guide for mvp_verbatim_analysis

## Project Summary

French-language MVP for AI-powered qualitative/quantitative analysis of customer verbatims (reviews, social media) from Brandwatch and Semantiweb sources. Uses GPT-4 to extract themes, merge duplicates, and quantify insights with GIDA pharmaceutical taxonomy detection.

## Tech Stack

- **Language:** Python 3.11+
- **Frontend:** Streamlit 1.29.0 (multi-page app)
- **Database:** PostgreSQL 15+ via SQLAlchemy 2.0.23 (UUID PKs, JSONB metadata)
- **LLM:** OpenAI GPT-4 Turbo via `openai` + `langchain` + `langgraph`
- **NLP:** rapidfuzz (dedup), scikit-learn (TF-IDF), tiktoken (token counting)
- **Deployment:** Posit Connect (rsconnect-python)
- **Testing:** pytest (stub — no tests written yet)

## Directory Structure

```
app/                    # Streamlit frontend
  app.py                # Main entry point (landing page, system checks)
  pages/
    1_import.py         # CSV upload with auto-detection (Brandwatch/Semantiweb)
    [2-5 planned]       # cleaning, analysis, quantification, exploration

src/                    # Core business logic
  db/
    connection.py       # SQLAlchemy engine, session context manager, pool config
    models.py           # 10 ORM models (Project, ProjectVerbatim, AnalysisRun, etc.)
  llm/
    client.py           # OpenAI singleton client, retry logic (tenacity), cost estimation
    prompts.py          # 3 system prompts (analyze, merge, generate keywords)
  utils/
    config.py           # Pydantic BaseSettings, column mappings, constants
  api/                  # Business logic (placeholder)

scripts/
  init_schema.sql       # Full DB schema (tables, indexes, views, triggers)

notebooks/
  01_spike_langgraph.ipynb  # LangGraph POC validation

tests/                  # Empty — needs implementation
docker-compose.yml      # PostgreSQL + pgAdmin
requirements.txt        # 50 dependencies
```

## Commands

```bash
# Setup
docker-compose up -d db                    # Start PostgreSQL
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run app
streamlit run app/app.py

# Run tests (when implemented)
pytest

# Deploy
rsconnect deploy streamlit app/ --name verbatim-analysis
```

## Required Environment Variables

```
DATABASE_URL=postgresql://user:pass@localhost:5432/verbatim_analysis
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview   # optional, this is the default
DEBUG=true                          # optional
```

## Key Conventions

- **Language:** All UI, documentation, comments, and prompts are in **French**
- **IDs:** UUID v4 for all primary keys
- **Config:** Centralized in `src/utils/config.py` via Pydantic `BaseSettings` with `get_settings()` singleton
- **DB sessions:** Always use the `get_db()` context manager from `src/db/connection.py`
- **LLM calls:** Use `call_llm()` or `call_llm_json()` from `src/llm/client.py` — they handle retries (tenacity, exponential backoff) and cost tracking
- **Column naming:** snake_case everywhere (Python and SQL)
- **Timestamps:** PostgreSQL `TIMESTAMP WITH TIME ZONE`
- **Metadata:** JSONB fields (`extra_data`, `metadata`) for extensibility
- **Status enums:** `pending → processing → success/partial/failed/interrupted`
- **Error handling:** try/except with `loguru` logger
- **Text fields:** `full_text` (raw) and `full_text_clean` (processed)

## Architecture Patterns

- **ORM-first** — all DB access through SQLAlchemy models, not raw SQL
- **Singleton clients** — OpenAI client lazily initialized once
- **Retry with tenacity** — exponential backoff for LLM and API calls
- **Two analysis modes:** Rapid (750-sample) and Full (chunked with parallelization)
- **Two-pass theme merging:** Pass 1 = fuzzy matching (rapidfuzz 0.92 threshold + Jaccard 0.75), Pass 2 = LLM semantic merge
- **Quantification is deterministic** — Python counting, not LLM

## Data Sources

- **Brandwatch:** auto-detected by columns `Full Text`, `Page Type`, `Query Id`
- **Semantiweb:** auto-detected by columns `review_text`, `review_date`, `review_id`
- **Generic CSV:** manual column mapping fallback

## Important Thresholds (from config)

| Setting | Default |
|---------|---------|
| max_verbatims | 30,000 |
| chunk_size | 200 verbatims |
| max_chunks | 500 |
| sample_size_rapid | 750 |
| dedup_threshold | 0.90 |
| fuzzy_merge_threshold | 0.92 |
| jaccard_merge_threshold | 0.75 |
| llm_timeout | 120s |
| llm_max_retries | 3 |
| llm_parallel_calls | 10 |

## Implementation Status

**Done:** DB schema/models, OpenAI client, config system, import page, prompts, LangGraph POC, Docker setup.

**TODO:** Pages 2-5 (cleaning/analysis/quantification/exploration), actual DB inserts in import, LangGraph pipeline, dedup module, text cleaning pipeline, theme fusion, quantification engine, GIDA detection, export (Excel/CSV/MD), test suite, CI/CD.

## Code Style

- Type hints throughout (use `TypedDict` for structured dicts)
- Docstrings on public functions
- Constants in ALL_CAPS with descriptive prefixes
- Streamlit session state for inter-page data sharing
- Custom CSS color: `#1F4E79` (primary blue)
