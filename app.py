import html
import json
import random
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
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

CODE_LANG_MAP: Dict[str, str] = {
    "Python": "python",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "C++": "cpp",
    "Java": "java",
    "Go": "go",
    "SQL": "sql",
}

CONFIDENCE_STYLES: Dict[str, Dict[str, str]] = {
    "high": {"pct": "92%", "color": "#34d399", "label": "High"},
    "medium": {"pct": "60%", "color": "#fbbf24", "label": "Medium"},
    "low": {"pct": "30%", "color": "#f87171", "label": "Low"},
}

STORY_SECTIONS = ["💡 What Happened", "🔍 Root Cause", "🛠️ The Fix", "🧠 Knowledge Check"]

STATS_PATH = Path(__file__).resolve().parent / ".error_assistant_stats.json"

BADGE_RULES = [
    ("First Fix 🎯", lambda s: s["total_diagnoses"] >= 1),
    ("Bug Hunter 🐞", lambda s: s["total_diagnoses"] >= 10),
    ("Debug Master 🏆", lambda s: s["total_diagnoses"] >= 25),
    ("Streak Starter 🔥", lambda s: s["current_streak"] >= 3),
    ("Polyglot 🌐", lambda s: len(s["languages_used"]) >= 4),
]


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


def confetti_html(count: int = 18) -> str:
    colors = ["#8b5cf6", "#22d3ee", "#34d399", "#f472b6", "#fbbf24", "#f87171", "#e1306c", "#f77737"]
    pieces = []
    for _ in range(count):
        left = random.randint(2, 98)
        delay = round(random.uniform(0, 0.4), 2)
        duration = round(random.uniform(0.9, 1.7), 2)
        color = random.choice(colors)
        rot = random.randint(-90, 90)
        pieces.append(
            f'<span class="confetti-piece" style="left:{left}%; animation-delay:{delay}s; '
            f'animation-duration:{duration}s; background:{color}; --rot:{rot}deg;"></span>'
        )
    return f'<div class="confetti-wrap">{"".join(pieces)}</div>'


# ---------------------------------------------------------------------------
# Local stats / streak / badge tracking (best-effort, single-user local file)
# ---------------------------------------------------------------------------

def load_stats() -> Dict[str, object]:
    default: Dict[str, object] = {
        "total_diagnoses": 0,
        "current_streak": 0,
        "best_streak": 0,
        "last_date": None,
        "languages_used": [],
        "badges": [],
    }
    if STATS_PATH.exists():
        try:
            data = json.loads(STATS_PATH.read_text())
            if isinstance(data, dict):
                default.update(data)
        except Exception:
            pass
    return default


def save_stats(stats: Dict[str, object]) -> None:
    try:
        STATS_PATH.write_text(json.dumps(stats))
    except Exception:
        pass  # local stats are a nice-to-have, never block the app on this


def record_diagnosis(language: str) -> Dict[str, object]:
    stats = load_stats()
    today = date.today().isoformat()

    stats["total_diagnoses"] = int(stats.get("total_diagnoses", 0)) + 1

    languages_used = list(stats.get("languages_used", []))
    if language not in languages_used:
        languages_used.append(language)
    stats["languages_used"] = languages_used

    last_date = stats.get("last_date")
    if last_date != today:
        if last_date:
            try:
                last = date.fromisoformat(str(last_date))
                gap_days = (date.today() - last).days
            except ValueError:
                gap_days = None
            stats["current_streak"] = int(stats.get("current_streak", 0)) + 1 if gap_days == 1 else 1
        else:
            stats["current_streak"] = 1
        stats["last_date"] = today

    stats["best_streak"] = max(int(stats.get("best_streak", 0)), int(stats.get("current_streak", 0)))

    badges = list(stats.get("badges", []))
    for name, rule in BADGE_RULES:
        if name not in badges and rule(stats):
            badges.append(name)
    stats["badges"] = badges

    save_stats(stats)
    return stats


def render_stats_bar(stats: Dict[str, object]) -> None:
    badges = stats.get("badges", [])
    badge_title = ", ".join(str(b) for b in badges) if badges else "No badges earned yet"
    st.markdown(
        f"""
        <div class="stats-bar">
            <div class="stat-pill">📊 <b>{stats.get('total_diagnoses', 0)}</b> diagnoses</div>
            <div class="stat-pill">🔥 <b>{stats.get('current_streak', 0)}</b> day streak</div>
            <div class="stat-pill">🏅 <b>{stats.get('best_streak', 0)}</b> best streak</div>
            <div class="stat-pill" title="{html.escape(badge_title)}">🏆 <b>{len(badges)}</b> badges</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if badges:
        chips = "".join(f'<span class="badge-chip">{html.escape(str(b))}</span>' for b in badges)
        st.markdown(f'<div style="margin-top:0.4rem;">{chips}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Quick-start templates
# ---------------------------------------------------------------------------

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
    "Python · ZeroDivisionError": {
        "language": "Python",
        "faulty_code": "total = 100\ncount = 0\naverage = total / count",
        "error_log": "Traceback (most recent call last):\n  File \"stats.py\", line 3, in <module>\n    average = total / count\nZeroDivisionError: division by zero",
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
    "JavaScript · Stack overflow": {
        "language": "JavaScript",
        "faulty_code": "function factorial(n) {\n  return n * factorial(n - 1);\n}\nfactorial(5);",
        "error_log": "RangeError: Maximum call stack size exceeded\n    at factorial (index.js:2:14)",
    },
    "TypeScript · Not assignable": {
        "language": "TypeScript",
        "faulty_code": "let age: number = \"25\";",
        "error_log": "error TS2322: Type 'string' is not assignable to type 'number'.",
    },
    "TypeScript · Possibly undefined": {
        "language": "TypeScript",
        "faulty_code": "function greet(user?: { name: string }) {\n  return user.name;\n}",
        "error_log": "error TS2532: Object is possibly 'undefined'.",
    },
    "C++ · Segfault": {
        "language": "C++",
        "faulty_code": "int *p = nullptr;\n*p = 5;",
        "error_log": "Segmentation fault (core dumped)",
    },
    "C++ · Missing semicolon": {
        "language": "C++",
        "faulty_code": "int x = 5\nint y = 10;",
        "error_log": "main.cpp:1:10: error: expected ';' before 'int'",
    },
    "Java · NullPointerException": {
        "language": "Java",
        "faulty_code": "String name = getUser().getName();",
        "error_log": "Exception in thread \"main\" java.lang.NullPointerException\n\tat Main.main(Main.java:5)",
    },
    "Java · ArrayIndexOutOfBounds": {
        "language": "Java",
        "faulty_code": "int[] arr = {1, 2, 3};\nfor (int i = 0; i <= arr.length; i++) {\n    System.out.println(arr[i]);\n}",
        "error_log": "Exception in thread \"main\" java.lang.ArrayIndexOutOfBoundsException: Index 3 out of bounds for length 3",
    },
    "Go · Nil pointer": {
        "language": "Go",
        "faulty_code": "var u *User\nfmt.Println(u.Name)",
        "error_log": "panic: runtime error: invalid memory address or nil pointer dereference",
    },
    "Go · Index out of range": {
        "language": "Go",
        "faulty_code": "items := []int{1, 2, 3}\nfmt.Println(items[3])",
        "error_log": "panic: runtime error: index out of range [3] with length 3",
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
    "SQL · Duplicate entry": {
        "language": "SQL",
        "faulty_code": "INSERT INTO users (email) VALUES ('ari@example.com');",
        "error_log": "Error Code: 1062. Duplicate entry 'ari@example.com' for key 'users.email'",
    },
}


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

        html { scroll-behavior: smooth; }
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: rgba(255,255,255,0.04); }
        ::-webkit-scrollbar-thumb { background: linear-gradient(180deg, #8b5cf6, #22d3ee); border-radius: 999px; }
        ::-webkit-scrollbar-thumb:hover { background: linear-gradient(180deg, #a78bfa, #67e8f9); }
        * { scrollbar-width: thin; scrollbar-color: #8b5cf6 rgba(255,255,255,0.04); }

        :root {
            --bg-main: radial-gradient(circle at 15% 10%, #2a1263 0%, #14103a 32%, #060814 68%, #030509 100%);
            --glass: rgba(16, 20, 40, 0.72);
            --glass-strong: rgba(20, 24, 48, 0.9);
            --border: rgba(139, 148, 255, 0.28);
            --text: #e8eaf6;
            --muted: #9aa1c4;
            --accent-1: #8b5cf6;
            --accent-2: #22d3ee;
            --accent-3: #34d399;
            --ig-gradient: linear-gradient(90deg, #833ab4, #c13584, #e1306c, #f77737, #fcaf45);
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
            display: inline-block;
            white-space: nowrap;
            overflow: hidden;
            max-width: 100%;
            vertical-align: bottom;
            width: 0;
            animation: shine 6s linear infinite, typeReveal 1.8s steps(34, end) 0.15s 1 forwards;
        }
        @keyframes typeReveal { from { width: 0; } to { width: max-content; } }
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
            background: var(--ig-gradient);
            background-size: 300% auto;
            animation: pulse 2.4s infinite, ig-flow 6s linear infinite;
            color: #fff;
            margin-bottom: 0.7rem;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(225, 48, 108, 0.45); }
            70% { box-shadow: 0 0 0 16px rgba(225, 48, 108, 0.01); }
            100% { box-shadow: 0 0 0 0 rgba(225, 48, 108, 0); }
        }
        @keyframes ig-flow { to { background-position: 300% center; } }

        .quick-stat-wrap { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-top: 1rem; }
        .pill-stat {
            border: 1px solid rgba(52, 211, 153, 0.45);
            color: #d1fae5;
            background: rgba(16, 185, 129, 0.14);
            border-radius: 999px;
            padding: 0.35rem 0.7rem;
            font-size: 0.78rem;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            opacity: 0;
            animation: popIn 0.45s ease forwards;
        }
        .pill-stat:hover { transform: translateY(-2px); box-shadow: 0 4px 14px rgba(52,211,153,0.25); }
        .quick-stat-wrap .pill-stat:nth-child(1) { animation-delay: 1.9s; }
        .quick-stat-wrap .pill-stat:nth-child(2) { animation-delay: 2.02s; }
        .quick-stat-wrap .pill-stat:nth-child(3) { animation-delay: 2.14s; }
        @keyframes popIn {
            from { opacity: 0; transform: translateY(6px) scale(0.92); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        .lang-strip { display: flex; gap: 0.45rem; margin-top: 1rem; flex-wrap: wrap; }
        .lang-chip {
            border: 1px solid rgba(255,255,255,0.14);
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 0.25rem 0.55rem;
            font-size: 0.82rem;
            transition: transform 0.15s ease, background 0.15s ease;
            opacity: 0;
            animation: popIn 0.4s ease forwards;
        }
        .lang-chip:hover { transform: translateY(-2px) scale(1.05); background: rgba(255,255,255,0.1); }
        .lang-strip .lang-chip:nth-child(1) { animation-delay: 2.3s; }
        .lang-strip .lang-chip:nth-child(2) { animation-delay: 2.36s; }
        .lang-strip .lang-chip:nth-child(3) { animation-delay: 2.42s; }
        .lang-strip .lang-chip:nth-child(4) { animation-delay: 2.48s; }
        .lang-strip .lang-chip:nth-child(5) { animation-delay: 2.54s; }
        .lang-strip .lang-chip:nth-child(6) { animation-delay: 2.6s; }
        .lang-strip .lang-chip:nth-child(7) { animation-delay: 2.66s; }

        button:focus-visible, [role="button"]:focus-visible, [tabindex]:focus-visible {
            outline: 2px solid #67e8f9 !important;
            outline-offset: 2px;
            transition: outline-offset 0.15s ease;
        }

        /* ---------- Stats bar ---------- */
        .stats-bar { display: flex; gap: 0.6rem; flex-wrap: wrap; margin: 0.8rem 0 0.2rem; }
        .stat-pill {
            border: 1px solid rgba(255,255,255,0.14);
            background: rgba(255,255,255,0.05);
            border-radius: 999px;
            padding: 0.4rem 0.85rem;
            font-size: 0.82rem;
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }
        .stat-pill b {
            background: var(--ig-gradient);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            font-size: 0.95rem;
        }
        .badge-chip {
            border: 1px solid rgba(252, 175, 69, 0.5);
            background: rgba(252, 175, 69, 0.12);
            color: #fde68a;
            border-radius: 999px;
            padding: 0.2rem 0.6rem;
            font-size: 0.72rem;
            margin: 0.15rem;
            display: inline-block;
        }

        /* ---------- Teaser (feed-post style) ---------- */
        .teaser-card {
            border: 1px solid rgba(255,255,255,0.16);
            background: linear-gradient(135deg, rgba(131,58,180,0.16), rgba(225,48,108,0.10), rgba(247,119,55,0.08));
            border-radius: 18px;
            padding: 1.1rem 1.25rem;
            margin-top: 0.8rem;
            box-shadow: 0 0 30px rgba(225,48,108,0.12);
            animation: fadeInUp 0.5s ease;
        }
        .teaser-excerpt { color: #d7d9ec; font-size: 0.94rem; line-height: 1.55; margin: 0.4rem 0 0.8rem; }

        /* ---------- Result / story cards ---------- */
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
        @keyframes fadeInUp { to { opacity: 1; transform: translateY(0); } }
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

        /* ---------- Story modal ---------- */
        .story-bar { display: flex; gap: 6px; margin-bottom: 1rem; }
        .story-seg { flex: 1; height: 5px; border-radius: 999px; background: rgba(255,255,255,0.12); overflow: hidden; }
        .story-seg.done, .story-seg.active {
            background: var(--ig-gradient);
            background-size: 300% auto;
            animation: ig-flow 4s linear infinite;
        }
        .story-card {
            border: 1px solid rgba(255,255,255,0.14);
            background: var(--glass-strong);
            border-radius: 18px;
            padding: 1.25rem 1.35rem;
            margin-bottom: 1rem;
            animation: storySlide 0.4s ease;
        }
        @keyframes storySlide { from { opacity: 0; transform: translateX(18px); } to { opacity: 1; transform: translateX(0); } }
        .story-title {
            font-size: 1.12rem;
            font-weight: 700;
            margin-bottom: 0.55rem;
            background: var(--ig-gradient);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            display: inline-block;
        }
        .story-body { color: #e5e7eb; line-height: 1.65; font-size: 0.97rem; }
        .story-body ul { margin: 0.3rem 0 0 1.2rem; padding: 0; }
        .story-body li { margin-bottom: 0.35rem; }

        .heart-pop { display: inline-block; animation: heartPop 0.35s ease; }
        @keyframes heartPop {
            0% { transform: scale(1); }
            40% { transform: scale(1.4); }
            100% { transform: scale(1); }
        }

        /* ---------- Confetti ---------- */
        .confetti-wrap { position: fixed; inset: 0; pointer-events: none; z-index: 9999; overflow: hidden; }
        .confetti-piece {
            position: absolute;
            top: -10px;
            width: 8px;
            height: 14px;
            opacity: 0.9;
            border-radius: 2px;
            animation-name: confettiFall;
            animation-timing-function: ease-in;
            animation-fill-mode: forwards;
            transform: rotate(var(--rot));
        }
        @keyframes confettiFall {
            to { transform: translateY(100vh) rotate(calc(var(--rot) + 200deg)); opacity: 0; }
        }

        /* ---------- Buttons ---------- */
        .stButton > button {
            position: relative;
            overflow: hidden;
            background: var(--ig-gradient);
            background-size: 300% auto;
            color: white;
            border-radius: 10px;
            border: none;
            font-weight: 700;
            box-shadow: 0 0 20px rgba(225, 48, 108, 0.3);
            padding: 0.6rem 1rem;
            transition: transform 0.12s ease, filter 0.15s ease, box-shadow 0.15s ease, background-position 0.5s ease;
        }
        .stButton > button:hover {
            filter: brightness(1.12);
            transform: translateY(-1px);
            box-shadow: 0 6px 24px rgba(225, 48, 108, 0.45);
            background-position: 100% center;
        }
        .stButton > button:active { transform: translateY(0px) scale(0.98); }

        div[data-testid="stVerticalBlockBorderWrapper"] { transition: transform 0.15s ease, border-color 0.15s ease; }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform: translateY(-2px);
            border-color: rgba(139, 148, 255, 0.55) !important;
        }

        /* ---------- Tabs ---------- */
        .stTabs [data-baseweb="tab-list"] { gap: 0.4rem; border-bottom: 1px solid rgba(139, 148, 255, 0.18); }
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

        div[data-testid="stCodeBlock"] { border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.25); }

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


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def reset_inputs() -> None:
    st.session_state["faulty_code"] = ""
    st.session_state["error_log"] = ""
    st.session_state["diagnosis"] = None
    st.session_state["language"] = "Python"
    st.session_state["show_dialog"] = False


def init_state() -> None:
    st.session_state.setdefault("faulty_code", "")
    st.session_state.setdefault("error_log", "")
    st.session_state.setdefault("diagnosis", None)
    st.session_state.setdefault("language", "Python")
    st.session_state.setdefault("show_dialog", False)
    st.session_state.setdefault("story_index", 0)
    st.session_state.setdefault("liked", False)
    st.session_state.setdefault("confetti_shown", False)


# ---------------------------------------------------------------------------
# Offline diagnostic engine
# ---------------------------------------------------------------------------

def parse_line_hint(text: str) -> str:
    line_match = re.search(r"line\s+(\d+)", text, flags=re.IGNORECASE)
    return f"Likely around line {line_match.group(1)}." if line_match else "Line information was not explicit in the log."


def infer_variable(text: str) -> str:
    quoted = re.findall(r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]", text)
    return quoted[0] if quoted else "an unexpected value"


OFFLINE_PATTERNS: List[Dict[str, object]] = [
    # ---------------- Python ----------------
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
        "pattern": r"ZeroDivisionError",
        "language": "Python",
        "what": "Your code divided a number by zero, which Python cannot evaluate.",
        "cause": "A denominator expression evaluated to 0, often from unvalidated input or an empty collection average.",
        "fix": "Guard the denominator before dividing, or catch ZeroDivisionError.",
        "buggy": "average = total / count",
        "fixed": "average = total / count if count else 0",
        "tips": ["Validate denominators before dividing.", "Decide what an empty dataset's average should be."],
    },
    {
        "pattern": r"ValueError: invalid literal for int",
        "language": "Python",
        "what": "A string that isn't a valid integer was passed to int().",
        "cause": "Unvalidated or malformed user input reached a numeric conversion.",
        "fix": "Validate and strip input, and handle conversion errors explicitly.",
        "buggy": "age = int(input('Age: '))",
        "fixed": "raw = input('Age: ').strip()\nage = int(raw) if raw.isdigit() else None",
        "tips": ["Use str.isdigit() or try/except around conversions.", "Never trust raw user input."],
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
    # ---------------- JavaScript ----------------
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
        "pattern": r"Maximum call stack size exceeded",
        "language": "JavaScript",
        "what": "A function called itself without a proper base case, exhausting the call stack.",
        "cause": "Infinite or excessively deep recursion.",
        "fix": "Add a base case that stops the recursion, or convert to an iterative loop.",
        "buggy": "function factorial(n) { return n * factorial(n - 1); }",
        "fixed": "function factorial(n) { return n <= 1 ? 1 : n * factorial(n - 1); }",
        "tips": ["Every recursive function needs a base case.", "Watch for off-by-one errors that skip the base case."],
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
    # ---------------- TypeScript ----------------
    {
        "pattern": r"is not assignable to type",
        "language": "TypeScript",
        "what": "A value's type doesn't match what the variable or parameter expects.",
        "cause": "Assigning a value of one type where TypeScript expects another.",
        "fix": "Convert the value to the expected type, or adjust the type definition.",
        "buggy": "let age: number = \"25\";",
        "fixed": "let age: number = Number(\"25\");",
        "tips": ["Let TypeScript infer types where possible.", "Enable strict mode to catch these earlier."],
    },
    {
        "pattern": r"Property .* does not exist on type",
        "language": "TypeScript",
        "what": "Code accessed a property that TypeScript's type definition doesn't declare.",
        "cause": "Typo in the property name, or the interface is missing that field.",
        "fix": "Fix the typo, or extend the interface/type to include the property.",
        "buggy": "interface User { name: string }\nconsole.log(user.naem);",
        "fixed": "interface User { name: string }\nconsole.log(user.name);",
        "tips": ["Let your editor's autocomplete catch typos.", "Keep interfaces in sync with the actual API shape."],
    },
    {
        "pattern": r"Object is possibly 'undefined'",
        "language": "TypeScript",
        "what": "TypeScript flagged that the value might be undefined at this point.",
        "cause": "Accessing a property on an optional value without checking it first.",
        "fix": "Use optional chaining or a narrowing check before access.",
        "buggy": "function greet(user?: { name: string }) { return user.name; }",
        "fixed": "function greet(user?: { name: string }) { return user?.name ?? 'stranger'; }",
        "tips": ["Optional chaining (?.) is your friend.", "Narrow types with if-checks before use."],
    },
    # ---------------- C++ ----------------
    {
        "pattern": r"[Ss]egmentation fault",
        "language": "C++",
        "what": "The program tried to access memory it doesn't own, crashing at the OS level.",
        "cause": "A null/dangling pointer dereference, buffer overrun, or stack overflow from deep recursion.",
        "fix": "Check pointers for null before dereferencing and verify array bounds.",
        "buggy": "int *p = nullptr;\n*p = 5;",
        "fixed": "int value = 5;\nint *p = &value;\n*p = 5;",
        "tips": ["Always initialize pointers.", "Use Valgrind/AddressSanitizer to catch these early."],
    },
    {
        "pattern": r"undefined reference to",
        "language": "C++",
        "what": "The linker couldn't find the implementation for a function or symbol you declared.",
        "cause": "A function is declared/called but never defined, or its object file wasn't linked in.",
        "fix": "Provide the missing implementation or link the correct object/library file.",
        "buggy": "// header.h declares greet(); but it's never defined anywhere",
        "fixed": "void greet() { std::cout << \"hello\"; }",
        "tips": ["Check your build's compile/link file list.", "A missing definition compiles fine but fails at link time."],
    },
    {
        "pattern": r"expected ';' before",
        "language": "C++",
        "what": "The compiler expected a semicolon where one was missing.",
        "cause": "A statement is missing its terminating semicolon, often on the previous line.",
        "fix": "Add the missing semicolon.",
        "buggy": "int x = 5\nint y = 10;",
        "fixed": "int x = 5;\nint y = 10;",
        "tips": ["The reported line is often one after the real mistake.", "Enable compiler warnings for faster feedback."],
    },
    {
        "pattern": r"no matching function for call",
        "language": "C++",
        "what": "No overload of the function matches the argument types you passed.",
        "cause": "Wrong number or type of arguments for any available overload.",
        "fix": "Match the call to an existing overload, or add/adjust one.",
        "buggy": "void add(int a, int b);\nadd(1, 2, 3);",
        "fixed": "void add(int a, int b, int c);\nadd(1, 2, 3);",
        "tips": ["Check the exact signature list in the compiler error.", "Implicit conversions don't always apply across overloads."],
    },
    # ---------------- Java ----------------
    {
        "pattern": r"NullPointerException",
        "language": "Java",
        "what": "Code called a method or accessed a field on a reference that is null.",
        "cause": "An object was expected to be initialized but was never assigned, or a lookup returned null.",
        "fix": "Check for null before use, or initialize the object properly.",
        "buggy": "String name = getUser().getName();",
        "fixed": "User user = getUser();\nString name = (user != null) ? user.getName() : \"unknown\";",
        "tips": ["Consider Optional<T> for values that may be absent.", "Initialize fields in the constructor."],
    },
    {
        "pattern": r"ArrayIndexOutOfBoundsException",
        "language": "Java",
        "what": "Code accessed an array index that is outside its valid range.",
        "cause": "A loop or index calculation went past the array's length.",
        "fix": "Bound-check the index against array.length before accessing it.",
        "buggy": "for (int i = 0; i <= arr.length; i++) { System.out.println(arr[i]); }",
        "fixed": "for (int i = 0; i < arr.length; i++) { System.out.println(arr[i]); }",
        "tips": ["Array indices are 0-based; length is exclusive.", "Prefer enhanced for-loops when you don't need the index."],
    },
    {
        "pattern": r"ClassNotFoundException",
        "language": "Java",
        "what": "The JVM couldn't locate a class it needed to load at runtime.",
        "cause": "Missing dependency on the classpath, or a typo in the fully-qualified class name.",
        "fix": "Add the missing JAR/dependency to the classpath or build file.",
        "buggy": "Class.forName(\"com.mysql.jdbc.Driver\"); // driver jar not on classpath",
        "fixed": "// add the driver dependency to your build file, then:\nClass.forName(\"com.mysql.cj.jdbc.Driver\");",
        "tips": ["Confirm the dependency is declared in your build file.", "Check for typos in fully-qualified class names."],
    },
    {
        "pattern": r"cannot find symbol",
        "language": "Java",
        "what": "The compiler doesn't recognize an identifier you're using.",
        "cause": "Typo in a variable/method/class name, or a missing import.",
        "fix": "Fix the typo or add the missing import.",
        "buggy": "System.out.println(usrName);",
        "fixed": "System.out.println(userName);",
        "tips": ["The compiler error points at the exact line and column.", "IDE auto-imports help prevent this."],
    },
    # ---------------- Go ----------------
    {
        "pattern": r"nil pointer dereference",
        "language": "Go",
        "what": "Code dereferenced a pointer that is nil.",
        "cause": "A struct pointer or interface was never initialized before being used.",
        "fix": "Check for nil before dereferencing, or initialize the value properly.",
        "buggy": "var u *User\nfmt.Println(u.Name)",
        "fixed": "u := &User{Name: \"Ari\"}\nfmt.Println(u.Name)",
        "tips": ["Zero-value pointers are nil in Go — check before use.", "Consider returning an error instead of a nil pointer."],
    },
    {
        "pattern": r"undefined:",
        "language": "Go",
        "what": "The compiler can't find a name you referenced.",
        "cause": "Typo in an identifier, or a missing import for a package-level symbol.",
        "fix": "Fix the identifier name or add the missing import.",
        "buggy": "fmt.Println(totalCost)",
        "fixed": "totalCost := 42\nfmt.Println(totalCost)",
        "tips": ["Go requires every declared variable to be used.", "gofmt/goimports catches many of these automatically."],
    },
    {
        "pattern": r"cannot use .* as .* value",
        "language": "Go",
        "what": "You passed a value of the wrong type where a specific type is expected.",
        "cause": "Mismatched types between a function's declared parameter and the argument passed.",
        "fix": "Convert the value to the expected type, or adjust the function signature.",
        "buggy": "func greet(name string) {}\ngreet(42)",
        "fixed": "func greet(name string) {}\ngreet(\"42\")",
        "tips": ["Go's type system won't implicitly convert for you.", "Use strconv for explicit conversions."],
    },
    {
        "pattern": r"index out of range",
        "language": "Go",
        "what": "Code accessed a slice/array index beyond its length.",
        "cause": "A loop or index calculation exceeded the slice's bounds.",
        "fix": "Check len(slice) before indexing, or use range-based iteration.",
        "buggy": "items := []int{1, 2, 3}\nfmt.Println(items[3])",
        "fixed": "items := []int{1, 2, 3}\nfor _, item := range items { fmt.Println(item) }",
        "tips": ["range gives you safe iteration without manual indices.", "len() is your friend before any manual index access."],
    },
    # ---------------- SQL ----------------
    {
        "pattern": r"SQL\s*Syntax\s*Error|syntax error",
        "language": "SQL",
        "what": "The SQL statement structure is invalid for the target engine.",
        "cause": "Malformed clause order, missing commas, or reserved keyword misuse.",
        "fix": "Rebuild the query with valid SQL clause order.",
        "buggy": "SELECT id name FROM users",
        "fixed": "SELECT id, name FROM users;",
        "tips": ["Write one clause per line while debugging.", "Test the query in a SQL console incrementally."],
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
        "pattern": r"Duplicate entry .* for key",
        "language": "SQL",
        "what": "An INSERT/UPDATE violated a unique constraint or primary key.",
        "cause": "Attempting to insert a value that already exists in a UNIQUE or PRIMARY KEY column.",
        "fix": "Check for existing rows first, or use an upsert (ON DUPLICATE KEY / ON CONFLICT).",
        "buggy": "INSERT INTO users (email) VALUES ('ari@example.com'); -- email already exists",
        "fixed": "INSERT INTO users (email) VALUES ('ari@example.com')\nON DUPLICATE KEY UPDATE email = VALUES(email);",
        "tips": ["Decide upfront: reject duplicates or upsert them.", "Unique constraints protect data integrity — don't remove them."],
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


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

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
                <span class="pill-stat">🧩 {len(OFFLINE_PATTERNS)}+ offline rules</span>
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


def render_teaser(diagnosis: DiagnosisResult) -> None:
    excerpt = diagnosis.what_happened.strip()
    if len(excerpt) > 160:
        excerpt = excerpt[:157].rstrip() + "..."
    st.markdown(
        f"""
        <div class="teaser-card">
            <span class="source-chip">{html.escape(diagnosis.source)}</span>
            <span class="source-chip">Confidence: {html.escape(diagnosis.confidence)}</span>
            <div class="teaser-excerpt">{html.escape(excerpt)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("📖 View full diagnosis", use_container_width=True, key="open_story_btn"):
        st.session_state["show_dialog"] = True
        st.rerun()


def _story_bar_html(active_index: int) -> str:
    segments = []
    for i in range(len(STORY_SECTIONS)):
        state = "done" if i < active_index else ("active" if i == active_index else "upcoming")
        segments.append(f'<div class="story-seg {state}"></div>')
    return f'<div class="story-bar">{"".join(segments)}</div>'


def _story_section_body(diagnosis: DiagnosisResult, index: int) -> str:
    if index == 0:
        return html.escape(diagnosis.what_happened)
    if index == 1:
        return html.escape(diagnosis.root_cause)
    if index == 2:
        return html.escape(diagnosis.fix_explanation)
    bullets = "".join(f"<li>{html.escape(str(tip))}</li>" for tip in diagnosis.knowledge_check[:5])
    return f"<ul>{bullets}</ul>"


@st.dialog("📖 Diagnosis Story", width="large")
def show_story_dialog(diagnosis: DiagnosisResult, language: str) -> None:
    index = st.session_state.get("story_index", 0)
    index = max(0, min(index, len(STORY_SECTIONS) - 1))

    if diagnosis.confidence.strip().lower() == "high" and not st.session_state.get("confetti_shown"):
        st.markdown(confetti_html(), unsafe_allow_html=True)
        st.session_state["confetti_shown"] = True

    st.markdown(f"<span class='source-chip'>{html.escape(diagnosis.source)}</span>", unsafe_allow_html=True)
    st.markdown(confidence_gauge_html(diagnosis.confidence), unsafe_allow_html=True)
    st.markdown(_story_bar_html(index), unsafe_allow_html=True)

    title = STORY_SECTIONS[index]
    body = _story_section_body(diagnosis, index)
    is_html_body = index == 3
    st.markdown(
        f"""
        <div class="story-card">
            <div class="story-title">{title}</div>
            <div class="story-body">{body if is_html_body else body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if index == 2:
        left, right = st.columns(2)
        with left:
            st.caption("🐞 Buggy Snippet")
            st.code(diagnosis.buggy_snippet, language=CODE_LANG_MAP.get(language, "text"))
        with right:
            st.caption("✅ Corrected Snippet")
            st.code(diagnosis.fixed_snippet, language=CODE_LANG_MAP.get(language, "text"))

    if index == len(STORY_SECTIONS) - 1:
        share_text = (
            f"Bug: {diagnosis.what_happened}\n"
            f"Root cause: {diagnosis.root_cause}\n"
            f"Fix: {diagnosis.fix_explanation}"
        )
        st.caption("📋 Shareable summary (hover to copy)")
        st.code(share_text, language=None)

    nav_left, nav_mid, nav_right = st.columns([1, 1, 1])
    with nav_left:
        if st.button("⬅ Prev", disabled=(index == 0), use_container_width=True, key="story_prev"):
            st.session_state["story_index"] = index - 1
            st.rerun()
    with nav_mid:
        liked = st.session_state.get("liked", False)
        heart_label = "❤️ Liked" if liked else "🤍 Like"
        if st.button(heart_label, use_container_width=True, key="story_like"):
            st.session_state["liked"] = not liked
            st.rerun()
    with nav_right:
        if st.button("Next ➡", disabled=(index == len(STORY_SECTIONS) - 1), use_container_width=True, key="story_next"):
            st.session_state["story_index"] = index + 1
            st.rerun()

    if st.button("✖ Close", use_container_width=True, key="story_close"):
        st.session_state["show_dialog"] = False
        st.rerun()


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Error Message Learning Assistant", page_icon="🧠", layout="wide")
    inject_css()
    init_state()
    render_header()

    stats = load_stats()
    render_stats_bar(stats)

    with st.sidebar:
        st.markdown("### 🧠 Error Assistant")
        st.caption("Developer-first debugging copilot")

        with st.expander("⚡ How it works", expanded=False):
            st.markdown(
                "1. Pick a language and paste your code + traceback\n"
                "2. Hit **Diagnose & Explain**\n"
                "3. Tap **View full diagnosis** to open the story view\n"
                "4. Add an API key for LLM-powered answers, or rely on the built-in offline engine"
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
                        st.session_state["show_dialog"] = False
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
                st.session_state["story_index"] = 0
                st.session_state["liked"] = False
                st.session_state["confetti_shown"] = False
                status.update(label="✅ Diagnosis ready", state="complete", expanded=False)

            stats = record_diagnosis(selected_language)
            if result.confidence.strip().lower() == "high":
                st.toast("Nailed it — high-confidence fix found!", icon="✅")
            st.session_state["show_dialog"] = True
            st.rerun()

    diagnosis: Optional[DiagnosisResult] = st.session_state.get("diagnosis")
    if diagnosis:
        render_teaser(diagnosis)
        if st.session_state.get("show_dialog"):
            show_story_dialog(diagnosis, selected_language)

    st.markdown(
        '<div class="app-footer">Built with 💜 for developers who read stack traces at 2am · '
        "<span>Error Message Learning Assistant</span></div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
