# Error Message Learning Assistant

A Streamlit learning app that helps students interpret Python and JavaScript error messages using guided hints and example fixes.

## Features

- Default error catalog (`data/default_errors.json`) with 8 detailed Python/JavaScript error entries
- Optional custom dataset upload (CSV/JSON)
- Traceback parser for `error_type`, `file_name`, and `line_number`
- Hybrid error matching (TF-IDF cosine similarity + difflib sequence match)
- Progressive Socratic hints
- Troubleshooting checklist
- Side-by-side code comparison + unified diff
- Exportable Markdown debugging summary

## Project Structure

- `/home/runner/work/error-message-learning-assistant/error-message-learning-assistant/app.py`
- `/home/runner/work/error-message-learning-assistant/error-message-learning-assistant/parser.py`
- `/home/runner/work/error-message-learning-assistant/error-message-learning-assistant/data_loader.py`
- `/home/runner/work/error-message-learning-assistant/error-message-learning-assistant/matcher.py`
- `/home/runner/work/error-message-learning-assistant/error-message-learning-assistant/data/default_errors.json`
- `/home/runner/work/error-message-learning-assistant/error-message-learning-assistant/requirements.txt`

## Setup

```bash
cd /home/runner/work/error-message-learning-assistant/error-message-learning-assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Custom Dataset Schema

Uploaded CSV/JSON files must include these columns:

- `id`
- `language`
- `error_type`
- `error_pattern`
- `concept_nudge`
- `location_clue`
- `root_cause`
- `troubleshooting_checklist` (list in JSON or `|`-separated text in CSV)
- `bad_code`
- `fixed_code`
