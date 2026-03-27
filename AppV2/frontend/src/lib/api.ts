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
