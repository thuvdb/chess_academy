import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, BookOpen, Clock, Users, CheckCircle } from 'lucide-react';
import { getAssignmentById, getAssignmentProgress, type AssignmentItem } from '../lib/puzzleApi';
import { getClassStudents, type EnrollmentItem } from '../lib/classApi';
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

  const [assignment, setAssignment] = useState<AssignmentItem | null>(null);
  const [progressData, setProgressData] = useState<ProgressRecord[]>([]);
  const [students, setStudents] = useState<EnrollmentItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDetails = useCallback(async () => {
    if (!assignmentId) return;
    setLoading(true);
    try {
      const asm = await getAssignmentById(assignmentId);
      setAssignment(asm);

      const prog = await getAssignmentProgress(assignmentId);
      setProgressData(prog);

      if (asm.class_id) {
        const stuRes = await getClassStudents(asm.class_id);
        setStudents(stuRes.data || []);
      }
    } catch (err: any) {
      toast.error('Không thể tải dữ liệu bài tập');
    } finally {
      setLoading(false);
    }
  }, [assignmentId]);

  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  const studentStats = useMemo(() => {
    if (!assignment) return [];

    const statsMap: Record<string, { id: string, name: string, completed: number, points: number, attempts: number }> = {};

    // Initialize with students in the class
    students.forEach(s => {
      statsMap[s.student_id] = {
        id: s.student_id,
        name: s.student_name || 'Unknown',
        completed: 0,
        points: 0,
        attempts: 0
      };
    });

    // Aggregate progress
    progressData.forEach(p => {
      if (!statsMap[p.student_id]) {
        statsMap[p.student_id] = {
          id: p.student_id,
          name: p.student_name,
          completed: 0,
          points: 0,
          attempts: 0
        };
      }
      
      const s = statsMap[p.student_id];
      s.attempts += p.attempts;
      s.points += p.points_earned;
      if (p.status === 'completed' || p.status === 'passed') {
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

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/assignments"
          className="p-2 hover:bg-slate-800 rounded-xl text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            {assignment.title}
          </h1>
          <p className="text-slate-400 mt-1 flex items-center gap-4 text-sm">
            <span className="flex items-center gap-1.5 bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded-lg border border-indigo-500/20">
              <Users className="w-4 h-4" />
              Lớp: {(assignment.class_?.name || (assignment as any).class?.name) || 'Chung'}
            </span>
            {assignment.due_date && (
              <span className="flex items-center gap-1.5 text-amber-400">
                <Clock className="w-4 h-4" />
                Hạn nộp: {new Date(assignment.due_date).toLocaleDateString('vi-VN')}
              </span>
            )}
            <span className="flex items-center gap-1.5 text-slate-300">
              <BookOpen className="w-4 h-4" />
              {totalPuzzles} thế cờ
            </span>
          </p>
        </div>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 shadow-xl">
        <h2 className="text-lg font-bold text-white mb-4">Mô tả bài tập</h2>
        <p className="text-slate-300 whitespace-pre-wrap">
          {assignment.description || 'Không có mô tả.'}
        </p>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-2xl shadow-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/50">
          <h2 className="text-lg font-bold text-white">Tiến độ Học viên</h2>
        </div>
        
        {studentStats.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            Chưa có học viên nào trong lớp hoặc chưa có dữ liệu.
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-800/80">
                <th className="text-left px-6 py-4 text-slate-400 text-xs font-semibold uppercase">Học viên</th>
                <th className="text-center px-6 py-4 text-slate-400 text-xs font-semibold uppercase">Tiến độ ({totalPuzzles})</th>
                <th className="text-center px-6 py-4 text-slate-400 text-xs font-semibold uppercase">Tổng Điểm</th>
                <th className="text-center px-6 py-4 text-slate-400 text-xs font-semibold uppercase">Trạng thái</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {studentStats.map((s, i) => {
                const isDone = s.completed >= totalPuzzles && totalPuzzles > 0;
                return (
                  <tr key={s.id} className="hover:bg-slate-700/30 transition-colors">
                    <td className="px-6 py-4 text-white font-medium flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-sm">
                        {i + 1}
                      </div>
                      {s.name}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <span className="text-white font-medium">{s.completed}</span>
                        <span className="text-slate-500">/ {totalPuzzles}</span>
                      </div>
                      <div className="w-24 mx-auto bg-slate-700 rounded-full h-1.5 mt-2">
                        <div 
                          className="bg-green-500 h-1.5 rounded-full transition-all" 
                          style={{ width: `${totalPuzzles > 0 ? (s.completed / totalPuzzles) * 100 : 0}%` }}
                        />
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className="text-amber-400 font-bold">{s.points} pts</span>
                    </td>
                    <td className="px-6 py-4 text-center flex justify-center">
                      {isDone ? (
                        <span className="bg-green-500/15 text-green-400 px-2 py-1 rounded-lg text-xs font-medium flex items-center gap-1">
                          <CheckCircle className="w-3.5 h-3.5" /> Hoàn thành
                        </span>
                      ) : (
                        <span className="bg-slate-700 text-slate-400 px-2 py-1 rounded-lg text-xs font-medium flex items-center gap-1">
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
    </div>
  );
}
