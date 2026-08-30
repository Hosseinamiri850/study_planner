/** API types mirroring the Flask backend contract (app/routes/api.py). */

export interface User {
  id: number;
  username: string;
  fullname: string;
}

export interface MeUser extends User {
  is_admin: boolean;
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
