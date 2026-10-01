import { useState, useEffect, useCallback } from 'react';
import { Chessboard } from 'react-chessboard';
import {
  BookOpen, Plus, Search, Filter, Play, Trash2,
  Zap, Tag, Star, X
} from 'lucide-react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  getPuzzles, createPuzzle, deletePuzzle,
  type PuzzleItem, type CreatePuzzleInput
} from '../lib/puzzleApi';

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  intermediate: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  advanced: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  master: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
};

export default function Puzzles() {
  const [puzzles, setPuzzles] = useState<PuzzleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [difficulty, setDifficulty] = useState<string>('');
  const [puzzleType, setPuzzleType] = useState<string>('');
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Form State
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [fen, setFen] = useState('r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 4');
  const [formDifficulty, setFormDifficulty] = useState('beginner');
  const [formType, setFormType] = useState('tactics');
  const [rating, setRating] = useState(1200);
  const [solutionUci, setSolutionUci] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchPuzzles = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getPuzzles({
        search: search || undefined,
        difficulty: difficulty || undefined,
        puzzle_type: puzzleType || undefined,
      });
      setPuzzles(data);
    } catch {
      toast.error('Failed to load puzzles');
    } finally {
      setLoading(false);
    }
  }, [search, difficulty, puzzleType]);

  useEffect(() => {
    fetchPuzzles();
  }, [fetchPuzzles]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !fen.trim()) {
      toast.error('Title and FEN are required');
      return;
    }
    setSaving(true);
    try {
      const solutions = solutionUci.trim()
        ? solutionUci.split(',').map((move, index) => ({
            move_order: index + 1,
            move_uci: move.trim(),
            move_san: move.trim(),
            is_best_move: true,
          }))
        : [];

      const payload: CreatePuzzleInput = {
        title,
        description: description || undefined,
        fen,
        difficulty: formDifficulty,
        puzzle_type: formType,
        rating: Number(rating),
        solutions,
      };

      await createPuzzle(payload);
      toast.success('Puzzle created successfully');
      setShowCreateModal(false);
      // Reset form
      setTitle('');
      setDescription('');
      setSolutionUci('');
      fetchPuzzles();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create puzzle');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Delete this puzzle from the library?')) return;
    try {
      await deletePuzzle(id);
      toast.success('Puzzle deleted');
      setPuzzles(puzzles.filter(p => p.id !== id));
    } catch {
      toast.error('Failed to delete puzzle');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <BookOpen className="w-7 h-7 text-indigo-400" />
            Puzzle Library & Bank
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Kho bài tập chiến thuật cờ vua, phân loại theo cấp độ và chủ đề
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/practice"
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-sm font-medium transition"
          >
            <Play className="w-4 h-4 fill-current" />
            Luyện tập ngay
          </Link>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition shadow-lg shadow-indigo-600/20"
          >
            <Plus className="w-4 h-4" />
            Tạo bài tập mới
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl p-4 flex flex-wrap gap-4 items-center justify-between">
        <div className="flex flex-1 min-w-[260px] items-center gap-2 bg-slate-900/60 border border-slate-700/50 rounded-xl px-3 py-2">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Tìm kiếm theo tiêu đề hoặc mô tả..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-transparent border-none text-white text-sm focus:outline-none w-full placeholder:text-slate-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-900/60 border border-slate-700/50 rounded-xl px-3 py-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              className="bg-transparent border-none text-slate-200 text-sm focus:outline-none cursor-pointer"
            >
              <option value="" className="bg-slate-800">Tất cả cấp độ</option>
              <option value="beginner" className="bg-slate-800">Beginner (1000 - 1200)</option>
              <option value="intermediate" className="bg-slate-800">Intermediate (1200 - 1600)</option>
              <option value="advanced" className="bg-slate-800">Advanced (1600 - 2000)</option>
              <option value="master" className="bg-slate-800">Master (&gt; 2000)</option>
            </select>
          </div>

          <div className="flex items-center gap-2 bg-slate-900/60 border border-slate-700/50 rounded-xl px-3 py-2">
            <Tag className="w-4 h-4 text-slate-400" />
            <select
              value={puzzleType}
              onChange={(e) => setPuzzleType(e.target.value)}
              className="bg-transparent border-none text-slate-200 text-sm focus:outline-none cursor-pointer"
            >
              <option value="" className="bg-slate-800">Tất cả thể loại</option>
              <option value="tactics" className="bg-slate-800">Chiến thuật (Tactics)</option>
              <option value="mate_in_1" className="bg-slate-800">Chiếu hết 1 nước</option>
              <option value="mate_in_2" className="bg-slate-800">Chiếu hết 2 nước</option>
              <option value="fork" className="bg-slate-800">Đòn chĩa đôi (Fork)</option>
              <option value="pin" className="bg-slate-800">Đòn ghim (Pin)</option>
              <option value="endgame" className="bg-slate-800">Tàn cuộc (Endgame)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Puzzle Grid */}
      {loading ? (
        <div className="flex justify-center items-center py-24">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
        </div>
      ) : puzzles.length === 0 ? (
        <div className="bg-slate-800/40 border border-slate-700/40 rounded-2xl p-12 text-center">
          <BookOpen className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-slate-300">Không tìm thấy bài tập nào</h3>
          <p className="text-slate-500 text-sm mt-1 max-w-sm mx-auto">
            Hãy tạo bài tập mới từ FEN, PGN hoặc duyệt từ AI Scanner
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {puzzles.map((p) => (
            <div
              key={p.id}
              className="bg-slate-800/80 border border-slate-700/60 rounded-2xl overflow-hidden hover:border-slate-600 transition flex flex-col group shadow-lg"
            >
              {/* Mini Board Preview */}
              <div className="h-56 bg-slate-900/90 flex items-center justify-center p-3 relative">
                <div className="w-48 h-48 pointer-events-none rounded-lg overflow-hidden shadow">
                  <Chessboard
                    options={{
                      position: p.fen,
                      allowDragging: false,
                    }}
                  />
                </div>
                <div className="absolute top-3 left-3 flex gap-2">
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                      DIFFICULTY_COLORS[p.difficulty || 'beginner']
                    }`}
                  >
                    {p.difficulty || 'beginner'}
                  </span>
                  <span className="bg-slate-800/90 text-amber-400 border border-slate-700 text-xs px-2 py-0.5 rounded-full flex items-center gap-1 font-semibold">
                    <Star className="w-3 h-3 fill-current" />
                    {p.rating}
                  </span>
                </div>
                <button
                  onClick={(e) => handleDelete(p.id, e)}
                  className="absolute top-3 right-3 p-1.5 bg-slate-800/80 hover:bg-red-500/20 text-slate-400 hover:text-red-400 rounded-lg opacity-0 group-hover:opacity-100 transition"
                  title="Xóa bài tập"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Content */}
              <div className="p-4 flex-1 flex flex-col justify-between">
                <div>
                  <h3 className="font-semibold text-white group-hover:text-indigo-400 transition line-clamp-1">
                    {p.title}
                  </h3>
                  <p className="text-slate-400 text-xs mt-1 line-clamp-2">
                    {p.description || 'Không có mô tả chi tiết'}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-700/50 flex items-center justify-between text-xs text-slate-400">
                  <span className="flex items-center gap-1">
                    <Zap className="w-3.5 h-3.5 text-amber-400" />
                    Lượt giải: {p.play_count}
                  </span>
                  <Link
                    to={`/practice?puzzleId=${p.id}`}
                    className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium"
                  >
                    Luyện tập
                    <Play className="w-3 h-3 fill-current" />
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-700 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-indigo-400" />
                Tạo bài tập cờ vua mới
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
                  Tiêu đề bài tập *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ví dụ: Đòn chĩa đôi Hậu trắng e4"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Chuỗi FEN vị trí bắt đầu *
                </label>
                <input
                  type="text"
                  required
                  placeholder="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
                  value={fen}
                  onChange={(e) => setFen(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white font-mono text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Cấp độ
                  </label>
                  <select
                    value={formDifficulty}
                    onChange={(e) => setFormDifficulty(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none"
                  >
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                    <option value="master">Master</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Thể loại
                  </label>
                  <select
                    value={formType}
                    onChange={(e) => setFormType(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none"
                  >
                    <option value="tactics">Tactics</option>
                    <option value="mate_in_1">Mate in 1</option>
                    <option value="mate_in_2">Mate in 2</option>
                    <option value="fork">Fork</option>
                    <option value="pin">Pin</option>
                    <option value="endgame">Endgame</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Rating đề xuất
                  </label>
                  <input
                    type="number"
                    value={rating}
                    onChange={(e) => setRating(Number(e.target.value))}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Nước đi lời giải (dạng UCI, cách nhau bằng dấu phẩy)
                </label>
                <input
                  type="text"
                  placeholder="e2e4, e7e5, g1f3"
                  value={solutionUci}
                  onChange={(e) => setSolutionUci(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white font-mono text-xs focus:outline-none focus:border-indigo-500"
                />
                <span className="text-[11px] text-slate-400 mt-0.5 block">
                  Định dạng ô đi đến ô đến: e2e4, d8h4...
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Mô tả / Hướng dẫn giải
                </label>
                <textarea
                  rows={2}
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
                  {saving ? 'Đang lưu...' : 'Lưu bài tập'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
