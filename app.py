import difflib

import streamlit as st

from data_loader import load_default_catalog, load_uploaded_dataset, merge_catalogs
from matcher import ErrorMatcher
from parser import extract_error_details


def _build_markdown_summary(error_input: str, parsed: dict, selected: dict) -> str:
    checklist = "\n".join([f"- [ ] {item}" for item in selected.get("troubleshooting_checklist", [])])
    return f"""# Debugging Summary

## Student Error
```
{error_input.strip()}
```

## Parsed Clues
- **Error Type**: {parsed.get('error_type') or 'Unknown'}
- **File**: {parsed.get('file_name') or 'Unknown'}
- **Line**: {parsed.get('line_number') or 'Unknown'}

## Likely Root Cause
{selected.get('root_cause', 'N/A')}

## Troubleshooting Checklist
{checklist or '- [ ] No checklist items available'}

## Code Correction Example
### Problematic Code
```text
{selected.get('bad_code', '').strip()}
```

### Improved Code
```text
{selected.get('fixed_code', '').strip()}
```
"""


def main():
    st.set_page_config(page_title="Error Message Learning Assistant", page_icon="🛠️", layout="wide")
    st.title("🛠️ Error Message Learning Assistant")
    st.write("Upload an optional custom dataset, then paste an error message to get guided debugging help.")

    default_df = load_default_catalog()

    st.sidebar.header("Dataset")
    uploaded_file = st.sidebar.file_uploader("Upload custom CSV/JSON", type=["csv", "json"])

    custom_df = None
    if uploaded_file is not None:
        try:
            custom_df = load_uploaded_dataset(uploaded_file)
            st.sidebar.success(f"Loaded {len(custom_df)} custom entries")
        except Exception as exc:
            st.sidebar.error(f"Could not load uploaded file: {exc}")

    catalog = merge_catalogs(default_df, custom_df)
    matcher = ErrorMatcher(catalog)

    error_input = st.text_area("Paste your traceback / error stack", height=220)

    if "hint_level" not in st.session_state:
        st.session_state.hint_level = 0

    if st.button("Analyze Error") and error_input.strip():
        st.session_state.hint_level = 0

    if error_input.strip():
        parsed = extract_error_details(error_input)
        matches = matcher.match(error_input, parsed.get("error_type"), top_k=3)

        if not matches:
            st.info("No strong match found. Try pasting a fuller traceback.")
            return

        selected = matches[0]

        st.subheader("Top Match")
        st.write(
            f"**{selected['language']} - {selected['error_type']}**  "
            f"(confidence: {selected['match_score']:.2f})"
        )
        st.caption(f"Pattern: {selected['error_pattern']}")

        with st.expander("Parsed traceback clues", expanded=True):
            st.write(parsed)

        st.subheader("Progressive Socratic Hints")
        hints = [
            selected.get("concept_nudge", ""),
            selected.get("location_clue", ""),
            selected.get("root_cause", ""),
        ]
        for i in range(min(st.session_state.hint_level + 1, len(hints))):
            st.markdown(f"**Hint {i + 1}:** {hints[i]}")

        if st.session_state.hint_level < len(hints) - 1:
            if st.button("Show next hint"):
                st.session_state.hint_level += 1
                st.rerun()

        st.subheader("Troubleshooting Checklist")
        for idx, item in enumerate(selected.get("troubleshooting_checklist", [])):
            st.checkbox(item, key=f"check_{selected.get('id')}_{idx}")

        st.subheader("Code Comparison")
        left, right = st.columns(2)
        with left:
            st.markdown("**Before (problematic)**")
            st.code(selected.get("bad_code", ""), language="python")
        with right:
            st.markdown("**After (fixed)**")
            st.code(selected.get("fixed_code", ""), language="python")

        with st.expander("Unified diff"):
            diff = difflib.unified_diff(
                selected.get("bad_code", "").splitlines(),
                selected.get("fixed_code", "").splitlines(),
                fromfile="bad_code",
                tofile="fixed_code",
                lineterm="",
            )
            st.code("\n".join(diff) or "No diff available", language="diff")

        markdown_summary = _build_markdown_summary(error_input, parsed, selected)
        st.download_button(
            label="Download Markdown Summary",
            data=markdown_summary,
            file_name="debugging_summary.md",
            mime="text/markdown",
        )

        st.subheader("Alternative Matches")
        for alternative in matches[1:]:
            st.write(
                f"- {alternative['language']} | {alternative['error_type']} | score {alternative['match_score']:.2f}"
            )


if __name__ == "__main__":
    main()
