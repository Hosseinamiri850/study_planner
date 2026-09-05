/** API types mirroring the Flask backend contract (app/routes/api.py). */

export interface User {
  id: number;
  username: string;
  fullname: string;
}

export interface MeUser extends User {
  is_admin: boolean;
  /** Role from the RBAC rollout (student/teacher/school_admin/site_admin/
   * support). Presence does not imply school-admin dashboard access —
   * the API enforces authorization; this drives UI gating only. */
  role?: string;
  theme: "dark" | "light";
  created_at: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
}

export interface Task {
  id: number;
  course_id: number | null;
  course_key: string;
  title: string;
  description: string;
  priority: "low" | "medium" | "high";
  status: "pending" | "completed";
  estimated_hours: number;
  created_at: string;
  completed_at: string | null;
  /** Id of the currently-open study session, when one is running (added
   * in release QA so the SPA can restore the timer after a reload). */
  open_session_id: number | null;
}

export interface TaskListResponse {
  tasks: Task[];
}

export interface TaskListPaginatedResponse extends TaskListResponse {
  page: number;
  per_page: number;
  total: number;
  pages: number;
}

export interface CreateTaskInput {
  course_id?: number;
  course_key?: string;
  title?: string;
  description?: string;
  priority: "low" | "medium" | "high";
  estimated_hours: number;
}

export interface UpdateTaskInput {
  course_id?: number;
  course_key?: string;
  title?: string;
  description?: string;
  priority?: "low" | "medium" | "high";
  estimated_hours?: number;
  status?: "pending" | "completed";
}

export interface StudySession {
  id: number;
  task_id: number;
  started_at: string | null;
  ended_at: string | null;
  duration: number | null;
  is_open: boolean;
}

export interface StudySessionListResponse {
  sessions: StudySession[];
}

export interface DashboardStats {
  total_tasks: number;
  total_done: number;
  today_hours: number;
  week_hours: Record<string, number>;
  total_week_hours: number;
  month_hours: Record<string, number>;
  total_month_hours: number;
  courses: Record<
    string,
    { name: string; total: number; done: number; hours: number }
  >;
}

export interface Course {
  id: number;
  key: string;
  name_fa: string;
  name_en: string;
  major_id: number;
}

export interface Major {
  id: number;
  key: string;
  name_fa: string;
  name_en: string;
  courses: Course[];
}

export interface CourseListResponse {
  courses: Course[];
}

export interface MajorListResponse {
  majors: Major[];
}

export interface CreateCourseInput {
  name_fa: string;
  name_en: string;
  major_id: number;
  key?: string;
}

export interface UpdateCourseInput {
  name_fa?: string;
  name_en?: string;
}

export interface CreateMajorInput {
  name_fa: string;
  name_en: string;
  key?: string;
}

export interface UpdateMajorInput {
  name_fa?: string;
  name_en?: string;
}

export interface UpdateMeInput {
  fullname?: string;
  theme?: "dark" | "light";
  current_password?: string;
  password?: string;
}

export interface TranslateResponse {
  fa: string;
  en: string;
  detected: "fa" | "en";
  success: boolean;
}

// --- school admin (institution-scoped) ---

export type UserRole = "student" | "teacher" | "school_admin" | "site_admin" | "support";

export interface SchoolUser {
  id: number;
  username: string;
  fullname: string;
  role: string;
  class_id: number | null;
}

export interface SchoolClass {
  id: number;
  institution_id: number;
  name: string;
  grade_level: string | null;
}

export interface SchoolOverview {
  institution_id: number;
  students: SchoolUser[];
  teachers: SchoolUser[];
  classes: SchoolClass[];
}

export interface SchoolUsersResponse {
  users: SchoolUser[];
}

export interface SchoolClassesResponse {
  classes: SchoolClass[];
}

export interface CreateClassInput {
  name: string;
  grade_level?: string;
}

export interface UpdateClassInput {
  name?: string;
  grade_level?: string | null;
}

export interface AssignClassInput {
  class_id: number | null;
}

export interface UpdateSchoolUserResponse {
  user: SchoolUser;
}
