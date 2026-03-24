const session = loadSession();
if (!session || session.role !== "professor") {
  window.location.href = "/";
}

const professorName = document.getElementById("professor-name");
const professorMeta = document.getElementById("professor-meta");
const assignStudentIds = document.getElementById("assign-student-ids");
const assignTitle = document.getElementById("assign-title");
const assignDescription = document.getElementById("assign-description");
const assignMessage = document.getElementById("assign-message");
const assignResultsTableBody = document.querySelector("#assign-results-table tbody");
const docLibraryName = document.getElementById("doc-library-name");
const docLibraryVersion = document.getElementById("doc-library-version");
const docSourceTitle = document.getElementById("doc-source-title");
const docContent = document.getElementById("doc-content");
const docMessage = document.getElementById("doc-message");
const submissionsTableBody = document.querySelector("#submissions-table tbody");
const docsTableBody = document.querySelector("#docs-table tbody");
const submissionSelect = document.getElementById("submission-select");
const detailGrade = document.getElementById("detail-grade");
const detailStatus = document.getElementById("detail-status");
const detailStudentCode = document.getElementById("detail-student-code");
const detailCorrectedCode = document.getElementById("detail-corrected-code");
const detailMistakes = document.getElementById("detail-mistakes");
const resultsMessage = document.getElementById("results-message");

professorName.textContent = `Welcome, ${session.full_name}`;
professorMeta.textContent = `${session.email}`;

function logout() {
  clearSession();
  window.location.href = "/";
}

document.getElementById("logout-btn").addEventListener("click", logout);

function parseStudentIds(raw) {
  return Array.from(
    new Set(
      String(raw)
        .split(/[\n,;\s]+/)
        .map((item) => item.trim())
        .filter(Boolean)
    )
  );
}

if (document.getElementById("assign-project")) {
  document.getElementById("assign-project").addEventListener("click", async () => {
    const ids = parseStudentIds(assignStudentIds ? assignStudentIds.value : "");
    const title = assignTitle ? assignTitle.value.trim() : "";
    const description = assignDescription ? assignDescription.value.trim() : "";

    if (ids.length === 0 || !title || !description) {
      setMessage(assignMessage, "Student IDs, title, and description are required.", "error");
      return;
    }

    setMessage(assignMessage, "Assigning projects...", "");

    try {
      const result = await apiFetch("/projects/bulk", {
        method: "POST",
        body: JSON.stringify({
          professor_id: session.id,
          student_id_numbers: ids,
          title,
          description,
        }),
      });

      if (assignResultsTableBody) {
        assignResultsTableBody.innerHTML = "";

        for (const created of result.created_projects || []) {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>${created.student_id}</td>
            <td>assigned</td>
            <td>Project #${created.id}</td>
          `;
          assignResultsTableBody.appendChild(tr);
        }

        for (const failed of result.failed_assignments || []) {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>${failed.student_id_number}</td>
            <td>failed</td>
            <td>${failed.error}</td>
          `;
          assignResultsTableBody.appendChild(tr);
        }
      }

      const createdCount = (result.created_projects || []).length;
      const failedCount = (result.failed_assignments || []).length;
      if (failedCount === 0) {
        setMessage(assignMessage, `Assigned successfully to ${createdCount} student(s).`, "success");
      } else {
        setMessage(assignMessage, `Assigned to ${createdCount}; failed for ${failedCount}.`, "error");
      }
    } catch (error) {
      setMessage(assignMessage, `Assignment failed: ${error.message}`, "error");
    }
  });
}

if (document.getElementById("ingest-doc")) {
document.getElementById("ingest-doc").addEventListener("click", async () => {
  const library_name = docLibraryName.value.trim();
  const library_version = docLibraryVersion.value.trim();
  const source_title = docSourceTitle.value.trim();
  const content = docContent.value.trim();

  if (!library_name || !library_version || !source_title || !content) {
    setMessage(docMessage, "Library, version, source title, and content are required.", "error");
    return;
  }

  setMessage(docMessage, "Embedding and ingesting documentation...", "");

  try {
    await apiFetch("/professors/library-documents", {
      method: "POST",
      body: JSON.stringify({
        professor_id: session.id,
        library_name,
        library_version,
        source_title,
        content,
      }),
    });

    setMessage(docMessage, "Documentation ingested into vector DB successfully.", "success");
    await loadLibraryDocuments();
  } catch (error) {
    setMessage(docMessage, `Ingestion failed: ${error.message}`, "error");
  }
});
}

if (document.getElementById("refresh-submissions")) {
  document.getElementById("refresh-submissions").addEventListener("click", () => {
    loadSubmissions().catch((error) => setMessage(resultsMessage, error.message, "error"));
  });
}

if (document.getElementById("load-submission")) {
document.getElementById("load-submission").addEventListener("click", async () => {
  const submissionId = Number(submissionSelect.value);
  if (!submissionId) {
    setMessage(resultsMessage, "Select a submission first.", "error");
    return;
  }

  try {
    const detail = await apiFetch(`/professors/${session.id}/submissions/${submissionId}`);
    detailGrade.textContent = `${Number(detail.grade_percent).toFixed(2)}%`;
    detailStatus.textContent = `${detail.status} | ${detail.created_at}`;
    detailStudentCode.value = detail.student_code || "";
    detailCorrectedCode.value = detail.corrected_code || "";
    detailMistakes.innerHTML = renderDiffHtml(detail.mistakes_diff);
    setMessage(resultsMessage, "Submission detail loaded.", "success");
  } catch (error) {
    setMessage(resultsMessage, `Detail load failed: ${error.message}`, "error");
  }
});
}

async function loadSubmissions() {
  if (!submissionsTableBody || !submissionSelect) {
    return;
  }
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
    setMessage(resultsMessage, `Loaded ${submissions.length} submission(s).`, "success");
  } else {
    setMessage(resultsMessage, "No submissions yet.", "");
  }
}

async function loadLibraryDocuments() {
  if (!docsTableBody) {
    return;
  }
  const rows = await apiFetch(`/professors/${session.id}/library-documents`);
  docsTableBody.innerHTML = "";

  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.id}</td>
      <td>${row.library_name}</td>
      <td>${row.library_version}</td>
      <td>${row.source_title}</td>
      <td>${row.chunk_count}</td>
    `;
    docsTableBody.appendChild(tr);
  }
}

if (document.getElementById("refresh-submissions")) {
  loadSubmissions().catch((error) => setMessage(resultsMessage, error.message, "error"));
}

if (document.getElementById("ingest-doc")) {
  loadLibraryDocuments().catch((error) => setMessage(docMessage, error.message, "error"));
}
