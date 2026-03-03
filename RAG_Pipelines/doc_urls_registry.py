"""
Documentation URL Registry (Focused for Code Correction)
=========================================================
Optimized registry for an auto-code-corrector RAG pipeline.

Priorities (in order):
1. migration  – Breaking changes, deprecated→replacement mappings (ESSENTIAL)
2. whatsnew   – Latest 1-2 releases only — recent deprecations & breaking changes
3. changelog  – Compact summaries of API changes

General tutorials / quick-start guides are excluded to improve retrieval
precision and reduce noise in the context window.

Usage
-----
    from doc_urls_registry import DOC_URLS
"""

DOC_URLS: dict[str, list[tuple[str, str, str]]] = {

    # ─── Core ────────────────────────────────────────────────────────────
    "numpy": [
        ("whatsnew",  "2.4.0",  "https://numpy.org/doc/stable/release/2.4.0-notes.html"),
        ("whatsnew",  "2.3.0",  "https://numpy.org/doc/stable/release/2.3.0-notes.html"),
        ("migration", "2.0.0",  "https://numpy.org/doc/stable/numpy_2_0_migration_guide.html"),
    ],
    "pandas": [
        ("whatsnew",  "3.0.0",  "https://pandas.pydata.org/docs/whatsnew/v3.0.0.html"),
        ("whatsnew",  "2.3.0",  "https://pandas.pydata.org/docs/whatsnew/v2.3.0.html"),
    ],
    "scipy": [
        ("whatsnew",  "1.17.0", "https://docs.scipy.org/doc/scipy/release/1.17.0-notes.html"),
        ("whatsnew",  "1.16.0", "https://docs.scipy.org/doc/scipy/release/1.16.0-notes.html"),
        ("migration", "latest", "https://docs.scipy.org/doc/scipy/migration.html"),
    ],

    # ─── Plotting ────────────────────────────────────────────────────────
    "matplotlib": [
        ("whatsnew",  "3.10.0", "https://matplotlib.org/stable/users/prev_whats_new/whats_new_3.10.0.html"),
        ("migration", "3.10.0", "https://matplotlib.org/stable/api/prev_api_changes/api_changes_3.10.0.html"),
        ("migration", "3.9.0",  "https://matplotlib.org/stable/api/prev_api_changes/api_changes_3.9.0.html"),
    ],
    "seaborn": [
        ("whatsnew",  "0.13.0", "https://seaborn.pydata.org/whatsnew/v0.13.0.html"),
    ],

    # ─── Classical ML ────────────────────────────────────────────────────
    "scikit-learn": [
        ("whatsnew",  "1.8",    "https://scikit-learn.org/stable/whats_new/v1.8.html"),
        ("whatsnew",  "1.7",    "https://scikit-learn.org/stable/whats_new/v1.7.html"),
    ],

    # ─── Data / files ────────────────────────────────────────────────────
    "pyarrow": [
        ("migration", "latest", "https://arrow.apache.org/docs/python/migration.html"),
    ],
    "openpyxl": [
        ("changelog", "latest", "https://openpyxl.readthedocs.io/en/stable/changes.html"),
    ],
    "pillow": [
        ("whatsnew",  "11.1.0", "https://pillow.readthedocs.io/en/stable/releasenotes/11.1.0.html"),
        ("whatsnew",  "11.0.0", "https://pillow.readthedocs.io/en/stable/releasenotes/11.0.0.html"),
        ("migration", "latest", "https://pillow.readthedocs.io/en/stable/deprecations.html"),
    ],

    # ─── Hugging Face ────────────────────────────────────────────────────
    "transformers": [
        ("migration", "latest", "https://huggingface.co/docs/transformers/en/migration"),
    ],
    "datasets": [
        ("guide",     "latest", "https://huggingface.co/docs/datasets/en/loading"),
    ],
    "accelerate": [
        ("migration", "latest", "https://huggingface.co/docs/accelerate/en/basic_tutorials/migration"),
    ],
    "sentencepiece": [
        ("guide",     "latest", "https://github.com/google/sentencepiece/blob/master/README.md"),
    ],

    # ─── LangChain ──────────────────────────────────────────────────────
    "langchain": [
        ("migration", "latest", "https://python.langchain.com/docs/versions/migrating_chains/"),
        ("migration", "latest", "https://python.langchain.com/docs/versions/migrating_memory/"),
    ],
    "langchain-openai": [
        ("guide",     "latest", "https://python.langchain.com/docs/integrations/chat/openai/"),
    ],

    # ─── Utilities ───────────────────────────────────────────────────────
    "python-dotenv": [
        ("guide",     "latest", "https://github.com/theskumar/python-dotenv/blob/main/README.md"),
    ],
    "requests": [
        ("migration", "latest", "https://requests.readthedocs.io/en/latest/community/updates/"),
    ],
    "httpx": [
        ("migration", "latest", "https://www.python-httpx.org/compatibility/"),
    ],
    "tqdm": [
        ("guide",     "latest", "https://github.com/tqdm/tqdm/blob/master/README.rst"),
    ],

    # ─── PyTorch ─────────────────────────────────────────────────────────
    "torch": [
        ("migration", "latest", "https://pytorch.org/docs/stable/notes/serialization.html"),
    ],
    "torchvision": [
        ("guide",     "latest", "https://pytorch.org/vision/stable/transforms.html"),
    ],
    "torchaudio": [
        ("guide",     "latest", "https://pytorch.org/audio/stable/index.html"),
    ],

    # ─── TensorFlow ──────────────────────────────────────────────────────
    "tensorflow": [
        ("migration", "2.x",    "https://www.tensorflow.org/guide/migrate/migrate_tf2"),
    ],

    # ─── Computer Vision ─────────────────────────────────────────────────
    "opencv-python": [
        ("guide",     "4.x",    "https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html"),
    ],
    "scikit-image": [
        ("whatsnew",  "0.24",   "https://scikit-image.org/docs/stable/release_notes/release_0.24.html"),
    ],

    # ─── Boosting ────────────────────────────────────────────────────────
    "xgboost": [
        ("migration", "latest", "https://xgboost.readthedocs.io/en/stable/python/python_api.html"),
    ],
    "lightgbm": [
        ("guide",     "latest", "https://lightgbm.readthedocs.io/en/latest/Python-Intro.html"),
    ],
    "catboost": [
        ("guide",     "latest", "https://catboost.ai/en/docs/concepts/python-quickstart"),
    ],
}
