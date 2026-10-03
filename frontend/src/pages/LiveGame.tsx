import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { Chess } from 'chess.js';
import type { Square } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import toast from 'react-hot-toast';

interface GameInfo {
  white_player_id: string;
  black_player_id: string;
  white_player_name: string | null;
  black_player_name: string | null;
}

export default function LiveGame() {
  const { id, gameId } = useParams<{ id: string; gameId: string }>();
  const { accessToken: token, user } = useAuthStore();

  const chessRef = useRef(new Chess());
  const [fen, setFen] = useState(chessRef.current.fen());
  const [isConnected, setIsConnected] = useState(false);
  const [gameOver, setGameOver] = useState<string | null>(null);
  const [isCheckmate, setIsCheckmate] = useState(false);
  const [gameInfo, setGameInfo] = useState<GameInfo | null>(null);
  const [ready, setReady] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const [moveHistory, setMoveHistory] = useState<string[]>([]);
  const [inCheck, setInCheck] = useState(false);

  // Legal move highlighting
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [legalMoves, setLegalMoves] = useState<string[]>([]);

  // User ID
  const userId: string | null = user?.id ?? (() => {
    if (!token) return null;
    try { return JSON.parse(atob(token.split('.')[1])).sub ?? null; }
    catch { return null; }
  })();

  // Roles
  const isWhitePlayer = !!(gameInfo && userId && userId === gameInfo.white_player_id);
  const isBlackPlayer = !!(gameInfo && userId && userId === gameInfo.black_player_id);
  const isPlayer = isWhitePlayer || isBlackPlayer;
  const isAdmin = !!(user?.role && ['super_admin', 'admin', 'center_admin', 'teacher'].includes(user.role));

  // Board orientation — only flip for actual black player
  const boardOrientation: 'white' | 'black' = isBlackPlayer ? 'black' : 'white';

  // Can this user move? Only actual players (NOT admin spectators)
  const isMyTurn = (() => {
    if (!isPlayer || gameOver) return false;
    const turn = chessRef.current.turn();
    if (turn === 'w' && isWhitePlayer) return true;
    if (turn === 'b' && isBlackPlayer) return true;
    return false;
  })();

  // ---- Fetch game pairing ----
  useEffect(() => {
    if (!id || !gameId || !token) { setReady(true); return; }
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    fetch(`${apiUrl}/tournaments/${id}/games`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then((games: any[]) => {
        const g = games.find((x: any) => x.id === gameId);
        if (g) {
          setGameInfo({
            white_player_id: g.white_player_id,
            black_player_id: g.black_player_id,
            white_player_name: g.white_player_name || null,
            black_player_name: g.black_player_name || null,
          });
        }
      })
      .catch(e => console.error('Fetch games failed:', e))
      .finally(() => setReady(true));
  }, [id, gameId, token]);

  // ---- WebSocket ----
  useEffect(() => {
    if (!gameId || !token) return;
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    const wsBase = apiUrl.replace(/^http/, 'ws').replace('/api', '');
    const wsUrl = `${wsBase}/ws/game/${gameId}?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      toast.success('Connected to live game');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'game_state' || data.type === 'move') {
          if (data.fen) {
            chessRef.current.load(data.fen);
            setFen(data.fen);
          }
          if (data.history) setMoveHistory(data.history);
          if (data.in_check !== undefined) setInCheck(data.in_check);
          // Clear selection after move
          setSelectedSquare(null);
          setLegalMoves([]);
        } else if (data.type === 'game_over') {
          setGameOver(data.result);
          setIsCheckmate(!!data.is_checkmate);
          toast(`Game Over: ${data.result}`, { icon: '🏆' });
        } else if (data.type === 'error') {
          toast.error(data.message || 'Move rejected');
        }
      } catch (e) {
        console.error('[WS] parse error:', e);
      }
    };

    ws.onerror = () => toast.error('WebSocket connection error');
    ws.onclose = (ev) => {
      setIsConnected(false);
      if (ev.code === 1008) toast.error('Auth failed');
    };

    return () => { ws.close(1000, 'unmount'); };
  }, [gameId, token]);

  // ---- Compute legal moves for selected square ----
  const showLegalMoves = useCallback((square: string) => {
    if (!isMyTurn) return;
    const moves = chessRef.current.moves({ square: square as Square, verbose: true });
    if (moves.length > 0) {
      setSelectedSquare(square);
      setLegalMoves(moves.map(m => m.to));
    } else {
      setSelectedSquare(null);
      setLegalMoves([]);
    }
  }, [isMyTurn]);

  // ---- Square styles: legal move dots + check highlight ----
  const squareStyles = useMemo(() => {
    const styles: Record<string, React.CSSProperties> = {};

    // Highlight selected square
    if (selectedSquare) {
      styles[selectedSquare] = {
        backgroundColor: 'rgba(255, 255, 0, 0.4)',
      };
    }

    // Legal move dots
    for (const sq of legalMoves) {
      const hasPiece = chessRef.current.get(sq as Square);
      if (hasPiece) {
        // Capture: ring
        styles[sq] = {
          background: 'radial-gradient(circle, transparent 55%, rgba(0, 0, 0, 0.3) 55%)',
          borderRadius: '50%',
        };
      } else {
        // Empty square: dot
        styles[sq] = {
          background: 'radial-gradient(circle, rgba(0, 0, 0, 0.25) 25%, transparent 25%)',
        };
      }
    }

    // Check highlight: find king square and highlight red
    if (inCheck || chessRef.current.isCheck()) {
      const turn = chessRef.current.turn();
      const board = chessRef.current.board();
      for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
          const piece = board[r][c];
          if (piece && piece.type === 'k' && piece.color === turn) {
            const file = String.fromCharCode(97 + c);
            const rank = 8 - r;
            const kingSq = `${file}${rank}`;
            styles[kingSq] = {
              ...styles[kingSq],
              backgroundColor: 'rgba(255, 0, 0, 0.5)',
              boxShadow: 'inset 0 0 15px 5px rgba(255, 0, 0, 0.6)',
            };
          }
        }
      }
    }

    // Checkmate: grey out the king
    if (gameOver && isCheckmate) {
      const loserColor = chessRef.current.turn(); // turn = loser in checkmate
      const board = chessRef.current.board();
      for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
          const piece = board[r][c];
          if (piece && piece.type === 'k' && piece.color === loserColor) {
            const file = String.fromCharCode(97 + c);
            const rank = 8 - r;
            const kingSq = `${file}${rank}`;
            styles[kingSq] = {
              backgroundColor: 'rgba(128, 128, 128, 0.7)',
              boxShadow: 'inset 0 0 20px 10px rgba(0, 0, 0, 0.5)',
            };
          }
        }
      }
    }

    return styles;
  }, [selectedSquare, legalMoves, fen, inCheck, gameOver, isCheckmate]);

  // ---- Piece drop ----
  const handlePieceDrop = useCallback(
    ({ sourceSquare, targetSquare }: any): boolean => {
      if (!isConnected || gameOver || !isMyTurn) return false;

      const tryMove = (opts: any) => {
        try { return chessRef.current.move(opts); }
        catch { return null; }
      };

      let move = tryMove({ from: sourceSquare, to: targetSquare });
      if (!move) move = tryMove({ from: sourceSquare, to: targetSquare, promotion: 'q' });
      if (!move) return false;

      setFen(chessRef.current.fen());
      setMoveHistory([...chessRef.current.history()]);
      setSelectedSquare(null);
      setLegalMoves([]);

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'move',
          from: sourceSquare,
          to: targetSquare,
          promotion: move.promotion ?? null,
        }));
      }
      return true;
    },
    [isConnected, gameOver, isMyTurn]
  );

  // ---- Square click: show legal moves or make move ----
  const handleSquareClick = useCallback(
    ({ square }: any) => {
      if (!isMyTurn || gameOver) return;

      // If a piece is selected and clicked square is a legal move -> make the move
      if (selectedSquare && legalMoves.includes(square)) {
        handlePieceDrop({ piece: '', sourceSquare: selectedSquare, targetSquare: square });
        return;
      }

      // Otherwise select the piece on this square
      showLegalMoves(square);
    },
    [isMyTurn, gameOver, selectedSquare, legalMoves, handlePieceDrop, showLegalMoves]
  );

  // ---- Piece click: show legal moves ----
  const handlePieceClick = useCallback(
    ({ square }: any) => {
      if (!isMyTurn || gameOver) return;

      // If clicking own piece while another is selected, and this square is legal -> move
      if (selectedSquare && legalMoves.includes(square)) {
        handlePieceDrop({ piece: '', sourceSquare: selectedSquare, targetSquare: square });
        return;
      }

      showLegalMoves(square);
    },
    [isMyTurn, gameOver, selectedSquare, legalMoves, handlePieceDrop, showLegalMoves]
  );

  // Display names
  const whiteName = gameInfo?.white_player_name || (gameInfo ? `${gameInfo.white_player_id.substring(0, 8)}…` : '—');
  const blackName = gameInfo?.black_player_name || (gameInfo ? `${gameInfo.black_player_id.substring(0, 8)}…` : '—');

  const statusText = () => {
    if (!ready) return 'Loading...';
    if (isWhitePlayer) return `♟ You are playing White`;
    if (isBlackPlayer) return `♟ You are playing Black`;
    if (isAdmin) return '👁 Spectating (Admin)';
    return '👁 Spectating';
  };

  const turn = chessRef.current.turn();

  return (
    <div className="p-6 max-w-5xl mx-auto text-slate-200 min-h-screen">
      <Link
        to={`/tournaments/${id}`}
        className="text-blue-400 hover:text-blue-300 text-sm font-medium mb-6 inline-flex items-center gap-1"
      >
        ← Back to Tournament Details
      </Link>

      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            Live Game
            {isConnected ? (
              <span className="flex h-3 w-3 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500" />
              </span>
            ) : (
              <span className="h-3 w-3 rounded-full bg-red-500 inline-block" />
            )}
          </h1>
          <p className="text-slate-400 mt-1 text-sm">{statusText()}</p>
        </div>

        {gameOver && (
          <div className={`px-6 py-2 rounded-xl font-bold border ${
            isCheckmate
              ? 'bg-red-500/20 border-red-500/50 text-red-400'
              : 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400'
          }`}>
            {isCheckmate ? '♚ CHECKMATE' : 'RESULT'}: {gameOver}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Board */}
        <div className="lg:col-span-2 flex justify-center">
          <div className="w-full max-w-[600px] bg-slate-900 p-4 rounded-2xl border border-slate-800 shadow-2xl">
            {/* Top player label (opponent from viewer's perspective) */}
            <div className="flex items-center gap-2 mb-2 px-1">
              <div className={`w-3 h-3 rounded-full ${boardOrientation === 'white' ? 'bg-slate-900 border border-slate-600' : 'bg-white border border-slate-300'}`} />
              <span className="text-sm font-semibold text-slate-300">
                {boardOrientation === 'white' ? blackName : whiteName}
              </span>
              {((boardOrientation === 'white' && turn === 'b') || (boardOrientation === 'black' && turn === 'w')) && !gameOver && (
                <span className="text-xs text-yellow-400 animate-pulse">● Thinking…</span>
              )}
            </div>

            {ready ? (
              <Chessboard
                key={`board-${boardOrientation}`}
                options={{
                  id: 'LiveBoard',
                  position: fen,
                  boardOrientation: boardOrientation,
                  allowDragging: isPlayer && !gameOver,
                  onPieceDrop: handlePieceDrop,
                  onPieceClick: handlePieceClick,
                  onSquareClick: handleSquareClick,
                  squareStyles: squareStyles,
                  darkSquareStyle: { backgroundColor: '#475569' },
                  lightSquareStyle: { backgroundColor: '#94a3b8' },
                  animationDurationInMs: 200,
                  showNotation: true,
                }}
              />
            ) : (
              <div className="flex items-center justify-center h-[560px] text-slate-500 animate-pulse">
                Loading game…
              </div>
            )}

            {/* Bottom player label (viewer) */}
            <div className="flex items-center gap-2 mt-2 px-1">
              <div className={`w-3 h-3 rounded-full ${boardOrientation === 'white' ? 'bg-white border border-slate-300' : 'bg-slate-900 border border-slate-600'}`} />
              <span className="text-sm font-semibold text-slate-300">
                {boardOrientation === 'white' ? whiteName : blackName}
                {isPlayer && <span className="ml-1 text-green-400 text-xs">(You)</span>}
              </span>
              {((boardOrientation === 'white' && turn === 'w') || (boardOrientation === 'black' && turn === 'b')) && !gameOver && (
                <span className="text-xs text-yellow-400 animate-pulse">● Your turn</span>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="flex flex-col gap-6">
          {/* Players */}
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-xl">
            <h3 className="text-lg font-bold text-white mb-4">Players</h3>
            <div className="space-y-4">
              {/* Black */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-slate-800 border-2 border-slate-600 flex items-center justify-center shrink-0">
                  <div className="w-4 h-4 rounded-full bg-slate-950" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-slate-500 uppercase tracking-wider">Black</div>
                  <div className="font-semibold text-white truncate">
                    {blackName}
                    {isBlackPlayer && <span className="ml-1 text-green-400 text-xs">(You)</span>}
                  </div>
                </div>
                {turn === 'b' && !gameOver && (
                  <span className="text-xs text-yellow-400 animate-pulse shrink-0">● Moving</span>
                )}
              </div>
              <div className="flex justify-center"><div className="w-px h-6 bg-slate-700" /></div>
              {/* White */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-slate-100 border-2 border-slate-300 flex items-center justify-center shrink-0">
                  <div className="w-4 h-4 rounded-full bg-white shadow" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-slate-500 uppercase tracking-wider">White</div>
                  <div className="font-semibold text-white truncate">
                    {whiteName}
                    {isWhitePlayer && <span className="ml-1 text-green-400 text-xs">(You)</span>}
                  </div>
                </div>
                {turn === 'w' && !gameOver && (
                  <span className="text-xs text-yellow-400 animate-pulse shrink-0">● Moving</span>
                )}
              </div>
            </div>
          </div>

          {/* Move History */}
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-xl flex-1">
            <h3 className="text-lg font-bold text-white mb-4">
              Move History
              <span className="text-xs text-slate-500 ml-2 font-normal">
                {moveHistory.length > 0 ? `${Math.ceil(moveHistory.length / 2)} moves` : ''}
              </span>
            </h3>
            <div className="bg-slate-950 rounded-xl p-4 h-[260px] overflow-y-auto text-sm font-mono text-slate-400 scrollbar-thin">
              {moveHistory.length === 0 ? (
                <div className="text-center text-slate-600 mt-8 text-xs">
                  {gameOver ? 'No moves recorded' : 'Waiting for first move…'}
                </div>
              ) : (
                moveHistory.map((mv, i) => {
                  if (i % 2 !== 0) return null;
                  const moveNum = Math.floor(i / 2) + 1;
                  const isLast = i >= moveHistory.length - 2;
                  return (
                    <div key={i} className={`flex gap-3 mb-1.5 px-2 py-0.5 rounded ${isLast ? 'bg-slate-800/50' : ''}`}>
                      <span className="text-slate-600 w-8 shrink-0">{moveNum}.</span>
                      <span className="text-white w-16 font-medium">{mv}</span>
                      <span className="text-slate-300 w-16">{moveHistory[i + 1] ?? ''}</span>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
