import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Chessboard } from 'react-chessboard';
import {
  ArrowLeft, BookOpen, Clock, Users, CheckCircle, Play, Swords, Star, AlertCircle,
  Lock, RotateCcw, Send, Eye, ShieldAlert, CheckCircle2, X, FileText,
  MessageSquare, Award, Check, Sparkles
} from 'lucide-react';
import {
  getAssignmentById, getAssignmentProgress, getAssignmentPuzzles,
  getMyAssignmentSubmission, submitAssignment, reopenAssignment,
  getStudentSubmissionDetail, gradeAndReturnAssignment,
  type AssignmentItem, type PuzzleItem, type AssignmentSubmission,
  type StudentSubmissionDetail
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
  submission_id?: string | null;
  attempt_no?: number;
  submission_version?: number;
  submission_status?: 'not_started' | 'in_progress' | 'reopened' | 'submitted' | 'graded' | 'returned';
  submission_total_points?: number;
  can_grade?: boolean;
  submitted_at?: string | null;
  reopened_at?: string | null;
  reopen_reason?: string | null;
  previous_submission?: {
    attempt_no: number;
    status: string;
    total_points: number;
    completed_puzzles: number;
    teacher_feedback?: string | null;
    submitted_at?: string | null;
    graded_at?: string | null;
  } | null;
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
  const [mySubmission, setMySubmission] = useState<AssignmentSubmission | null>(null);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [reopenModalStudent, setReopenModalStudent] = useState<{ id: string; name: string } | null>(null);
  const [reopenReason, setReopenReason] = useState('');
  const [reopening, setReopening] = useState(false);

  // ── State Chấm bài cho Giáo viên (Grading Modal) ──
  const [gradingStudent, setGradingStudent] = useState<{ id: string; name: string } | null>(null);
  const [gradingDetail, setGradingDetail] = useState<StudentSubmissionDetail | null>(null);
  const [loadingGradingDetail, setLoadingGradingDetail] = useState(false);
  const [selectedGradingIndex, setSelectedGradingIndex] = useState(0);
  const [, setSelectedAttemptNo] = useState<number | undefined>(undefined);
  const [teacherFeedback, setTeacherFeedback] = useState('');
  const [teacherAdjustment, setTeacherAdjustment] = useState<number>(0);
  const [submittingGrade, setSubmittingGrade] = useState(false);

  const isStudent = user?.role === 'student';

  const fetchDetails = useCallback(async () => {
    if (!assignmentId) return;
    setLoading(true);
    try {
      const [asmResult, progResult, asmPuzzlesResult, subResult] = await Promise.allSettled([
        getAssignmentById(assignmentId),
        getAssignmentProgress(assignmentId),
        getAssignmentPuzzles(assignmentId),
        isStudent ? getMyAssignmentSubmission(assignmentId) : Promise.resolve(null),
      ]);

      if (asmResult.status === 'fulfilled') {
        const asm = asmResult.value;
        setAssignment(asm);

        if (asm.class_id && !isStudent) {
          try {
            const stuRes = await getClassStudents(asm.class_id);
            setStudents(stuRes.data || []);
          } catch (err) {
            console.error('Failed to load class students:', err);
          }
        }
      } else {
        toast.error('Không thể tải thông tin bài tập');
      }

      if (progResult.status === 'fulfilled') {
        setProgressData(progResult.value);
      } else {
        console.error('Failed to load progress data:', progResult.reason);
      }

      if (asmPuzzlesResult.status === 'fulfilled') {
        setPuzzles(asmPuzzlesResult.value);
      } else {
        console.error('Failed to load puzzles:', asmPuzzlesResult.reason);
      }

      if (subResult.status === 'fulfilled' && subResult.value) {
        setMySubmission(subResult.value);
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

  const handleSubmitAssignment = async () => {
    if (!assignmentId) return;
    setSubmitting(true);
    try {
      const res = await submitAssignment(assignmentId);
      setMySubmission(res);
      setShowSubmitModal(false);
      toast.success('🎉 Nộp bài thành công! Bài tập đã được gửi cho giáo viên chấm.');
      await fetchDetails();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Không thể nộp bài tập';
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReopenAssignment = async () => {
    if (!assignmentId || !reopenModalStudent) return;
    if (!reopenReason.trim()) {
      toast.error('Vui lòng nhập lý do mở lại bài');
      return;
    }
    setReopening(true);
    try {
      await reopenAssignment(assignmentId, reopenModalStudent.id, reopenReason.trim());
      toast.success(`Đã mở lại bài tập cho ${reopenModalStudent.name}`);
      setReopenModalStudent(null);
      setReopenReason('');
      await fetchDetails();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Không thể mở lại bài tập';
      toast.error(msg);
    } finally {
      setReopening(false);
    }
  };

  // Mở modal Chấm bài & xem chi tiết lời giải
  const handleOpenGradingModal = async (student: { id: string; name: string }, attemptNo?: number) => {
    if (!assignmentId) return;
    setGradingStudent(student);
    setLoadingGradingDetail(true);
    setSelectedGradingIndex(0);
    setSelectedAttemptNo(attemptNo);
    try {
      const data = await getStudentSubmissionDetail(assignmentId, student.id, attemptNo);
      setGradingDetail(data);
      setTeacherFeedback(data.submission.teacher_feedback || '');
      setTeacherAdjustment(data.submission.teacher_adjustment || 0);
    } catch {
      toast.error('Không thể tải chi tiết bài làm của học sinh');
      setGradingStudent(null);
    } finally {
      setLoadingGradingDetail(false);
    }
  };

  // Chuyển đổi xem attempt khác trong Modal chấm bài
  const handleSwitchGradingAttempt = async (attemptNo: number) => {
    if (!assignmentId || !gradingStudent) return;
    setLoadingGradingDetail(true);
    setSelectedAttemptNo(attemptNo);
    setSelectedGradingIndex(0);
    try {
      const data = await getStudentSubmissionDetail(assignmentId, gradingStudent.id, attemptNo);
      setGradingDetail(data);
      setTeacherFeedback(data.submission.teacher_feedback || '');
      setTeacherAdjustment(data.submission.teacher_adjustment || 0);
    } catch {
      toast.error('Không thể tải chi tiết lần làm bài');
    } finally {
      setLoadingGradingDetail(false);
    }
  };

  // Lưu nhận xét và Trả bài cho học sinh
  const handleGradeAndReturn = async () => {
    if (!assignmentId || !gradingStudent || !gradingDetail) return;
    if (!gradingDetail.submission.can_grade) {
      toast.error('Học sinh chưa nộp bài lần này, không thể chấm hoặc trả bài.');
      return;
    }
    setSubmittingGrade(true);
    try {
      await gradeAndReturnAssignment(
        assignmentId,
        gradingStudent.id,
        teacherFeedback.trim() || undefined,
        Number(teacherAdjustment) || 0,
        gradingDetail.submission.version,
        gradingDetail.submission.attempt_no
      );
      toast.success(`🎉 Đã trả bài thành công cho ${gradingStudent.name}!`);
      setGradingStudent(null);
      await fetchDetails();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Không thể chấm và trả bài';
      toast.error(msg);
    } finally {
      setSubmittingGrade(false);
    }
  };

  // Student progress aggregation (deduplicated by puzzle_id to avoid race condition duplicates)
  const myProgressMap = useMemo(() => {
    if (!user) return new Map<string, ProgressRecord>();
    const map = new Map<string, ProgressRecord>();
    (progressData || [])
      .filter((p) => p.student_id === user.id)
      .forEach((p) => {
        const existing = map.get(p.puzzle_id);
        if (!existing || (p.points_earned || 0) > (existing.points_earned || 0)) {
          map.set(p.puzzle_id, p);
        }
      });
    return map;
  }, [progressData, user]);

  const solvedPuzzleIds = useMemo(() => {
    const solvedSet = new Set<string>();
    myProgressMap.forEach((p, puzzleId) => {
      if (p.status === 'completed' || p.status === 'passed' || p.status === 'solved') {
        solvedSet.add(puzzleId);
      }
    });
    return solvedSet;
  }, [myProgressMap]);

  // Danh sách các thế cờ học sinh đã thực hiện làm (dù đúng hay sai)
  const attemptedPuzzleIds = useMemo(() => {
    const attemptedSet = new Set<string>();
    myProgressMap.forEach((p, puzzleId) => {
      if ((p.attempts || 0) > 0 || p.status === 'completed' || p.status === 'passed' || p.status === 'solved') {
        attemptedSet.add(puzzleId);
      }
    });
    return attemptedSet;
  }, [myProgressMap]);

  const myPoints = useMemo(() => {
    if (mySubmission) {
      if (['submitted', 'graded', 'returned'].includes(mySubmission.status)) {
        return mySubmission.total_points;
      }
      if (mySubmission.previous_submission) {
        return mySubmission.previous_submission.total_points;
      }
      return 0;
    }
    let sum = 0;
    myProgressMap.forEach((p) => {
      sum += p.points_earned || 0;
    });
    return sum;
  }, [mySubmission, myProgressMap]);

  // Overall class stats for teacher (deduplicated by puzzle_id)
  const studentStats = useMemo(() => {
    if (!assignment) return [];

    const statsMap: Record<
      string,
      {
        id: string;
        name: string;
        completedSet: Set<string>;
        puzzleMap: Map<string, ProgressRecord>;
        attempts: number;
        attemptNo: number;
        submissionTotalPoints: number;
        canGrade: boolean;
        submissionStatus: 'not_started' | 'in_progress' | 'reopened' | 'submitted' | 'graded' | 'returned';
        submittedAt: string | null;
        reopenedAt: string | null;
        reopenReason: string | null;
        previousSubmission: any;
      }
    > = {};

    (students || []).forEach((s) => {
      statsMap[s.student_id] = {
        id: s.student_id,
        name: s.student_name || 'Unknown',
        completedSet: new Set(),
        puzzleMap: new Map(),
        attempts: 0,
        attemptNo: 1,
        submissionTotalPoints: 0,
        canGrade: false,
        submissionStatus: 'not_started',
        submittedAt: null,
        reopenedAt: null,
        reopenReason: null,
        previousSubmission: null,
      };
    });

    (progressData || []).forEach((p) => {
      if (!statsMap[p.student_id]) {
        statsMap[p.student_id] = {
          id: p.student_id,
          name: p.student_name || 'Unknown',
          completedSet: new Set(),
          puzzleMap: new Map(),
          attempts: 0,
          attemptNo: p.attempt_no || 1,
          submissionTotalPoints: p.submission_total_points || 0,
          canGrade: p.can_grade ?? false,
          submissionStatus: 'not_started',
          submittedAt: null,
          reopenedAt: null,
          reopenReason: null,
          previousSubmission: p.previous_submission || null,
        };
      }
      const s = statsMap[p.student_id];
      // Keep best record per puzzle_id
      const existing = s.puzzleMap.get(p.puzzle_id);
      if (!existing || (p.points_earned || 0) > (existing.points_earned || 0)) {
        s.puzzleMap.set(p.puzzle_id, p);
      }
      s.attempts += p.attempts || 0;
      if (p.status === 'completed' || p.status === 'passed' || p.status === 'solved') {
        s.completedSet.add(p.puzzle_id);
      }
      if (p.submission_status) {
        s.submissionStatus = p.submission_status;
        s.submittedAt = p.submitted_at || null;
        s.reopenedAt = p.reopened_at || null;
        s.reopenReason = p.reopen_reason || null;
        s.attemptNo = p.attempt_no || 1;
        s.submissionTotalPoints = p.submission_total_points ?? 0;
        s.canGrade = p.can_grade ?? false;
        s.previousSubmission = p.previous_submission || null;
      }
    });

    return Object.values(statsMap)
      .map((s) => {
        const isUnsubmitted = ['reopened', 'in_progress'].includes(s.submissionStatus);
        const displayPoints = isUnsubmitted
          ? (s.previousSubmission ? s.previousSubmission.total_points : 0)
          : s.submissionTotalPoints;

        return {
          id: s.id,
          name: s.name,
          attempted: s.puzzleMap.size,
          completed: isUnsubmitted && s.previousSubmission ? s.previousSubmission.completed_puzzles : s.completedSet.size,
          points: displayPoints,
          attempts: s.attempts,
          attemptNo: s.attemptNo,
          canGrade: s.canGrade,
          previousSubmission: s.previousSubmission,
          submissionStatus: s.submissionStatus,
          submittedAt: s.submittedAt,
          reopenedAt: s.reopenedAt,
          reopenReason: s.reopenReason,
        };
      })
      .sort((a, b) => b.points - a.points);
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
  const nextUnattemptedPuzzle = puzzles.find((p) => !attemptedPuzzleIds.has(p.id)) || puzzles[0];

  const studentSubStatus = mySubmission?.status || 'not_started';
  const isSubmitted = isStudent && studentSubStatus === 'submitted';
  const isReturned = isStudent && studentSubStatus === 'returned';

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
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                {assignment.title}
              </h1>
              {isReturned ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40">
                  <CheckCircle2 className="w-3 h-3" /> Đã trả bài 📝
                </span>
              ) : isSubmitted ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  <Lock className="w-3 h-3" /> Đã nộp bài 🔒
                </span>
              ) : null}
            </div>
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

        {/* Action Buttons for Student */}
        {isStudent && (
          <div className="flex items-center gap-3 shrink-0 self-start sm:self-auto">
            {isSubmitted || isReturned ? (
              <Link
                to={`/practice?puzzleId=${puzzles[0]?.id || ''}&assignmentId=${assignment.id}&readonly=1`}
                className="flex items-center gap-2 px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold rounded-xl text-sm transition border border-slate-600 shadow-md"
              >
                <Eye className="w-4 h-4 text-slate-400" />
                Xem lại bài giải (Chế độ xem 🔒)
              </Link>
            ) : (
              <>
                {nextUnattemptedPuzzle && (
                  <Link
                    to={`/practice?puzzleId=${nextUnattemptedPuzzle.id}&assignmentId=${assignment.id}`}
                    className="flex items-center gap-2 px-5 py-2.5 bg-linear-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-900 font-bold rounded-xl text-sm transition shadow-lg shadow-amber-500/25"
                  >
                    <Play className="w-4 h-4 fill-current" />
                    {attemptedPuzzleIds.size === 0
                      ? 'Bắt đầu làm bài'
                      : attemptedPuzzleIds.size < totalPuzzles
                      ? 'Tiếp tục làm bài'
                      : 'Xem lại / Làm lại'}
                  </Link>
                )}
                {attemptedPuzzleIds.size > 0 && (
                  <button
                    onClick={() => setShowSubmitModal(true)}
                    className="flex items-center gap-2 px-5 py-2.5 bg-linear-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold rounded-xl text-sm transition shadow-lg shadow-emerald-600/25"
                  >
                    <Send className="w-4 h-4" />
                    Nộp bài tập 🔒
                  </button>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Student Progress Summary Card */}
      {isStudent && (
        <div className={`border rounded-2xl p-6 shadow-xl ${
          isReturned
            ? 'bg-linear-to-br from-purple-950/40 via-slate-800/80 to-slate-900/80 border-purple-500/40'
            : isSubmitted
            ? 'bg-linear-to-br from-emerald-950/40 via-slate-800/80 to-slate-900/80 border-emerald-500/40'
            : 'bg-linear-to-br from-indigo-950/40 via-slate-800/80 to-slate-900/80 border-indigo-500/30'
        }`}>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div>
              <p className="text-slate-400 text-xs uppercase tracking-wider font-semibold">Tiến độ làm bài</p>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-3xl font-extrabold text-white">{attemptedPuzzleIds.size}</span>
                <span className="text-slate-400 text-sm">/ {totalPuzzles} thế cờ</span>
              </div>
              <div className="w-full bg-slate-700/60 rounded-full h-2 mt-3">
                <div
                  className={`h-2 rounded-full transition-all ${
                    isReturned
                      ? 'bg-linear-to-r from-purple-400 to-indigo-500'
                      : isSubmitted
                      ? 'bg-linear-to-r from-emerald-400 to-teal-500'
                      : 'bg-linear-to-r from-amber-400 to-orange-500'
                  }`}
                  style={{ width: `${totalPuzzles > 0 ? (attemptedPuzzleIds.size / totalPuzzles) * 100 : 0}%` }}
                />
              </div>
              <p className="text-xs text-slate-400 mt-2">
                {isReturned ? (
                  <>Giải đúng: <span className="text-emerald-400 font-semibold">{solvedPuzzleIds.size}</span> / {totalPuzzles} thế cờ</>
                ) : isSubmitted ? (
                  <span className="text-emerald-300 font-medium flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" /> Đã nộp đủ phương án cho toàn bộ thế cờ
                  </span>
                ) : (
                  <>Đã làm: <span className="text-indigo-300 font-semibold">{attemptedPuzzleIds.size}</span> / {totalPuzzles} thế cờ</>
                )}
              </p>
            </div>

            <div>
              <p className="text-slate-400 text-xs uppercase tracking-wider font-semibold">Điểm đánh giá</p>
              {isReturned ? (
                <>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-3xl font-extrabold text-amber-400">{mySubmission?.total_points} pts</span>
                    {mySubmission?.teacher_adjustment !== undefined && mySubmission.teacher_adjustment !== 0 && (
                      <span className="text-xs text-purple-300 bg-purple-500/20 px-2 py-0.5 rounded-md font-semibold">
                        {mySubmission.teacher_adjustment > 0 ? `+${mySubmission.teacher_adjustment}` : mySubmission.teacher_adjustment} pts thưởng/trừ
                      </span>
                    )}
                  </div>
                  <p className="text-slate-400 text-xs mt-3 flex items-center gap-1">
                    <Award className="w-3.5 h-3.5 text-amber-400" />
                    Điểm chính thức đã được Thầy/Cô chấm & trả bài
                  </p>
                </>
              ) : isSubmitted ? (
                <>
                  <p className="text-2xl font-bold text-slate-300 mt-2 flex items-center gap-2">
                    <Clock className="w-6 h-6 text-emerald-400 animate-pulse" />
                    Đang chờ chấm điểm ⏳
                  </p>
                  <p className="text-slate-400 text-xs mt-3 flex items-center gap-1">
                    Điểm số và câu đúng/sai sẽ hiển thị khi Thầy/Cô trả bài
                  </p>
                </>
              ) : mySubmission?.status === 'reopened' || (mySubmission?.status === 'in_progress' && (mySubmission?.attempt_no || 1) > 1) ? (
                <>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-2xl font-bold text-amber-400">
                      {mySubmission.previous_submission ? `${mySubmission.previous_submission.total_points} pts` : '—'}
                    </span>
                    <span className="text-xs text-slate-400">
                      (Lần {(mySubmission.previous_submission?.attempt_no) || 1} cũ)
                    </span>
                  </div>
                  <p className="text-slate-400 text-xs mt-3 flex items-center gap-1">
                    <RotateCcw className="w-3.5 h-3.5 text-amber-400" />
                    Lần {mySubmission.attempt_no} chưa nộp — chưa tính điểm mới
                  </p>
                </>
              ) : (
                <>
                  <p className="text-3xl font-extrabold text-amber-400 mt-2">{myPoints} pts</p>
                  <p className="text-slate-400 text-xs mt-3 flex items-center gap-1">
                    <Star className="w-3.5 h-3.5 text-amber-400 fill-current" />
                    Điểm tạm tính (sẽ chốt khi nộp và giáo viên chấm)
                  </p>
                </>
              )}
            </div>

            <div>
              <p className="text-slate-400 text-xs uppercase tracking-wider font-semibold">Trạng thái bài tập</p>
              <div className="mt-2">
                {isReturned ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-500/20 text-purple-300 border border-purple-500/40 text-sm font-semibold">
                    <CheckCircle2 className="w-4 h-4" /> Đã có kết quả (Đã trả bài 🎉)
                  </span>
                ) : isSubmitted ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-sm font-semibold">
                    <Lock className="w-4 h-4" /> Đã nộp bài chính thức (Đang chờ chấm)
                  </span>
                ) : mySubmission?.status === 'reopened' || (mySubmission?.status === 'in_progress' && (mySubmission?.attempt_no || 1) > 1) ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/40 text-sm font-semibold">
                    <RotateCcw className="w-4 h-4" /> Đang làm lại (Lần {mySubmission?.attempt_no || 2})
                  </span>
                ) : attemptedPuzzleIds.size >= totalPuzzles && totalPuzzles > 0 ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-green-500/20 text-green-400 border border-green-500/40 text-sm font-semibold">
                    <CheckCircle className="w-4 h-4" /> Đã làm hết {totalPuzzles} bài (Hãy bấm nộp bài)
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/40 text-sm font-semibold">
                    <AlertCircle className="w-4 h-4" /> Đang thực hiện ({totalPuzzles - attemptedPuzzleIds.size} bài chưa làm)
                  </span>
                )}
              </div>
              <p className="text-slate-400 text-xs mt-3">
                {isReturned ? (
                  <span>
                    Chấm và trả bài lúc {mySubmission?.graded_at ? new Date(mySubmission.graded_at).toLocaleString('vi-VN') : ''}.
                  </span>
                ) : isSubmitted ? (
                  <>
                    Nộp lúc {mySubmission?.submitted_at ? new Date(mySubmission.submitted_at).toLocaleString('vi-VN') : ''}.
                    <br />
                    <span className="text-slate-300">Bài tập đã bị khóa cứng chỉnh sửa. Đang chờ giáo viên kiểm tra & trả bài.</span>
                  </>
                ) : mySubmission?.reopen_reason ? (
                  <span className="text-amber-300">
                    Lý do mở lại: <em>"{mySubmission.reopen_reason}"</em>. Hãy hoàn thiện và nộp bài trước hạn.
                  </span>
                ) : isExpired ? (
                  'Đã hết hạn nộp — bạn vẫn có thể luyện tập nhưng không tính thêm điểm'
                ) : (
                  'Tiến độ được lưu tự động. Bấm "Nộp bài tập 🔒" khi bạn muốn hoàn tất và gửi cho thầy cô.'
                )}
              </p>
            </div>
          </div>

          {/* Callout kết quả lần nộp trước cho học sinh (khi đang làm lại) */}
          {mySubmission?.previous_submission && !isSubmitted && !isReturned && (
            <div className="mt-5 pt-4 border-t border-amber-500/20">
              <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-700/60 text-slate-200">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-purple-300 flex items-center gap-1.5">
                    <Award className="w-4 h-4 text-purple-400" /> Kết quả lần trước (Lần {mySubmission.previous_submission.attempt_no}):
                  </span>
                  <span className="text-sm font-bold text-amber-400">
                    {mySubmission.previous_submission.total_points} pts
                  </span>
                </div>
                {mySubmission.previous_submission.teacher_feedback && (
                  <div className="mt-2 text-xs text-slate-300 pl-3 border-l-2 border-purple-500/50">
                    <strong>Nhận xét của Thầy / Cô:</strong> <em>"{mySubmission.previous_submission.teacher_feedback}"</em>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Teacher Feedback Callout for Student (When Returned) */}
          {isReturned && mySubmission?.teacher_feedback && (
            <div className="mt-5 pt-4 border-t border-purple-500/30">
              <div className="p-4 rounded-xl bg-purple-950/50 border border-purple-500/30 text-slate-200">
                <div className="flex items-center gap-2 font-bold text-purple-300 mb-1.5">
                  <MessageSquare className="w-4 h-4" /> Nhận xét & Đánh giá của Thầy / Cô:
                </div>
                <p className="whitespace-pre-wrap leading-relaxed text-sm text-slate-200 pl-6 border-l-2 border-purple-500/50">
                  {mySubmission.teacher_feedback}
                </p>
              </div>
            </div>
          )}

          <div className="mt-5 pt-4 border-t border-slate-700/60 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-300 gap-3">
            <span className="flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-indigo-400 shrink-0" />
              <strong>Quy trình BTVN:</strong> Học viên làm bài &rarr; Bấm nộp bài &rarr; Giáo viên chấm & xem nước đi &rarr; Trả kết quả và nhận xét.
            </span>
            {!isSubmitted && !isReturned && attemptedPuzzleIds.size > 0 && (
              <button
                onClick={() => setShowSubmitModal(true)}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg text-xs transition flex items-center gap-1.5 self-start sm:self-auto shrink-0 shadow"
              >
                <Send className="w-3.5 h-3.5" /> Nộp bài tập ngay
              </button>
            )}
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
          Danh sách thế cờ trong bài tập ({puzzles.length})
        </h2>

        {puzzles.length === 0 ? (
          <p className="text-slate-500 text-sm italic">Chưa có thông tin thế cờ chi tiết.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {puzzles.map((p, idx) => {
              const isSolved = solvedPuzzleIds.has(p.id);
              const isAttempted = attemptedPuzzleIds.has(p.id);

              // ── BẢO MẬT ĐÁP ÁN: Nếu học sinh đã nộp mà chưa được trả bài, KHÔNG lộ câu nào đúng, câu nào sai! ──
              let badgeElement = null;
              if (isReturned) {
                // Đã trả bài: hiện kết quả minh bạch
                if (isSolved) {
                  badgeElement = (
                    <span className="text-xs text-green-400 flex items-center gap-1 font-medium bg-green-500/15 px-2.5 py-1 rounded-lg">
                      <CheckCircle className="w-3.5 h-3.5" /> Chính xác
                    </span>
                  );
                } else if (isAttempted) {
                  badgeElement = (
                    <span className="text-xs text-amber-400 flex items-center gap-1 font-medium bg-amber-500/15 px-2.5 py-1 rounded-lg">
                      <AlertCircle className="w-3.5 h-3.5" /> Chưa chính xác
                    </span>
                  );
                } else {
                  badgeElement = <span className="text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded-lg">Chưa làm</span>;
                }
              } else if (isSubmitted) {
                // Đang nộp chờ chấm: ẩn câu đúng/sai, chỉ hiện "Đã nộp phương án"
                if (isAttempted) {
                  badgeElement = (
                    <span className="text-xs text-emerald-300 flex items-center gap-1 font-medium bg-emerald-500/15 px-2.5 py-1 rounded-lg border border-emerald-500/30">
                      <Check className="w-3.5 h-3.5" /> Đã nộp phương án 🔒
                    </span>
                  );
                } else {
                  badgeElement = <span className="text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded-lg">Chưa làm</span>;
                }
              } else {
                // Đang làm bài
                if (isAttempted) {
                  badgeElement = (
                    <span className="text-xs text-indigo-300 flex items-center gap-1 font-medium bg-indigo-500/15 px-2.5 py-1 rounded-lg">
                      <CheckCircle className="w-3.5 h-3.5" /> Đã ghi nhận
                    </span>
                  );
                } else {
                  badgeElement = <span className="text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded-lg">Chưa làm</span>;
                }
              }

              return (
                <div
                  key={p.id}
                  className={`flex items-center justify-between p-4 rounded-xl border transition-all ${
                    isReturned && isSolved
                      ? 'bg-green-500/10 border-green-500/30'
                      : isReturned && isAttempted
                      ? 'bg-amber-500/10 border-amber-500/30'
                      : isSubmitted && isAttempted
                      ? 'bg-emerald-500/10 border-emerald-500/30'
                      : isAttempted
                      ? 'bg-indigo-500/10 border-indigo-500/30'
                      : 'bg-slate-900/60 border-slate-700/60 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${
                      isReturned && isSolved
                        ? 'bg-green-500/20 text-green-400'
                        : isSubmitted && isAttempted
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : isAttempted
                        ? 'bg-indigo-500/20 text-indigo-400'
                        : 'bg-slate-800 text-slate-400'
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
                    {badgeElement}
                    {isSubmitted || isReturned ? (
                      <Link
                        to={`/practice?puzzleId=${p.id}&assignmentId=${assignment.id}&readonly=1`}
                        className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-xs font-semibold transition flex items-center gap-1.5"
                      >
                        <Eye className="w-3.5 h-3.5 text-slate-400" /> Xem lại
                      </Link>
                    ) : (
                      <Link
                        to={`/practice?puzzleId=${p.id}&assignmentId=${assignment.id}`}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                          isAttempted
                            ? 'bg-slate-700 hover:bg-slate-600 text-slate-200'
                            : 'bg-indigo-600 hover:bg-indigo-500 text-white'
                        }`}
                      >
                        {isAttempted ? 'Làm lại' : 'Làm bài'}
                      </Link>
                    )}
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
              Tiến độ & Chấm bài Học viên trong lớp ({studentStats.length} học viên)
            </h2>
            <span className="text-xs text-slate-400 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Bấm <strong>"Chấm / Xem bài"</strong> để xem chi tiết nước đi và chấm điểm
            </span>
          </div>

          {studentStats.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-sm">
              Chưa có học viên nào trong lớp hoặc chưa có dữ liệu tiến độ.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700/60 bg-slate-800/80">
                    <th className="text-left px-6 py-3.5 text-slate-400 text-xs font-semibold uppercase">Học viên</th>
                    <th className="text-center px-4 py-3.5 text-slate-400 text-xs font-semibold uppercase">Tiến độ làm ({totalPuzzles})</th>
                    <th className="text-center px-4 py-3.5 text-slate-400 text-xs font-semibold uppercase">Giải đúng</th>
                    <th className="text-center px-4 py-3.5 text-slate-400 text-xs font-semibold uppercase">Tổng Điểm</th>
                    <th className="text-center px-6 py-3.5 text-slate-400 text-xs font-semibold uppercase">Trạng thái</th>
                    <th className="text-center px-6 py-3.5 text-slate-400 text-xs font-semibold uppercase">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/40">
                  {studentStats.map((s, i) => {
                    const isAllAttempted = s.attempted >= totalPuzzles && totalPuzzles > 0;
                    const isStudentSubmitted = s.submissionStatus === 'submitted';
                    const isStudentReturned = s.submissionStatus === 'returned';
                    const isReopenedAttempt = s.submissionStatus === 'reopened' || (s.submissionStatus === 'in_progress' && s.attemptNo > 1);

                    return (
                      <tr key={s.id} className="hover:bg-slate-700/30 transition-colors">
                        <td className="px-6 py-3.5 text-white font-medium">
                          <div className="flex items-center gap-3">
                            <div className="w-7 h-7 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-xs shrink-0">
                              {i + 1}
                            </div>
                            <div>
                              <span className="text-sm font-semibold">{s.name}</span>
                              {s.reopenReason && isReopenedAttempt && (
                                <div className="text-[11px] text-amber-400 flex items-center gap-1 mt-0.5">
                                  <RotateCcw className="w-3 h-3" /> Lý do: {s.reopenReason}
                                </div>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Cột Tiến độ làm bài (Đã làm bao nhiêu / tổng số thế cờ) */}
                        <td className="px-4 py-3.5 text-center">
                          <div className="flex items-center justify-center gap-1.5 text-sm">
                            <span className="text-white font-bold">{s.attempted}</span>
                            <span className="text-slate-500">/ {totalPuzzles}</span>
                          </div>
                          <div className="w-24 mx-auto bg-slate-700 rounded-full h-1.5 mt-1.5">
                            <div
                              className={`h-1.5 rounded-full transition-all ${
                                isAllAttempted ? 'bg-emerald-400' : 'bg-amber-400'
                              }`}
                              style={{ width: `${totalPuzzles > 0 ? (s.attempted / totalPuzzles) * 100 : 0}%` }}
                            />
                          </div>
                        </td>

                        {/* Cột Giải đúng (Số câu đúng / tổng số câu) */}
                        <td className="px-4 py-3.5 text-center">
                          <div className="flex items-center justify-center gap-1 text-sm">
                            <span className="text-emerald-400 font-bold">{s.completed}</span>
                            <span className="text-slate-500">/ {totalPuzzles}</span>
                          </div>
                        </td>

                        {/* Cột Tổng điểm */}
                        <td className="px-4 py-3.5 text-center">
                          {isReopenedAttempt ? (
                            s.previousSubmission ? (
                              <div>
                                <span className="text-amber-400 font-bold text-sm">{s.previousSubmission.total_points} pts</span>
                                <div className="text-[10px] text-slate-400">
                                  (Lần {s.previousSubmission.attempt_no}: {s.previousSubmission.total_points} pts · Lần {s.attemptNo} đang làm)
                                </div>
                              </div>
                            ) : (
                              <span className="text-slate-400 text-sm">Chưa có điểm</span>
                            )
                          ) : (
                            <span className="text-amber-400 font-bold text-sm">{s.points} pts</span>
                          )}
                        </td>

                        {/* Cột Trạng thái */}
                        <td className="px-6 py-3.5 text-center">
                          {isReopenedAttempt ? (
                            <div>
                              <span className="bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2.5 py-1 rounded-lg text-xs font-semibold inline-flex items-center gap-1">
                                <RotateCcw className="w-3.5 h-3.5" /> Đang làm lại (Lần {s.attemptNo})
                              </span>
                            </div>
                          ) : isStudentReturned ? (
                            <div>
                              <span className="bg-purple-500/20 text-purple-300 border border-purple-500/40 px-2.5 py-1 rounded-lg text-xs font-semibold inline-flex items-center gap-1">
                                <CheckCircle2 className="w-3.5 h-3.5 text-purple-400" /> Đã trả bài 📝
                              </span>
                            </div>
                          ) : isStudentSubmitted ? (
                            <div>
                              <span className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 px-2.5 py-1 rounded-lg text-xs font-semibold inline-flex items-center gap-1">
                                <Lock className="w-3.5 h-3.5" /> Đã nộp 🔒
                              </span>
                              {s.submittedAt && (
                                <div className="text-[10px] text-slate-400 mt-0.5">
                                  {new Date(s.submittedAt).toLocaleDateString('vi-VN')}
                                </div>
                              )}
                            </div>
                          ) : isAllAttempted ? (
                            <span className="bg-blue-500/15 text-blue-400 px-2.5 py-1 rounded-lg text-xs font-medium inline-flex items-center gap-1">
                              <CheckCircle className="w-3.5 h-3.5" /> Đã làm 100% (chưa nộp)
                            </span>
                          ) : s.attempted > 0 ? (
                            <span className="bg-slate-700 text-slate-300 px-2.5 py-1 rounded-lg text-xs font-medium inline-flex items-center gap-1">
                              Đang làm ({s.attempted}/{totalPuzzles})
                            </span>
                          ) : (
                            <span className="text-slate-500 text-xs">Chưa làm</span>
                          )}
                        </td>

                        {/* Cột Thao tác: Chấm bài / Xem bài & Mở lại bài */}
                        <td className="px-6 py-3.5 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <button
                              onClick={() => handleOpenGradingModal({ id: s.id, name: s.name })}
                              className="px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 rounded-lg text-xs font-semibold transition inline-flex items-center gap-1.5 shadow-xs"
                              title="Xem chi tiết cách giải và chấm bài"
                            >
                              <FileText className="w-3.5 h-3.5" /> Chấm / Xem bài
                            </button>
                            {(isStudentSubmitted || isStudentReturned) && !isReopenedAttempt && (
                              <button
                                onClick={() => {
                                  setReopenModalStudent({ id: s.id, name: s.name });
                                  setReopenReason('');
                                }}
                                className="px-2.5 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-lg text-xs font-medium transition inline-flex items-center gap-1"
                                title="Cho phép học viên làm lại"
                              >
                                <RotateCcw className="w-3 h-3" /> Mở lại
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── MODAL CHẤM BÀI & XEM CHI TIẾT LỜI GIẢI (DÀNH CHO GIÁO VIÊN) ── */}
      {gradingStudent && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 z-50 animate-fade-in overflow-y-auto">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-5xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden my-auto">
            {/* Header Modal */}
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-800/80 shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-sm">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    Chấm bài & Xem lời giải: <span className="text-indigo-400">{gradingStudent.name}</span>
                  </h3>
                  <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                    <span>Trạng thái: {
                      gradingDetail?.submission.status === 'returned'
                        ? <strong className="text-purple-400">Đã trả bài</strong>
                        : gradingDetail?.submission.status === 'submitted'
                        ? <strong className="text-emerald-400">Đã nộp bài (Chờ chấm)</strong>
                        : <strong className="text-slate-300">Đang thực hiện</strong>
                    }</span>
                    {gradingDetail?.submission.submitted_at && (
                      <span>Nộp lúc: {new Date(gradingDetail.submission.submitted_at).toLocaleString('vi-VN')}</span>
                    )}
                  </div>
                </div>
              </div>
              <button
                onClick={() => setGradingStudent(null)}
                className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-700 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            {loadingGradingDetail || !gradingDetail ? (
              <div className="flex flex-col items-center justify-center py-20 space-y-3">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
                <p className="text-sm text-slate-400">Đang tải toàn bộ dữ liệu thế cờ và lời giải...</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Lịch sử lần nộp bài (Attempts Switcher) */}
                {gradingDetail.history && gradingDetail.history.length > 1 && (
                  <div className="flex flex-wrap items-center gap-2 bg-slate-800/80 p-3 rounded-xl border border-slate-700/60">
                    <span className="text-xs text-slate-400 font-semibold uppercase px-1">Lịch sử bài nộp:</span>
                    <div className="flex flex-wrap gap-2">
                      {gradingDetail.history.map((h) => {
                        const isCurrent = gradingDetail.submission.attempt_no === h.attempt_no;
                        const isUnsub = ['reopened', 'in_progress'].includes(h.status);
                        return (
                          <button
                            key={h.attempt_no}
                            onClick={() => handleSwitchGradingAttempt(h.attempt_no)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                              isCurrent
                                ? 'bg-indigo-600 text-white shadow-md'
                                : 'bg-slate-700/70 hover:bg-slate-700 text-slate-300'
                            }`}
                          >
                            <span>Lần {h.attempt_no}</span>
                            <span className="text-[11px] opacity-80">
                              ({isUnsub ? 'Đang làm lại' : `${h.total_points} pts`})
                            </span>
                            {h.status === 'returned' && <CheckCircle2 className="w-3.5 h-3.5 text-purple-300" />}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Banner cảnh báo nếu học sinh chưa nộp bài lần này */}
                {!gradingDetail.submission.can_grade && (
                  <div className="p-4 rounded-xl bg-amber-500/15 border border-amber-500/40 text-amber-300 text-xs flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 shrink-0 text-amber-400 mt-0.5" />
                    <div>
                      <p className="font-bold text-amber-200">
                        Học sinh chưa nộp bài lần này (Lần {gradingDetail.submission.attempt_no} · Trạng thái: {gradingDetail.submission.status === 'reopened' ? 'Được giáo viên mở lại' : 'Đang làm lại'}).
                      </p>
                      <p className="text-slate-300 mt-1 leading-relaxed">
                        Thầy/Cô có thể xem các nước cờ học sinh đã đi bên dưới để theo dõi tiến độ, nhưng hệ thống <strong>chưa cho phép chấm hoặc trả bài</strong> cho đến khi học sinh hoàn thành và bấm <strong>"Nộp bài tập"</strong>.
                      </p>
                    </div>
                  </div>
                )}

                {/* Thanh tóm tắt nhanh */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3">
                    <p className="text-[11px] text-slate-400 uppercase font-semibold">Tổng thế cờ</p>
                    <p className="text-xl font-bold text-white mt-1">{gradingDetail.items.length} bài</p>
                  </div>
                  <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3">
                    <p className="text-[11px] text-slate-400 uppercase font-semibold">Máy chấm tự động</p>
                    <p className="text-xl font-bold text-emerald-400 mt-1">
                      {gradingDetail.items.filter((it) => it.is_solved).length} / {gradingDetail.items.length} đúng
                    </p>
                  </div>
                  <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3">
                    <p className="text-[11px] text-slate-400 uppercase font-semibold">Điểm bài làm</p>
                    <p className="text-xl font-bold text-amber-400 mt-1">{gradingDetail.submission.total_points} pts</p>
                  </div>
                  <div className="bg-slate-800/70 border border-slate-700/60 rounded-xl p-3">
                    <p className="text-[11px] text-slate-400 uppercase font-semibold">Lần trả bài trước</p>
                    <p className="text-sm font-semibold text-slate-300 mt-1">
                      {gradingDetail.submission.graded_at
                        ? new Date(gradingDetail.submission.graded_at).toLocaleDateString('vi-VN')
                        : 'Chưa chấm'}
                    </p>
                  </div>
                </div>

                {/* Tabs chọn thế cờ */}
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase mb-2">
                    Chọn thế cờ để xem chi tiết lời giải:
                  </label>
                  <div className="flex gap-2 overflow-x-auto pb-1">
                    {gradingDetail.items.map((item, idx) => {
                      const isSelected = selectedGradingIndex === idx;
                      return (
                        <button
                          key={item.puzzle_id}
                          onClick={() => setSelectedGradingIndex(idx)}
                          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold border transition shrink-0 ${
                            isSelected
                              ? 'bg-indigo-600 text-white border-indigo-400 shadow-md'
                              : 'bg-slate-800 text-slate-300 border-slate-700 hover:border-slate-600'
                          }`}
                        >
                          <span>Thế cờ #{idx + 1}</span>
                          {item.is_solved ? (
                            <span className="w-2 h-2 rounded-full bg-emerald-400" title="Giải đúng" />
                          ) : item.attempts_count > 0 ? (
                            <span className="w-2 h-2 rounded-full bg-amber-400" title="Chưa đúng" />
                          ) : (
                            <span className="w-2 h-2 rounded-full bg-slate-500" title="Chưa làm" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Chi tiết thế cờ được chọn */}
                {(() => {
                  const currentItem = gradingDetail.items[selectedGradingIndex];
                  if (!currentItem) return null;

                  const fenTurn = currentItem.fen ? currentItem.fen.split(' ')[1] : 'w';
                  const orientation = fenTurn === 'b' ? 'black' : 'white';
                  const lastAttempt = currentItem.last_attempt;
                  const studentMovesSan = lastAttempt?.moves_san || [];

                  // Đáp án mẫu từ model_solutions
                  const modelSanList = (currentItem.model_solutions || []).map((s) => s.move_san).filter(Boolean);

                  return (
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-6 bg-slate-800/40 border border-slate-700/60 rounded-2xl p-5">
                      {/* Cột trái: Bàn cờ nhỏ */}
                      <div className="md:col-span-5 flex flex-col items-center">
                        <div className="w-64 h-64 bg-slate-900 rounded-xl overflow-hidden border border-slate-700 shadow-lg relative">
                          <Chessboard
                            key={`grading-board-${currentItem.puzzle_id}`}
                            options={{
                              id: `grading-board-${currentItem.puzzle_id}`,
                              position: currentItem.fen,
                              boardOrientation: orientation,
                              allowDragging: false,
                              showNotation: true,
                            }}
                          />
                        </div>
                        <div className="mt-2 text-center text-xs text-slate-400">
                          Bên đi trước: <strong className="text-white">{orientation === 'black' ? 'Đen (Quân Đen)' : 'Trắng (Quân Trắng)'}</strong>
                        </div>
                      </div>

                      {/* Cột phải: So sánh lời giải học sinh vs Đáp án mẫu */}
                      <div className="md:col-span-7 space-y-4">
                        <div>
                          <div className="flex items-center justify-between">
                            <h4 className="text-base font-bold text-white">{currentItem.title}</h4>
                            <span className="text-xs text-amber-400 font-mono bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                              Rating {currentItem.rating}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-xs mt-1">
                            {currentItem.is_solved ? (
                              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                                <CheckCircle className="w-3.5 h-3.5" /> Máy chấm: Giải đúng (+{currentItem.points_earned} pts)
                              </span>
                            ) : currentItem.attempts_count > 0 ? (
                              <span className="text-amber-400 font-semibold flex items-center gap-1">
                                <AlertCircle className="w-3.5 h-3.5" /> Máy chấm: Chưa chính xác (0 pts)
                              </span>
                            ) : (
                              <span className="text-slate-400">Học sinh chưa thực hiện làm câu này</span>
                            )}
                          </div>
                        </div>

                        {/* Box 1: Nước đi của học sinh */}
                        <div className="bg-slate-900/90 border border-slate-700/80 rounded-xl p-3.5 space-y-1.5">
                          <div className="flex justify-between items-center text-xs text-slate-400">
                            <span className="font-semibold uppercase text-indigo-300">
                              Phương án học sinh đã đi ({studentMovesSan.length} nước):
                            </span>
                            {currentItem.attempts_count > 0 && (
                              <span className="text-[11px] text-slate-400">
                                Số lượt thử: <strong>{currentItem.attempts_count}</strong>
                              </span>
                            )}
                          </div>
                          {studentMovesSan.length > 0 ? (
                            <div className="bg-slate-800/80 rounded-lg p-2.5 font-mono text-sm text-white flex flex-wrap gap-2 border border-slate-700/50">
                              {studentMovesSan.map((m, mIdx) => (
                                <span key={mIdx} className="bg-slate-700/60 px-2 py-0.5 rounded text-indigo-200">
                                  {mIdx % 2 === 0 ? `${Math.floor(mIdx / 2) + 1}. ` : ''}{m}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <p className="text-xs text-slate-500 italic">Không có nước đi nào được ghi nhận.</p>
                          )}
                        </div>

                        {/* Box 2: Đáp án chuẩn / Lời giải mẫu */}
                        <div className="bg-slate-900/90 border border-slate-700/80 rounded-xl p-3.5 space-y-1.5">
                          <span className="block text-xs font-semibold uppercase text-emerald-300">
                            Đáp án chuẩn của bài tập:
                          </span>
                          {modelSanList.length > 0 ? (
                            <div className="bg-slate-800/80 rounded-lg p-2.5 font-mono text-sm text-emerald-300 flex flex-wrap gap-2 border border-slate-700/50">
                              {modelSanList.map((m, mIdx) => (
                                <span key={mIdx} className="bg-emerald-950/40 px-2 py-0.5 rounded text-emerald-300 border border-emerald-500/30">
                                  {mIdx % 2 === 0 ? `${Math.floor(mIdx / 2) + 1}. ` : ''}{m}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <p className="text-xs text-slate-500 italic">Thế cờ cấu hình dạng cây hoặc không có SAN phẳng.</p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })()}

                {/* Phần Nhập nhận xét & Chấm bài của Giáo viên */}
                <div className="bg-slate-800/60 border border-slate-700 rounded-2xl p-5 space-y-4">
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-purple-400" />
                    Đánh giá & Trả bài của Giáo viên
                  </h4>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase">
                      Lời nhận xét của Thầy / Cô:
                    </label>
                    <textarea
                      value={teacherFeedback}
                      onChange={(e) => setTeacherFeedback(e.target.value)}
                      placeholder="Ví dụ: Con đã tìm được nước chiếu rút rất hay ở câu 2, nhưng câu 4 cần quan sát đường chéo của Hậu. Cố gắng phát huy nhé!..."
                      rows={3}
                      className="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500 placeholder-slate-500 leading-relaxed"
                    />
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <label className="text-xs font-semibold text-slate-300 uppercase whitespace-nowrap">
                        Điểm điều chỉnh / Thưởng:
                      </label>
                      <input
                        type="number"
                        value={teacherAdjustment}
                        onChange={(e) => setTeacherAdjustment(Number(e.target.value))}
                        className="w-24 bg-slate-900/90 border border-slate-700 rounded-lg px-3 py-1.5 text-white text-sm font-bold text-center focus:outline-none focus:border-purple-500"
                        placeholder="0"
                      />
                      <span className="text-xs text-slate-400">
                        (Cộng thêm hoặc trừ điểm khuyến khích, vd: +5)
                      </span>
                    </div>

                    <div className="text-xs text-slate-300">
                      Tổng điểm sau khi trả: <strong className="text-amber-400 text-sm">{Math.max(0, gradingDetail.submission.total_points + (Number(teacherAdjustment) || 0))} pts</strong>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-slate-800 bg-slate-800/60 flex justify-end gap-3 shrink-0">
              <button
                onClick={() => setGradingStudent(null)}
                disabled={submittingGrade}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-xl text-xs font-medium transition"
              >
                Đóng
              </button>
              <button
                onClick={handleGradeAndReturn}
                disabled={!gradingDetail?.submission?.can_grade || submittingGrade || loadingGradingDetail}
                className="px-5 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-bold transition flex items-center gap-2 shadow-lg shadow-purple-600/30 disabled:opacity-40 disabled:cursor-not-allowed"
                title={!gradingDetail?.submission?.can_grade ? 'Chỉ có thể chấm & trả bài khi học sinh đã nộp bài' : 'Lưu nhận xét và trả kết quả cho học sinh'}
              >
                {submittingGrade ? (
                  <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-white" />
                ) : (
                  <CheckCircle2 className="w-4 h-4" />
                )}
                Lưu nhận xét & Trả bài cho học sinh 📝
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal xác nhận nộp bài cho học sinh */}
      {showSubmitModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <Lock className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Xác nhận nộp bài tập</h3>
                  <p className="text-xs text-slate-400">Gửi toàn bộ bài làm cho Giáo viên chấm</p>
                </div>
              </div>
              <button
                onClick={() => setShowSubmitModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-700 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-slate-900/70 border border-slate-700/50 rounded-xl p-4 space-y-2 text-sm">
              <div className="flex justify-between text-slate-300">
                <span>Số thế cờ đã hoàn thành:</span>
                <strong className="text-white">{attemptedPuzzleIds.size} / {totalPuzzles}</strong>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Trạng thái:</span>
                <strong className="text-emerald-400">Sẵn sàng gửi bài</strong>
              </div>
            </div>

            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 text-xs text-amber-300 flex items-start gap-2.5">
              <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <strong>Lưu ý:</strong> Sau khi nộp, bài tập sẽ được <strong>khóa cứng</strong>. Thầy/Cô sẽ xem chi tiết các nước đi bạn đã giải và gửi nhận xét đánh giá khi trả bài.
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowSubmitModal(false)}
                disabled={submitting}
                className="px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-xl text-sm font-medium transition"
              >
                Hủy bỏ
              </button>
              <button
                onClick={handleSubmitAssignment}
                disabled={submitting}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-sm font-bold transition flex items-center gap-2 shadow-lg shadow-emerald-600/30 disabled:opacity-50"
              >
                {submitting ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                ) : (
                  <CheckCircle2 className="w-4 h-4" />
                )}
                Xác nhận nộp bài
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal mở lại bài cho giáo viên (Reopen Modal) */}
      {reopenModalStudent && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center">
                  <RotateCcw className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Mở lại bài tập (Reopen)</h3>
                  <p className="text-xs text-slate-400">Cho phép học viên làm lại và nộp lại</p>
                </div>
              </div>
              <button
                onClick={() => setReopenModalStudent(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-700 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-slate-900/70 border border-slate-700/50 rounded-xl p-3 text-sm text-slate-300">
              Học viên: <strong className="text-white">{reopenModalStudent.name}</strong>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5 uppercase">
                Lý do mở lại bài <span className="text-red-400">*</span>
              </label>
              <textarea
                value={reopenReason}
                onChange={(e) => setReopenReason(e.target.value)}
                placeholder="Ví dụ: Học sinh xin nộp lại do bấm nhầm, cho cơ hội gỡ điểm..."
                rows={3}
                className="w-full bg-slate-900/90 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-amber-500 placeholder-slate-500"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setReopenModalStudent(null)}
                disabled={reopening}
                className="px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-xl text-sm font-medium transition"
              >
                Hủy bỏ
              </button>
              <button
                onClick={handleReopenAssignment}
                disabled={reopening}
                className="px-5 py-2.5 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold rounded-xl text-sm transition flex items-center gap-2 shadow-lg shadow-amber-600/30 disabled:opacity-50"
              >
                {reopening ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-slate-950" />
                ) : (
                  <RotateCcw className="w-4 h-4" />
                )}
                Xác nhận mở lại bài
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
