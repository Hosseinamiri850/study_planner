/**
 * Typed client for the Flask API, called from the BROWSER.
 *
 * Every request goes through `authFetch` (see lib/auth-context.tsx), which
 * injects the in-memory Bearer token and transparently refreshes once on a
 * 401. The refresh token itself never touches JS — it lives in an httpOnly
 * cookie set by the Next route handlers under app/api/auth/*.
 *
 * Routing: /api/auth/* have dedicated route handlers (cookie custody);
 * everything else goes through the /api/proxy/* catch-all, which forwards
 * to Flask server-side. Same-origin everywhere — no CORS involved.
 */

import { ApiError } from "./errors";
import type {
  AuthResponse,
  Course,
  CourseListResponse,
  CreateCourseInput,
  CreateMajorInput,
  CreateTaskInput,
  DashboardStats,
  Major,
  MajorListResponse,
  MeUser,
  RefreshResponse,
  StudySession,
  StudySessionListResponse,
  Task,
  TaskListPaginatedResponse,
  TaskListResponse,
  TranslateResponse,
  UpdateCourseInput,
  UpdateMajorInput,
  UpdateMeInput,
  UpdateTaskInput,
} from "@/types/api";

export class ApiClient {
  constructor(private authFetch: (path: string, init?: RequestInit) => Promise<Response>) {}

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await this.authFetch(path, init);
    return handleResponse<T>(response);
  }

  private async requestVoid(path: string, init?: RequestInit): Promise<void> {
    const response = await this.authFetch(path, init);
    if (!response.ok) await handleResponse<never>(response);
  }

  private json(init: Record<string, unknown>): RequestInit {
    return {
      ...init,
      headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    };
  }

  private post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, this.json({ method: "POST", body: JSON.stringify(body ?? {}) }));
  }

  private put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, this.json({ method: "PUT", body: JSON.stringify(body) }));
  }

  // --- auth (browser -> /api/auth/* Next route handlers -> Flask) ---

  register(username: string, password: string, fullname: string): Promise<AuthResponse> {
    return this.post("/api/auth/register", { username, password, fullname });
  }

  login(username: string, password: string): Promise<AuthResponse> {
    return this.post("/api/auth/login", { username, password });
  }

  /** Exchange the httpOnly refresh cookie for a fresh token pair. The
   * route handler also re-sets the cookie with the rotated token. */
  refresh(): Promise<RefreshResponse> {
    return this.post("/api/auth/refresh");
  }

  /** Revoke the refresh token behind the httpOnly cookie. */
  logout(): Promise<void> {
    return this.requestVoid("/api/auth/logout", { method: "POST" });
  }

  // --- me ---

  me(): Promise<{ user: MeUser }> {
    return this.request("/api/proxy/me");
  }

  updateMe(input: UpdateMeInput): Promise<{ user: MeUser }> {
    return this.put("/api/proxy/me", input);
  }

  // --- tasks ---

  listTasks(page?: number, perPage?: number): Promise<TaskListResponse | TaskListPaginatedResponse> {
    const query = page != null && perPage != null ? `?page=${page}&per_page=${perPage}` : "";
    return this.request(`/api/proxy/tasks${query}`);
  }

  createTask(input: CreateTaskInput): Promise<{ task: Task }> {
    return this.post("/api/proxy/tasks", input);
  }

  updateTask(taskId: number, input: UpdateTaskInput): Promise<{ task: Task }> {
    return this.put(`/api/proxy/tasks/${taskId}`, input);
  }

  deleteTask(taskId: number): Promise<void> {
    return this.requestVoid(`/api/proxy/tasks/${taskId}`, { method: "DELETE" });
  }

  // --- study sessions ---

  startSession(taskId: number): Promise<{ session: StudySession }> {
    return this.post(`/api/proxy/tasks/${taskId}/sessions`);
  }

  stopSession(taskId: number, sessionId: number): Promise<{ session: StudySession }> {
    return this.post(`/api/proxy/tasks/${taskId}/sessions/${sessionId}/stop`);
  }

  listSessions(taskId: number): Promise<StudySessionListResponse> {
    return this.request(`/api/proxy/tasks/${taskId}/sessions`);
  }

  // --- statistics ---

  dashboardStats(): Promise<DashboardStats> {
    return this.request("/api/proxy/statistics/dashboard");
  }

  // --- courses / majors ---

  listCourses(): Promise<CourseListResponse> {
    return this.request("/api/proxy/courses");
  }

  listMajors(): Promise<MajorListResponse> {
    return this.request("/api/proxy/majors");
  }

  createCourse(input: CreateCourseInput): Promise<{ course: Course }> {
    return this.post("/api/proxy/courses", input);
  }

  updateCourse(courseId: number, input: UpdateCourseInput): Promise<{ course: Course }> {
    return this.put(`/api/proxy/courses/${courseId}`, input);
  }

  deleteCourse(courseId: number): Promise<void> {
    return this.requestVoid(`/api/proxy/courses/${courseId}`, { method: "DELETE" });
  }

  createMajor(input: CreateMajorInput): Promise<{ major: Major }> {
    return this.post("/api/proxy/majors", input);
  }

  updateMajor(majorId: number, input: UpdateMajorInput): Promise<{ major: Major }> {
    return this.put(`/api/proxy/majors/${majorId}`, input);
  }

  deleteMajor(majorId: number): Promise<void> {
    return this.requestVoid(`/api/proxy/majors/${majorId}`, { method: "DELETE" });
  }

  // --- translate ---

  translate(text: string): Promise<TranslateResponse> {
    return this.post("/api/proxy/translate", { text });
  }
}

export async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }
  let message = `Request failed (${response.status}).`;
  try {
    const body = await response.json();
    if (body && typeof body.error === "string") message = body.error;
  } catch {
    // non-JSON error body — keep the generic message
  }
  throw new ApiError(response.status, message);
}

export const api = new ApiClient(() => {
  // Replaced at runtime by AuthProvider wiring — see lib/auth-context.tsx.
  throw new Error("ApiClient used before AuthProvider mounted. Wrap your app in <AuthProvider>.");
});
