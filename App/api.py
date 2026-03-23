from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .config import settings
from .schemas import (
    HealthResponse,
    LoginRequest,
    ProjectCreateRequest,
    ProjectOut,
    RegisterRequest,
    RepairRequest,
    RepairResult,
    SubmissionCreateRequest,
    SubmissionOut,
    SubmissionSummary,
    UserOut,
)
from .service import (
    create_project_assignment,
    ensure_initialized,
    get_submission_detail_for_professor,
    list_professor_submissions,
    list_student_projects,
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
    def student_page(request: Request):
        return TEMPLATES.TemplateResponse(
            request=request,
            name="student.html",
            context={"title": "Student Dashboard"},
        )

    @app.get("/professor")
    def professor_page(request: Request):
        return TEMPLATES.TemplateResponse(
            request=request,
            name="professor.html",
            context={"title": "Professor Dashboard"},
        )

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

    return app


app = create_app()
