# App Backend and Frontend

This app now supports role-based learning workflows with persistent storage.

## Main Features

- Login and registration with role selection: student or professor.
- Authentication uses university email.
- Student registration requires student ID number.
- Student dashboard:
    - See assigned projects.
    - Write and submit Python code in an in-browser coding console.
    - Get corrected code, grade percentage, status, and visible mistakes (diff).
- Professor dashboard:
    - Assign projects to specific students.
    - Assignment target is student ID number.
        - Ingest local library documentation into vector DB with metadata:
            library name, version, and source title.
    - Review student submissions.
    - Open each submission to inspect student code, corrected code, mistake diff, and grade.
- Persistent SQLite database:
    - Users, roles, password hashes.
    - University email and student ID number.
    - Project assignments.
    - Student submissions, grades, and corrections.

## Page Flow

- Login/Register page is shown first.
- After login, UI navigates to a separate role page:
    - Student Dashboard page
    - Professor Dashboard page
- Logout returns to the Login/Register page.

## Architecture

- FastAPI backend: api.py
- HTML templates: templates/
- Static frontend assets: static/css and static/js
- Service/business logic: service.py
- SQLite access and schema: database.py
- Repair backend adapter: repair_engine.py
- Workflow loader adapter: workflow_entrypoint.py
- Settings: config.py

## Install

```bash
pip install -r App/requirements_app.txt
```

## Run

Recommended single process (FastAPI + HTML/CSS/JS frontend):

```bash
python -m App.main --mode all
```

Open the UI:

- http://127.0.0.1:8000/
- Student page: http://127.0.0.1:8000/student
- Professor page: http://127.0.0.1:8000/professor

Other modes:

```bash
python -m App.main --mode api
python -m App.main --mode ui
```

Note: --mode ui is kept as backward-compatible alias for the same FastAPI server.

## Database

- Default database path: App/mentorapp.db
- Override with:
    - MENTOR_APP_DB_PATH

## Key Environment Variables

- MENTOR_APP_HOST (default: 127.0.0.1)
- MENTOR_APP_PORT (default: 8000)
- MENTOR_APP_DB_PATH (default: App/mentorapp.db)

Repair backend selection:

- REPAIR_BACKEND_MODE = mock or workflow
- REPAIR_WORKFLOW_SOURCE = auto | module | pyfile | notebook
- REPAIR_WORKFLOW_MODULE
- REPAIR_WORKFLOW_FUNCTION
- REPAIR_WORKFLOW_PY_PATH
- REPAIR_WORKFLOW_NOTEBOOK_PATH

## GPU Workflow Integration

On GPU infrastructure, switch to workflow mode and point to your real run_workflow source.

Example notebook source:

```bash
set REPAIR_BACKEND_MODE=workflow
set REPAIR_WORKFLOW_SOURCE=notebook
set REPAIR_WORKFLOW_NOTEBOOK_PATH=Graph Workflow\LangGraph_SFT_Repair_Workflow.ipynb
set REPAIR_WORKFLOW_FUNCTION=run_workflow
```
