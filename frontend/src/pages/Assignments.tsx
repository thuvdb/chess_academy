import { useState, useEffect, useCallback } from 'react';
import {
  ClipboardList, Plus, Clock, BookOpen, ChevronRight, X
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  getAssignments, createAssignment,
  type AssignmentItem
} from '../lib/puzzleApi';
import { getClasses, type ClassItem } from '../lib/classApi';
import { getPuzzles, type PuzzleItem } from '../lib/puzzleApi';

export default function Assignments() {
  const [assignments, setAssignments] = useState<AssignmentItem[]>([]);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [puzzles, setPuzzles] = useState<PuzzleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Form State
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [classId, setClassId] = useState('');
  const [filterClassId, setFilterClassId] = useState('');
  const [selectedPuzzles, setSelectedPuzzles] = useState<string[]>([]);
  const [dueDate, setDueDate] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [assigns, clsRes, puzList] = await Promise.all([
        getAssignments(),
        getClasses(),
        getPuzzles({ limit: 50 }),
      ]);
      setAssignments(assigns);
      setClasses(clsRes.data);
      setPuzzles(puzList);
      if (clsRes.data.length > 0) {
        setClassId(clsRes.data[0].id);
      }
    } catch {
      toast.error('Failed to load assignments');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !classId) {
      toast.error('Tiêu đề và lớp học là bắt buộc');
      return;
    }
    setSaving(true);
    try {
      await createAssignment({
        class_id: classId,
        title,
        description: description || undefined,
        puzzle_ids: selectedPuzzles,
        due_date: dueDate ? new Date(dueDate).toISOString() : undefined,
      });
      toast.success('Đã giao bài tập thành công');
      setShowCreateModal(false);
      setTitle('');
      setDescription('');
      setSelectedPuzzles([]);
      setDueDate('');
      fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Không thể tạo bài giao');
    } finally {
      setSaving(false);
    }
  };

  const togglePuzzleSelection = (id: string) => {
    if (selectedPuzzles.includes(id)) {
      setSelectedPuzzles(selectedPuzzles.filter((p) => p !== id));
    } else {
      setSelectedPuzzles([...selectedPuzzles, id]);
    }
  };

  const filteredAssignments = filterClassId 
    ? assignments.filter(a => a.class_id === filterClassId)
    : assignments;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <ClipboardList className="w-7 h-7 text-indigo-400" />
            Bài tập về nhà & Lớp học
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Giao bài tập cho học sinh theo lớp, đặt hạn nộp và theo dõi tiến độ
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={filterClassId}
            onChange={(e) => setFilterClassId(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none"
          >
            <option value="">Tất cả các lớp</option>
            {classes.map((cls) => (
              <option key={cls.id} value={cls.id}>
                {cls.name}
              </option>
            ))}
          </select>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition shadow-lg shadow-indigo-600/20"
          >
            <Plus className="w-4 h-4" />
            Giao bài tập mới
          </button>
        </div>
      </div>

      {/* Assignments List */}
      {loading ? (
        <div className="flex justify-center items-center py-24">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
        </div>
      ) : filteredAssignments.length === 0 ? (
        <div className="bg-slate-800/40 border border-slate-700/40 rounded-2xl p-12 text-center">
          <ClipboardList className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-slate-300">Không tìm thấy bài tập nào</h3>
          <p className="text-slate-500 text-sm mt-1 max-w-sm mx-auto">
            Thay đổi bộ lọc hoặc tạo bài tập mới.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAssignments.map((item) => (
            <div
              key={item.id}
              className="bg-slate-800/80 border border-slate-700/60 rounded-2xl p-5 hover:border-slate-600 transition flex flex-col justify-between shadow-lg"
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
                    Lớp: {item.class_?.name || 'Chung'}
                  </span>
                  {item.due_date && (
                    <span className="text-xs text-amber-400 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      Hạn: {new Date(item.due_date).toLocaleDateString('vi-VN')}
                    </span>
                  )}
                </div>
                <h3 className="font-bold text-white text-lg mt-3">{item.title}</h3>
                <p className="text-slate-400 text-sm mt-1 line-clamp-2">
                  {item.description || 'Không có mô tả chi tiết'}
                </p>
              </div>

              <div className="mt-5 pt-4 border-t border-slate-700/60 flex items-center justify-between text-xs text-slate-400">
                <span className="flex items-center gap-1.5">
                  <BookOpen className="w-4 h-4 text-indigo-400" />
                  {item.puzzle_ids?.length || 0} bài tập
                </span>
                <span className="text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1 cursor-pointer">
                  Xem chi tiết
                  <ChevronRight className="w-4 h-4" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Assignment Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-700 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-indigo-400" />
                Giao bài tập mới cho lớp
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Chọn lớp học *
                </label>
                <select
                  value={classId}
                  onChange={(e) => setClassId(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none"
                  required
                >
                  {classes.map((cls) => (
                    <option key={cls.id} value={cls.id}>
                      {cls.name} ({cls.level})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Tiêu đề bài giao *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ví dụ: Bài tập chiến thuật tuần 11 - Đòn chĩa"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Hạn nộp bài
                </label>
                <input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Chọn các thế cờ từ Thư viện ({selectedPuzzles.length} đã chọn)
                </label>
                <div className="max-h-48 overflow-y-auto space-y-1.5 p-2 bg-slate-900 rounded-xl border border-slate-700">
                  {puzzles.length === 0 ? (
                    <p className="text-xs text-slate-500 italic p-2">Chưa có bài tập trong thư viện</p>
                  ) : (
                    puzzles.map((p) => {
                      const isSelected = selectedPuzzles.includes(p.id);
                      return (
                        <div
                          key={p.id}
                          onClick={() => togglePuzzleSelection(p.id)}
                          className={`flex items-center justify-between p-2 rounded-lg cursor-pointer text-xs transition ${
                            isSelected
                              ? 'bg-indigo-600/30 border border-indigo-500/50 text-white'
                              : 'bg-slate-800/60 border border-slate-700 text-slate-300 hover:bg-slate-800'
                          }`}
                        >
                          <span className="font-medium line-clamp-1">{p.title}</span>
                          <span className="text-[11px] text-amber-400 font-mono">Rating {p.rating}</span>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Hướng dẫn làm bài
                </label>
                <textarea
                  rows={2}
                  placeholder="Ghi chú thêm cho học sinh..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-700">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-xl text-sm font-medium transition"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition disabled:opacity-50"
                >
                  {saving ? 'Đang giao...' : 'Giao bài tập'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
