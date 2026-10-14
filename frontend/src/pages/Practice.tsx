import { useState, useEffect, useCallback, useMemo, useRef, Fragment } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Chess, type Square } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import {
  Lightbulb, RotateCcw, ArrowRight, CheckCircle2,
  AlertCircle, Bot, Star, Clock, ArrowLeft, Lock, BookOpen, FileCheck
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  getPuzzles, getPuzzle, submitPuzzleAttempt, getAssignmentById, getAssignmentPuzzles, getMyAssignmentSubmission,
  type PuzzleItem, type AttemptResult, type SolutionTreeNode, type SolutionReply
} from '../lib/puzzleApi';
import { useAuthStore } from '../store/authStore';

/** Nước đáp trả máy sẽ đi: nhánh chống đỡ chính do backend đánh dấu. */
function mainReply(move: { replies: SolutionReply[] }): SolutionReply | null {
  if (!move.replies || move.replies.length === 0) return null;
  return move.replies.find((r) => r.is_main) ?? move.replies[0];
}

export default function Practice() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const puzzleIdParam = searchParams.get('puzzleId');
  const assignmentIdParam = searchParams.get('assignmentId');
  const readonlyParam = searchParams.get('readonly') === '1';

  const isAssignmentMode = Boolean(assignmentIdParam);
  const { user } = useAuthStore();
  const [isAssignmentLocked, setIsAssignmentLocked] = useState<boolean>(readonlyParam);

  const [puzzles, setPuzzles] = useState<PuzzleItem[]>([]);
  const [currentPuzzleIndex, setCurrentPuzzleIndex] = useState(0);
  const [puzzle, setPuzzle] = useState<PuzzleItem | null>(null);
  const [game, setGame] = useState<Chess>(new Chess());
  const [loading, setLoading] = useState(true);
  // Hai danh sách TÁCH RIÊNG. Trước đây nước của người chơi và đáp trả của máy
  // nằm chung một mảng nên UI gắn nhãn cả hai là "Nước đi của bạn".
  const [playerMovesSan, setPlayerMovesSan] = useState<string[]>([]);
  const [opponentMovesSan, setOpponentMovesSan] = useState<string[]>([]);
  const [isSolved, setIsSolved] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const [isRecorded, setIsRecorded] = useState(false);
  const [hintUsed, setHintUsed] = useState(false);
  const [hintText, setHintText] = useState<string | null>(null);
  const [attemptResult, setAttemptResult] = useState<AttemptResult | null>(null);
  const [timeSeconds, setTimeSeconds] = useState(0);

  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [legalMoves, setLegalMoves] = useState<string[]>([]);

  // Synchronous refs to prevent race conditions & duplicate move events
  const gameRef = useRef<Chess>(new Chess());
  const isBotMovingRef = useRef<boolean>(false);
  const selectedSquareRef = useRef<string | null>(null);
  const counterTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const playerUciRef = useRef<string[]>([]);
  const playerSanRef = useRef<string[]>([]);
  const opponentUciRef = useRef<string[]>([]);
  const opponentSanRef = useRef<string[]>([]);
  // Toàn bộ dãy theo thứ tự đã đi — chỉ dùng để gửi lên server (tương thích cũ)
  const allUciRef = useRef<string[]>([]);
  const allSanRef = useRef<string[]>([]);
  // Vị trí hiện tại trong cây biến thể; null khi bài chưa có cây
  const treeNodeRef = useRef<SolutionTreeNode | null>(null);

  const initialOrientation = useMemo<'white' | 'black'>(() => {
    if (!puzzle?.fen) return 'white';
    const parts = puzzle.fen.split(' ');
    return parts.length > 1 && parts[1] === 'b' ? 'black' : 'white';
  }, [puzzle?.fen]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (counterTimeoutRef.current) {
        clearTimeout(counterTimeoutRef.current);
      }
    };
  }, []);

  // Timer
  useEffect(() => {
    if (isSolved || isFailed || !puzzle) return;
    const interval = setInterval(() => {
      setTimeSeconds((s) => s + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isSolved, isFailed, puzzle]);

  // Load Puzzles
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        if (assignmentIdParam) {
          const promises: [Promise<any>, Promise<any>, Promise<any>?] = [
            getAssignmentById(assignmentIdParam),
            getAssignmentPuzzles(assignmentIdParam),
          ];
          if (user?.role === 'student') {
            promises.push(getMyAssignmentSubmission(assignmentIdParam).catch(() => null));
          }

          const [, asmPuzzles, sub] = await Promise.all(promises);

          if (readonlyParam || (sub && sub.status === 'submitted')) {
            setIsAssignmentLocked(true);
          }

          if (asmPuzzles && asmPuzzles.length > 0) {
            setPuzzles(asmPuzzles);
            const targetId = puzzleIdParam || asmPuzzles[0].id;
            const targetIdx = asmPuzzles.findIndex((p: PuzzleItem) => p.id === targetId);
            const activeIdx = targetIdx >= 0 ? targetIdx : 0;
            setCurrentPuzzleIndex(activeIdx);
            setPuzzle(asmPuzzles[activeIdx]);
            return;
          }
        }

        if (puzzleIdParam) {
          const single = await getPuzzle(puzzleIdParam);
          setPuzzle(single);
          setPuzzles([single]);
          setCurrentPuzzleIndex(0);
        } else {
          const list = await getPuzzles({ limit: 20 });
          setPuzzles(list);
          if (list.length > 0) {
            setPuzzle(list[0]);
            setCurrentPuzzleIndex(0);
          }
        }
      } catch {
        toast.error('Failed to load puzzle');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [puzzleIdParam, assignmentIdParam, user, readonlyParam]);

  // Setup game board when puzzle changes
  const initBoard = useCallback((p: PuzzleItem) => {
    try {
      if (counterTimeoutRef.current) {
        clearTimeout(counterTimeoutRef.current);
        counterTimeoutRef.current = null;
      }
      isBotMovingRef.current = false;
      selectedSquareRef.current = null;
      playerUciRef.current = [];
      playerSanRef.current = [];
      opponentUciRef.current = [];
      opponentSanRef.current = [];
      allUciRef.current = [];
      allSanRef.current = [];
      treeNodeRef.current = p.solution_tree ?? null;

      const newGame = new Chess(p.fen);
      gameRef.current = newGame;
      setGame(newGame);
      setPlayerMovesSan([]);
      setOpponentMovesSan([]);
      setIsSolved(false);
      setIsFailed(false);
      setIsRecorded(false);
      setHintUsed(false);
      setHintText(null);
      setAttemptResult(null);
      setTimeSeconds(0);
      setSelectedSquare(null);
      setLegalMoves([]);
    } catch {
      toast.error('Invalid FEN position');
    }
  }, []);

  useEffect(() => {
    if (puzzle) {
      initBoard(puzzle);
    }
  }, [puzzle, initBoard]);

  const handleCompleted = async (correct: boolean) => {
    if (!puzzle) return;

    if (isAssignmentMode) {
      // ── CHẾ ĐỘ BÀI TẬP VỀ NHÀ (BTVN): Không báo đúng/sai tức thì ──
      if (correct) {
        setIsSolved(true);
      } else {
        setIsRecorded(true);
      }
      toast('Đã ghi nhận phương án giải của bạn.', { icon: '📝' });
    } else {
      // ── CHẾ ĐỘ LUYỆN TẬP TỰ DO: Báo đúng/sai ngay để học phản xạ ──
      if (correct) {
        setIsSolved(true);
        toast.success(isAssignmentLocked ? 'Chính xác! (Chế độ xem lại)' : 'Chính xác! Bạn đã giải thành công!');
      } else {
        setIsFailed(true);
        toast.error('Nước đi chưa chính xác!');
      }
    }

    if (isAssignmentLocked) {
      // Đã khóa nộp bài: không gửi attempt để ghi đè điểm
      return;
    }

    try {
      const res = await submitPuzzleAttempt({
        puzzle_id: puzzle.id,
        assignment_id: assignmentIdParam || undefined,
        moves_uci: [...allUciRef.current],
        moves_san: [...allSanRef.current],
        player_moves_uci: [...playerUciRef.current],
        opponent_moves_uci: [...opponentUciRef.current],
        time_spent_seconds: timeSeconds,
        hint_used: hintUsed,
      });
      setAttemptResult(res);
    } catch (err: any) {
      if (err.response?.status === 400 && err.response?.data?.detail?.includes('khóa')) {
        setIsAssignmentLocked(true);
        toast.error('Bài tập đã nộp và khóa — chuyển sang chế độ Xem lại');
      }
    }
  };

  /** Máy đi nước đáp trả sau một khoảng ngắn cho dễ theo dõi. */
  const scheduleOpponentMove = useCallback((uci: string, expectedPlayerColor: 'w' | 'b') => {
    isBotMovingRef.current = true;
    if (counterTimeoutRef.current) {
      clearTimeout(counterTimeoutRef.current);
    }
    counterTimeoutRef.current = setTimeout(() => {
      try {
        // Double check if still opponent's turn and not cancelled
        if (gameRef.current.turn() === expectedPlayerColor) return;

        const counterResult = gameRef.current.move({
          from: uci.slice(0, 2),
          to: uci.slice(2, 4),
          promotion: uci.slice(4, 5) || undefined,
        });
        if (counterResult) {
          opponentUciRef.current.push(uci);
          opponentSanRef.current.push(counterResult.san);
          allUciRef.current.push(uci);
          allSanRef.current.push(counterResult.san);
          setOpponentMovesSan([...opponentSanRef.current]);
          setGame(new Chess(gameRef.current.fen()));
        }
      } finally {
        isBotMovingRef.current = false;
      }
    }, 400);
  }, []);

  // Make move on board
  const makeAMove = useCallback((move: { from: string; to: string; promotion?: string }): boolean => {
    try {
      if (isBotMovingRef.current || isSolved || isFailed || isRecorded) return false;

      // Verify it is indeed the player's turn to move
      const currentTurn = gameRef.current.turn();
      const expectedPlayerColor = initialOrientation === 'black' ? 'b' : 'w';
      if (currentTurn !== expectedPlayerColor) {
        return false;
      }

      const result = gameRef.current.move(move);
      if (!result) return false;

      const uci = `${result.from}${result.to}${result.promotion || ''}`;
      playerUciRef.current.push(uci);
      playerSanRef.current.push(result.san);
      allUciRef.current.push(uci);
      allSanRef.current.push(result.san);
      setPlayerMovesSan([...playerSanRef.current]);
      setGame(new Chess(gameRef.current.fen()));

      // ── Bài đã có cây biến thể: chấp nhận MỌI nước ép được mate ──
      const node = treeNodeRef.current;
      if (node && node.player_moves && node.player_moves.length > 0) {
        const played = node.player_moves.find(
          (pm) => pm.uci.toLowerCase() === uci.toLowerCase()
        );
        if (!played) {
          handleCompleted(false);
          return true;
        }
        if (played.is_mate || gameRef.current.isCheckmate()) {
          handleCompleted(true);
          return true;
        }
        const reply = mainReply(played);
        if (!reply) {
          handleCompleted(false);
          return true;
        }
        treeNodeRef.current = reply.next;
        scheduleOpponentMove(reply.uci, expectedPlayerColor);
        return true;
      }

      // ── Bài cũ chưa có cây: giữ nguyên so khớp theo mảng phẳng ──
      if (puzzle && puzzle.solutions && puzzle.solutions.length > 0) {
        const expectedOrder = allUciRef.current.length;
        const currentExpected = puzzle.solutions.find(
          (s) => s.move_order === expectedOrder && s.is_best_move
        );

        if (currentExpected) {
          if (currentExpected.move_uci.toLowerCase() === uci.toLowerCase()) {
            // Correct move!
            if (expectedOrder >= puzzle.solutions.length) {
              // Solved full puzzle!
              handleCompleted(true);
            } else {
              // Opponent counter-move if available
              const nextCounter = puzzle.solutions.find(
                (s) => s.move_order === expectedOrder + 1
              );
              if (nextCounter) {
                scheduleOpponentMove(nextCounter.move_uci, expectedPlayerColor);
              }
            }
          } else {
            // Incorrect move
            handleCompleted(false);
          }
        } else {
          // No expected move configured for this order
          handleCompleted(false);
        }
      } else {
        // Puzzles without solutions are marked as failed until verified by server
        handleCompleted(false);
      }

      return true;
    } catch {
      return false;
    }
  }, [isSolved, isFailed, isRecorded, initialOrientation, puzzle, scheduleOpponentMove, handleCompleted]);

  const onDrop = (sourceSquare: string, targetSquare: string) => {
    if (isSolved || isFailed || isRecorded || !puzzle || isBotMovingRef.current) return false;
    selectedSquareRef.current = null;
    setSelectedSquare(null);
    setLegalMoves([]);
    return makeAMove({
      from: sourceSquare,
      to: targetSquare,
      promotion: 'q',
    });
  };

  const handleHint = () => {
    if (!puzzle || isSolved || isFailed || isRecorded || isAssignmentMode) return;
    setHintUsed(true);

    // Gợi ý lấy từ cây: nước chìa khoá tại đúng nút hiện tại
    const node = treeNodeRef.current;
    if (node && node.player_moves && node.player_moves.length > 0) {
      const from = node.player_moves[0].uci.slice(0, 2).toUpperCase();
      const alts = node.player_moves.length;
      setHintText(
        alts > 1
          ? `Gợi ý: Có ${alts} nước dẫn tới chiếu hết, một trong số đó xuất phát từ ô ${from}`
          : `Gợi ý: Tìm nước đi cho quân ở ô ${from}`
      );
      return;
    }

    if (puzzle.solutions && puzzle.solutions.length > 0) {
      const nextExpected = puzzle.solutions.find(
        (s) => s.move_order === allUciRef.current.length + 1 && s.is_best_move
      );
      if (nextExpected) {
        setHintText(`Gợi ý: Tìm nước đi cho quân ở ô ${nextExpected.move_uci.slice(0, 2).toUpperCase()}`);
      } else {
        setHintText('Gợi ý: Hãy quan sát kỹ các đòn chiến thuật trực tiếp vào Vua hoặc Hậu');
      }
    } else {
      setHintText('Gợi ý: Hãy kiểm tra các nước ăn quân hoặc chiếu vua đối phương');
    }
  };

  const handleReset = () => {
    if (isAssignmentMode && (isSolved || isRecorded)) {
      toast('Bài tập về nhà đã ghi nhận phương án, không thể đặt lại.', { icon: '🔒' });
      return;
    }
    if (puzzle) {
      initBoard(puzzle);
    }
  };

  const handleNextPuzzle = () => {
    if (puzzles.length > currentPuzzleIndex + 1) {
      const nextIdx = currentPuzzleIndex + 1;
      const nextPuz = puzzles[nextIdx];
      setCurrentPuzzleIndex(nextIdx);
      setPuzzle(nextPuz);
      if (assignmentIdParam) {
        const query = isAssignmentLocked
          ? `?puzzleId=${nextPuz.id}&assignmentId=${assignmentIdParam}&readonly=1`
          : `?puzzleId=${nextPuz.id}&assignmentId=${assignmentIdParam}`;
        navigate(`/practice${query}`, { replace: true });
      }
    } else {
      if (assignmentIdParam) {
        toast.success(isAssignmentLocked ? 'Đã xem hết danh sách bài tập!' : '🎉 Bạn đã hoàn thành toàn bộ bài tập về nhà!');
        navigate(`/assignments/${assignmentIdParam}`);
      } else {
        toast('Đã hoàn thành hết danh sách bài tập hiện tại!');
      }
    }
  };

  const turn = game.turn() === 'w' ? 'Trắng đi' : 'Đen đi';
  const playerColorLabel = initialOrientation === 'black' ? 'Đen' : 'Trắng';
  const opponentColorLabel = initialOrientation === 'black' ? 'Trắng' : 'Đen';

  const handleSquareClick = useCallback(
    (square: string) => {
      if (isSolved || isFailed || isRecorded || !puzzle) return;

      if (selectedSquare && legalMoves.includes(square)) {
        makeAMove({
          from: selectedSquare,
          to: square,
          promotion: 'q',
        });
        setSelectedSquare(null);
        setLegalMoves([]);
        return;
      }

      const piece = game.get(square as Square);
      if (piece && piece.color === game.turn()) {
        setSelectedSquare(square);
        const moves = game.moves({ square: square as Square, verbose: true });
        setLegalMoves(moves.map((m: any) => m.to));
      } else {
        setSelectedSquare(null);
        setLegalMoves([]);
      }
    },
    [game, isSolved, isFailed, isRecorded, puzzle, selectedSquare, legalMoves, makeAMove]
  );

  const customSquareStyles = useMemo(() => {
    const styles: Record<string, React.CSSProperties> = {};
    if (selectedSquare) {
      styles[selectedSquare] = { backgroundColor: 'rgba(255, 255, 0, 0.4)' };
    }
    for (const sq of legalMoves) {
      const hasPiece = game.get(sq as Square);
      if (hasPiece) {
        styles[sq] = {
          background: 'radial-gradient(circle, transparent 55%, rgba(0, 0, 0, 0.3) 55%)',
          borderRadius: '50%',
        };
      } else {
        styles[sq] = {
          background: 'radial-gradient(circle, rgba(0, 0, 0, 0.25) 25%, transparent 25%)',
        };
      }
    }
    if (game.inCheck() || game.isCheck()) {
      const turnColor = game.turn();
      const board = game.board();
      for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
          const piece = board[r][c];
          if (piece && piece.type === 'k' && piece.color === turnColor) {
            const sq = `${String.fromCharCode(97 + c)}${8 - r}`;
            styles[sq] = {
              ...styles[sq],
              backgroundColor: 'rgba(255, 0, 0, 0.5)',
              boxShadow: 'inset 0 0 15px 5px rgba(255, 0, 0, 0.6)',
            };
          }
        }
      }
    }
    if (game.isGameOver() && game.isCheckmate()) {
      const turnColor = game.turn();
      const board = game.board();
      for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
          const piece = board[r][c];
          if (piece && piece.type === 'k' && piece.color === turnColor) {
            const sq = `${String.fromCharCode(97 + c)}${8 - r}`;
            styles[sq] = {
              backgroundColor: 'rgba(128, 128, 128, 0.7)',
              boxShadow: 'inset 0 0 20px 10px rgba(0, 0, 0, 0.5)',
            };
          }
        }
      }
    }
    return styles;
  }, [selectedSquare, legalMoves, game]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-32">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  if (!puzzle) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-12 text-center max-w-lg mx-auto mt-12">
        <AlertCircle className="w-12 h-12 text-amber-400 mx-auto mb-3" />
        <h3 className="text-lg font-bold text-white">Chưa có bài tập nào</h3>
        <p className="text-slate-400 text-sm mt-1 mb-4">
          Hãy quay lại thư viện bài tập để chọn bài luyện tập.
        </p>
        <button
          onClick={() => navigate('/puzzles')}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition"
        >
          Đến thư viện
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Top Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(assignmentIdParam ? `/assignments/${assignmentIdParam}` : '/puzzles')}
            className="flex items-center gap-2 text-slate-400 hover:text-white text-sm transition"
          >
            <ArrowLeft className="w-4 h-4" />
            {assignmentIdParam ? 'Về bài tập về nhà' : 'Về danh sách bài tập'}
          </button>
          {assignmentIdParam && puzzles.length > 0 && (
            <span className="text-xs bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 px-2.5 py-1 rounded-lg font-semibold">
              Thế cờ {currentPuzzleIndex + 1} / {puzzles.length}
            </span>
          )}
          {isAssignmentMode && !isAssignmentLocked && (
            <span className="text-xs bg-amber-500/15 text-amber-300 border border-amber-500/30 px-2.5 py-1 rounded-lg font-semibold flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5" /> Chế độ BTVN
            </span>
          )}
          {isAssignmentLocked && (
            <span className="text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2.5 py-1 rounded-lg font-bold flex items-center gap-1">
              <Lock className="w-3 h-3" /> Xem lại (Đã khóa)
            </span>
          )}
        </div>
        <div className="flex items-center gap-4 text-sm text-slate-300">
          <span className="flex items-center gap-1.5 bg-slate-800 border border-slate-700 px-3 py-1 rounded-full">
            <Clock className="w-4 h-4 text-indigo-400" />
            {Math.floor(timeSeconds / 60)}:{('0' + (timeSeconds % 60)).slice(-2)}
          </span>
          <span className="flex items-center gap-1.5 bg-slate-800 border border-slate-700 px-3 py-1 rounded-full text-amber-400 font-semibold">
            <Star className="w-4 h-4 fill-current" />
            Rating: {puzzle.rating}
          </span>
        </div>
      </div>

      {/* Lock Mode Banner */}
      {isAssignmentLocked && (
        <div className="bg-emerald-950/50 border border-emerald-500/40 rounded-xl px-4 py-2.5 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-emerald-200 gap-2">
          <span className="flex items-center gap-2 font-medium">
            <Lock className="w-4 h-4 text-emerald-400 shrink-0" />
            Bài tập này đã được nộp và khóa cứng — Đang ở chế độ Xem lại (không tính thêm điểm hoặc ghi đè kết quả).
          </span>
          {assignmentIdParam && (
            <button
              onClick={() => navigate(`/assignments/${assignmentIdParam}`)}
              className="text-emerald-400 hover:text-emerald-300 hover:underline font-semibold shrink-0"
            >
              Xem chi tiết bài tập &rarr;
            </button>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Chess Board Area */}
        <div className="lg:col-span-7 flex flex-col items-center">
          <div className="w-full max-w-125 aspect-square bg-slate-900 rounded-2xl p-3 shadow-2xl border border-slate-700 relative">
            <Chessboard
              key={puzzle?.id || 'default-board'}
              options={{
                id: `PracticeBoard-${puzzle?.id || 'default'}`,
                position: game.fen(),
                boardOrientation: initialOrientation,
                allowDragging: !isSolved && !isFailed && !isRecorded,
                canDragPiece: ({ piece }) => {
                  if (isSolved || isFailed || isRecorded) return false;
                  return piece.pieceType.startsWith(game.turn());
                },
                onPieceDrop: ({ sourceSquare, targetSquare }) => {
                  if (!targetSquare) return false;
                  return onDrop(sourceSquare, targetSquare);
                },
                onSquareClick: ({ square }) => {
                  handleSquareClick(square);
                },
                onPieceClick: ({ square }) => {
                  if (square) handleSquareClick(square);
                },
                squareStyles: customSquareStyles,
                boardStyle: {
                  borderRadius: '12px',
                  boxShadow: '0 5px 15px rgba(0, 0, 0, 0.5)',
                },
                showNotation: true,
              }}
            />

            {/* Overlay banner khi làm BTVN (cả đúng hoặc sai đều ghi nhận phương án và cho đi tiếp) */}
            {isAssignmentMode && (isSolved || isRecorded) && (
              <div className="absolute inset-0 bg-slate-950/85 backdrop-blur-xs rounded-2xl flex flex-col items-center justify-center p-6 text-center animate-fade-in z-20">
                <div className="w-16 h-16 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center mb-3">
                  <FileCheck className="w-9 h-9" />
                </div>
                <h2 className="text-xl font-bold text-white uppercase tracking-wide">
                  ĐÃ GHI NHẬN PHƯƠNG ÁN GIẢI
                </h2>
                <p className="text-slate-300 text-sm mt-2 max-w-sm">
                  {isAssignmentLocked
                    ? 'Bài tập đã nộp chính thức — đang ở chế độ xem lại.'
                    : 'Phương án của bạn cho thế cờ này đã được lưu lại để gửi giáo viên chấm điểm.'}
                </p>
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={handleNextPuzzle}
                    className="flex items-center gap-2 px-6 py-2.5 bg-linear-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-bold rounded-xl text-sm transition shadow-lg shadow-amber-500/25"
                  >
                    {currentPuzzleIndex + 1 >= puzzles.length
                      ? 'Hoàn thành bài tập'
                      : `Bài kế tiếp (${currentPuzzleIndex + 2}/${puzzles.length})`}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* Solved Overlay banner cho chế độ Luyện tập tự do */}
            {!isAssignmentMode && isSolved && (
              <div className="absolute inset-0 bg-emerald-950/80 backdrop-blur-xs rounded-2xl flex flex-col items-center justify-center p-6 text-center animate-fade-in">
                <CheckCircle2 className="w-16 h-16 text-emerald-400 mb-2 animate-bounce" />
                <h2 className="text-2xl font-bold text-white">XUẤT SẮC! BÀI TẬP ĐÃ GIẢI XONG</h2>
                {attemptResult && (
                  <div className="mt-3 bg-emerald-900/60 border border-emerald-500/40 rounded-xl px-4 py-2 flex items-center gap-2 text-emerald-200 text-sm">
                    <Bot className="w-5 h-5 text-emerald-400" />
                    <span>Hệ thống tự động chấm: <strong>+{attemptResult.points_earned} điểm</strong></span>
                  </div>
                )}
                <div className="flex gap-3 mt-5">
                  <button
                    onClick={handleReset}
                    className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-sm font-medium transition"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Xem lại
                  </button>
                  <button
                    onClick={handleNextPuzzle}
                    className="flex items-center gap-1.5 px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-sm font-medium transition shadow-lg shadow-emerald-600/30"
                  >
                    {`Bài kế tiếp (${currentPuzzleIndex + 2}/${puzzles.length})`}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Turn indicator */}
          <div className="mt-3 flex items-center justify-between w-full max-w-125 text-xs text-slate-400">
            <span className="flex items-center gap-2">
              <span
                className={`w-3 h-3 rounded-full border ${
                  game.turn() === 'w' ? 'bg-white border-slate-300' : 'bg-black border-slate-700'
                }`}
              />
              Lượt: <strong>{turn}</strong>
            </span>
            <span>Kéo thả quân cờ để thực hiện nước đi</span>
          </div>
        </div>

        {/* Sidebar Controls & Info */}
        <div className="lg:col-span-5 space-y-5">
          <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl p-5 shadow-lg space-y-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
                  {puzzle.puzzle_type || 'Tactics'}
                </span>
                <span className="text-xs text-slate-400 uppercase tracking-wider font-mono">
                  {puzzle.difficulty}
                </span>
              </div>
              <h2 className="text-xl font-bold text-white mt-2">{puzzle.title}</h2>
              <p className="text-slate-400 text-sm mt-1">{puzzle.description || 'Tìm nước đi tối ưu nhất cho thế cờ này.'}</p>
            </div>

            {/* Hint Box */}
            {hintText && (
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 text-xs text-amber-300 flex items-start gap-2">
                <Lightbulb className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <span>{hintText}</span>
              </div>
            )}

            {/* Move History — hai bên TÁCH RIÊNG, ghép theo cặp như biên bản cờ */}
            <div className="bg-slate-900/70 border border-slate-700/50 rounded-xl p-3">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-xs font-semibold text-slate-400 uppercase">
                  Diễn biến ván cờ
                </h4>
                {puzzle.mate_in ? (
                  <span className="text-[10px] font-semibold text-indigo-300 bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 rounded-full">
                    Chiếu hết sau {puzzle.mate_in} nước
                  </span>
                ) : null}
              </div>

              {playerMovesSan.length === 0 ? (
                <p className="text-slate-500 text-xs italic">Chưa có nước đi nào</p>
              ) : (
                <>
                  <div className="grid grid-cols-[2rem_1fr_1fr] gap-x-2 gap-y-1.5 items-center">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider">#</span>
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                      {playerColorLabel} — bạn
                    </span>
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                      {opponentColorLabel} — đối thủ
                    </span>

                    {playerMovesSan.map((san, idx) => (
                      <Fragment key={idx}>
                        <span className="text-[11px] text-slate-500 font-mono">{idx + 1}.</span>
                        <span className="bg-slate-800 text-slate-100 text-xs font-mono px-2 py-1 rounded border border-slate-700 text-center">
                          {san}
                        </span>
                        {opponentMovesSan[idx] ? (
                          <span className="bg-slate-800/60 text-slate-300 text-xs font-mono px-2 py-1 rounded border border-slate-700/60 text-center">
                            {opponentMovesSan[idx]}
                          </span>
                        ) : (
                          <span className="text-slate-600 text-xs text-center">—</span>
                        )}
                      </Fragment>
                    ))}
                  </div>
                  <p className="text-[10px] text-slate-500 mt-2">
                    Bạn đã đi {playerMovesSan.length} nước
                    {opponentMovesSan.length > 0
                      ? `, đối thủ đáp trả ${opponentMovesSan.length} nước`
                      : ''}
                  </p>
                </>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              {!isAssignmentMode && (
                <button
                  onClick={handleHint}
                  disabled={isSolved || isFailed || hintUsed}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 rounded-xl text-sm font-medium transition disabled:opacity-40"
                >
                  <Lightbulb className="w-4 h-4" />
                  {hintUsed ? 'Đã xem gợi ý' : 'Gợi ý (Hint)'}
                </button>
              )}
              <button
                onClick={handleReset}
                disabled={isAssignmentMode && (isSolved || isRecorded)}
                className={`flex items-center justify-center gap-2 py-2.5 bg-slate-700/60 hover:bg-slate-700 border border-slate-600/50 text-slate-200 rounded-xl text-sm font-medium transition disabled:opacity-40 disabled:cursor-not-allowed ${
                  isAssignmentMode ? 'w-full' : 'px-4'
                }`}
              >
                <RotateCcw className="w-4 h-4" />
                {isAssignmentMode && (isSolved || isRecorded) ? 'Đã lưu phương án' : 'Đặt lại'}
              </button>
            </div>
          </div>

          {/* Mode Notice Card */}
          {isAssignmentMode ? (
            <div className="bg-indigo-950/40 border border-indigo-500/30 rounded-2xl p-4 flex items-center gap-3">
              <BookOpen className="w-8 h-8 text-indigo-400 shrink-0" />
              <div className="text-xs text-slate-300 leading-relaxed">
                <p className="font-semibold text-indigo-300">Chế độ Bài tập về nhà (BTVN)</p>
                Hệ thống lưu lại dãy nước đi của bạn để thầy giáo chấm điểm. Bạn có thể làm tiếp các bài khác và nộp bài khi hoàn tất.
              </div>
            </div>
          ) : (
            <div className="bg-indigo-950/30 border border-indigo-500/20 rounded-2xl p-4 flex items-center gap-3">
              <Bot className="w-8 h-8 text-indigo-400 shrink-0" />
              <div className="text-xs text-slate-300 leading-relaxed">
                <p className="font-semibold text-indigo-300">Cơ chế Auto AI Grading</p>
                Hệ thống tự động phân tích nước đi UCI, chấm điểm bài tập và cập nhật Puzzle Rating của bạn ngay lập tức.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
