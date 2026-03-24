from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .config import settings
from .schemas import (
    HealthResponse,
    LibraryDocumentCreateRequest,
    LibraryDocumentOut,
    LoginRequest,
    ProjectBulkCreateRequest,
    ProjectBulkCreateResponse,
    ProjectCreateRequest,
    ProjectOut,
    RegisterRequest,
    RepairRequest,
    RepairResult,
    SubmissionCreateRequest,
    SubmissionOut,
    SubmissionSummary,
    StudentSubmissionSummary,
    UserOut,
)
from .service import (
    add_professor_library_document,
    create_project_assignment,
    create_project_assignments_bulk,
    ensure_initialized,
    get_submission_detail_for_professor,
    get_submission_detail_for_student,
    list_professor_submissions,
    list_professor_library_documents,
    list_student_projects,
    list_student_submissions,
    list_students,
    login_user,
    register_user,
    run_repair,
    submit_student_code,
)


APP_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(APP_DIR / "templates"))


def create_app() -> FastAPI:
    app = FastAPI(
        title="MentorApp Code Repair API",
        description="FastAPI backend for LangGraph-based code repair workflow",
        version="0.2.0",
    )
    ensure_initialized()
    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

    @app.get("/")
    def home(request: Request):
        return TEMPLATES.TemplateResponse(
            request=request,
            name="login.html",
            context={"title": "MentorApp Login"},
        )

    @app.get("/student")
    def student_page() -> RedirectResponse:
        return RedirectResponse(url="/student/projects", status_code=307)

    def _render_student_page(request: Request, active_tab: str, title: str):
        return TEMPLATES.TemplateResponse(
            request=request,
            name="student.html",
            context={"title": title, "active_tab": active_tab},
        )

    @app.get("/student/projects")
    def student_projects_page(request: Request):
        return _render_student_page(request, active_tab="projects", title="Student - Projects")

    @app.get("/student/results")
    def student_results_page(request: Request):
        return _render_student_page(request, active_tab="results", title="Student - Previous Results")

    @app.get("/professor")
    def professor_page() -> RedirectResponse:
        return RedirectResponse(url="/professor/assign", status_code=307)

    def _render_professor_page(request: Request, active_tab: str, title: str):
        return TEMPLATES.TemplateResponse(
            request=request,
            name="professor.html",
            context={"title": title, "active_tab": active_tab},
        )

    @app.get("/professor/assign")
    def professor_assign_page(request: Request):
        return _render_professor_page(request, active_tab="assign", title="Professor - Assign Projects")

    @app.get("/professor/docs")
    def professor_docs_page(request: Request):
        return _render_professor_page(request, active_tab="docs", title="Professor - Library Documents")

    @app.get("/professor/results")
    def professor_results_page(request: Request):
        return _render_professor_page(request, active_tab="results", title="Professor - Student Results")

    @app.get("/app")
    def app_entry() -> RedirectResponse:
        return RedirectResponse(url="/", status_code=307)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(backend_mode=settings.backend_mode)

    @app.post("/repair", response_model=RepairResult)
    def repair_code(request: RepairRequest) -> RepairResult:
        try:
            return run_repair(request.broken_code, max_attempts=request.max_attempts)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.post("/auth/register", response_model=UserOut)
    def register(request: RegisterRequest) -> UserOut:
        try:
            return register_user(
                email=request.email,
                full_name=request.full_name,
                student_id_number=request.student_id_number,
                password=request.password,
                role=request.role,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/auth/login", response_model=UserOut)
    def login(request: LoginRequest) -> UserOut:
        try:
            return login_user(
                email=request.email,
                password=request.password,
                role=request.role,
            )
        except Exception as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @app.get("/students", response_model=list[UserOut])
    def students() -> list[UserOut]:
        return list_students()

    @app.post("/projects", response_model=ProjectOut)
    def create_project(request: ProjectCreateRequest) -> ProjectOut:
        try:
            return create_project_assignment(
                professor_id=request.professor_id,
                student_id_number=request.student_id_number,
                title=request.title,
                description=request.description,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/projects/bulk", response_model=ProjectBulkCreateResponse)
    def create_projects_bulk(request: ProjectBulkCreateRequest) -> ProjectBulkCreateResponse:
        try:
            return create_project_assignments_bulk(
                professor_id=request.professor_id,
                student_id_numbers=request.student_id_numbers,
                title=request.title,
                description=request.description,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/students/{student_id}/projects", response_model=list[ProjectOut])
    def student_projects(student_id: int) -> list[ProjectOut]:
        return list_student_projects(student_id)

    @app.post("/submissions", response_model=SubmissionOut)
    def create_submission(request: SubmissionCreateRequest) -> SubmissionOut:
        try:
            return submit_student_code(
                project_id=request.project_id,
                student_id=request.student_id,
                student_code=request.student_code,
                max_attempts=request.max_attempts,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/students/{student_id}/submissions", response_model=list[StudentSubmissionSummary])
    def student_submissions(student_id: int) -> list[StudentSubmissionSummary]:
        return list_student_submissions(student_id)

    @app.get("/students/{student_id}/submissions/{submission_id}", response_model=SubmissionOut)
    def student_submission_detail(student_id: int, submission_id: int) -> SubmissionOut:
        try:
            return get_submission_detail_for_student(submission_id=submission_id, student_id=student_id)
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/professors/{professor_id}/submissions", response_model=list[SubmissionSummary])
    def professor_submissions(professor_id: int) -> list[SubmissionSummary]:
        return list_professor_submissions(professor_id)

    @app.get("/professors/{professor_id}/submissions/{submission_id}", response_model=SubmissionOut)
    def professor_submission_detail(professor_id: int, submission_id: int) -> SubmissionOut:
        try:
            return get_submission_detail_for_professor(
                submission_id=submission_id,
                professor_id=professor_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/professors/library-documents", response_model=LibraryDocumentOut)
    def add_library_document(request: LibraryDocumentCreateRequest) -> LibraryDocumentOut:
        try:
            return add_professor_library_document(
                professor_id=request.professor_id,
                library_name=request.library_name,
                library_version=request.library_version,
                source_title=request.source_title,
                content=request.content,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/professors/{professor_id}/library-documents", response_model=list[LibraryDocumentOut])
    def get_library_documents(professor_id: int) -> list[LibraryDocumentOut]:
        try:
            return list_professor_library_documents(professor_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()
