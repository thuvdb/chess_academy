import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, BookOpen, Clock, Users, CheckCircle, Play, Swords, Star, AlertCircle
} from 'lucide-react';
import {
  getAssignmentById, getAssignmentProgress, getPuzzles,
  type AssignmentItem, type PuzzleItem
} from '../lib/puzzleApi';
import { getClassStudents, type EnrollmentItem } from '../lib/classApi';
import { useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';

interface ProgressRecord {
  id: string;
  student_id: string;
  student_name: string;
  puzzle_id: string;
  status: string;
  attempts: number;
  points_earned: number;
  updated_at: string;
}

export default function AssignmentDetail() {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const { user } = useAuthStore();

  const [assignment, setAssignment] = useState<AssignmentItem | null>(null);
  const [progressData, setProgressData] = useState<ProgressRecord[]>([]);
  const [students, setStudents] = useState<EnrollmentItem[]>([]);
  const [puzzles, setPuzzles] = useState<PuzzleItem[]>([]);
  const [loading, setLoading] = useState(true);

  const isStudent = user?.role === 'student';

  const fetchDetails = useCallback(async () => {
    if (!assignmentId) return;
    setLoading(true);
    try {
      const [asm, prog, allPuz] = await Promise.all([
        getAssignmentById(assignmentId),
        getAssignmentProgress(assignmentId),
        getPuzzles({ limit: 100 }),
      ]);

      setAssignment(asm);
      setProgressData(prog);

      // Filter puzzles belonging to this assignment
      if (asm.puzzle_ids && asm.puzzle_ids.length > 0) {
        const matched = allPuz.filter((p) => asm.puzzle_ids?.includes(p.id));
        setPuzzles(matched);
      }

      if (asm.class_id && !isStudent) {
        const stuRes = await getClassStudents(asm.class_id);
        setStudents(stuRes.data || []);
      }
    } catch {
      toast.error('Không thể tải dữ liệu bài tập');
    } finally {
      setLoading(false);
    }
  }, [assignmentId, isStudent]);

  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  // Student progress aggregation
  const myProgressRecords = useMemo(() => {
    if (!user) return [];
    return progressData.filter((p) => p.student_id === user.id);
  }, [progressData, user]);

  const solvedPuzzleIds = useMemo(() => {
    return new Set(
      myProgressRecords
        .filter((p) => p.status === 'completed' || p.status === 'passed' || p.status === 'solved')
        .map((p) => p.puzzle_id)
    );
  }, [myProgressRecords]);

  const myPoints = useMemo(() => {
    return myProgressRecords.reduce((sum, p) => sum + (p.points_earned || 0), 0);
  }, [myProgressRecords]);

  // Overall class stats for teacher
  const studentStats = useMemo(() => {
    if (!assignment) return [];

    const statsMap: Record<string, { id: string; name: string; completed: number; points: number; attempts: number }> = {};

    students.forEach((s) => {
      statsMap[s.student_id] = {
        id: s.student_id,
        name: s.student_name || 'Unknown',
        completed: 0,
        points: 0,
        attempts: 0,
      };
    });

    progressData.forEach((p) => {
      if (!statsMap[p.student_id]) {
        statsMap[p.student_id] = {
          id: p.student_id,
          name: p.student_name,
          completed: 0,
          points: 0,
          attempts: 0,
        };
      }
      const s = statsMap[p.student_id];
      s.attempts += p.attempts;
      s.points += p.points_earned;
      if (p.status === 'completed' || p.status === 'passed' || p.status === 'solved') {
        s.completed += 1;
      }
    });

    return Object.values(statsMap).sort((a, b) => b.points - a.points);
  }, [assignment, progressData, students]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-24">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  if (!assignment) {
    return (
      <div className="text-center py-12 text-slate-400">
        Bài tập không tồn tại.
      </div>
    );
  }

  const totalPuzzles = assignment.puzzle_ids?.length || 0;
  const isExpired = assignment.due_date ? new Date(assignment.due_date) < new Date() : false;
  const nextUnsolvedPuzzle = puzzles.find((p) => !solvedPuzzleIds.has(p.id)) || puzzles[0];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <Link
            to="/assignments"
            className="p-2.5 hover:bg-slate-800 rounded-xl text-slate-400 hover:text-white transition-colors border border-slate-700/60 mt-1"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              {assignment.title}
            </h1>
            <div className="text-slate-400 mt-2 flex flex-wrap items-center gap-3 text-sm">
              <span className="flex items-center gap-1.5 bg-indigo-500/15 text-indigo-400 px-2.5 py-1 rounded-lg border border-indigo-500/30 text-xs font-medium">
                <Users className="w-3.5 h-3.5" />
                Lớp: {assignment.class_?.name || 'Chung'}
              </span>
              {assignment.due_date && (
                <span className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg border ${
                  isExpired
                    ? 'bg-red-500/15 text-red-400 border-red-500/30'
                    : 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                }`}>
                  <Clock className="w-3.5 h-3.5" />
                  Hạn nộp: {new Date(assignment.due_date).toLocaleDateString('vi-VN')}
                  {isExpired && <span className="ml-1 text-[10px] bg-red-500/30 px-1 py-0.5 rounded text-red-200">Đã hết hạn</span>}
                </span>
              )}
              <span className="flex items-center gap-1.5 text-slate-300 text-xs">
                <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
                {totalPuzzles} thế cờ
              </span>
            </div>
          </div>
        </div>

        {/* Action Button for Student */}
        {nextUnsolvedPuzzle && (
          <Link
            to={`/practice?puzzleId=${nextUnsolvedPuzzle.id}&assignmentId=${assignment.id}`}
            className="flex items-center gap-2 px-6 py-3 bg-linear-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-900 font-bold rounded-xl text-sm transition shadow-lg shadow-amber-500/25 shrink-0 self-start sm:self-auto"
          >
            <Play className="w-4 h-4 fill-current" />
            {solvedPuzzleIds.size === 0
              ? 'Bắt đầu làm bài'
              : solvedPuzzleIds.size < totalPuzzles
              ? 'Tiếp tục làm bài'
              : 'Luyện tập lại'}
          </Link>
        )}
      </div>

      {/* Student Progress Summary Card */}
      {isStudent && (
        <div className="bg-linear-to-br from-indigo-950/40 via-slate-800/80 to-slate-900/80 border border-indigo-500/30 rounded-2xl p-6 shadow-xl">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div>
              <p className="text-slate-400 text-xs uppercase tracking-wider font-semibold">Tiến độ của bạn</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-3xl font-extrabold text-white">{solvedPuzzleIds.size}</span>
                <span className="text-slate-400 text-sm">/ {totalPuzzles} thế cờ</span>
              </div>
              <div className="w-full bg-slate-700/60 rounded-full h-2 mt-3">
                <div
                  className="bg-linear-to-r from-amber-400 to-orange-500 h-2 rounded-full transition-all"
                  style={{ width: `${totalPuzzles > 0 ? (solvedPuzzleIds.size / totalPuzzles) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div>
              <p className="text-slate-400 text-xs uppercase tracking-wider font-semibold">Điểm tích lũy</p>
              <p className="text-3xl font-extrabold text-amber-400 mt-2">{myPoints} pts</p>
              <p className="text-slate-400 text-xs mt-3 flex items-center gap-1">
                <Star className="w-3.5 h-3.5 text-amber-400 fill-current" />
                Cộng trực tiếp vào bảng xếp hạng
              </p>
            </div>

            <div>
              <p className="text-slate-400 text-xs uppercase tracking-wider font-semibold">Trạng thái nộp bài</p>
              <div className="mt-2">
                {solvedPuzzleIds.size >= totalPuzzles && totalPuzzles > 0 ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-green-500/20 text-green-400 border border-green-500/40 text-sm font-semibold">
                    <CheckCircle className="w-4 h-4" /> Hoàn thành 100%
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/40 text-sm font-semibold">
                    <AlertCircle className="w-4 h-4" /> Đang thực hiện ({totalPuzzles - solvedPuzzleIds.size} bài còn lại)
                  </span>
                )}
              </div>
              <p className="text-slate-400 text-xs mt-3">
                {isExpired ? 'Hạn chót đã qua, hãy cố gắng hoàn thành sớm' : 'Vẫn còn trong thời hạn nộp bài'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Description */}
      <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl p-6 shadow-xl">
        <h2 className="text-base font-bold text-white mb-2 flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-indigo-400" />
          Hướng dẫn & Yêu cầu bài tập
        </h2>
        <p className="text-slate-300 text-sm whitespace-pre-wrap leading-relaxed">
          {assignment.description || 'Không có ghi chú thêm.'}
        </p>
      </div>

      {/* Puzzles in Assignment */}
      <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl p-6 shadow-xl space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Swords className="w-4 h-4 text-amber-400" />
          Danh sách thế cờ cần giải ({puzzles.length})
        </h2>

        {puzzles.length === 0 ? (
          <p className="text-slate-500 text-sm italic">Chưa có thông tin thế cờ chi tiết.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {puzzles.map((p, idx) => {
              const isSolved = solvedPuzzleIds.has(p.id);
              return (
                <div
                  key={p.id}
                  className={`flex items-center justify-between p-4 rounded-xl border transition-all ${
                    isSolved
                      ? 'bg-green-500/10 border-green-500/30'
                      : 'bg-slate-900/60 border-slate-700/60 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${
                      isSolved ? 'bg-green-500/20 text-green-400' : 'bg-slate-800 text-slate-400'
                    }`}>
                      #{idx + 1}
                    </div>
                    <div>
                      <p className="text-white text-sm font-medium line-clamp-1">{p.title}</p>
                      <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                        <span className="text-amber-400 font-mono">Rating {p.rating}</span>
                        <span>·</span>
                        <span className="capitalize">{p.difficulty || 'Normal'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {isSolved ? (
                      <span className="text-xs text-green-400 flex items-center gap-1 font-medium bg-green-500/15 px-2.5 py-1 rounded-lg">
                        <CheckCircle className="w-3.5 h-3.5" /> Đã giải
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded-lg">
                        Chưa làm
                      </span>
                    )}
                    <Link
                      to={`/practice?puzzleId=${p.id}&assignmentId=${assignment.id}`}
                      className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition"
                    >
                      {isSolved ? 'Làm lại' : 'Làm bài'}
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Class Progress Table (Teachers/Admins Only) */}
      {!isStudent && (
        <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl shadow-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-700/60 flex justify-between items-center bg-slate-800/50">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Users className="w-4 h-4 text-indigo-400" />
              Tiến độ Học viên trong lớp ({studentStats.length} học viên)
            </h2>
          </div>

          {studentStats.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-sm">
              Chưa có học viên nào trong lớp hoặc chưa có dữ liệu tiến độ.
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700/60 bg-slate-800/80">
                  <th className="text-left px-6 py-3.5 text-slate-400 text-xs font-semibold uppercase">Học viên</th>
                  <th className="text-center px-6 py-3.5 text-slate-400 text-xs font-semibold uppercase">Tiến độ ({totalPuzzles})</th>
                  <th className="text-center px-6 py-3.5 text-slate-400 text-xs font-semibold uppercase">Tổng Điểm</th>
                  <th className="text-center px-6 py-3.5 text-slate-400 text-xs font-semibold uppercase">Trạng thái</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40">
                {studentStats.map((s, i) => {
                  const isDone = s.completed >= totalPuzzles && totalPuzzles > 0;
                  return (
                    <tr key={s.id} className="hover:bg-slate-700/30 transition-colors">
                      <td className="px-6 py-3.5 text-white font-medium flex items-center gap-3">
                        <div className="w-7 h-7 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-xs">
                          {i + 1}
                        </div>
                        <span className="text-sm">{s.name}</span>
                      </td>
                      <td className="px-6 py-3.5 text-center">
                        <div className="flex items-center justify-center gap-1.5 text-sm">
                          <span className="text-white font-medium">{s.completed}</span>
                          <span className="text-slate-500">/ {totalPuzzles}</span>
                        </div>
                        <div className="w-24 mx-auto bg-slate-700 rounded-full h-1.5 mt-1.5">
                          <div
                            className="bg-green-500 h-1.5 rounded-full transition-all"
                            style={{ width: `${totalPuzzles > 0 ? (s.completed / totalPuzzles) * 100 : 0}%` }}
                          />
                        </div>
                      </td>
                      <td className="px-6 py-3.5 text-center">
                        <span className="text-amber-400 font-bold text-sm">{s.points} pts</span>
                      </td>
                      <td className="px-6 py-3.5 text-center">
                        {isDone ? (
                          <span className="bg-green-500/15 text-green-400 px-2.5 py-1 rounded-lg text-xs font-medium inline-flex items-center gap-1">
                            <CheckCircle className="w-3.5 h-3.5" /> Hoàn thành
                          </span>
                        ) : (
                          <span className="bg-slate-700 text-slate-400 px-2.5 py-1 rounded-lg text-xs font-medium inline-flex items-center gap-1">
                            Đang làm
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
