import re
from typing import Dict, Optional


PYTHON_FILE_LINE_RE = re.compile(r'File\s+"(?P<file>[^"]+)",\s+line\s+(?P<line>\d+)')
JS_STACK_RE = re.compile(r'\((?P<file>[^()\n]+?):(?P<line>\d+):\d+\)')
ERROR_TYPE_RE = re.compile(r'(?P<error>[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))')


def extract_error_details(error_text: str) -> Dict[str, Optional[object]]:
    """Extract error type, filename, and line number from traceback/stack trace text."""
    details: Dict[str, Optional[object]] = {
        "error_type": None,
        "file_name": None,
        "line_number": None,
    }

    if not error_text:
        return details

    python_matches = list(PYTHON_FILE_LINE_RE.finditer(error_text))
    if python_matches:
        last = python_matches[-1]
        details["file_name"] = last.group("file")
        details["line_number"] = int(last.group("line"))
    else:
        js_matches = list(JS_STACK_RE.finditer(error_text))
        if js_matches:
            last = js_matches[-1]
            details["file_name"] = last.group("file")
            details["line_number"] = int(last.group("line"))

    lines = [line.strip() for line in error_text.splitlines() if line.strip()]
    for line in reversed(lines):
        match = ERROR_TYPE_RE.search(line)
        if match:
            details["error_type"] = match.group("error")
            break

    return details
