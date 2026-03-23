const session = loadSession();
if (!session || session.role !== "professor") {
  window.location.href = "/";
}

const professorName = document.getElementById("professor-name");
const professorMeta = document.getElementById("professor-meta");
const assignStudentId = document.getElementById("assign-student-id");
const assignTitle = document.getElementById("assign-title");
const assignDescription = document.getElementById("assign-description");
const assignMessage = document.getElementById("assign-message");
const submissionsTableBody = document.querySelector("#submissions-table tbody");
const submissionSelect = document.getElementById("submission-select");
const detailGrade = document.getElementById("detail-grade");
const detailStatus = document.getElementById("detail-status");
const detailStudentCode = document.getElementById("detail-student-code");
const detailCorrectedCode = document.getElementById("detail-corrected-code");
const detailMistakes = document.getElementById("detail-mistakes");

professorName.textContent = `Welcome, ${session.full_name}`;
professorMeta.textContent = `${session.email}`;

function logout() {
  clearSession();
  window.location.href = "/";
}

document.getElementById("logout-btn").addEventListener("click", logout);

document.getElementById("assign-project").addEventListener("click", async () => {
  const student_id_number = assignStudentId.value.trim();
  const title = assignTitle.value.trim();
  const description = assignDescription.value.trim();

  if (!student_id_number || !title || !description) {
    setMessage(assignMessage, "Student ID, title, and description are required.", "error");
    return;
  }

  setMessage(assignMessage, "Assigning project...", "");

  try {
    await apiFetch("/projects", {
      method: "POST",
      body: JSON.stringify({
        professor_id: session.id,
        student_id_number,
        title,
        description,
      }),
    });

    setMessage(assignMessage, "Project assigned successfully.", "success");
    await loadSubmissions();
  } catch (error) {
    setMessage(assignMessage, `Assignment failed: ${error.message}`, "error");
  }
});

document.getElementById("refresh-submissions").addEventListener("click", () => {
  loadSubmissions().catch((error) => setMessage(assignMessage, error.message, "error"));
});

document.getElementById("load-submission").addEventListener("click", async () => {
  const submissionId = Number(submissionSelect.value);
  if (!submissionId) {
    setMessage(assignMessage, "Select a submission first.", "error");
    return;
  }

  try {
    const detail = await apiFetch(`/professors/${session.id}/submissions/${submissionId}`);
    detailGrade.textContent = `${Number(detail.grade_percent).toFixed(2)}%`;
    detailStatus.textContent = `${detail.status} | ${detail.created_at}`;
    detailStudentCode.value = detail.student_code || "";
    detailCorrectedCode.value = detail.corrected_code || "";
    detailMistakes.textContent = toDiffBlock(detail.mistakes_diff);
    setMessage(assignMessage, "Submission detail loaded.", "success");
  } catch (error) {
    setMessage(assignMessage, `Detail load failed: ${error.message}`, "error");
  }
});

async function loadSubmissions() {
  const submissions = await apiFetch(`/professors/${session.id}/submissions`);

  submissionsTableBody.innerHTML = "";
  submissionSelect.innerHTML = "";

  for (const row of submissions) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.id}</td>
      <td>${row.student_name}</td>
      <td>${row.student_id_number || "-"}</td>
      <td>${row.project_title}</td>
      <td>${Number(row.grade_percent).toFixed(2)}%</td>
      <td>${row.status}</td>
    `;
    submissionsTableBody.appendChild(tr);

    const option = document.createElement("option");
    option.value = String(row.id);
    option.textContent = `${row.id} | ${row.student_name} | ${row.project_title}`;
    submissionSelect.appendChild(option);
  }

  if (submissions.length > 0) {
    submissionSelect.value = String(submissions[0].id);
    setMessage(assignMessage, `Loaded ${submissions.length} submission(s).`, "success");
  } else {
    setMessage(assignMessage, "No submissions yet.", "");
  }
}

loadSubmissions().catch((error) => setMessage(assignMessage, error.message, "error"));
