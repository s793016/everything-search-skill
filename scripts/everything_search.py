"""
Everything SDK wrapper for Claude Code.
Uses ctypes to call Everything64.dll directly.
Session-cached: DLL is loaded once and reused.
"""

import argparse
import ctypes
import datetime
import os
import sys
import json
from typing import Optional

# ── Configuration ──────────────────────────────────────────────
# Lookup order: $EVERYTHING_SDK_PATH → DLL next to this script
_DLL_CANDIDATES = [
    os.getenv("EVERYTHING_SDK_PATH"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "Everything64.dll"),
]
DLL_PATH = next((p for p in _DLL_CANDIDATES if p and os.path.isfile(p)), _DLL_CANDIDATES[1])

# Windows long-path limit (MAX_PATH=260 truncates deep paths)
PATH_BUF_LEN = 32768

# ── SDK Constants ─────────────────────────────────────────────
EVERYTHING_OK = 0
EVERYTHING_ERROR_MEMORY = 1
EVERYTHING_ERROR_IPC = 2
EVERYTHING_ERROR_REGISTERCLASSEX = 3
EVERYTHING_ERROR_CREATEWINDOW = 4
EVERYTHING_ERROR_CREATETHREAD = 5
EVERYTHING_ERROR_INVALIDINDEX = 6
EVERYTHING_ERROR_INVALIDCALL = 7

EVERYTHING_REQUEST_FILE_NAME = 0x00000001
EVERYTHING_REQUEST_PATH = 0x00000002
EVERYTHING_REQUEST_FULL_PATH_AND_FILE_NAME = 0x00000004
EVERYTHING_REQUEST_EXTENSION = 0x00000008
EVERYTHING_REQUEST_SIZE = 0x00000010
EVERYTHING_REQUEST_DATE_CREATED = 0x00000020
EVERYTHING_REQUEST_DATE_MODIFIED = 0x00000040
EVERYTHING_REQUEST_DATE_ACCESSED = 0x00000080
EVERYTHING_REQUEST_ATTRIBUTES = 0x00000100
EVERYTHING_REQUEST_RUN_COUNT = 0x00000400
EVERYTHING_REQUEST_DATE_RUN = 0x00000800
EVERYTHING_REQUEST_DATE_RECENTLY_CHANGED = 0x00001000
EVERYTHING_REQUEST_HIGHLIGHTED_FILE_NAME = 0x00002000
EVERYTHING_REQUEST_HIGHLIGHTED_PATH = 0x00004000

EVERYTHING_SORT_NAME_ASCENDING = 1
EVERYTHING_SORT_NAME_DESCENDING = 2
EVERYTHING_SORT_PATH_ASCENDING = 3
EVERYTHING_SORT_PATH_DESCENDING = 4
EVERYTHING_SORT_SIZE_ASCENDING = 5
EVERYTHING_SORT_SIZE_DESCENDING = 6
EVERYTHING_SORT_EXTENSION_ASCENDING = 7
EVERYTHING_SORT_EXTENSION_DESCENDING = 8
EVERYTHING_SORT_TYPE_NAME_ASCENDING = 9
EVERYTHING_SORT_TYPE_NAME_DESCENDING = 10
EVERYTHING_SORT_DATE_CREATED_ASCENDING = 11
EVERYTHING_SORT_DATE_CREATED_DESCENDING = 12
EVERYTHING_SORT_DATE_MODIFIED_ASCENDING = 13
EVERYTHING_SORT_DATE_MODIFIED_DESCENDING = 14
EVERYTHING_SORT_ATTRIBUTES_ASCENDING = 15
EVERYTHING_SORT_ATTRIBUTES_DESCENDING = 16
EVERYTHING_SORT_RUN_COUNT_ASCENDING = 19
EVERYTHING_SORT_RUN_COUNT_DESCENDING = 20
EVERYTHING_SORT_DATE_RECENTLY_CHANGED_ASCENDING = 21
EVERYTHING_SORT_DATE_RECENTLY_CHANGED_DESCENDING = 22
EVERYTHING_SORT_DATE_ACCESSED_ASCENDING = 23
EVERYTHING_SORT_DATE_ACCESSED_DESCENDING = 24

WINDOWS_EPOCH = datetime.datetime(1601, 1, 1)
WINDOWS_TICKS_PER_SECOND = 10000000
EPOCH_DIFF_SECONDS = (datetime.datetime(1970, 1, 1) - WINDOWS_EPOCH).total_seconds()
WINDOWS_TICKS_TO_POSIX = EPOCH_DIFF_SECONDS * WINDOWS_TICKS_PER_SECOND


class EverythingError(Exception):
    def __init__(self, error_code: int):
        self.error_code = error_code
        msgs = {
            EVERYTHING_ERROR_MEMORY: "Failed to allocate memory",
            EVERYTHING_ERROR_IPC: "IPC failed (Everything service not running?)",
            EVERYTHING_ERROR_REGISTERCLASSEX: "Failed to register window class",
            EVERYTHING_ERROR_CREATEWINDOW: "Failed to create window",
            EVERYTHING_ERROR_CREATETHREAD: "Failed to create thread",
            EVERYTHING_ERROR_INVALIDINDEX: "Invalid index",
            EVERYTHING_ERROR_INVALIDCALL: "Invalid call",
        }
        super().__init__(msgs.get(error_code, f"Unknown error: {error_code}"))


# ── Singleton DLL Handle ──────────────────────────────────────
_dll = None


def _get_dll():
    """Lazy-load the Everything SDK DLL (singleton)."""
    global _dll
    if _dll is not None:
        return _dll
    try:
        _dll = ctypes.WinDLL(DLL_PATH)
        _configure_dll(_dll)
        return _dll
    except OSError as e:
        raise RuntimeError(f"Cannot load Everything SDK DLL at {DLL_PATH}: {e}") from e


def _configure_dll(dll):
    """Set up function signatures."""
    # Search config
    dll.Everything_SetSearchW.argtypes = [ctypes.c_wchar_p]
    dll.Everything_SetMatchPath.argtypes = [ctypes.c_bool]
    dll.Everything_SetMatchCase.argtypes = [ctypes.c_bool]
    dll.Everything_SetMatchWholeWord.argtypes = [ctypes.c_bool]
    dll.Everything_SetRegex.argtypes = [ctypes.c_bool]
    dll.Everything_SetMax.argtypes = [ctypes.c_uint]
    dll.Everything_SetSort.argtypes = [ctypes.c_uint]
    dll.Everything_SetRequestFlags.argtypes = [ctypes.c_uint]

    # Query
    dll.Everything_QueryW.argtypes = [ctypes.c_bool]
    dll.Everything_QueryW.restype = ctypes.c_bool

    # Result getters
    dll.Everything_SetOffset.argtypes = [ctypes.c_uint]
    dll.Everything_GetNumResults.restype = ctypes.c_uint
    dll.Everything_GetTotResults.restype = ctypes.c_uint
    dll.Everything_GetLastError.restype = ctypes.c_uint

    dll.Everything_GetResultFileNameW.argtypes = [ctypes.c_uint]
    dll.Everything_GetResultFileNameW.restype = ctypes.c_wchar_p
    dll.Everything_GetResultExtensionW.argtypes = [ctypes.c_uint]
    dll.Everything_GetResultExtensionW.restype = ctypes.c_wchar_p
    dll.Everything_GetResultPathW.argtypes = [ctypes.c_uint]
    dll.Everything_GetResultPathW.restype = ctypes.c_wchar_p

    dll.Everything_GetResultFullPathNameW.argtypes = [
        ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint
    ]

    dll.Everything_GetResultDateCreated.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_ulonglong)]
    dll.Everything_GetResultDateModified.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_ulonglong)]
    dll.Everything_GetResultDateAccessed.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_ulonglong)]
    dll.Everything_GetResultSize.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_ulonglong)]

    dll.Everything_GetResultAttributes.argtypes = [ctypes.c_uint]
    dll.Everything_GetResultRunCount.argtypes = [ctypes.c_uint]


def _windows_time_to_iso(ft: int) -> Optional[str]:
    """Convert Windows FILETIME to ISO datetime string."""
    if ft == 0:
        return None
    microseconds = (ft - WINDOWS_TICKS_TO_POSIX) / WINDOWS_TICKS_PER_SECOND
    try:
        return datetime.datetime.fromtimestamp(microseconds).isoformat()
    except (OSError, ValueError):
        return None


def _check_error(dll):
    """Check for SDK errors."""
    code = dll.Everything_GetLastError()
    if code != EVERYTHING_OK:
        raise EverythingError(code)


def everything_search(
    query: str,
    max_results: int = 10,
    offset: int = 0,
    match_path: bool = False,
    match_case: bool = False,
    match_whole_word: bool = False,
    match_regex: bool = False,
    sort_by: int = EVERYTHING_SORT_NAME_ASCENDING,
    as_json: bool = False,
) -> str:
    """
    Search for files/folders using Everything SDK.

    IMPORTANT: Always set max_results to a small number (5-10).
    Never dump hundreds of results into context — use offset for pagination.

    Args:
        query: Search query string (supports Everything SDK syntax)
        max_results: Max results per page (1-1000, default 10). KEEP SMALL.
        offset: Result offset for pagination (0 = first page).
                To get results 11-20: max_results=10, offset=10
        match_path: Match against full path
        match_case: Case-sensitive search
        match_whole_word: Whole words only
        match_regex: Enable regex
        sort_by: Sort option constant
        as_json: Return JSON instead of formatted text

    Returns:
        Formatted search results or JSON string
    """
    dll = _get_dll()

    # Normalize query
    query = query.replace("\\\\", "\\").replace("/", "\\")

    # Set search parameters
    dll.Everything_SetSearchW(query)
    dll.Everything_SetMatchPath(match_path)
    dll.Everything_SetMatchCase(match_case)
    dll.Everything_SetMatchWholeWord(match_whole_word)
    dll.Everything_SetRegex(match_regex)
    dll.Everything_SetMax(max_results)
    dll.Everything_SetSort(sort_by)
    dll.Everything_SetOffset(offset)

    # Request all available data
    request_flags = (
        EVERYTHING_REQUEST_FILE_NAME
        | EVERYTHING_REQUEST_PATH
        | EVERYTHING_REQUEST_FULL_PATH_AND_FILE_NAME
        | EVERYTHING_REQUEST_EXTENSION
        | EVERYTHING_REQUEST_SIZE
        | EVERYTHING_REQUEST_DATE_CREATED
        | EVERYTHING_REQUEST_DATE_MODIFIED
        | EVERYTHING_REQUEST_DATE_ACCESSED
        | EVERYTHING_REQUEST_ATTRIBUTES
        | EVERYTHING_REQUEST_RUN_COUNT
    )
    dll.Everything_SetRequestFlags(request_flags)

    # Execute
    if not dll.Everything_QueryW(True):
        _check_error(dll)
        raise RuntimeError("Search query failed")

    num_results = min(dll.Everything_GetNumResults(), max_results)
    total_results = dll.Everything_GetTotResults()
    results = []

    filename_buf = ctypes.create_unicode_buffer(PATH_BUF_LEN)
    date_created = ctypes.c_ulonglong()
    date_modified = ctypes.c_ulonglong()
    date_accessed = ctypes.c_ulonglong()
    file_size = ctypes.c_ulonglong()

    for i in range(num_results):
        try:
            dll.Everything_GetResultFullPathNameW(i, filename_buf, PATH_BUF_LEN)
            dll.Everything_GetResultDateCreated(i, date_created)
            dll.Everything_GetResultDateModified(i, date_modified)
            dll.Everything_GetResultDateAccessed(i, date_accessed)
            dll.Everything_GetResultSize(i, file_size)

            results.append({
                "path": filename_buf.value,
                "filename": dll.Everything_GetResultFileNameW(i),
                "extension": dll.Everything_GetResultExtensionW(i) or "",
                "size": file_size.value,
                "created": _windows_time_to_iso(date_created.value),
                "modified": _windows_time_to_iso(date_modified.value),
                "accessed": _windows_time_to_iso(date_accessed.value),
                "attributes": dll.Everything_GetResultAttributes(i),
                "run_count": dll.Everything_GetResultRunCount(i),
            })
        except Exception:
            continue

    dll.Everything_Reset()

    if as_json:
        return json.dumps(results, ensure_ascii=False, indent=2)

    # Formatted text output
    if not results:
        return f"No results found for: {query}"

    lines = [f"Found {num_results} of {total_results} result(s) (offset={offset}):"]
    for r in results:
        size_str = _format_size(r["size"])
        lines.append(f"  {r['path']}")
        lines.append(f"    Size: {size_str}")
        if r["modified"]:
            lines.append(f"    Modified: {r['modified']}")
        if r["created"]:
            lines.append(f"    Created: {r['created']}")

    if total_results > offset + max_results:
        lines.append(f"\n  ← More results available. Use offset={offset + max_results} for next page.")

    return "\n".join(lines)


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"


SORT_ALIASES = {
    "name": EVERYTHING_SORT_NAME_ASCENDING,
    "name-desc": EVERYTHING_SORT_NAME_DESCENDING,
    "path": EVERYTHING_SORT_PATH_ASCENDING,
    "path-desc": EVERYTHING_SORT_PATH_DESCENDING,
    "size": EVERYTHING_SORT_SIZE_ASCENDING,
    "size-desc": EVERYTHING_SORT_SIZE_DESCENDING,
    "modified": EVERYTHING_SORT_DATE_MODIFIED_ASCENDING,
    "modified-desc": EVERYTHING_SORT_DATE_MODIFIED_DESCENDING,
    "created": EVERYTHING_SORT_DATE_CREATED_ASCENDING,
    "created-desc": EVERYTHING_SORT_DATE_CREATED_DESCENDING,
}


def _parse_sort(value: str) -> int:
    """Accept a sort alias (e.g. modified-desc) or a raw SDK sort number."""
    if value.isdigit():
        return int(value)
    if value in SORT_ALIASES:
        return SORT_ALIASES[value]
    raise argparse.ArgumentTypeError(
        f"unknown sort '{value}' (use a number or one of: {', '.join(SORT_ALIASES)})"
    )


def _parse_args(args: list[str]) -> dict:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description="Search files/folders via the Everything SDK.")
    p.add_argument("query", help="Everything search query (full SDK syntax)")
    p.add_argument("-n", "--max-results", type=int, default=10)
    p.add_argument("-o", "--offset", type=int, default=0)
    p.add_argument("-s", "--sort", dest="sort_by", type=_parse_sort,
                   default=EVERYTHING_SORT_NAME_ASCENDING)
    p.add_argument("--match-path", action="store_true")
    p.add_argument("--case", dest="match_case", action="store_true")
    p.add_argument("--whole-word", dest="match_whole_word", action="store_true")
    p.add_argument("--regex", dest="match_regex", action="store_true")
    p.add_argument("--json", dest="as_json", action="store_true")
    return vars(p.parse_args(args))


if __name__ == "__main__":
    # Bash/PowerShell on zh-TW Windows default to cp950; force UTF-8 so
    # non-ASCII paths print instead of raising UnicodeEncodeError.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    kwargs = _parse_args(sys.argv[1:])
    try:
        print(everything_search(**kwargs))
    except EverythingError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Search failed: {e}", file=sys.stderr)
        sys.exit(1)
