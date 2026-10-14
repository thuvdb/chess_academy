import { useState, useEffect, useCallback } from 'react';
import { Chessboard } from 'react-chessboard';
import {
  BookOpen, Plus, Search, Filter, Play, Trash2, Pencil,
  Zap, Tag, Star, X, ShieldCheck, ShieldAlert, Loader2,
  GitBranch, ChevronRight, ChevronDown
} from 'lucide-react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  getPuzzles, createPuzzle, updatePuzzle, deletePuzzle, validateSolution,
  type PuzzleItem, type CreatePuzzleInput, type ValidateSolutionResult,
  type PlyCheck, type SolutionTree, type SolutionTreeNode
} from '../lib/puzzleApi';

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  beginner: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  medium: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  intermediate: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  hard: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  advanced: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  expert: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  master: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
};

function parseUciList(raw: string): string[] {
  return raw.split(',').map((s) => s.trim()).filter(Boolean);
}

/** Một nước trong báo cáo kiểm tra, kèm trạng thái hợp lệ. */
function PlyChip({ ply }: { ply: PlyCheck }) {
  const bad = !ply.legal || ply.forces_mate === false || !!ply.error;
  return (
    <span
      title={ply.error || undefined}
      className={`text-xs font-mono px-2 py-1 rounded border ${
        bad
          ? 'bg-rose-500/15 text-rose-300 border-rose-500/40'
          : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
      }`}
    >
      {ply.san || ply.uci}
    </span>
  );
}

/**
 * Báo cáo kiểm tra lời giải: tách hẳn nước của bên giải khỏi đáp trả của đối
 * phương, thay vì liệt kê chung một dãy như trước.
 */
function SolutionReport({ check }: { check: ValidateSolutionResult | null }) {
  if (!check) return null;
  const solverLabel = check.player_color === 'w' ? 'Trắng' : 'Đen';
  const defenderLabel = check.player_color === 'w' ? 'Đen' : 'Trắng';

  return (
    <div
      className={`rounded-xl border p-3 space-y-2.5 ${
        check.ok
          ? 'bg-emerald-500/5 border-emerald-500/30'
          : 'bg-rose-500/5 border-rose-500/30'
      }`}
    >
      <div className="flex items-center gap-2">
        {check.ok ? (
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
        ) : (
          <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0" />
        )}
        <span className={`text-xs font-semibold ${check.ok ? 'text-emerald-300' : 'text-rose-300'}`}>
          {check.ok ? 'Lời giải đã được chứng minh' : 'Lời giải chưa hợp lệ'}
        </span>
        {check.mate_in ? (
          <span className="text-[10px] font-semibold text-indigo-300 bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 rounded-full">
            Chiếu hết sau {check.mate_in} nước · tối đa {check.expected_plies} nước trong dãy
          </span>
        ) : (
          <span className="text-[10px] font-semibold text-amber-300 bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 rounded-full">
            Không có chiếu hết cưỡng bức
          </span>
        )}
      </div>

      {(check.player_moves.length > 0 || check.opponent_moves.length > 0) && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">
              {solverLabel} — nước của bạn ({check.player_moves.length})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {check.player_moves.map((p) => <PlyChip key={p.index} ply={p} />)}
            </div>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">
              {defenderLabel} — đáp trả ({check.opponent_moves.length})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {check.opponent_moves.length > 0
                ? check.opponent_moves.map((p) => <PlyChip key={p.index} ply={p} />)
                : <span className="text-slate-500 text-xs italic">chưa có</span>}
            </div>
          </div>
        </div>
      )}

      {check.errors.length > 0 && (
        <ul className="space-y-1">
          {check.errors.map((e, i) => (
            <li key={i} className="text-[11px] text-rose-300 leading-snug">• {e}</li>
          ))}
        </ul>
      )}
      {check.warnings.map((w, i) => (
        <p key={i} className="text-[11px] text-amber-300 leading-snug">• {w}</p>
      ))}
    </div>
  );
}

/** Nhánh của cây biến thể hiển thị đệ quy các nước tấn công và đối thủ đáp trả. */
function SolutionTreeNodeBranch({
  node,
  depth = 1,
  side = 'w',
  step = 1,
}: {
  node: SolutionTreeNode | null | undefined;
  depth?: number;
  side?: 'w' | 'b';
  step?: number;
}) {
  if (!node || !node.player_moves || node.player_moves.length === 0) return null;

  const playerSideLabel = side === 'w' ? 'Trắng' : 'Đen';
  const defenderSideLabel = side === 'w' ? 'Đen' : 'Trắng';

  return (
    <div className="space-y-2">
      {node.player_moves.map((pm, pmIdx) => (
        <div key={pm.uci || pmIdx} className="space-y-1.5">
          {/* Nước của bên tấn công / người giải */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-mono font-bold text-slate-400">
              {step}.
            </span>
            <span
              className={`text-xs font-mono font-semibold px-2.5 py-1 rounded-md border flex items-center gap-1.5 ${
                pm.is_mate
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-sm'
                  : 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30'
              }`}
            >
              <span className="text-[10px] uppercase font-sans text-slate-400 font-normal">
                {playerSideLabel}:
              </span>
              <span>{pm.san || pm.uci}</span>
              {pm.is_mate && (
                <span className="text-[10px] font-sans font-bold bg-emerald-500/30 text-emerald-200 px-1.5 py-0.5 rounded">
                  Chiếu hết
                </span>
              )}
            </span>

            {pm.replies && pm.replies.length > 1 && (
              <span className="text-[10px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                {pm.replies.length} biến phản đòn
              </span>
            )}
          </div>

          {/* Các nước đối phương có thể đáp trả */}
          {pm.replies && pm.replies.length > 0 && (
            <div className="ml-4 pl-3 border-l-2 border-slate-700/80 space-y-2 mt-1">
              {pm.replies.map((reply, rIdx) => (
                <div key={reply.uci || rIdx} className="space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`text-xs font-mono px-2 py-0.5 rounded border flex items-center gap-1.5 ${
                        reply.is_main
                          ? 'bg-slate-700/80 text-amber-300 border-amber-500/40'
                          : 'bg-slate-800/80 text-slate-300 border-slate-700'
                      }`}
                    >
                      <span className="text-[10px] uppercase font-sans text-slate-400 font-normal">
                        {defenderSideLabel}:
                      </span>
                      <span>{reply.san || reply.uci}</span>
                      {reply.is_main && (
                        <span className="text-[9px] font-sans text-amber-400 font-medium bg-amber-500/15 px-1 py-0.5 rounded">
                          Nhánh chính
                        </span>
                      )}
                    </span>
                  </div>

                  {/* Đệ quy nước tiếp theo của bên giải */}
                  {reply.next && (
                    <SolutionTreeNodeBranch
                      node={reply.next}
                      depth={depth + 1}
                      side={side}
                      step={step + 1}
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/** Giao diện trực quan hoá cây biến thể đối kháng cho bài tập. */
function SolutionTreeView({
  tree,
  playerColor = 'w',
  mateIn,
}: {
  tree: SolutionTree | SolutionTreeNode | null | undefined;
  playerColor?: 'w' | 'b';
  mateIn?: number | null;
}) {
  const [expanded, setExpanded] = useState(true);

  if (!tree || !tree.player_moves || tree.player_moves.length === 0) {
    return (
      <div className="bg-slate-900/50 border border-slate-700/40 rounded-xl p-3 text-center">
        <div className="flex items-center justify-center gap-1.5 text-xs text-slate-400">
          <GitBranch className="w-4 h-4 text-slate-500" />
          <span>Chưa có cây biến thể</span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">
          Bấm &ldquo;Kiểm tra lời giải&rdquo; để tự động sinh và hiển thị cây biến thể đối kháng.
        </p>
      </div>
    );
  }

  const colorLabel = (tree as any).player_color === 'b' || playerColor === 'b' ? 'Đen' : 'Trắng';
  const mateCount = (tree as any).mate_in || mateIn;

  return (
    <div className="bg-slate-900/80 border border-slate-700/60 rounded-xl p-3 space-y-2.5">
      <div className="flex items-center justify-between border-b border-slate-700/50 pb-2">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-semibold text-slate-200">
            Cây biến thể lời giải (Variation Tree)
          </span>
          {mateCount && (
            <span className="text-[10px] font-semibold text-emerald-300 bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 rounded-full">
              Chiếu hết {mateCount} nước ({colorLabel} đi trước)
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-slate-400 hover:text-white transition flex items-center gap-1"
        >
          {expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          {expanded ? 'Thu gọn' : 'Mở rộng'}
        </button>
      </div>

      {expanded && (
        <div className="max-h-56 overflow-y-auto pr-1 text-xs">
          <SolutionTreeNodeBranch
            node={tree}
            depth={1}
            side={(tree as any).player_color || playerColor}
            step={1}
          />
        </div>
      )}
    </div>
  );
}

export default function Puzzles() {
  const [puzzles, setPuzzles] = useState<PuzzleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [difficulty, setDifficulty] = useState<string>('');
  const [puzzleType, setPuzzleType] = useState<string>('');
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Create Form State
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [fen, setFen] = useState('r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 4');
  const [formDifficulty, setFormDifficulty] = useState('easy');
  const [formType, setFormType] = useState('tactic');
  const [rating, setRating] = useState(1200);
  const [solutionUci, setSolutionUci] = useState('');
  const [saving, setSaving] = useState(false);

  // Edit Form State
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingPuzzle, setEditingPuzzle] = useState<PuzzleItem | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editFen, setEditFen] = useState('');
  const [editDifficulty, setEditDifficulty] = useState('easy');
  const [editType, setEditType] = useState('tactic');
  const [editRating, setEditRating] = useState(1200);
  const [editSolutionUci, setEditSolutionUci] = useState('');
  const [updating, setUpdating] = useState(false);

  // Kiểm tra lời giải trước khi lưu
  const [createCheck, setCreateCheck] = useState<ValidateSolutionResult | null>(null);
  const [editCheck, setEditCheck] = useState<ValidateSolutionResult | null>(null);
  const [checking, setChecking] = useState(false);

  const runValidate = useCallback(async (
    fenValue: string,
    uciValue: string,
    typeValue: string,
  ): Promise<ValidateSolutionResult | null> => {
    const moves = parseUciList(uciValue);
    if (!fenValue.trim()) {
      toast.error('Cần nhập FEN trước khi kiểm tra');
      return null;
    }
    if (moves.length === 0) {
      toast.error('Cần nhập ít nhất một nước đi lời giải');
      return null;
    }
    setChecking(true);
    try {
      return await validateSolution({
        fen: fenValue.trim(),
        moves_uci: moves,
        puzzle_type: typeValue,
      });
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Không kiểm tra được lời giải');
      return null;
    } finally {
      setChecking(false);
    }
  }, []);

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
      toast.error('Không thể tải danh sách bài tập');
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
      toast.error('Tiêu đề và FEN là bắt buộc');
      return;
    }

    // Chặn ngay ở client khi lời giải chưa chứng minh được — backend cũng
    // chặn lần nữa, nhưng báo lỗi ở đây giúp giáo viên sửa tại chỗ.
    const moves = parseUciList(solutionUci);
    if (moves.length > 0) {
      const check = await runValidate(fen, solutionUci, formType);
      setCreateCheck(check);
      if (!check) return;
      if (!check.ok) {
        toast.error('Lời giải chưa hợp lệ, xem chi tiết bên dưới ô nhập');
        return;
      }
    }

    setSaving(true);
    try {
      const solutions = moves.map((move, index) => ({
        move_order: index + 1,
        move_uci: move,
        is_best_move: true,
      }));

      const payload: CreatePuzzleInput = {
        title: title.trim(),
        description: description.trim() || undefined,
        fen: fen.trim(),
        difficulty: formDifficulty,
        puzzle_type: formType,
        rating: Number(rating),
        solutions,
      };

      await createPuzzle(payload);
      toast.success('Tạo bài tập thành công');
      setShowCreateModal(false);
      // Reset form
      setTitle('');
      setDescription('');
      setSolutionUci('');
      setCreateCheck(null);
      fetchPuzzles();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Không thể tạo bài tập');
    } finally {
      setSaving(false);
    }
  };

  const handleOpenEdit = (p: PuzzleItem, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingPuzzle(p);
    setEditTitle(p.title || '');
    setEditDescription(p.description || '');
    setEditFen(p.fen || '');
    setEditDifficulty(p.difficulty || 'easy');
    setEditType(p.puzzle_type || 'tactic');
    setEditRating(p.rating || 1200);

    const uciMoves = p.solutions && p.solutions.length > 0
      ? [...p.solutions]
          .sort((a, b) => a.move_order - b.move_order)
          .map((s) => s.move_uci)
          .join(', ')
      : '';
    setEditSolutionUci(uciMoves);
    setEditCheck(null);
    setShowEditModal(true);
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPuzzle) return;
    if (!editTitle.trim() || !editFen.trim()) {
      toast.error('Tiêu đề và FEN là bắt buộc');
      return;
    }

    const moves = parseUciList(editSolutionUci);
    if (moves.length > 0) {
      const check = await runValidate(editFen, editSolutionUci, editType);
      setEditCheck(check);
      if (!check) return;
      if (!check.ok) {
        toast.error('Lời giải chưa hợp lệ, xem chi tiết bên dưới ô nhập');
        return;
      }
    }

    setUpdating(true);
    try {
      const solutions = moves.map((move, index) => ({
        move_order: index + 1,
        move_uci: move,
        is_best_move: true,
      }));

      const payload = {
        title: editTitle.trim(),
        description: editDescription.trim() || undefined,
        fen: editFen.trim(),
        difficulty: editDifficulty,
        puzzle_type: editType,
        rating: Number(editRating),
        solutions,
      };

      await updatePuzzle(editingPuzzle.id, payload);
      toast.success('Cập nhật bài tập thành công');
      setShowEditModal(false);
      setEditingPuzzle(null);
      setEditCheck(null);
      fetchPuzzles();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Không thể cập nhật bài tập');
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Bạn có chắc chắn muốn xóa bài tập này khỏi thư viện?')) return;
    try {
      await deletePuzzle(id);
      toast.success('Đã xóa bài tập');
      setPuzzles((prev) => prev.filter((p) => p.id !== id));
    } catch {
      toast.error('Không thể xóa bài tập');
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
        <div className="flex flex-1 min-w-65 items-center gap-2 bg-slate-900/60 border border-slate-700/50 rounded-xl px-3 py-2">
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
              <option value="easy" className="bg-slate-800">Dễ (Easy / Beginner)</option>
              <option value="medium" className="bg-slate-800">Trung bình (Medium)</option>
              <option value="hard" className="bg-slate-800">Khó (Hard / Advanced)</option>
              <option value="expert" className="bg-slate-800">Chuyên gia (Expert / Master)</option>
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
              <option value="tactic" className="bg-slate-800">Chiến thuật (Tactic)</option>
              <option value="mate_in_1" className="bg-slate-800">Chiếu hết 1 nước</option>
              <option value="mate_in_2" className="bg-slate-800">Chiếu hết 2 nước</option>
              <option value="mate_in_3" className="bg-slate-800">Chiếu hết 3 nước</option>
              <option value="mate_in_4" className="bg-slate-800">Chiếu hết 4 nước</option>
              <option value="endgame" className="bg-slate-800">Tàn cuộc (Endgame)</option>
              <option value="opening" className="bg-slate-800">Khai cuộc (Opening)</option>
              <option value="strategy" className="bg-slate-800">Chiến lược (Strategy)</option>
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
                    key={p.id}
                    options={{
                      id: `preview-${p.id}`,
                      position: p.fen,
                      allowDragging: false,
                    }}
                  />
                </div>
                <div className="absolute top-3 left-3 flex gap-2">
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                      DIFFICULTY_COLORS[p.difficulty || 'easy'] || DIFFICULTY_COLORS.easy
                    }`}
                  >
                    {p.difficulty || 'easy'}
                  </span>
                  <span className="bg-slate-800/90 text-amber-400 border border-slate-700 text-xs px-2 py-0.5 rounded-full flex items-center gap-1 font-semibold">
                    <Star className="w-3 h-3 fill-current" />
                    {p.rating}
                  </span>
                  {/* Trạng thái chứng minh lời giải — bài chưa verify bị ẩn khỏi học sinh */}
                  {p.solution_verified ? (
                    <span
                      title={p.mate_in ? `Đã chứng minh: chiếu hết sau ${p.mate_in} nước` : 'Lời giải đã được chứng minh'}
                      className="bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-xs px-2 py-0.5 rounded-full flex items-center gap-1 font-semibold"
                    >
                      <ShieldCheck className="w-3 h-3" />
                      {p.mate_in ? `M${p.mate_in}` : 'OK'}
                    </span>
                  ) : (
                    <span
                      title={p.verification_error || 'Lời giải chưa được chứng minh — học sinh chưa nhìn thấy bài này'}
                      className="bg-amber-500/15 text-amber-400 border border-amber-500/30 text-xs px-2 py-0.5 rounded-full flex items-center gap-1 font-semibold"
                    >
                      <ShieldAlert className="w-3 h-3" />
                      Cần rà
                    </span>
                  )}
                </div>

                {/* Action Buttons: Edit (Pencil) & Delete (Trash) */}
                <div className="absolute top-3 right-3 flex items-center gap-1.5 z-10">
                  <button
                    onClick={(e) => handleOpenEdit(p, e)}
                    className="p-1.5 bg-slate-900/90 hover:bg-indigo-600 text-slate-300 hover:text-white rounded-lg transition border border-slate-700/80 shadow-md backdrop-blur-sm"
                    title="Chỉnh sửa bài tập"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => handleDelete(p.id, e)}
                    className="p-1.5 bg-slate-900/90 hover:bg-red-600 text-slate-300 hover:text-white rounded-lg transition border border-slate-700/80 shadow-md backdrop-blur-sm"
                    title="Xóa bài tập"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
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

      {/* Edit Modal */}
      {showEditModal && editingPuzzle && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-xl p-6 shadow-2xl space-y-5 my-8">
            <div className="flex items-center justify-between border-b border-slate-700 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Pencil className="w-5 h-5 text-indigo-400" />
                Chỉnh sửa bài tập cờ vua
              </h3>
              <button
                onClick={() => {
                  setShowEditModal(false);
                  setEditingPuzzle(null);
                }}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdate} className="space-y-4">
              {/* Live Preview Chessboard */}
              <div className="flex flex-col sm:flex-row gap-4 items-center bg-slate-900/60 p-3 rounded-xl border border-slate-700/60">
                <div className="w-36 h-36 shrink-0 rounded-lg overflow-hidden border border-slate-700 shadow-md">
                  <Chessboard
                    key={`edit-preview-${editFen}`}
                    options={{
                      id: 'edit-preview-board',
                      position: editFen,
                      allowDragging: false,
                    }}
                  />
                </div>
                <div className="flex-1 text-xs text-slate-400 space-y-1">
                  <p className="font-semibold text-slate-200">Xem trước thế cờ:</p>
                  <p>Bàn cờ tự động cập nhật theo chuỗi FEN bên dưới.</p>
                  <p className="text-amber-400/90 font-mono break-all text-[11px] line-clamp-3">
                    {editFen || 'Chưa có FEN'}
                  </p>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Tiêu đề bài tập *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ví dụ: Đòn chĩa đôi Hậu trắng e4"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
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
                  value={editFen}
                  onChange={(e) => setEditFen(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white font-mono text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Cấp độ
                  </label>
                  <select
                    value={editDifficulty}
                    onChange={(e) => setEditDifficulty(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none"
                  >
                    <option value="easy">Dễ (Easy)</option>
                    <option value="medium">Trung bình (Medium)</option>
                    <option value="hard">Khó (Hard)</option>
                    <option value="expert">Chuyên gia (Expert)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Thể loại
                  </label>
                  <select
                    value={editType}
                    onChange={(e) => setEditType(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none"
                  >
                    <option value="tactic">Chiến thuật (Tactic)</option>
                    <option value="mate_in_1">Chiếu hết 1 nước</option>
                    <option value="mate_in_2">Chiếu hết 2 nước</option>
                    <option value="mate_in_3">Chiếu hết 3 nước</option>
                    <option value="mate_in_4">Chiếu hết 4 nước</option>
                    <option value="endgame">Tàn cuộc (Endgame)</option>
                    <option value="opening">Khai cuộc (Opening)</option>
                    <option value="strategy">Chiến lược (Strategy)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Rating đề xuất
                  </label>
                  <input
                    type="number"
                    value={editRating}
                    onChange={(e) => setEditRating(Number(e.target.value))}
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
                  value={editSolutionUci}
                  onChange={(e) => { setEditSolutionUci(e.target.value); setEditCheck(null); }}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white font-mono text-xs focus:outline-none focus:border-indigo-500"
                />
                <div className="flex items-center justify-between mt-1 gap-3">
                  <span className="text-[11px] text-slate-400">
                    Gồm cả nước đáp trả của đối phương, xen kẽ theo đúng lượt đi.
                  </span>
                  <button
                    type="button"
                    disabled={checking}
                    onClick={async () => setEditCheck(await runValidate(editFen, editSolutionUci, editType))}
                    className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-100 rounded-lg text-xs font-medium transition disabled:opacity-50"
                  >
                    {checking
                      ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      : <ShieldCheck className="w-3.5 h-3.5" />}
                    Kiểm tra lời giải
                  </button>
                </div>
                {editCheck && (
                  <div className="mt-2">
                    <SolutionReport check={editCheck} />
                  </div>
                )}

                {/* Variation Tree View trong Edit modal */}
                <div className="mt-3">
                  <SolutionTreeView
                    tree={editCheck?.solution_tree ?? editingPuzzle?.solution_tree}
                    playerColor={editCheck?.player_color ?? (editingPuzzle?.solution_tree as any)?.player_color ?? (editingPuzzle?.fen?.split(' ')[1] === 'b' ? 'b' : 'w')}
                    mateIn={editCheck?.mate_in ?? editingPuzzle?.mate_in}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Mô tả / Hướng dẫn giải
                </label>
                <textarea
                  rows={2}
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white text-sm focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-700">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false);
                    setEditingPuzzle(null);
                  }}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-xl text-sm font-medium transition"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={updating}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition disabled:opacity-50"
                >
                  {updating ? 'Đang lưu...' : 'Lưu thay đổi'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-xl p-6 shadow-2xl space-y-5 my-8">
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
              {/* Live Preview Chessboard */}
              <div className="flex flex-col sm:flex-row gap-4 items-center bg-slate-900/60 p-3 rounded-xl border border-slate-700/60">
                <div className="w-36 h-36 shrink-0 rounded-lg overflow-hidden border border-slate-700 shadow-md">
                  <Chessboard
                    key={`create-preview-${fen}`}
                    options={{
                      id: 'create-preview-board',
                      position: fen,
                      allowDragging: false,
                    }}
                  />
                </div>
                <div className="flex-1 text-xs text-slate-400 space-y-1">
                  <p className="font-semibold text-slate-200">Xem trước thế cờ:</p>
                  <p>Bàn cờ tự động cập nhật theo chuỗi FEN bên dưới.</p>
                  <p className="text-amber-400/90 font-mono break-all text-[11px] line-clamp-3">
                    {fen || 'Chưa có FEN'}
                  </p>
                </div>
              </div>

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
                    <option value="easy">Dễ (Easy)</option>
                    <option value="medium">Trung bình (Medium)</option>
                    <option value="hard">Khó (Hard)</option>
                    <option value="expert">Chuyên gia (Expert)</option>
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
                    <option value="tactic">Chiến thuật (Tactic)</option>
                    <option value="mate_in_1">Chiếu hết 1 nước</option>
                    <option value="mate_in_2">Chiếu hết 2 nước</option>
                    <option value="mate_in_3">Chiếu hết 3 nước</option>
                    <option value="mate_in_4">Chiếu hết 4 nước</option>
                    <option value="endgame">Tàn cuộc (Endgame)</option>
                    <option value="opening">Khai cuộc (Opening)</option>
                    <option value="strategy">Chiến lược (Strategy)</option>
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
                  onChange={(e) => { setSolutionUci(e.target.value); setCreateCheck(null); }}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white font-mono text-xs focus:outline-none focus:border-indigo-500"
                />
                <div className="flex items-center justify-between mt-1 gap-3">
                  <span className="text-[11px] text-slate-400">
                    Gồm cả nước đáp trả của đối phương, xen kẽ theo đúng lượt đi.
                  </span>
                  <button
                    type="button"
                    disabled={checking}
                    onClick={async () => setCreateCheck(await runValidate(fen, solutionUci, formType))}
                    className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-100 rounded-lg text-xs font-medium transition disabled:opacity-50"
                  >
                    {checking
                      ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      : <ShieldCheck className="w-3.5 h-3.5" />}
                    Kiểm tra lời giải
                  </button>
                </div>
                {createCheck && (
                  <div className="mt-2">
                    <SolutionReport check={createCheck} />
                  </div>
                )}

                {/* Variation Tree View trong Create modal */}
                {createCheck?.solution_tree && (
                  <div className="mt-3">
                    <SolutionTreeView
                      tree={createCheck.solution_tree}
                      playerColor={createCheck.player_color}
                      mateIn={createCheck.mate_in}
                    />
                  </div>
                )}
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
