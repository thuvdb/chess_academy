import api from '../lib/api';

export interface ClassItem {
  id: string;
  name: string;
  level: string | null;
  max_students: number;
  current_students: number;
  schedule_json: Record<string, string[]> | null;
  is_active: boolean;
  teacher_id: string | null;
  teacher_name: string | null;
  center_id: string | null;
  branch_id: string | null;
  created_at: string;
}

export interface EnrollmentItem {
  id: string;
  class_id: string;
  student_id: string;
  enrolled_at: string;
  status: string;
  student_name: string | null;
  student_email: string | null;
}

export interface ClassCreatePayload {
  name: string;
  level?: string;
  max_students?: number;
  schedule_json?: Record<string, string[]>;
  teacher_id?: string;
}

export interface ClassUpdatePayload {
  name?: string;
  level?: string;
  max_students?: number;
  schedule_json?: Record<string, string[]>;
  is_active?: boolean;
  teacher_id?: string;
}

// List classes with filters
export const getClasses = (params?: {
  skip?: number;
  limit?: number;
  level?: string;
  search?: string;
  is_active?: boolean;
}) => api.get<ClassItem[]>('/classes', { params });

// Get single class
export const getClassById = (id: string) =>
  api.get<ClassItem>(`/classes/${id}`);

// Create class
export const createClass = (data: ClassCreatePayload) =>
  api.post<ClassItem>('/classes', data);

// Update class
export const updateClass = (id: string, data: ClassUpdatePayload) =>
  api.put<ClassItem>(`/classes/${id}`, data);

// Delete (soft) class
export const deleteClass = (id: string) =>
  api.delete(`/classes/${id}`);

// Get students in class
export const getClassStudents = (classId: string) =>
  api.get<EnrollmentItem[]>(`/classes/${classId}/students`);

// Enroll student
export const enrollStudent = (classId: string, studentId: string) =>
  api.post<EnrollmentItem>(`/classes/${classId}/students`, { student_id: studentId });

// Unenroll student
export const unenrollStudent = (classId: string, studentId: string) =>
  api.delete(`/classes/${classId}/students/${studentId}`);
