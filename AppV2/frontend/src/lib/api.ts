import { browser } from "$app/environment";

const TOKEN_KEY = "mentorapp_v2_token";

export function getToken(): string | null {
  if (!browser) return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (!browser) return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (!browser) return;
  localStorage.removeItem(TOKEN_KEY);
}

export async function apiFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(path, { ...options, headers });
}

export async function apiJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = (err as { detail?: unknown }).detail;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => JSON.stringify(d)).join(", ")
          : `Request failed (${res.status})`;
    throw new Error(msg);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export async function downloadDocumentFile(documentId: string, filename: string): Promise<void> {
  const res = await apiFetch(`/api/documents/${documentId}/file`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Download failed");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || "document";
  a.click();
  URL.revokeObjectURL(url);
}

export type UserRole = "student" | "teacher" | "admin";

export type MeResponse = {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  student_id_number: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export async function fetchMe(): Promise<MeResponse> {
  return apiJson<MeResponse>("/api/auth/me");
}

export type UserRead = {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  student_id_number: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AssignmentRead = {
  id: string;
  title: string;
  description: string;
  teacher_id: string;
  due_date: string | null;
  created_at: string;
  updated_at: string;
};

export type AssignmentCreateBody = {
  title: string;
  description: string;
  teacher_id: string;
  due_date: string | null;
  student_ids: string[];
};

export type AssignmentStudentRead = {
  assignment_id: string;
  student_id: string;
  assigned_at: string;
};

export type SubmissionStatus = "pending" | "running" | "completed" | "failed";

export type SubmissionRead = {
  id: string;
  assignment_id: string;
  student_id: string;
  code: string;
  corrected_code: string;
  diff: string;
  grade: number;
  status: SubmissionStatus;
  stdout: string;
  stderr: string;
  feedback: string;
  created_at: string;
  updated_at: string;
};

export type SubmissionCreateBody = {
  assignment_id: string;
  student_id: string;
  code: string;
};

export type DocumentRead = {
  id: string;
  uploaded_by: string;
  title: string;
  description: string;
  file_path: string;
  file_type: string;
  file_size_bytes: number;
  assignment_id: string | null;
  created_at: string;
  updated_at: string;
};

export async function fetchUsers(): Promise<UserRead[]> {
  return apiJson<UserRead[]>("/api/users");
}

export async function fetchAssignments(): Promise<AssignmentRead[]> {
  return apiJson<AssignmentRead[]>("/api/assignments");
}

export async function createAssignment(body: AssignmentCreateBody): Promise<AssignmentRead> {
  return apiJson<AssignmentRead>("/api/assignments", {
    method: "POST",
    body: JSON.stringify({
      title: body.title.trim(),
      description: body.description ?? "",
      teacher_id: body.teacher_id,
      due_date: body.due_date,
      student_ids: body.student_ids,
    }),
  });
}

export async function fetchAssignment(id: string): Promise<AssignmentRead> {
  return apiJson<AssignmentRead>(`/api/assignments/${id}`);
}

export async function fetchAssignmentStudents(
  assignmentId: string
): Promise<AssignmentStudentRead[]> {
  return apiJson<AssignmentStudentRead[]>(`/api/assignments/${assignmentId}/students`);
}

export async function addAssignmentStudents(
  assignmentId: string,
  studentIds: string[]
): Promise<AssignmentStudentRead[]> {
  return apiJson<AssignmentStudentRead[]>(`/api/assignments/${assignmentId}/students`, {
    method: "POST",
    body: JSON.stringify({ student_ids: studentIds }),
  });
}

export async function fetchSubmissions(): Promise<SubmissionRead[]> {
  return apiJson<SubmissionRead[]>("/api/submissions");
}

export async function createSubmission(body: SubmissionCreateBody): Promise<SubmissionRead> {
  return apiJson<SubmissionRead>("/api/submissions", {
    method: "POST",
    body: JSON.stringify({
      assignment_id: body.assignment_id,
      student_id: body.student_id,
      code: body.code.trim(),
    }),
  });
}

export async function fetchSubmission(id: string): Promise<SubmissionRead> {
  return apiJson<SubmissionRead>(`/api/submissions/${id}`);
}

export async function fetchDocuments(): Promise<DocumentRead[]> {
  return apiJson<DocumentRead[]>("/api/documents");
}

export async function deleteDocument(id: string): Promise<void> {
  await apiJson(`/api/documents/${id}`, { method: "DELETE" });
}

/** Admin API */
export type AdminConfigResponse = {
  backend_version: string;
  database_path: string;
  storage_dir: string;
  grading_worker_enabled: boolean;
  grading_backend: string;
  grading_poll_interval_seconds: number;
  grading_mock_sleep_seconds: number;
  grading_max_attempts: number;
  jwt_expire_minutes: number;
};

export type StudentEnrollmentItem = {
  assignment: AssignmentRead;
  assigned_at: string;
};

export type AdminUserInsightsResponse = {
  user: UserRead;
  teacher_assignments: AssignmentRead[] | null;
  student_enrollments: StudentEnrollmentItem[] | null;
  student_submissions: SubmissionRead[] | null;
};

export async function fetchAdminConfig(): Promise<AdminConfigResponse> {
  return apiJson<AdminConfigResponse>("/api/admin/config");
}

/** Grading models catalog + llama health (admin). */
export type GradingModelRead = {
  id: string;
  display_name: string;
  notes: string;
  openai_model_name: string;
  n_ctx: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type GradingStatusResponse = {
  llama_health_ok: boolean;
  llama_health_url: string;
  llama_server_url: string;
  active_model: GradingModelRead | null;
  llama_auto_start: boolean;
  llama_health_error: string | null;
  note: string;
};

export type GradingModelCreateBody = {
  display_name: string;
  notes?: string;
  openai_model_name: string;
  n_ctx?: number;
};

export async function fetchGradingStatus(): Promise<GradingStatusResponse> {
  return apiJson<GradingStatusResponse>("/api/admin/grading/status");
}

export async function fetchGradingModels(): Promise<GradingModelRead[]> {
  return apiJson<GradingModelRead[]>("/api/admin/grading-models");
}

export async function createGradingModel(body: GradingModelCreateBody): Promise<GradingModelRead> {
  return apiJson<GradingModelRead>("/api/admin/grading-models", {
    method: "POST",
    body: JSON.stringify({
      display_name: body.display_name.trim(),
      notes: (body.notes ?? "").trim(),
      openai_model_name: body.openai_model_name.trim(),
      n_ctx: body.n_ctx ?? 8192,
    }),
  });
}

export async function activateGradingModel(modelId: string): Promise<GradingModelRead> {
  return apiJson<GradingModelRead>(`/api/admin/grading-models/${encodeURIComponent(modelId)}/activate`, {
    method: "POST",
  });
}

export async function deleteGradingModel(modelId: string): Promise<void> {
  await apiJson(`/api/admin/grading-models/${encodeURIComponent(modelId)}`, { method: "DELETE" });
}

export async function fetchAdminUsers(role?: UserRole | ""): Promise<UserRead[]> {
  const q = role ? `?role=${encodeURIComponent(role)}` : "";
  return apiJson<UserRead[]>(`/api/admin/users${q}`);
}

export async function fetchAdminUserInsights(userId: string): Promise<AdminUserInsightsResponse> {
  return apiJson<AdminUserInsightsResponse>(`/api/admin/users/${userId}/insights`);
}

export type UserUpdatePayload = {
  email?: string;
  full_name?: string;
  role?: UserRole;
  student_id_number?: string;
  is_active?: boolean;
  password?: string;
};

export async function patchUser(userId: string, body: UserUpdatePayload): Promise<UserRead> {
  return apiJson<UserRead>(`/api/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteUserAccount(userId: string): Promise<void> {
  await apiJson(`/api/users/${userId}`, { method: "DELETE" });
}
