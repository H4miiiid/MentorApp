from __future__ import annotations

import hashlib
import hmac
import os
from difflib import unified_diff
from typing import Any

from .database import execute_insert, fetch_all, fetch_one, init_db, utc_now_iso
from .repair_engine import RepairEngineError, get_repair_engine
from .schemas import ProjectOut, RepairResult, SubmissionOut, SubmissionSummary, UserOut


def _normalize_role(role: str) -> str:
    value = role.strip().lower()
    if value not in {"student", "professor"}:
        raise ValueError("Role must be 'student' or 'professor'.")
    return value


def _normalize_email(email: str) -> str:
    value = email.strip().lower()
    if "@" not in value or value.startswith("@") or value.endswith("@"):
        raise ValueError("A valid university email is required.")
    return value


def _normalize_student_id(student_id_number: str) -> str:
    value = student_id_number.strip()
    if not value:
        return ""
    if len(value) > 64:
        raise ValueError("Student ID number is too long.")
    return value


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_value: str) -> bool:
    try:
        salt_hex, digest_hex = stored_value.split("$", 1)
    except ValueError:
        return False

    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(digest_hex)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return hmac.compare_digest(actual, expected)


def _mistake_diff(student_code: str, corrected_code: str) -> str:
    diff = unified_diff(
        student_code.splitlines(),
        corrected_code.splitlines(),
        fromfile="student_code.py",
        tofile="corrected_code.py",
        lineterm="",
    )
    diff_text = "\n".join(diff)
    if not diff_text:
        return "No changes were needed."
    return diff_text


def _grade_percent(student_code: str, corrected_code: str, status: str) -> float:
    if student_code.strip() == corrected_code.strip():
        return 100.0

    student_lines = [line.rstrip() for line in student_code.splitlines() if line.strip()]
    corrected_lines = [line.rstrip() for line in corrected_code.splitlines() if line.strip()]

    if not corrected_lines:
        return 0.0

    corrected_set = set(corrected_lines)
    overlap = sum(1 for line in student_lines if line in corrected_set)
    base = (overlap / max(1, len(corrected_lines))) * 100.0

    status_lc = status.lower()
    bonus = 10.0 if status_lc in {"success", "succeeded", "passed"} else 0.0
    score = min(100.0, max(0.0, base + bonus))
    return round(score, 2)


def run_repair(broken_code: str, max_attempts: int) -> RepairResult:
    """Execute a repair request using the configured backend engine."""

    engine = get_repair_engine()
    return engine.repair(broken_code, max_attempts=max_attempts)


def run_repair_safe(broken_code: str, max_attempts: int) -> tuple[RepairResult | None, str | None]:
    """Run repair and return (result, error_message) for UI-friendly handling."""

    try:
        return run_repair(broken_code, max_attempts=max_attempts), None
    except RepairEngineError as exc:
        return None, str(exc)


def ensure_initialized() -> None:
    init_db()


def register_user(email: str, full_name: str, password: str, role: str, student_id_number: str = "") -> UserOut:
    ensure_initialized()

    normalized_role = _normalize_role(role)
    normalized_email = _normalize_email(email)
    normalized_student_id = _normalize_student_id(student_id_number)

    if normalized_role == "student" and not normalized_student_id:
        raise ValueError("Student ID number is required for student registration.")

    existing = fetch_one("SELECT id FROM users WHERE email = ?", (normalized_email,))
    if existing is not None:
        raise ValueError("Email already exists.")

    if normalized_student_id:
        existing_sid = fetch_one(
            "SELECT id FROM users WHERE student_id_number = ?",
            (normalized_student_id,),
        )
        if existing_sid is not None:
            raise ValueError("Student ID number already exists.")

    user_id = execute_insert(
        """
        INSERT INTO users (username, email, student_id_number, full_name, role, password_hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            normalized_email,
            normalized_email,
            normalized_student_id,
            full_name,
            normalized_role,
            _hash_password(password),
            utc_now_iso(),
        ),
    )
    return UserOut(
        id=user_id,
        email=normalized_email,
        full_name=full_name,
        role=normalized_role,
        student_id_number=normalized_student_id,
    )


def login_user(email: str, password: str, role: str) -> UserOut:
    ensure_initialized()

    normalized_role = _normalize_role(role)
    normalized_email = _normalize_email(email)
    row = fetch_one(
        """
        SELECT id, email, full_name, role, password_hash, student_id_number
        FROM users
        WHERE email = ?
        """,
        (normalized_email,),
    )
    if row is None:
        raise ValueError("Invalid email or password.")
    if row["role"] != normalized_role:
        raise ValueError("Selected role does not match the account role.")
    if not _verify_password(password, row["password_hash"]):
        raise ValueError("Invalid email or password.")

    return UserOut(
        id=int(row["id"]),
        email=str(row["email"]),
        full_name=str(row["full_name"]),
        role=str(row["role"]),
        student_id_number=str(row.get("student_id_number", "")),
    )


def list_students() -> list[UserOut]:
    ensure_initialized()
    rows = fetch_all(
        """
        SELECT id, email, student_id_number, full_name, role
        FROM users
        WHERE role = 'student'
        ORDER BY full_name, email
        """
    )
    return [UserOut(**row) for row in rows]


def create_project_assignment(
    professor_id: int,
    student_id_number: str,
    title: str,
    description: str,
) -> ProjectOut:
    ensure_initialized()

    professor = fetch_one("SELECT id, role FROM users WHERE id = ?", (professor_id,))
    normalized_student_id = _normalize_student_id(student_id_number)
    if not normalized_student_id:
        raise ValueError("Student ID number is required.")

    student = fetch_one(
        "SELECT id, role FROM users WHERE student_id_number = ?",
        (normalized_student_id,),
    )
    if professor is None or professor["role"] != "professor":
        raise ValueError("Professor account not found.")
    if student is None or student["role"] != "student":
        raise ValueError("Student account not found.")

    project_id = execute_insert(
        """
        INSERT INTO projects (professor_id, student_id, title, description, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (professor_id, int(student["id"]), title, description, utc_now_iso()),
    )
    row = fetch_one("SELECT * FROM projects WHERE id = ?", (project_id,))
    if row is None:
        raise RuntimeError("Project creation failed.")
    return ProjectOut(**row)


def list_student_projects(student_id: int) -> list[ProjectOut]:
    ensure_initialized()
    rows = fetch_all(
        """
        SELECT *
        FROM projects
        WHERE student_id = ?
        ORDER BY id DESC
        """,
        (student_id,),
    )
    return [ProjectOut(**row) for row in rows]


def submit_student_code(project_id: int, student_id: int, student_code: str, max_attempts: int) -> SubmissionOut:
    ensure_initialized()

    project = fetch_one("SELECT * FROM projects WHERE id = ?", (project_id,))
    if project is None:
        raise ValueError("Project not found.")
    if int(project["student_id"]) != int(student_id):
        raise ValueError("This project is not assigned to the logged-in student.")

    result, error = run_repair_safe(student_code, max_attempts=max_attempts)
    if error is not None or result is None:
        raise ValueError(f"Repair failed: {error}")

    corrected = result.final_code
    status = result.final_status
    diff_text = _mistake_diff(student_code, corrected)
    grade = _grade_percent(student_code, corrected, status)

    submission_id = execute_insert(
        """
        INSERT INTO submissions (
            project_id,
            student_id,
            student_code,
            corrected_code,
            mistakes_diff,
            grade_percent,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            student_id,
            student_code,
            corrected,
            diff_text,
            grade,
            status,
            utc_now_iso(),
        ),
    )

    row = fetch_one("SELECT * FROM submissions WHERE id = ?", (submission_id,))
    if row is None:
        raise RuntimeError("Submission save failed.")
    return SubmissionOut(**row)


def list_professor_submissions(professor_id: int) -> list[SubmissionSummary]:
    ensure_initialized()
    rows = fetch_all(
        """
        SELECT
            s.id,
            s.project_id,
            p.title AS project_title,
            s.student_id,
            u.full_name AS student_name,
            u.student_id_number AS student_id_number,
            s.grade_percent,
            s.status,
            s.created_at
        FROM submissions s
        JOIN projects p ON p.id = s.project_id
        JOIN users u ON u.id = s.student_id
        WHERE p.professor_id = ?
        ORDER BY s.id DESC
        """,
        (professor_id,),
    )
    return [SubmissionSummary(**row) for row in rows]


def get_submission_detail_for_professor(submission_id: int, professor_id: int) -> SubmissionOut:
    ensure_initialized()
    row = fetch_one(
        """
        SELECT s.*
        FROM submissions s
        JOIN projects p ON p.id = s.project_id
        WHERE s.id = ? AND p.professor_id = ?
        """,
        (submission_id, professor_id),
    )
    if row is None:
        raise ValueError("Submission not found or not accessible.")
    return SubmissionOut(**row)
