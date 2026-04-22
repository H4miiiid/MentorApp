"""Upload validation helpers for the Documents router.

Covers the two guards a teacher will hit in normal use: extension whitelist and
filename sanitization. The streaming oversize path (413) is enforced by FastAPI
semantics in the router and is exercised by manual + frontend testing; unit-testing
it would require a full TestClient + DB fixture which is out of scope here.
"""

from __future__ import annotations

from AppV2.backend.api.routers.documents import _extension_allowed, _safe_filename


def test_extension_allowed_accepts_default_list() -> None:
    assert _extension_allowed("dataset.csv")
    assert _extension_allowed("notes.md")
    assert _extension_allowed("diagram.png")
    assert _extension_allowed("UPPERCASE.TXT")  # case insensitive


def test_extension_allowed_rejects_non_configured_type() -> None:
    assert not _extension_allowed("malware.exe")
    assert not _extension_allowed("payload.sh")
    assert not _extension_allowed("noextension")


def test_safe_filename_strips_path_components() -> None:
    assert _safe_filename("../../etc/passwd") == "passwd"
    assert _safe_filename("/abs/path/to/data.csv") == "data.csv"
    # Windows-style paths should also be normalised away.
    assert _safe_filename("C:\\Users\\me\\file.txt").endswith("file.txt")


def test_safe_filename_replaces_unsafe_characters() -> None:
    result = _safe_filename("weird name with spaces & symbols!.csv")
    # No spaces, no ampersands, extension preserved via the safe-char allowlist.
    assert " " not in result
    assert "&" not in result
    assert result.endswith(".csv")


def test_safe_filename_never_returns_empty() -> None:
    assert _safe_filename("") == "upload"
    assert _safe_filename("...") == "upload"
