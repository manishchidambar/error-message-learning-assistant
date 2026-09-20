import html
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

LANGUAGE_ICONS: Dict[str, str] = {
    "Python": "🐍",
    "JavaScript": "🟨",
    "TypeScript": "🔷",
    "C++": "⚙️",
    "Java": "☕",
    "Go": "🐹",
    "SQL": "🗄️",
}

CONFIDENCE_STYLES: Dict[str, Dict[str, str]] = {
    "high": {"pct": "92%", "color": "#34d399", "label": "High"},
    "medium": {"pct": "60%", "color": "#fbbf24", "label": "Medium"},
    "low": {"pct": "30%", "color": "#f87171", "label": "Low"},
}


def confidence_gauge_html(confidence: str) -> str:
    style = CONFIDENCE_STYLES.get(confidence.strip().lower(), {"pct": "50%", "color": "#60a5fa", "label": confidence})
    safe_label = html.escape(confidence or style["label"])
    return f"""
    <div class="gauge-wrap">
        <div class="gauge-label"><span>Confidence</span><span>{safe_label}</span></div>
        <div class="gauge-track">
            <div class="gauge-fill" style="width:{style['pct']}; background:{style['color']};"></div>
        </div>
    </div>
    """

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
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

        :root {
            --bg-main: radial-gradient(circle at 15% 10%, #2a1263 0%, #14103a 32%, #060814 68%, #030509 100%);
            --glass: rgba(16, 20, 40, 0.72);
            --glass-strong: rgba(20, 24, 48, 0.88);
            --border: rgba(139, 148, 255, 0.28);
            --text: #e8eaf6;
            --muted: #9aa1c4;
            --accent-1: #8b5cf6;
            --accent-2: #22d3ee;
            --accent-3: #34d399;
            --accent-4: #f472b6;
        }

        html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
        code, pre, .stCodeBlock, div[data-testid="stCodeBlock"] * { font-family: 'JetBrains Mono', monospace !important; }

        .stApp {
            background: var(--bg-main);
            background-size: 200% 200%;
            animation: drift 22s ease-in-out infinite;
            color: var(--text);
        }
        @keyframes drift {
            0% { background-position: 0% 0%; }
            50% { background-position: 100% 60%; }
            100% { background-position: 0% 0%; }
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(20, 16, 48, 0.96), rgba(8, 10, 24, 0.98));
            border-right: 1px solid rgba(139, 148, 255, 0.18);
        }

        /* ---------- Header ---------- */
        .main-header {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(167, 139, 250, 0.42);
            background: linear-gradient(135deg, rgba(80, 40, 200, 0.45), rgba(6, 182, 212, 0.18) 55%, rgba(5, 150, 105, 0.2));
            border-radius: 24px;
            padding: 1.5rem 1.75rem;
            box-shadow: 0 0 55px rgba(99, 102, 241, 0.25), inset 0 1px 0 rgba(255,255,255,0.06);
            margin-bottom: 1.1rem;
        }
        .main-header::before {
            content: "";
            position: absolute;
            inset: -40%;
            background: conic-gradient(from 0deg, rgba(139,92,246,0.18), rgba(34,211,238,0.14), rgba(52,211,153,0.14), rgba(244,114,182,0.14), rgba(139,92,246,0.18));
            animation: spin 16s linear infinite;
            pointer-events: none;
        }
        .main-header > * { position: relative; z-index: 1; }
        @keyframes spin { to { transform: rotate(360deg); } }

        .gradient-title {
            margin: 0;
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(90deg, #c4b5fd, #67e8f9, #6ee7b7, #c4b5fd);
            background-size: 300% auto;
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            animation: shine 6s linear infinite;
        }
        @keyframes shine { to { background-position: 300% center; } }

        .cursor-blink {
            display: inline-block;
            width: 3px;
            height: 1.1em;
            background: #67e8f9;
            margin-left: 4px;
            vertical-align: text-bottom;
            animation: blink 1s steps(1) infinite;
        }
        @keyframes blink { 50% { opacity: 0; } }

        .badge-anim {
            display: inline-block;
            border-radius: 999px;
            padding: 0.3rem 0.75rem;
            font-weight: 600;
            font-size: 0.8rem;
            background: linear-gradient(90deg, #7c3aed, #06b6d4);
            color: #fff;
            animation: pulse 2.4s infinite;
            margin-bottom: 0.7rem;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(124, 58, 237, 0.45); }
            70% { box-shadow: 0 0 0 16px rgba(124, 58, 237, 0.01); }
            100% { box-shadow: 0 0 0 0 rgba(124, 58, 237, 0); }
        }

        .quick-stat-wrap { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-top: 1rem; }
        .pill-stat {
            border: 1px solid rgba(52, 211, 153, 0.45);
            color: #d1fae5;
            background: rgba(16, 185, 129, 0.14);
            border-radius: 999px;
            padding: 0.35rem 0.7rem;
            font-size: 0.78rem;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .pill-stat:hover { transform: translateY(-2px); box-shadow: 0 4px 14px rgba(52,211,153,0.25); }

        .lang-strip { display: flex; gap: 0.45rem; margin-top: 1rem; flex-wrap: wrap; }
        .lang-chip {
            border: 1px solid rgba(255,255,255,0.14);
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 0.25rem 0.55rem;
            font-size: 0.82rem;
            transition: transform 0.15s ease;
        }
        .lang-chip:hover { transform: translateY(-2px) scale(1.05); background: rgba(255,255,255,0.1); }

        /* ---------- Result cards ---------- */
        .result-card {
            border: 1px solid var(--border);
            background: var(--glass);
            border-radius: 16px;
            padding: 1.05rem 1.15rem;
            margin-bottom: 0.8rem;
            box-shadow: 0 0 18px rgba(6, 182, 212, 0.1);
            opacity: 0;
            transform: translateY(14px);
            animation: fadeInUp 0.5s ease forwards;
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }
        .result-card:hover {
            transform: translateY(-3px);
            border-color: rgba(167, 139, 250, 0.6);
            box-shadow: 0 8px 28px rgba(139, 92, 246, 0.22);
        }
        @keyframes fadeInUp {
            to { opacity: 1; transform: translateY(0); }
        }
        .result-title {
            font-size: 1.02rem;
            font-weight: 700;
            color: #bfdbfe;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        .result-body { color: #d7d9ec; line-height: 1.6; font-size: 0.95rem; }
        .result-body ul { margin: 0.2rem 0 0 1.1rem; padding: 0; }
        .result-body li { margin-bottom: 0.3rem; }

        .source-chip {
            display: inline-block;
            margin: 0 0.5rem 0.6rem 0;
            border-radius: 999px;
            padding: 0.18rem 0.6rem;
            font-size: 0.74rem;
            color: #cffafe;
            border: 1px solid rgba(34, 211, 238, 0.45);
            background: rgba(8, 145, 178, 0.2);
        }

        /* ---------- Confidence gauge ---------- */
        .gauge-wrap { margin: 0.2rem 0 1rem 0; max-width: 320px; }
        .gauge-label { display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--muted); margin-bottom: 0.3rem; }
        .gauge-track { height: 8px; border-radius: 999px; background: rgba(255,255,255,0.08); overflow: hidden; }
        .gauge-fill { height: 100%; border-radius: 999px; transition: width 0.6s ease; animation: growBar 0.8s ease; }
        @keyframes growBar { from { width: 0; } }

        /* ---------- Buttons ---------- */
        .stButton > button {
            position: relative;
            overflow: hidden;
            background: linear-gradient(90deg, #8b5cf6, #06b6d4);
            color: white;
            border-radius: 10px;
            border: none;
            font-weight: 700;
            box-shadow: 0 0 20px rgba(99, 102, 241, 0.35);
            padding: 0.6rem 1rem;
            transition: transform 0.12s ease, filter 0.15s ease, box-shadow 0.15s ease;
        }
        .stButton > button:hover {
            filter: brightness(1.12);
            transform: translateY(-1px);
            box-shadow: 0 6px 24px rgba(99, 102, 241, 0.45);
        }
        .stButton > button:active { transform: translateY(0px) scale(0.98); }

        /* Template mini-cards in the sidebar */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            transition: transform 0.15s ease, border-color 0.15s ease;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform: translateY(-2px);
            border-color: rgba(139, 148, 255, 0.55) !important;
        }

        /* ---------- Tabs ---------- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.4rem;
            border-bottom: 1px solid rgba(139, 148, 255, 0.18);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px 10px 0 0;
            padding: 0.55rem 1rem;
            background: rgba(255,255,255,0.03);
            transition: background 0.15s ease;
        }
        .stTabs [data-baseweb="tab"]:hover { background: rgba(139, 92, 246, 0.12); }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(90deg, rgba(139,92,246,0.28), rgba(34,211,238,0.18));
            box-shadow: inset 0 -2px 0 #67e8f9;
        }

        div[data-testid="stCodeBlock"] {
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.25);
        }

        /* ---------- Footer ---------- */
        .app-footer {
            margin-top: 2rem;
            padding: 0.9rem 1rem;
            text-align: center;
            font-size: 0.78rem;
            color: var(--muted);
            border-top: 1px solid rgba(139, 148, 255, 0.14);
        }
        .app-footer span { color: #a5b4fc; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def reset_inputs() -> None:
    st.session_state["faulty_code"] = ""
    st.session_state["error_log"] = ""
    st.session_state["diagnosis"] = None
    st.session_state["language"] = "Python"


def init_state() -> None:
    st.session_state.setdefault("faulty_code", "")
    st.session_state.setdefault("error_log", "")
    st.session_state.setdefault("diagnosis", None)
    st.session_state.setdefault("language", "Python")


def parse_line_hint(text: str) -> str:
    line_match = re.search(r"line\s+(\d+)", text, flags=re.IGNORECASE)
    return f"Likely around line {line_match.group(1)}." if line_match else "Line information was not explicit in the log."


def infer_variable(text: str) -> str:
    quoted = re.findall(r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]", text)
    return quoted[0] if quoted else "an unexpected value"


OFFLINE_PATTERNS: List[Dict[str, object]] = [
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
    for rule in OFFLINE_PATTERNS:
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


def llm_diagnose(
    provider: str, api_key: str, language: str, code: str, error_log: str
) -> "tuple[Optional[DiagnosisResult], Optional[str]]":
    """Returns (result, error_message). error_message is set only when result is None."""
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

        return (
            DiagnosisResult(
                what_happened=payload.get("what_happened", "No explanation generated."),
                root_cause=payload.get("root_cause", "No root cause generated."),
                fix_explanation=payload.get("fix_explanation", "No fix generated."),
                buggy_snippet=payload.get("buggy_snippet", code or ""),
                fixed_snippet=payload.get("fixed_snippet", ""),
                knowledge_check=payload.get("knowledge_check", []),
                confidence=payload.get("confidence", "Medium"),
                source=f"{provider} API",
            ),
            None,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced to the user, not swallowed
        return None, f"{provider} call failed ({exc.__class__.__name__}): {exc}"


def choose_provider_from_key(api_key: str) -> str:
    if api_key.startswith("AIza"):
        return "Gemini"
    if api_key.startswith("sk-"):
        return "OpenAI"
    return "Gemini"


def render_header() -> None:
    lang_chips = "".join(
        f'<span class="lang-chip">{icon} {html.escape(name)}</span>' for name, icon in LANGUAGE_ICONS.items()
    )
    st.markdown(
        f"""
        <div class="main-header">
            <div class="badge-anim">⚡ Instant Debugging Mode</div>
            <h1 class="gradient-title">Error Message Learning Assistant<span class="cursor-blink"></span></h1>
            <p style="margin:0.45rem 0 0; color:#cbd5e1;">Understand stack traces fast, fix confidently, and retain the lesson.</p>
            <div class="quick-stat-wrap">
                <span class="pill-stat">✨ 7 languages</span>
                <span class="pill-stat">🧩 12+ offline rules</span>
                <span class="pill-stat">🤖 Optional LLM boost</span>
            </div>
            <div class="lang-strip">{lang_chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_result_card(title: str, body: str, escape_body: bool = True, index: int = 0) -> None:
    safe_title = html.escape(title)
    safe_body = html.escape(body) if escape_body else body
    delay = 0.08 * index
    st.markdown(
        f"""
        <div class="result-card" style="animation-delay:{delay:.2f}s;">
            <div class="result-title">{safe_title}</div>
            <div class="result-body">{safe_body}</div>
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

        with st.expander("⚡ How it works", expanded=False):
            st.markdown(
                "1. Pick a language and paste your code + traceback\n"
                "2. Hit **Diagnose & Explain**\n"
                "3. Get a plain-English cause, a fix, and a side-by-side diff\n"
                "4. Add an API key in the sidebar for LLM-powered answers, or rely on the built-in offline engine"
            )

        st.markdown("#### 🚀 Quick-start templates")
        st.caption("Tap one to load it instantly")
        for name, template in TEMPLATES.items():
            with st.container(border=True):
                cols = st.columns([5, 2])
                with cols[0]:
                    icon = LANGUAGE_ICONS.get(template["language"], "🧩")
                    st.markdown(f"**{icon} {name}**")
                with cols[1]:
                    if st.button("Load", key=f"tmpl_{name}", use_container_width=True):
                        st.session_state["faulty_code"] = template["faulty_code"]
                        st.session_state["error_log"] = template["error_log"]
                        st.session_state["language"] = template["language"]
                        st.session_state["diagnosis"] = None
                        st.rerun()

        st.markdown("---")
        api_key = st.text_input("Optional LLM API Key (Gemini/OpenAI)", type="password")
        provider_choice = st.selectbox("Provider", ["Auto", "Gemini", "OpenAI"], index=0)
        enable_llm = st.toggle("Use LLM when key is present", value=True)
        show_confidence = st.toggle("Show confidence gauge", value=True)

        if st.button("🗑️ Clear All", use_container_width=True):
            reset_inputs()
            st.rerun()

    st.markdown("##### Programming language")
    selected_language = st.pills(
        "Programming language",
        LANGUAGE_CHOICES,
        format_func=lambda lang: f"{LANGUAGE_ICONS.get(lang, '🧩')} {lang}",
        key="language",
        label_visibility="collapsed",
    )
    if not selected_language:
        selected_language = "Python"

    tab_code, tab_trace = st.tabs(["📝 Faulty Code", "📋 Traceback / Error Log"])
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

    if st.button("🔎 Diagnose & Explain", type="primary", use_container_width=True):
        if not st.session_state["error_log"].strip() and not st.session_state["faulty_code"].strip():
            st.warning("Add faulty code or an error log to diagnose.")
        else:
            use_llm = bool(api_key.strip() and enable_llm)
            with st.status("🧠 Analyzing your error...", expanded=True) as status:
                st.write("🔎 Scanning the traceback for a known signature...")
                result: Optional[DiagnosisResult] = None
                if use_llm:
                    provider = choose_provider_from_key(api_key) if provider_choice == "Auto" else provider_choice
                    st.write(f"🤖 Asking {provider} for a diagnosis...")
                    result, llm_error = llm_diagnose(
                        provider=provider,
                        api_key=api_key.strip(),
                        language=selected_language,
                        code=st.session_state["faulty_code"],
                        error_log=st.session_state["error_log"],
                    )
                    if llm_error:
                        st.warning(f"{llm_error} — falling back to the offline rule engine.")
                if result is None:
                    st.write("🧩 Matching against the offline pattern library...")
                    result = offline_diagnose(
                        language=selected_language,
                        code=st.session_state["faulty_code"],
                        error_log=st.session_state["error_log"],
                    )
                st.write("🛠️ Building the fix and knowledge check...")
                st.session_state["diagnosis"] = result
                status.update(label="✅ Diagnosis ready", state="complete", expanded=False)
            if result.confidence.strip().lower() == "high":
                st.toast("Nailed it — high-confidence fix found!", icon="✅")

    diagnosis: Optional[DiagnosisResult] = st.session_state.get("diagnosis")
    if diagnosis:
        st.markdown(f"<span class='source-chip'>{html.escape(diagnosis.source)}</span>", unsafe_allow_html=True)
        if show_confidence:
            st.markdown(confidence_gauge_html(diagnosis.confidence), unsafe_allow_html=True)

        render_result_card("💡 What Happened?", diagnosis.what_happened, index=0)
        render_result_card("🔍 Root Cause Identified", diagnosis.root_cause, index=1)
        render_result_card("🛠️ The Fix & Side-by-Side Comparison", diagnosis.fix_explanation, index=2)

        left, right = st.columns(2)
        with left:
            st.caption("🐞 Buggy Snippet")
            st.code(diagnosis.buggy_snippet, language=selected_language.lower())
        with right:
            st.caption("✅ Corrected Snippet")
            st.code(diagnosis.fixed_snippet, language=selected_language.lower())

        bullet_items = "".join(f"<li>{html.escape(str(tip))}</li>" for tip in diagnosis.knowledge_check[:4])
        render_result_card(
            "🧠 Knowledge Check & Best Practice", f"<ul>{bullet_items}</ul>", escape_body=False, index=3
        )

    st.markdown(
        '<div class="app-footer">Built with 💜 for developers who read stack traces at 2am · '
        "<span>Error Message Learning Assistant</span></div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
