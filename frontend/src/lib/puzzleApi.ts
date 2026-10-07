import api from './api';

export interface PuzzleSolution {
  id?: string;
  move_order: number;
  move_uci: string;
  move_san: string;
  is_best_move: boolean;
  alternative_moves?: string[] | null;
  explanation?: string | null;
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
}

export interface CreatePuzzleInput {
  title: string;
  description?: string;
  fen: string;
  difficulty?: string;
  puzzle_type?: string;
  tags?: string[];
  rating?: number;
  solutions: {
    move_order: number;
    move_uci: string;
    move_san: string;
    is_best_move: boolean;
    explanation?: string;
  }[];
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

// ── Practice & Progress API ──────────────────────────────────
export async function submitPuzzleAttempt(input: {
  puzzle_id: string;
  assignment_id?: string;
  moves_uci: string[];
  moves_san?: string[];
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
