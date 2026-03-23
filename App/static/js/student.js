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
let studentEditor = null;

studentName.textContent = `Welcome, ${session.full_name}`;
studentMeta.textContent = `${session.email} | Student ID: ${session.student_id_number || "-"}`;

function logout() {
  clearSession();
  window.location.href = "/";
}

document.getElementById("logout-btn").addEventListener("click", logout);

document.getElementById("refresh-projects").addEventListener("click", () => {
  loadProjects().catch((error) => setMessage(studentMessage, error.message, "error"));
});

projectSelect.addEventListener("change", async () => {
  const selectedId = projectSelect.value;
  const projects = projectSelect._projects || [];
  const selected = projects.find((item) => String(item.id) === String(selectedId));
  projectDescription.value = selected?.description || "";
});

document.getElementById("submit-code").addEventListener("click", async () => {
  const project_id = Number(projectSelect.value);
  const student_code = studentEditor ? studentEditor.getValue() : "";

  if (!project_id) {
    setMessage(studentMessage, "Please select a project.", "error");
    return;
  }
  if (!student_code.trim()) {
    setMessage(studentMessage, "Code cannot be empty.", "error");
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

    correctedCode.value = submission.corrected_code || "";
    grade.textContent = `${Number(submission.grade_percent).toFixed(2)}%`;
    resultStatus.textContent = `${submission.status} | Submission #${submission.id}`;
    mistakes.textContent = toDiffBlock(submission.mistakes_diff);

    setMessage(studentMessage, "Code checked successfully.", "success");
  } catch (error) {
    setMessage(studentMessage, `Submission failed: ${error.message}`, "error");
  }
});

async function loadProjects() {
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
    projectDescription.value = projects[0].description || "";
    setMessage(studentMessage, `Loaded ${projects.length} assigned project(s).`, "success");
  } else {
    projectDescription.value = "";
    setMessage(studentMessage, "No projects assigned yet.", "");
  }
}

function initEditor() {
  if (!window.require) {
    setMessage(studentMessage, "Editor failed to load (Monaco loader missing).", "error");
    return;
  }

  window.require.config({
    paths: { vs: "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs" },
  });

  window.require(["vs/editor/editor.main"], () => {
    studentEditor = monaco.editor.create(document.getElementById("student-code-editor"), {
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
loadProjects().catch((error) => setMessage(studentMessage, error.message, "error"));
