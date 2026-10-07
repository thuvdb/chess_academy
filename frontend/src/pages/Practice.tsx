import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Chess } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import {
  Lightbulb, RotateCcw, ArrowRight, CheckCircle2,
  AlertCircle, Bot, Star, Clock, ArrowLeft
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  getPuzzles, getPuzzle, submitPuzzleAttempt,
  type PuzzleItem, type AttemptResult
} from '../lib/puzzleApi';

export default function Practice() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const puzzleIdParam = searchParams.get('puzzleId');

  const [puzzles, setPuzzles] = useState<PuzzleItem[]>([]);
  const [currentPuzzleIndex, setCurrentPuzzleIndex] = useState(0);
  const [puzzle, setPuzzle] = useState<PuzzleItem | null>(null);
  const [game, setGame] = useState<Chess>(new Chess());
  const [loading, setLoading] = useState(true);
  const [movesUci, setMovesUci] = useState<string[]>([]);
  const [movesSan, setMovesSan] = useState<string[]>([]);
  const [isSolved, setIsSolved] = useState(false);
  const [isFailed, setIsFailed] = useState(false);
  const [hintUsed, setHintUsed] = useState(false);
  const [hintText, setHintText] = useState<string | null>(null);
  const [attemptResult, setAttemptResult] = useState<AttemptResult | null>(null);
  const [timeSeconds, setTimeSeconds] = useState(0);

  // Timer
  useEffect(() => {
    if (isSolved || isFailed || !puzzle) return;
    const interval = setInterval(() => {
      setTimeSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isSolved, isFailed, puzzle]);

  // Load Puzzles
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        if (puzzleIdParam) {
          const single = await getPuzzle(puzzleIdParam);
          setPuzzle(single);
          setPuzzles([single]);
        } else {
          const list = await getPuzzles({ limit: 20 });
          setPuzzles(list);
          if (list.length > 0) {
            setPuzzle(list[0]);
          }
        }
      } catch {
        toast.error('Failed to load puzzle');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [puzzleIdParam]);

  // Setup game board when puzzle changes
  const initBoard = useCallback((p: PuzzleItem) => {
    try {
      const newGame = new Chess(p.fen);
      setGame(newGame);
      setMovesUci([]);
      setMovesSan([]);
      setIsSolved(false);
      setIsFailed(false);
      setHintUsed(false);
      setHintText(null);
      setAttemptResult(null);
      setTimeSeconds(0);
    } catch {
      toast.error('Invalid FEN position');
    }
  }, []);

  useEffect(() => {
    if (puzzle) {
      initBoard(puzzle);
    }
  }, [puzzle, initBoard]);

  // Make move on board
  const makeAMove = (move: { from: string; to: string; promotion?: string }) => {
    try {
      const gameCopy = new Chess(game.fen());
      const result = gameCopy.move(move);
      if (!result) return false;

      setGame(gameCopy);
      const uci = `${result.from}${result.to}${result.promotion || ''}`;
      const newUcis = [...movesUci, uci];
      const newSans = [...movesSan, result.san];
      setMovesUci(newUcis);
      setMovesSan(newSans);

      // Check against puzzle solution
      if (puzzle && puzzle.solutions && puzzle.solutions.length > 0) {
        const expectedOrder = movesUci.length + 1;
        const currentExpected = puzzle.solutions.find(
          (s) => s.move_order === expectedOrder && s.is_best_move
        );

        if (currentExpected) {
          if (currentExpected.move_uci.toLowerCase() === uci.toLowerCase()) {
            // Correct move!
            if (expectedOrder >= puzzle.solutions.length) {
              // Solved full puzzle!
              handleCompleted(newUcis, newSans, true);
            } else {
              // Opponent counter-move if available
              const nextCounter = puzzle.solutions.find(
                (s) => s.move_order === expectedOrder + 1
              );
              if (nextCounter) {
                setTimeout(() => {
                  const counterCopy = new Chess(gameCopy.fen());
                  const fromSquare = nextCounter.move_uci.slice(0, 2);
                  const toSquare = nextCounter.move_uci.slice(2, 4);
                  const promo = nextCounter.move_uci.slice(4, 5) || undefined;
                  const counterResult = counterCopy.move({
                    from: fromSquare,
                    to: toSquare,
                    promotion: promo,
                  });
                  if (counterResult) {
                    setGame(counterCopy);
                    setMovesUci((prev) => [...prev, nextCounter.move_uci]);
                    setMovesSan((prev) => [...prev, counterResult.san]);
                  }
                }, 400);
              }
            }
          } else {
            // Incorrect move
            handleCompleted(newUcis, newSans, false);
          }
        } else {
          // If no specific expected move, mark as solved
          handleCompleted(newUcis, newSans, true);
        }
      } else {
        // Fallback for puzzles without predefined solutions
        handleCompleted(newUcis, newSans, true);
      }

      return true;
    } catch {
      return false;
    }
  };

  const onDrop = (sourceSquare: string, targetSquare: string) => {
    if (isSolved || isFailed) return false;
    const move = makeAMove({
      from: sourceSquare,
      to: targetSquare,
      promotion: 'q',
    });
    return move;
  };

  const handleCompleted = async (ucis: string[], sans: string[], correct: boolean) => {
    if (!puzzle) return;
    if (correct) {
      setIsSolved(true);
      toast.success('Chính xác! Bạn đã giải thành công!');
    } else {
      setIsFailed(true);
      toast.error('Nước đi chưa chính xác!');
    }

    try {
      const res = await submitPuzzleAttempt({
        puzzle_id: puzzle.id,
        moves_uci: ucis,
        moves_san: sans,
        time_spent_seconds: timeSeconds,
        hint_used: hintUsed,
      });
      setAttemptResult(res);
    } catch {
      // Ignored
    }
  };

  const handleHint = () => {
    if (!puzzle || isSolved || isFailed) return;
    setHintUsed(true);
    if (puzzle.solutions && puzzle.solutions.length > 0) {
      const nextExpected = puzzle.solutions.find(
        (s) => s.move_order === movesUci.length + 1 && s.is_best_move
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
    if (puzzle) {
      initBoard(puzzle);
    }
  };

  const handleNextPuzzle = () => {
    if (puzzles.length > currentPuzzleIndex + 1) {
      const nextIdx = currentPuzzleIndex + 1;
      setCurrentPuzzleIndex(nextIdx);
      setPuzzle(puzzles[nextIdx]);
    } else {
      toast('Đã hoàn thành hết danh sách bài tập hiện tại!');
    }
  };

  const turn = game.turn() === 'w' ? 'Trắng đi' : 'Đen đi';

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
        <button
          onClick={() => navigate('/puzzles')}
          className="flex items-center gap-2 text-slate-400 hover:text-white text-sm transition"
        >
          <ArrowLeft className="w-4 h-4" />
          Về danh sách bài tập
        </button>
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

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Chess Board Area */}
        <div className="lg:col-span-7 flex flex-col items-center">
          <div className="w-full max-w-125 aspect-square bg-slate-900 rounded-2xl p-3 shadow-2xl border border-slate-700 relative">
            <Chessboard
              options={{
                position: game.fen(),
                onPieceDrop: ({ sourceSquare, targetSquare }) => {
                  if (!targetSquare) return false;
                  return onDrop(sourceSquare, targetSquare);
                },
                boardOrientation: game.turn() === 'b' ? 'black' : 'white',
                boardStyle: {
                  borderRadius: '12px',
                  boxShadow: '0 5px 15px rgba(0, 0, 0, 0.5)',
                },
              }}
            />

            {/* Solved Overlay banner */}
            {isSolved && (
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
                    Bài kế tiếp
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

            {/* Move History */}
            <div className="bg-slate-900/70 border border-slate-700/50 rounded-xl p-3">
              <h4 className="text-xs font-semibold text-slate-400 uppercase mb-2">
                Nước đi của bạn ({movesSan.length})
              </h4>
              {movesSan.length === 0 ? (
                <p className="text-slate-500 text-xs italic">Chưa có nước đi nào</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {movesSan.map((san, idx) => (
                    <span
                      key={idx}
                      className="bg-slate-800 text-slate-200 text-xs font-mono px-2 py-1 rounded border border-slate-700"
                    >
                      {idx + 1}. {san}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                onClick={handleHint}
                disabled={isSolved || isFailed || hintUsed}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 rounded-xl text-sm font-medium transition disabled:opacity-40"
              >
                <Lightbulb className="w-4 h-4" />
                {hintUsed ? 'Đã xem gợi ý' : 'Gợi ý (Hint)'}
              </button>
              <button
                onClick={handleReset}
                className="flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-700/60 hover:bg-slate-700 border border-slate-600/50 text-slate-200 rounded-xl text-sm font-medium transition"
              >
                <RotateCcw className="w-4 h-4" />
                Đặt lại
              </button>
            </div>
          </div>

          {/* AI Auto-grading Notice Card */}
          <div className="bg-indigo-950/30 border border-indigo-500/20 rounded-2xl p-4 flex items-center gap-3">
            <Bot className="w-8 h-8 text-indigo-400 shrink-0" />
            <div className="text-xs text-slate-300 leading-relaxed">
              <p className="font-semibold text-indigo-300">Cơ chế Auto AI Grading</p>
              Hệ thống tự động phân tích nước đi UCI, chấm điểm bài tập và cập nhật Puzzle Rating của bạn ngay lập tức.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
