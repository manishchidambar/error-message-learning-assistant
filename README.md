# Error Message Learning Assistant

A production-ready Streamlit app that helps developers understand stack traces, pinpoint root causes, and apply corrected code quickly.

## Highlights

- Modern dark-mode, glassmorphic UI with gradient accents and animated status badge
- Quick-start debugging templates (Python, JavaScript, SQL)
- Optional Gemini/OpenAI API-key powered diagnosis
- Automatic offline fallback engine with 12+ realistic error-pattern rules
- Structured output cards:
  - 💡 What Happened?
  - 🔍 Root Cause Identified
  - 🛠️ The Fix & Side-by-Side Comparison
  - 🧠 Knowledge Check & Best Practice

## Supported Languages

- Python
- JavaScript
- TypeScript
- C++
- Java
- Go
- SQL

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## LLM Integration (Optional)

In the sidebar, provide a Gemini or OpenAI API key.

- `AIza...` keys auto-route to Gemini (`gemini-1.5-flash`)
- `sk-...` keys auto-route to OpenAI (`gpt-4o-mini`)
- If no key is provided (or the API call fails), the app automatically uses the built-in offline diagnosis engine

## Repository Deliverables

- `app.py` — full Streamlit UI, custom CSS, quick templates, fallback diagnostics, optional LLM handler
- `requirements.txt` — runtime dependencies
- `README.md` — setup, features, and usage
