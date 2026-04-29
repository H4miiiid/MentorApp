# Grading sandbox image: minimal Python + a curated data-science stack.
#
# Why a separate image (not the backend image):
#   - Keeps student code isolated from FastAPI / SQLModel / LangChain / Chroma.
#   - Lets us grow the data stack independently of backend dependencies.
#   - Smaller surface for students to probe via `import …`.
#
# How it's used:
#   docker-compose.yml builds & tags this as `mentorapp-sandbox:latest` and
#   `workflow_runtime/sandbox.py` launches ephemeral containers from it with
#   `--network none --read-only --memory=… --cpus=… --cap-drop=ALL`.
FROM python:3.13-slim-bookworm

# libgomp1 is required at runtime by scikit-learn / scipy's OpenMP code paths.
# curl is convenient for future data-fetching exercises if a teacher chooses to
# enable network for specific runs; it's tiny so we keep it. Nothing else is
# installed so the surface stays small.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends libgomp1 ca-certificates; \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    # Force matplotlib headless; the sandbox has no display.
    MPLBACKEND=Agg

WORKDIR /work

COPY AppV2/sandbox/requirements.txt /tmp/sandbox-requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /tmp/sandbox-requirements.txt \
    && rm /tmp/sandbox-requirements.txt \
    # Smoke-test: catch broken wheels at build time instead of inside a student's grading run.
    && python -c "import numpy,pandas,scipy,sklearn,matplotlib,seaborn,openpyxl,pyarrow,lxml,bs4,PIL,requests,sympy,networkx,statsmodels,tqdm,polars,cv2,skimage,xgboost,lightgbm,numba,imblearn,category_encoders,torch,torchvision; print('sandbox stack ok')"

# No default command — workflow_runtime/sandbox.py launches `python /work/candidate.py`
# inside an ephemeral `docker run --rm` container.
CMD ["python", "-c", "print('mentorapp sandbox image; run via docker run python /work/candidate.py')"]
