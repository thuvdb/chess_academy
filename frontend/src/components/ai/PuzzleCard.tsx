import React, { useState } from 'react';
import { Chess, type Square } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import {
  Lightbulb,
  RotateCcw,
  Eye,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Swords,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../lib/api';

export interface PuzzleData {
  id: string;
  fen: string;
  side_to_move: 'w' | 'b';
  theme: string;
  title: string;
  difficulty?: string;
  rating?: number;
}

interface PuzzleCardProps {
  puzzle: PuzzleData;
  sessionId?: string | null;
}

interface SolutionMove {
  move_order: number;
  uci: string;
  san: string;
  side: string;
  explanation?: string;
}

export const PuzzleCard: React.FC<PuzzleCardProps> = ({ puzzle, sessionId }) => {
  const [game, setGame] = useState<Chess>(() => new Chess(puzzle.fen));
  const [currentFen, setCurrentFen] = useState<string>(puzzle.fen);
  const [playerStepIndex, setPlayerStepIndex] = useState<number>(0);
  const [isSolved, setIsSolved] = useState<boolean>(false);
  const [isChecking, setIsChecking] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isError, setIsError] = useState<boolean>(false);

  // Hint & Solution states
  const [hintText, setHintText] = useState<string | null>(null);
  const [isLoadingHint, setIsLoadingHint] = useState<boolean>(false);
  const [solutionMoves, setSolutionMoves] = useState<SolutionMove[] | null>(null);
  const [isLoadingSolution, setIsLoadingSolution] = useState<boolean>(false);
  const [isSolutionRevealed, setIsSolutionRevealed] = useState<boolean>(false);

  // AI Explanation
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);
  const [isLoadingExplain, setIsLoadingExplain] = useState<boolean>(false);
  const [showExplanation, setShowExplanation] = useState<boolean>(true);

  // Click-to-move support
  const [selectedSquare, setSelectedSquare] = useState<Square | null>(null);
  const [legalTargetSquares, setLegalTargetSquares] = useState<Square[]>([]);

  const orientation = puzzle.side_to_move === 'b' ? 'black' : 'white';

  // Reset board back to initial starting position
  const handleReset = () => {
    const newG = new Chess(puzzle.fen);
    setGame(newG);
    setCurrentFen(puzzle.fen);
    setPlayerStepIndex(0);
    setIsSolved(false);
    setStatusMessage(null);
    setIsError(false);
    setSelectedSquare(null);
    setLegalTargetSquares([]);
  };

  // Asynchronously verify move with backend
  const verifyMoveAsync = async (uci: string, fenBefore: string, stepIdx: number) => {
    setIsChecking(true);
    setStatusMessage(null);
    setIsError(false);

    try {
      const res = await api.post(`/ai-tutor/puzzles/${puzzle.id}/check`, {
        move: uci,
        current_fen: fenBefore,
        step_index: stepIdx,
        session_id: sessionId || null,
      });

      const data = res.data;

      if (data.is_correct) {
        setIsError(false);
        if (data.is_completed) {
          setIsSolved(true);
          setStatusMessage(data.message || 'Tuyệt vời! Bạn đã giải chính xác thế cờ.');
          setCurrentFen(data.next_fen);
          setGame(new Chess(data.next_fen));
          toast.success('Chính xác! Bạn đã giải xong thế cờ!');
        } else {
          // Opponent replied
          setStatusMessage(data.message || 'Nước đi chính xác! Đối thủ đã đáp trả.');
          setCurrentFen(data.next_fen);
          setGame(new Chess(data.next_fen));
          setPlayerStepIndex((prev) => prev + 1);
        }
      } else {
        // Incorrect move: revert board
        setIsError(true);
        setStatusMessage(data.message || 'Nước đi chưa chính xác, hãy thử lại!');
        setGame(new Chess(fenBefore));
        setCurrentFen(fenBefore);
      }
    } catch {
      setIsError(true);
      setStatusMessage('Không thể kiểm tra nước đi lúc này. Vui lòng thử lại.');
      setGame(new Chess(fenBefore));
      setCurrentFen(fenBefore);
    } finally {
      setIsChecking(false);
    }
  };

  // Submit move synchronously on board and trigger verify
  const submitMove = (from: Square, to: Square): boolean => {
    if (isSolved || isChecking) return false;

    const fenBefore = game.fen();
    const gameCopy = new Chess(fenBefore);
    let moveObj = null;

    try {
      moveObj = gameCopy.move({ from, to, promotion: 'q' });
    } catch {
      return false;
    }

    if (!moveObj) return false;

    const uci = `${moveObj.from}${moveObj.to}${moveObj.promotion || ''}`;

    // Apply tentatively on client
    setGame(gameCopy);
    setCurrentFen(gameCopy.fen());
    setSelectedSquare(null);
    setLegalTargetSquares([]);

    // Check with backend asynchronously
    verifyMoveAsync(uci, fenBefore, playerStepIndex);
    return true;
  };

  // Drag and drop piece
  const handleDrop = (sourceSquare: Square, targetSquare: Square): boolean => {
    return submitMove(sourceSquare, targetSquare);
  };

  // Click square to select or move
  const handleSquareClick = (square: Square) => {
    if (isSolved || isChecking) return;

    if (selectedSquare) {
      if (selectedSquare === square) {
        setSelectedSquare(null);
        setLegalTargetSquares([]);
        return;
      }

      if (legalTargetSquares.includes(square)) {
        submitMove(selectedSquare, square);
        return;
      }
    }

    // Select piece if it belongs to active turn
    const piece = game.get(square);
    if (piece && piece.color === game.turn()) {
      setSelectedSquare(square);
      const moves = game.moves({ square, verbose: true });
      setLegalTargetSquares(moves.map((m) => m.to as Square));
    } else {
      setSelectedSquare(null);
      setLegalTargetSquares([]);
    }
  };

  // Get gentle hint (theme)
  const handleGetHint = async () => {
    if (hintText) return;
    setIsLoadingHint(true);
    try {
      const res = await api.get(`/ai-tutor/puzzles/${puzzle.id}/hint`, {
        params: { session_id: sessionId || undefined },
      });
      setHintText(res.data.hint || `Chủ đề: ${res.data.theme}`);
    } catch {
      toast.error('Không thể tải gợi ý lúc này.');
    } finally {
      setIsLoadingHint(false);
    }
  };

  // View full solution
  const handleViewSolution = async () => {
    if (solutionMoves) {
      setIsSolutionRevealed((prev) => !prev);
      return;
    }

    setIsLoadingSolution(true);
    try {
      const res = await api.post(`/ai-tutor/puzzles/${puzzle.id}/solution`, null, {
        params: { session_id: sessionId || undefined },
      });
      setSolutionMoves(res.data.moves || []);
      setIsSolutionRevealed(true);
    } catch {
      toast.error('Không thể tải đáp án.');
    } finally {
      setIsLoadingSolution(false);
    }
  };

  // Request AI explanation
  const handleRequestExplanation = async () => {
    if (aiExplanation) {
      setShowExplanation(true);
      return;
    }

    setIsLoadingExplain(true);
    try {
      const res = await api.post(`/ai-tutor/puzzles/${puzzle.id}/explain`);
      setAiExplanation(res.data.explanation || 'Không có giải thích.');
      setShowExplanation(true);
    } catch {
      toast.error('Không thể nhờ AI giải thích lúc này.');
    } finally {
      setIsLoadingExplain(false);
    }
  };

  // Custom highlights for selected square and legal targets
  const customSquareStyles = React.useMemo(() => {
    const styles: Record<string, React.CSSProperties> = {};
    if (selectedSquare) {
      styles[selectedSquare] = {
        backgroundColor: 'rgba(234, 179, 8, 0.45)',
      };
    }
    for (const sq of legalTargetSquares) {
      styles[sq] = {
        background: 'radial-gradient(circle, rgba(16, 185, 129, 0.65) 25%, transparent 30%)',
        borderRadius: '50%',
      };
    }
    return styles;
  }, [selectedSquare, legalTargetSquares]);

  return (
    <div className="mt-3 p-3.5 bg-slate-900/95 border border-slate-700/80 rounded-2xl max-w-sm shadow-2xl flex flex-col items-center select-none text-slate-100">
      {/* Header Info */}
      <div className="w-full flex items-center justify-between gap-2 mb-2 pb-2 border-b border-slate-800">
        <div className="flex items-center gap-1.5 truncate">
          <Swords className="w-4 h-4 text-amber-400 shrink-0" />
          <span className="text-xs font-bold text-white truncate" title={puzzle.title}>
            {puzzle.title}
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            {puzzle.theme || 'Chiến thuật'}
          </span>
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
              puzzle.side_to_move === 'w'
                ? 'bg-amber-400/20 text-amber-300'
                : 'bg-slate-700 text-slate-300'
            }`}
          >
            {puzzle.side_to_move === 'w' ? 'Trắng đi' : 'Đen đi'}
          </span>
        </div>
      </div>

      {/* Interactive Chessboard */}
      <div className="w-64 h-64 relative rounded-xl overflow-hidden border border-slate-800 shadow-md">
        <Chessboard
          options={{
            id: `AIPuzzleBoard-${puzzle.id}`,
            position: currentFen,
            boardOrientation: orientation,
            allowDragging: !isSolved && !isChecking,
            canDragPiece: ({ piece }) => {
              if (isSolved || isChecking) return false;
              return piece.pieceType.startsWith(game.turn());
            },
            onPieceDrop: ({ sourceSquare, targetSquare }) => {
              if (!targetSquare) return false;
              return handleDrop(sourceSquare as Square, targetSquare as Square);
            },
            onSquareClick: ({ square }) => {
              if (square) handleSquareClick(square as Square);
            },
            squareStyles: customSquareStyles,
            boardStyle: {
              borderRadius: '8px',
            },
            showNotation: true,
          }}
        />

        {isChecking && (
          <div className="absolute inset-0 bg-slate-950/40 backdrop-blur-[1px] flex items-center justify-center z-10">
            <Loader2 className="w-6 h-6 text-amber-400 animate-spin" />
          </div>
        )}
      </div>

      {/* Status Alert */}
      {statusMessage && (
        <div
          className={`mt-2.5 w-full text-xs px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 transition animate-fade-in ${
            isError
              ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
              : isSolved
              ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-semibold'
              : 'bg-blue-500/15 text-blue-300 border border-blue-500/30'
          }`}
        >
          {isError ? (
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          ) : isSolved ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin shrink-0" />
          )}
          <span className="leading-tight">{statusMessage}</span>
        </div>
      )}

      {/* Hint Alert */}
      {hintText && (
        <div className="mt-2 w-full text-xs px-2.5 py-1.5 rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-start gap-1.5">
          <Lightbulb className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
          <span className="leading-tight">{hintText}</span>
        </div>
      )}

      {/* Control Buttons */}
      <div className="flex items-center justify-between gap-1 mt-3 w-full">
        <button
          onClick={handleReset}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white transition"
          title="Đặt lại thế cờ xuất phát"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Làm lại</span>
        </button>

        <button
          onClick={handleGetHint}
          disabled={isLoadingHint || isSolved}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-amber-300 bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 disabled:opacity-50 transition"
          title="Xem gợi ý chủ đề đòn chiến thuật"
        >
          {isLoadingHint ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Lightbulb className="w-3.5 h-3.5" />
          )}
          <span>Gợi ý</span>
        </button>

        <button
          onClick={handleViewSolution}
          disabled={isLoadingSolution}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-indigo-300 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/30 disabled:opacity-50 transition"
          title="Xem chuỗi nước đi lời giải"
        >
          {isLoadingSolution ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Eye className="w-3.5 h-3.5" />
          )}
          <span>{isSolutionRevealed ? 'Ẩn đáp án' : 'Xem đáp án'}</span>
        </button>
      </div>

      {/* Solution Moves Dropdown */}
      {isSolutionRevealed && solutionMoves && (
        <div className="mt-2.5 w-full bg-slate-950/80 border border-slate-800 rounded-xl p-2.5 text-xs animate-fade-in">
          <div className="font-bold text-amber-400 mb-1.5 flex items-center justify-between">
            <span>Chuỗi nước đi lời giải:</span>
            <span className="text-[10px] text-slate-400">({solutionMoves.length} nước)</span>
          </div>
          <div className="space-y-1 font-mono text-[11px] max-h-28 overflow-y-auto pr-1">
            {solutionMoves.map((m) => (
              <div key={m.move_order} className="flex items-center justify-between text-slate-300 bg-slate-900/60 px-2 py-1 rounded">
                <span>
                  <strong className={m.side === 'w' ? 'text-amber-300' : 'text-slate-400'}>
                    Nước {m.move_order} ({m.side === 'w' ? 'Trắng' : 'Đen'}):
                  </strong>{' '}
                  {m.san}
                </span>
                {m.explanation && (
                  <span className="text-slate-500 text-[10px] italic">{m.explanation}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Button: Nhờ AI giải thích */}
      {(isSolved || isSolutionRevealed) && (
        <div className="mt-2 w-full">
          <button
            onClick={handleRequestExplanation}
            disabled={isLoadingExplain}
            className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-semibold text-white bg-linear-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 transition shadow-md disabled:opacity-50"
          >
            {isLoadingExplain ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            )}
            <span>Nhờ AI giải thích chiến thuật</span>
          </button>
        </div>
      )}

      {/* AI Explanation Box */}
      {aiExplanation && (
        <div className="mt-2 w-full bg-indigo-950/40 border border-indigo-500/30 rounded-xl p-2.5 text-xs text-indigo-100 animate-fade-in">
          <div
            className="flex items-center justify-between font-bold text-indigo-300 cursor-pointer"
            onClick={() => setShowExplanation(!showExplanation)}
          >
            <div className="flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Phân tích từ Huấn luyện viên AI:</span>
            </div>
            {showExplanation ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </div>
          {showExplanation && (
            <p className="mt-1.5 text-slate-300 leading-relaxed text-[11px] whitespace-pre-wrap">
              {aiExplanation}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default PuzzleCard;
