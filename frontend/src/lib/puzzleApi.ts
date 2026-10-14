import api from './api';

export interface PuzzleSolution {
  id?: string;
  move_order: number;
  move_uci: string;
  move_san: string;
  /** 'w' | 'b' — bên thực hiện nước này. Trước đây không có nên UI gắn nhãn sai bên. */
  side?: 'w' | 'b' | null;
  is_best_move: boolean;
  alternative_moves?: string[] | null;
  explanation?: string | null;
}

/**
 * Cây biến thể lời giải.
 *
 * `player_moves` giữ MỌI nước của bên giải ép được chiếu hết tại nút đó, và mỗi
 * nước giữ MỌI đáp trả hợp lệ của đối phương, mỗi đáp trả lại có nhánh riêng.
 * Thay cho mảng phẳng cũ vốn trộn nước hai bên vào một danh sách.
 */
export interface SolutionTreeNode {
  player_moves: SolutionPlayerMove[];
}

export interface SolutionPlayerMove {
  uci: string;
  san: string;
  is_mate: boolean;
  replies: SolutionReply[];
}

export interface SolutionReply {
  uci: string;
  san: string;
  /** Nhánh chống đỡ cầm cự lâu nhất — nước máy nên đáp trả. */
  is_main?: boolean;
  next: SolutionTreeNode;
}

export interface SolutionTree extends SolutionTreeNode {
  player_color: 'w' | 'b';
  mate_in: number;
  generated_by?: string;
  generated_at?: string;
}

export interface PuzzleItem {
  id: string;
  title: string;
  description?: string | null;
  fen: string;
  pgn?: string | null;
  difficulty?: 'easy' | 'medium' | 'hard' | 'expert' | string;
  puzzle_type?: string;
  source?: string;
  tags?: string[] | null;
  rating: number;
  play_count: number;
  success_rate?: number | null;
  board_image_url?: string | null;
  created_at?: string;
  solutions: PuzzleSolution[];
  solution_tree?: SolutionTree | null;
  mate_in?: number | null;
  solution_verified?: boolean;
  solution_verified_at?: string | null;
  verification_error?: string | null;
}

export interface CreatePuzzleInput {
  title: string;
  description?: string;
  fen: string;
  difficulty?: string;
  puzzle_type?: string;
  tags?: string[];
  rating?: number;
  /** move_san do backend sinh khi replay — client chỉ cần gửi UCI. */
  solutions: {
    move_order: number;
    move_uci: string;
    is_best_move: boolean;
    explanation?: string;
  }[];
}

// ── Kiểm tra lời giải trước khi lưu ──────────────────────────
export interface PlyCheck {
  index: number;
  uci: string;
  san?: string | null;
  side?: 'w' | 'b' | null;
  legal: boolean;
  is_player_move: boolean;
  forces_mate?: boolean | null;
  error?: string | null;
}

export interface ValidateSolutionResult {
  ok: boolean;
  fen: string;
  player_color: 'w' | 'b';
  plies: PlyCheck[];
  ends_in_mate: boolean;
  mate_in?: number | null;
  declared_mate_in?: number | null;
  expected_plies?: number | null;
  errors: string[];
  warnings: string[];
  player_moves: PlyCheck[];
  opponent_moves: PlyCheck[];
  solution_tree?: SolutionTree | null;
}

export interface AssignmentItem {
  id: string;
  class_id: string;
  teacher_id: string;
  title: string;
  description?: string | null;
  puzzle_ids?: string[] | null;
  due_date?: string | null;
  max_attempts?: number;
  created_at?: string;
  class_?: { id: string; name: string };
  teacher?: { id: string; full_name: string };
}

export interface AttemptResult {
  id: string;
  progress_id: string;
  attempt_no: number;
  is_correct: boolean;
  points_earned: number;
  result: string;
}

export interface LeaderboardUser {
  student_id: string;
  full_name: string;
  avatar_url?: string | null;
  rating: number;
  puzzles_solved: number;
  points: number;
}

// ── Puzzles API ──────────────────────────────────────────────
export async function getPuzzles(params?: {
  difficulty?: string;
  puzzle_type?: string;
  search?: string;
  skip?: number;
  limit?: number;
}): Promise<PuzzleItem[]> {
  const { data } = await api.get('/puzzles', { params });
  return data;
}

export async function getPuzzle(id: string): Promise<PuzzleItem> {
  const { data } = await api.get(`/puzzles/${id}`);
  return data;
}

export async function createPuzzle(input: CreatePuzzleInput): Promise<PuzzleItem> {
  const { data } = await api.post('/puzzles', input);
  return data;
}

export async function updatePuzzle(id: string, input: Partial<CreatePuzzleInput>): Promise<PuzzleItem> {
  const { data } = await api.put(`/puzzles/${id}`, input);
  return data;
}

export async function deletePuzzle(id: string): Promise<void> {
  await api.delete(`/puzzles/${id}`);
}

/** Kiểm tra dãy UCI trước khi lưu bài — không ghi gì vào DB. */
export async function validateSolution(input: {
  fen: string;
  moves_uci: string[];
  puzzle_type?: string;
}): Promise<ValidateSolutionResult> {
  const { data } = await api.post('/puzzles/validate-solution', input);
  return data;
}

// ── Practice & Progress API ──────────────────────────────────
export async function submitPuzzleAttempt(input: {
  puzzle_id: string;
  assignment_id?: string;
  moves_uci: string[];
  moves_san?: string[];
  /** Tách riêng nước của học sinh khỏi đáp trả của máy. */
  player_moves_uci?: string[];
  opponent_moves_uci?: string[];
  time_spent_seconds: number;
  hint_used: boolean;
}): Promise<AttemptResult> {
  const { data } = await api.post('/progress/attempt', input);
  return data;
}

// ── Assignments API ──────────────────────────────────────────
export async function getAssignments(params?: {
  class_id?: string;
  skip?: number;
  limit?: number;
}): Promise<AssignmentItem[]> {
  const { data } = await api.get('/assignments', { params });
  return data;
}

export async function getAssignmentById(id: string): Promise<AssignmentItem> {
  const { data } = await api.get(`/assignments/${id}`);
  return data;
}

export async function getAssignmentProgress(id: string): Promise<any[]> {
  const { data } = await api.get(`/assignments/${id}/progress`);
  return data;
}

export async function getAssignmentPuzzles(id: string): Promise<PuzzleItem[]> {
  const { data } = await api.get(`/assignments/${id}/puzzles`);
  return data;
}

export async function createAssignment(input: {
  class_id: string;
  title: string;
  description?: string;
  puzzle_ids: string[];
  due_date?: string;
  max_attempts?: number;
}): Promise<AssignmentItem> {
  const { data } = await api.post('/assignments', input);
  return data;
}

// ── Leaderboard API ──────────────────────────────────────────
export async function getLeaderboard(limit = 50): Promise<LeaderboardUser[]> {
  const { data } = await api.get('/leaderboard', { params: { limit } });
  return data;
}

// ── Assignment Submission & Lock API ──────────────────────────
export interface SubmissionHistoryItem {
  attempt_no: number;
  status: string;
  total_points: number;
  completed_puzzles: number;
  submitted_at?: string | null;
  graded_at?: string | null;
  version: number;
  teacher_feedback?: string | null;
  teacher_adjustment?: number;
  reopened_at?: string | null;
  reopen_reason?: string | null;
}

export interface PreviousSubmissionSummary {
  attempt_no: number;
  status: string;
  total_points: number;
  completed_puzzles: number;
  teacher_feedback?: string | null;
  submitted_at?: string | null;
  graded_at?: string | null;
}

export interface AssignmentSubmission {
  id: string;
  assignment_id: string;
  student_id: string;
  attempt_no: number;
  version: number;
  status: 'not_started' | 'in_progress' | 'reopened' | 'submitted' | 'graded' | 'returned';
  submitted_at?: string | null;
  total_points: number;
  completed_puzzles: number;
  reopened_at?: string | null;
  reopened_by?: string | null;
  reopen_reason?: string | null;
  teacher_feedback?: string | null;
  graded_at?: string | null;
  graded_by?: string | null;
  teacher_adjustment?: number;
  created_at?: string;
  updated_at?: string;
  can_grade?: boolean;
  previous_submission?: PreviousSubmissionSummary | null;
}

export interface SubmissionAttempt {
  attempt_no: number;
  moves_san: string[];
  moves_uci: string[];
  is_correct: boolean | null;
  hint_used: boolean;
  points_earned: number;
}

export interface SubmissionModelSolution {
  move_order: number;
  move_san: string;
  move_uci: string;
  is_best_move: boolean;
}

export interface SubmissionDetailItem {
  puzzle_id: string;
  title: string;
  fen: string;
  difficulty: string;
  puzzle_type: string;
  rating: number;
  solution_tree?: any;
  model_solutions: SubmissionModelSolution[];
  status: string;
  is_solved: boolean;
  attempts_count: number;
  points_earned: number;
  hints_used: number;
  time_spent_seconds: number;
  last_attempt?: SubmissionAttempt | null;
  all_attempts: SubmissionAttempt[];
}

export interface StudentSubmissionDetail {
  submission: AssignmentSubmission;
  history?: SubmissionHistoryItem[];
  previous_submission?: PreviousSubmissionSummary | null;
  items: SubmissionDetailItem[];
}

export async function getMyAssignmentSubmission(id: string): Promise<AssignmentSubmission | null> {
  const { data } = await api.get(`/assignments/${id}/my-submission`);
  return data;
}

export async function submitAssignment(id: string): Promise<AssignmentSubmission> {
  const { data } = await api.post(`/assignments/${id}/submit`);
  return data;
}

export async function reopenAssignment(
  id: string,
  studentId: string,
  reason: string,
): Promise<AssignmentSubmission> {
  const { data } = await api.post(`/assignments/${id}/reopen`, {
    student_id: studentId,
    reason,
  });
  return data;
}

export async function getStudentSubmissionDetail(
  assignmentId: string,
  studentId: string,
  attemptNo?: number
): Promise<StudentSubmissionDetail> {
  const { data } = await api.get(`/assignments/${assignmentId}/submissions/${studentId}`, {
    params: attemptNo !== undefined ? { attempt_no: attemptNo } : undefined,
  });
  return data;
}

export async function gradeAndReturnAssignment(
  assignmentId: string,
  studentId: string,
  feedback?: string,
  adjustment: number = 0,
  expectedVersion?: number,
  attemptNo?: number
): Promise<AssignmentSubmission> {
  const { data } = await api.post(`/assignments/${assignmentId}/submissions/${studentId}/return`, {
    student_id: studentId,
    teacher_feedback: feedback,
    teacher_adjustment: adjustment,
    expected_version: expectedVersion,
    attempt_no: attemptNo,
  });
  return data;
}


