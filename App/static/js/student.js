const session = loadSession();
if (!session || session.role !== "student") {
  window.location.href = "/";
}

const studentName = document.getElementById("student-name");
const studentMeta = document.getElementById("student-meta");
const projectSelect = document.getElementById("project-select");
const projectDescription = document.getElementById("project-description");
const correctedCode = document.getElementById("corrected-code");
const grade = document.getElementById("grade");
const resultStatus = document.getElementById("result-status");
const mistakes = document.getElementById("mistakes");
const studentMessage = document.getElementById("student-message");
const submissionSelect = document.getElementById("submission-select");
const studentResultsTableBody = document.querySelector("#student-results-table tbody");
const submitCodeButton = document.getElementById("submit-code");
let studentEditor = null;

studentName.textContent = `Welcome, ${session.full_name}`;
studentMeta.textContent = `${session.email} | Student ID: ${session.student_id_number || "-"}`;

function logout() {
  clearSession();
  window.location.href = "/";
}

document.getElementById("logout-btn").addEventListener("click", logout);

if (document.getElementById("refresh-projects")) {
  document.getElementById("refresh-projects").addEventListener("click", () => {
    loadProjects().catch((error) => setMessage(studentMessage, error.message, "error"));
  });
}

if (projectSelect) {
  projectSelect.addEventListener("change", async () => {
    const selectedId = projectSelect.value;
    const projects = projectSelect._projects || [];
    const selected = projects.find((item) => String(item.id) === String(selectedId));
    if (projectDescription) {
      projectDescription.value = selected?.description || "";
    }
  });
}

if (submitCodeButton) {
  submitCodeButton.addEventListener("click", async () => {
    const project_id = Number(projectSelect ? projectSelect.value : 0);
    const student_code = studentEditor ? studentEditor.getValue() : "";

    if (!project_id) {
      setMessage(studentMessage, "Please select a project.", "error");
      return;
    }
    if (!student_code.trim()) {
      setMessage(studentMessage, "Code cannot be empty.", "error");
      return;
    }

    const isConfirmed = window.confirm(
      "Are you sure about your code? You cannot change your code after submission."
    );
    if (!isConfirmed) {
      setMessage(studentMessage, "Submission canceled. Continue editing until you are ready.", "");
      return;
    }

    setMessage(studentMessage, "Checking code...", "");

    try {
      const submission = await apiFetch("/submissions", {
        method: "POST",
        body: JSON.stringify({
          project_id,
          student_id: session.id,
          student_code,
          max_attempts: 6,
        }),
      });

      if (correctedCode) {
        correctedCode.value = submission.corrected_code || "";
      }
      if (grade) {
        grade.textContent = `${Number(submission.grade_percent).toFixed(2)}%`;
      }
      if (resultStatus) {
        resultStatus.textContent = `${submission.status} | Submission #${submission.id}`;
      }
      if (mistakes) {
        mistakes.innerHTML = renderDiffHtml(submission.mistakes_diff);
      }

      if (studentEditor) {
        studentEditor.updateOptions({ readOnly: true });
      }
      if (submitCodeButton) {
        submitCodeButton.disabled = true;
        submitCodeButton.textContent = "Submitted";
      }

      setMessage(studentMessage, "Submitted. Now you can check your results from Previous Results.", "success");
    } catch (error) {
      setMessage(studentMessage, `Submission failed: ${error.message}`, "error");
    }
  });
}

if (document.getElementById("refresh-results")) {
  document.getElementById("refresh-results").addEventListener("click", () => {
    loadResults().catch((error) => setMessage(studentMessage, error.message, "error"));
  });
}

if (document.getElementById("load-result")) {
  document.getElementById("load-result").addEventListener("click", () => {
    loadResultDetail().catch((error) => setMessage(studentMessage, error.message, "error"));
  });
}

async function loadProjects() {
  if (!projectSelect) {
    return;
  }

  const projects = await apiFetch(`/students/${session.id}/projects`);
  projectSelect._projects = projects;

  projectSelect.innerHTML = "";
  for (const project of projects) {
    const option = document.createElement("option");
    option.value = String(project.id);
    option.textContent = `${project.id} | ${project.title}`;
    projectSelect.appendChild(option);
  }

  if (projects.length > 0) {
    projectSelect.value = String(projects[0].id);
    if (projectDescription) {
      projectDescription.value = projects[0].description || "";
    }
    setMessage(studentMessage, `Loaded ${projects.length} assigned project(s).`, "success");
  } else {
    if (projectDescription) {
      projectDescription.value = "";
    }
    setMessage(studentMessage, "No projects assigned yet.", "");
  }
}

async function loadResults() {
  if (!submissionSelect || !studentResultsTableBody) {
    return;
  }

  const rows = await apiFetch(`/students/${session.id}/submissions`);

  submissionSelect.innerHTML = "";
  studentResultsTableBody.innerHTML = "";

  for (const row of rows) {
    const option = document.createElement("option");
    option.value = String(row.id);
    option.textContent = `${row.id} | ${row.project_title}`;
    submissionSelect.appendChild(option);

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.id}</td>
      <td>${row.project_title}</td>
      <td>${Number(row.grade_percent).toFixed(2)}%</td>
      <td>${row.status}</td>
      <td>${row.created_at}</td>
    `;
    studentResultsTableBody.appendChild(tr);
  }

  if (rows.length > 0) {
    submissionSelect.value = String(rows[0].id);
    await loadResultDetail();
    setMessage(studentMessage, `Loaded ${rows.length} previous result(s).`, "success");
  } else {
    if (correctedCode) {
      correctedCode.value = "";
    }
    if (grade) {
      grade.textContent = "-";
    }
    if (resultStatus) {
      resultStatus.textContent = "-";
    }
    if (mistakes) {
      mistakes.innerHTML = "";
    }
    setMessage(studentMessage, "No previous results yet.", "");
  }
}

async function loadResultDetail() {
  if (!submissionSelect) {
    return;
  }
  const submissionId = Number(submissionSelect.value);
  if (!submissionId) {
    setMessage(studentMessage, "Select a result first.", "error");
    return;
  }

  const detail = await apiFetch(`/students/${session.id}/submissions/${submissionId}`);

  if (correctedCode) {
    correctedCode.value = detail.corrected_code || "";
  }
  if (grade) {
    grade.textContent = `${Number(detail.grade_percent).toFixed(2)}%`;
  }
  if (resultStatus) {
    resultStatus.textContent = `${detail.status} | Submission #${detail.id}`;
  }
  if (mistakes) {
    mistakes.innerHTML = renderDiffHtml(detail.mistakes_diff);
  }
}

function initEditor() {
  const editorNode = document.getElementById("student-code-editor");
  if (!editorNode) {
    return;
  }

  if (!window.require) {
    setMessage(studentMessage, "Editor failed to load (Monaco loader missing).", "error");
    return;
  }

  window.require.config({
    paths: { vs: "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs" },
  });

  window.require(["vs/editor/editor.main"], () => {
    studentEditor = monaco.editor.create(editorNode, {
      value: "# Write your Python solution here\n",
      language: "python",
      theme: "vs",
      automaticLayout: true,
      minimap: { enabled: false },
      fontFamily: "IBM Plex Mono, Consolas, monospace",
      fontSize: 14,
      lineNumbers: "on",
      roundedSelection: false,
      scrollBeyondLastLine: false,
      smoothScrolling: true,
      wordWrap: "on",
      tabSize: 4,
      insertSpaces: true,
    });
  });
}

initEditor();

if (projectSelect) {
  loadProjects().catch((error) => setMessage(studentMessage, error.message, "error"));
}

if (submissionSelect) {
  loadResults().catch((error) => setMessage(studentMessage, error.message, "error"));
}
