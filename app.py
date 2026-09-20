import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import streamlit as st


@dataclass
class DiagnosisResult:
    what_happened: str
    root_cause: str
    fix_explanation: str
    buggy_snippet: str
    fixed_snippet: str
    knowledge_check: List[str]
    confidence: str
    source: str


LANGUAGE_CHOICES = ["Python", "JavaScript", "TypeScript", "C++", "Java", "Go", "SQL"]

TEMPLATES: Dict[str, Dict[str, str]] = {
    "Python · IndexError": {
        "language": "Python",
        "faulty_code": "numbers = [10, 20, 30]\nfor i in range(4):\n    print(numbers[i])",
        "error_log": "Traceback (most recent call last):\n  File \"main.py\", line 3, in <module>\n    print(numbers[i])\nIndexError: list index out of range",
    },
    "Python · KeyError": {
        "language": "Python",
        "faulty_code": "profile = {\"name\": \"Ari\"}\nprint(profile[\"email\"])",
        "error_log": "Traceback (most recent call last):\n  File \"app.py\", line 2, in <module>\n    print(profile[\"email\"])\nKeyError: 'email'",
    },
    "JavaScript · Undefined property": {
        "language": "JavaScript",
        "faulty_code": "const user = null;\nconsole.log(user.name.toUpperCase());",
        "error_log": "TypeError: Cannot read properties of undefined (reading 'toUpperCase')\n    at renderUser (app.js:14:19)",
    },
    "JavaScript · Undefined is not a function": {
        "language": "JavaScript",
        "faulty_code": "const total = 10;\ntotal.map(x => x * 2);",
        "error_log": "TypeError: total.map is not a function\n    at main (index.js:2:7)",
    },
    "SQL · Syntax error near FROM": {
        "language": "SQL",
        "faulty_code": "SELECT id, name users FROM customers;",
        "error_log": "SQL Syntax Error: You have an error in your SQL syntax near 'users FROM customers' at line 1",
    },
    "SQL · Unknown column": {
        "language": "SQL",
        "faulty_code": "SELECT full_name FROM users;",
        "error_log": "Unknown column 'full_name' in 'field list'",
    },
}


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg-main: radial-gradient(circle at top left, #1f1147 0%, #0c1327 45%, #06111a 100%);
            --glass: rgba(14, 20, 36, 0.76);
            --border: rgba(129, 140, 248, 0.32);
            --text: #e5e7eb;
            --muted: #9ca3af;
            --accent-1: #8b5cf6;
            --accent-2: #22d3ee;
            --accent-3: #34d399;
        }
        .stApp {
            background: var(--bg-main);
            color: var(--text);
        }
        .main-header {
            border: 1px solid rgba(167, 139, 250, 0.42);
            background: linear-gradient(135deg, rgba(55, 48, 163, 0.42), rgba(5, 150, 105, 0.22));
            border-radius: 22px;
            padding: 1.25rem 1.5rem;
            box-shadow: 0 0 40px rgba(99, 102, 241, 0.2);
            margin-bottom: 1rem;
        }
        .badge-anim {
            display: inline-block;
            border-radius: 999px;
            padding: 0.28rem 0.7rem;
            font-weight: 600;
            font-size: 0.8rem;
            background: linear-gradient(90deg, #7c3aed, #06b6d4);
            color: #fff;
            animation: pulse 2.4s infinite;
            margin-bottom: 0.6rem;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(124, 58, 237, 0.45); }
            70% { box-shadow: 0 0 0 16px rgba(124, 58, 237, 0.01); }
            100% { box-shadow: 0 0 0 0 rgba(124, 58, 237, 0); }
        }
        .quick-stat-wrap {
            display: flex;
            gap: 0.6rem;
            flex-wrap: wrap;
            margin-top: 0.9rem;
        }
        .pill-stat {
            border: 1px solid rgba(52, 211, 153, 0.45);
            color: #d1fae5;
            background: rgba(16, 185, 129, 0.14);
            border-radius: 999px;
            padding: 0.35rem 0.65rem;
            font-size: 0.78rem;
        }
        .result-card {
            border: 1px solid var(--border);
            background: var(--glass);
            border-radius: 16px;
            padding: 1rem 1.05rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 0 18px rgba(6, 182, 212, 0.12);
        }
        .result-title {
            font-size: 1rem;
            font-weight: 700;
            color: #bfdbfe;
            margin-bottom: 0.45rem;
        }
        .result-body {
            color: #d1d5db;
            line-height: 1.55;
            font-size: 0.94rem;
        }
        .source-chip {
            display:inline-block;
            margin-left:0.5rem;
            border-radius:999px;
            padding:0.15rem 0.5rem;
            font-size:0.72rem;
            color:#cffafe;
            border:1px solid rgba(34, 211, 238, 0.45);
            background:rgba(8, 145, 178, 0.2);
        }
        .stButton > button {
            background: linear-gradient(90deg, #8b5cf6, #06b6d4);
            color: white;
            border-radius: 10px;
            border: none;
            font-weight: 700;
            box-shadow: 0 0 20px rgba(99, 102, 241, 0.35);
            padding: 0.6rem 1rem;
        }
        .stButton > button:hover {
            filter: brightness(1.08);
        }
        div[data-testid="stCodeBlock"] {
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.25);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def reset_inputs() -> None:
    st.session_state["faulty_code"] = ""
    st.session_state["error_log"] = ""
    st.session_state["diagnosis"] = None


def init_state() -> None:
    st.session_state.setdefault("faulty_code", "")
    st.session_state.setdefault("error_log", "")
    st.session_state.setdefault("diagnosis", None)


def parse_line_hint(text: str) -> str:
    line_match = re.search(r"line\s+(\d+)", text, flags=re.IGNORECASE)
    return f"Likely around line {line_match.group(1)}." if line_match else "Line information was not explicit in the log."


def infer_variable(text: str) -> str:
    quoted = re.findall(r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]", text)
    return quoted[0] if quoted else "an unexpected value"


def build_offline_patterns() -> List[Dict[str, object]]:
    return [
        {
            "pattern": r"IndexError: list index out of range",
            "language": "Python",
            "what": "Your code tried to access an index that does not exist in the list.",
            "cause": "A loop or direct index access exceeded the list length.",
            "fix": "Guard the index range or iterate directly over values.",
            "buggy": "for i in range(len(items) + 1):\n    print(items[i])",
            "fixed": "for item in items:\n    print(item)",
            "tips": ["Use enumerate(items) when you need indexes.", "Avoid +1 unless you intentionally need an extra position."],
        },
        {
            "pattern": r"KeyError",
            "language": "Python",
            "what": "A dictionary key was requested but does not exist.",
            "cause": "Direct key access with dict[key] on missing data.",
            "fix": "Use dict.get(), key checks, or defaults.",
            "buggy": "email = profile['email']",
            "fixed": "email = profile.get('email', 'unknown@example.com')",
            "tips": ["Validate payload shape before reading fields.", "Prefer get() for optional keys."],
        },
        {
            "pattern": r"TypeError: unsupported operand type\(s\)",
            "language": "Python",
            "what": "Two incompatible types were used in one operation.",
            "cause": "Mixing values like str + int without conversion.",
            "fix": "Normalize values to compatible types before operations.",
            "buggy": "total = '5' + 2",
            "fixed": "total = int('5') + 2",
            "tips": ["Inspect types with type(value).", "Convert input data early."],
        },
        {
            "pattern": r"AttributeError",
            "language": "Python",
            "what": "The object does not expose the attribute or method being called.",
            "cause": "Wrong object type or typo in method name.",
            "fix": "Confirm object type and use valid API methods.",
            "buggy": "count = data.lenght()",
            "fixed": "count = len(data)",
            "tips": ["Watch for spelling mistakes in attributes.", "Use IDE autocomplete when possible."],
        },
        {
            "pattern": r"ModuleNotFoundError",
            "language": "Python",
            "what": "Python could not find the imported package.",
            "cause": "Dependency missing or wrong virtual environment.",
            "fix": "Install the package in the active environment.",
            "buggy": "import pandas",
            "fixed": "# pip install pandas\nimport pandas",
            "tips": ["Activate the expected virtualenv before running.", "Pin dependencies in requirements.txt."],
        },
        {
            "pattern": r"TypeError: Cannot read properties of undefined",
            "language": "JavaScript",
            "what": "Your code accessed a property on undefined/null.",
            "cause": "Data object not initialized before property read.",
            "fix": "Add null checks, optional chaining, or defaults.",
            "buggy": "console.log(user.name.toUpperCase())",
            "fixed": "console.log(user?.name?.toUpperCase() ?? 'UNKNOWN')",
            "tips": ["Validate API responses before rendering.", "Use optional chaining for nested access."],
        },
        {
            "pattern": r"is not a function",
            "language": "JavaScript",
            "what": "A non-function value was called like a function.",
            "cause": "Method used on wrong data type or overridden variable.",
            "fix": "Confirm expected type before method calls.",
            "buggy": "const total = 10; total.map(x => x * 2)",
            "fixed": "const nums = [10]; nums.map(x => x * 2)",
            "tips": ["Use Array.isArray before calling array methods.", "Keep variable names type-specific."],
        },
        {
            "pattern": r"ReferenceError",
            "language": "JavaScript",
            "what": "A variable was used before declaration or outside scope.",
            "cause": "Misspelled name or block scope mismatch.",
            "fix": "Declare before use and check naming consistency.",
            "buggy": "console.log(totalPrice); let total = 5;",
            "fixed": "let totalPrice = 5; console.log(totalPrice);",
            "tips": ["Prefer const/let and narrow scopes.", "Linting catches many ReferenceErrors early."],
        },
        {
            "pattern": r"SyntaxError: Unexpected token",
            "language": "JavaScript",
            "what": "The parser encountered invalid JavaScript syntax.",
            "cause": "Missing braces, commas, or malformed expressions.",
            "fix": "Format code and validate brackets/symbols.",
            "buggy": "const user = { name: 'Ana'",
            "fixed": "const user = { name: 'Ana' };",
            "tips": ["Use a formatter like Prettier.", "Check surrounding lines, not only the highlighted one."],
        },
        {
            "pattern": r"SQL\s*Syntax\s*Error|syntax error",
            "language": "SQL",
            "what": "The SQL statement structure is invalid for the target engine.",
            "cause": "Malformed clause order, missing commas, or reserved keyword misuse.",
            "fix": "Rebuild the query with valid SQL clause order.",
            "buggy": "SELECT id name FROM users",
            "fixed": "SELECT id, name FROM users;",
            "tips": ["Write one clause per line while debugging.", "Test query in a SQL console incrementally."],
        },
        {
            "pattern": r"Unknown column",
            "language": "SQL",
            "what": "The query references a column not present in the table.",
            "cause": "Schema drift, typo, or alias mismatch.",
            "fix": "Inspect schema and align selected column names.",
            "buggy": "SELECT full_name FROM users;",
            "fixed": "SELECT name FROM users;",
            "tips": ["Run DESCRIBE/PRAGMA to verify schema.", "Avoid assuming column names across environments."],
        },
        {
            "pattern": r"not properly ended|ORA-00933",
            "language": "SQL",
            "what": "The SQL command has extra or misplaced tokens.",
            "cause": "Database-specific syntax mismatch.",
            "fix": "Use SQL syntax compatible with your DB vendor.",
            "buggy": "SELECT * FROM users LIMIT 10; -- Oracle",
            "fixed": "SELECT * FROM users FETCH FIRST 10 ROWS ONLY;",
            "tips": ["Check dialect differences before copying queries.", "Keep environment-specific query variants."],
        },
    ]


def offline_diagnose(language: str, code: str, error_log: str) -> DiagnosisResult:
    combined = f"{code}\n{error_log}"
    for rule in build_offline_patterns():
        if re.search(str(rule["pattern"]), combined, flags=re.IGNORECASE):
            line_hint = parse_line_hint(error_log)
            culprit = infer_variable(error_log)
            return DiagnosisResult(
                what_happened=str(rule["what"]),
                root_cause=f"{rule['cause']} {line_hint} Culprit signal: `{culprit}`.",
                fix_explanation=str(rule["fix"]),
                buggy_snippet=str(rule["buggy"]),
                fixed_snippet=str(rule["fixed"]),
                knowledge_check=list(rule["tips"]),
                confidence="High",
                source="Offline Rule Engine",
            )

    generic_culprit = infer_variable(error_log)
    return DiagnosisResult(
        what_happened="The error indicates a mismatch between what the code expects and what the runtime actually received.",
        root_cause=f"I could not map this to a specific known trace. {parse_line_hint(error_log)} Potential culprit: `{generic_culprit}`.",
        fix_explanation="Verify input assumptions, add guards, and isolate the failing expression with print/log statements.",
        buggy_snippet=code.strip() or "# Provide faulty code to generate an exact fix",
        fixed_snippet="# Add validation before risky access\nif value is not None:\n    ...",
        knowledge_check=[
            "Validate external data at boundaries.",
            "Keep functions small so stack traces map faster to root cause.",
            "Reproduce with a minimal example to narrow failure scope.",
        ],
        confidence="Medium",
        source="Offline Rule Engine",
    )


def llm_diagnose(provider: str, api_key: str, language: str, code: str, error_log: str) -> Optional[DiagnosisResult]:
    system_prompt = (
        "You are an expert debugging assistant. Return STRICT JSON with keys: "
        "what_happened, root_cause, fix_explanation, buggy_snippet, fixed_snippet, knowledge_check (array of 3 short bullets), confidence."
    )
    user_prompt = (
        f"Language: {language}\n"
        f"Faulty code:\n{code}\n\n"
        f"Error log:\n{error_log}\n\n"
        "Provide practical, specific diagnosis and corrected code."
    )

    try:
        if provider == "Gemini":
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([system_prompt, user_prompt])
            raw_text = response.text.strip()
        else:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            raw_text = response.choices[0].message.content.strip()

        raw_text = re.sub(r"^```json|```$", "", raw_text, flags=re.MULTILINE).strip()
        payload = json.loads(raw_text)

        if not isinstance(payload.get("knowledge_check"), list):
            payload["knowledge_check"] = ["Test edge cases.", "Validate inputs.", "Keep logs readable."]

        return DiagnosisResult(
            what_happened=payload.get("what_happened", "No explanation generated."),
            root_cause=payload.get("root_cause", "No root cause generated."),
            fix_explanation=payload.get("fix_explanation", "No fix generated."),
            buggy_snippet=payload.get("buggy_snippet", code or ""),
            fixed_snippet=payload.get("fixed_snippet", ""),
            knowledge_check=payload.get("knowledge_check", []),
            confidence=payload.get("confidence", "Medium"),
            source=f"{provider} API",
        )
    except Exception:
        return None


def choose_provider_from_key(api_key: str) -> str:
    if api_key.startswith("AIza"):
        return "Gemini"
    if api_key.startswith("sk-"):
        return "OpenAI"
    return "Gemini"


def render_header() -> None:
    st.markdown(
        """
        <div class="main-header">
            <div class="badge-anim">⚡ Instant Debugging Mode</div>
            <h1 style="margin:0; font-size: 1.85rem;">Error Message Learning Assistant</h1>
            <p style="margin:0.45rem 0 0; color:#cbd5e1;">Understand stack traces fast, fix confidently, and retain the lesson.</p>
            <div class="quick-stat-wrap">
                <span class="pill-stat">Supported Languages: 7</span>
                <span class="pill-stat">Offline Rules: 12+</span>
                <span class="pill-stat">Ready for Instant Debugging</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_result_card(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="result-card">
            <div class="result-title">{title}</div>
            <div class="result-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="Error Message Learning Assistant", page_icon="🧠", layout="wide")
    inject_css()
    init_state()
    render_header()

    with st.sidebar:
        st.markdown("### 🧠 Error Assistant")
        st.caption("Developer-first debugging copilot")

        template_name = st.selectbox("Quick-start template", ["None"] + list(TEMPLATES.keys()))
        if st.button("Load Template") and template_name != "None":
            template = TEMPLATES[template_name]
            st.session_state["faulty_code"] = template["faulty_code"]
            st.session_state["error_log"] = template["error_log"]
            st.session_state["language"] = template["language"]
            st.session_state["diagnosis"] = None

        st.markdown("---")
        api_key = st.text_input("Optional LLM API Key (Gemini/OpenAI)", type="password")
        provider_choice = st.selectbox("Provider", ["Auto", "Gemini", "OpenAI"], index=0)
        enable_llm = st.toggle("Use LLM when key is present", value=True)
        show_confidence = st.toggle("Show confidence badge", value=True)

        if st.button("Clear All"):
            reset_inputs()
            st.rerun()

    selected_language = st.selectbox(
        "Programming Language",
        LANGUAGE_CHOICES,
        index=LANGUAGE_CHOICES.index(st.session_state.get("language", "Python"))
        if st.session_state.get("language", "Python") in LANGUAGE_CHOICES
        else 0,
    )

    tab_code, tab_trace = st.tabs(["Faulty Code", "Traceback / Error Log"])
    with tab_code:
        st.session_state["faulty_code"] = st.text_area(
            "Paste buggy code here",
            value=st.session_state.get("faulty_code", ""),
            height=280,
            placeholder="def calculate_total(items): ...",
        )
    with tab_trace:
        st.session_state["error_log"] = st.text_area(
            "Paste traceback or runtime log here",
            value=st.session_state.get("error_log", ""),
            height=280,
            placeholder="Traceback (most recent call last): ...",
        )

    if st.button("Diagnose & Explain", type="primary", use_container_width=True):
        if not st.session_state["error_log"].strip() and not st.session_state["faulty_code"].strip():
            st.warning("Add faulty code or an error log to diagnose.")
        else:
            with st.spinner("Running analysis engine..."):
                result: Optional[DiagnosisResult] = None
                if api_key.strip() and enable_llm:
                    provider = choose_provider_from_key(api_key) if provider_choice == "Auto" else provider_choice
                    result = llm_diagnose(
                        provider=provider,
                        api_key=api_key.strip(),
                        language=selected_language,
                        code=st.session_state["faulty_code"],
                        error_log=st.session_state["error_log"],
                    )
                if result is None:
                    result = offline_diagnose(
                        language=selected_language,
                        code=st.session_state["faulty_code"],
                        error_log=st.session_state["error_log"],
                    )
                st.session_state["diagnosis"] = result

    diagnosis: Optional[DiagnosisResult] = st.session_state.get("diagnosis")
    if diagnosis:
        source_chip = f"<span class='source-chip'>{diagnosis.source}</span>"
        confidence_chip = f"<span class='source-chip'>Confidence: {diagnosis.confidence}</span>" if show_confidence else ""
        st.markdown(f"{source_chip}{confidence_chip}", unsafe_allow_html=True)

        render_result_card("💡 What Happened?", diagnosis.what_happened)
        render_result_card("🔍 Root Cause Identified", diagnosis.root_cause)
        render_result_card("🛠️ The Fix & Side-by-Side Comparison", diagnosis.fix_explanation)

        left, right = st.columns(2)
        with left:
            st.caption("Buggy Snippet")
            st.code(diagnosis.buggy_snippet, language=selected_language.lower())
        with right:
            st.caption("Corrected Snippet")
            st.code(diagnosis.fixed_snippet, language=selected_language.lower())

        bullet_items = "".join(f"<li>{tip}</li>" for tip in diagnosis.knowledge_check[:4])
        render_result_card("🧠 Knowledge Check & Best Practice", f"<ul>{bullet_items}</ul>")


if __name__ == "__main__":
    main()
