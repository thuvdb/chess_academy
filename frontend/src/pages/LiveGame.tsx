import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { Chess } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import toast from 'react-hot-toast';

export default function LiveGame() {
  const { id, gameId } = useParams<{ id: string, gameId: string }>();
  const { accessToken: token } = useAuthStore();
  
  const [chess] = useState(new Chess());
  const [fen, setFen] = useState(chess.fen());
  const [isConnected, setIsConnected] = useState(false);
  const [gameOver, setGameOver] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);

  const [game, setGame] = useState<any>(null);
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    // Decode JWT to get user ID
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setUserId(payload.sub);
      } catch (e) {
        console.error("Failed to decode token");
      }
    }
  }, [token]);

  useEffect(() => {
    if (!id || !gameId) return;
    
    // Fetch game details to know players
    const fetchGame = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
        const res = await fetch(`${apiUrl}/tournaments/${id}/games`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const games = await res.json();
          const currentGame = games.find((g: any) => g.id === gameId);
          if (currentGame) setGame(currentGame);
        }
      } catch (e) {
        console.error("Failed to fetch game details", e);
      }
    };
    fetchGame();
  }, [id, gameId, token]);

  useEffect(() => {
    if (!gameId || !token) return;

    // Connect to WebSocket dynamically based on API URL
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    const wsBaseUrl = apiUrl.replace('http', 'ws').replace('/api', '');
    const wsUrl = `${wsBaseUrl}/ws/game/${gameId}?token=${token}`;
    
    console.log("Connecting to WS:", wsUrl);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      toast.success('Connected to live game');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'game_state') {
        chess.load(data.fen);
        setFen(chess.fen());
      } else if (data.type === 'move') {
        try {
          chess.move(data.san);
          setFen(chess.fen());
        } catch (e) {
          // Fallback if move fails, use FEN
          if (data.fen) {
            chess.load(data.fen);
            setFen(chess.fen());
          }
        }
      } else if (data.type === 'game_over') {
        setGameOver(data.result);
        toast(`Game Over: ${data.result}`, { icon: '🏆' });
      } else if (data.type === 'error') {
        toast.error(data.message);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket Error:", error);
    };

    ws.onclose = (event) => {
      console.log("WebSocket Closed:", event.code, event.reason);
      setIsConnected(false);
      if (event.code === 1008) {
        toast.error('Authentication failed. Please login again.');
      } else if (event.code !== 1000) {
        toast.error(`Disconnected from live game (Code: ${event.code})`);
      }
    };

    return () => {
      ws.close();
    };
  }, [gameId, token, chess]);

  const isWhite = game && userId === game.white_player_id;
  const isBlack = game && userId === game.black_player_id;
  const boardOrientation = isBlack ? 'black' : 'white';

  const onDrop = (sourceSquare: string, targetSquare: string): boolean => {
    if (!isConnected || gameOver) return false;
    
    // Prevent spectator or moving opponent's pieces
    const turn = chess.turn(); // 'w' or 'b'
    if (turn === 'w' && !isWhite) {
      toast.error("It is White's turn");
      return false;
    }
    if (turn === 'b' && !isBlack) {
      toast.error("It is Black's turn");
      return false;
    }

    let move;
    try {
      // Validate move locally first (without promotion)
      move = chess.move({
        from: sourceSquare,
        to: targetSquare,
      });
    } catch (e) {
      try {
        // Try with promotion
        move = chess.move({
          from: sourceSquare,
          to: targetSquare,
          promotion: 'q',
        });
      } catch (e2) {
        return false; // Invalid move
      }
    }

    if (move) {
      setFen(chess.fen());
      
      // Send move to server
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'move',
          san: move.san
        }));
      }
      return true;
    }
    return false;
  };

  return (
    <div className="p-6 max-w-5xl mx-auto text-slate-200 min-h-screen">
      <Link to={`/tournaments/${id}`} className="text-blue-400 hover:text-blue-300 text-sm font-medium mb-6 inline-flex items-center gap-1 transition-colors">
        ← Back to Tournament Details
      </Link>
      
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            Live Game 
            {isConnected ? (
              <span className="flex h-3 w-3 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
              </span>
            ) : (
              <span className="h-3 w-3 rounded-full bg-red-500"></span>
            )}
          </h1>
          <p className="text-slate-400 mt-2 font-mono text-sm">Game ID: {gameId}</p>
        </div>
        
        {gameOver && (
          <div className="bg-yellow-500/20 border border-yellow-500/50 text-yellow-400 px-6 py-2 rounded-xl font-bold tracking-wider">
            RESULT: {gameOver.replace('_', ' ').toUpperCase()}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 flex justify-center">
          <div className="w-full max-w-[600px] bg-slate-900 p-4 rounded-2xl border border-slate-800 shadow-2xl">
            {game ? (
              <Chessboard 
                id="BasicBoard"
                position={fen} 
                onPieceDrop={onDrop}
                boardOrientation={boardOrientation as 'white' | 'black'}
                darkSquareStyle={{ backgroundColor: '#475569' }}
                lightSquareStyle={{ backgroundColor: '#94a3b8' }}
                animationDurationInMs={300}
              />
            ) : (
              <div className="flex items-center justify-center h-[600px] text-slate-500">Loading game...</div>
            )}
          </div>
        </div>
        
        <div className="flex flex-col gap-6">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-xl">
            <h3 className="text-lg font-bold text-white mb-4">Players</h3>
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-600 shadow-inner flex items-center justify-center">
                  <div className="w-4 h-4 rounded-full bg-slate-900"></div>
                </div>
                <div>
                  <div className="text-sm text-slate-400">Black</div>
                  <div className="font-medium text-white">{game ? game.black_player_id.substring(0,8) : 'Player 2'} {isBlack ? '(You)' : ''}</div>
                </div>
              </div>
              
              <div className="flex justify-center py-2">
                <div className="w-px h-8 bg-slate-700"></div>
              </div>
              
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-slate-100 shadow-inner flex items-center justify-center">
                  <div className="w-4 h-4 rounded-full bg-white shadow-xs"></div>
                </div>
                <div>
                  <div className="text-sm text-slate-400">White</div>
                  <div className="font-medium text-white">{game ? game.white_player_id.substring(0,8) : 'Player 1'} {isWhite ? '(You)' : ''}</div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-xl flex-1">
            <h3 className="text-lg font-bold text-white mb-4">Move History</h3>
            <div className="bg-slate-950 rounded-xl p-4 h-[200px] overflow-y-auto text-sm font-mono text-slate-400">
              {/* Simple rendering of history */}
              {chess.history().map((move, i) => {
                if (i % 2 === 0) {
                  return (
                    <div key={i} className="flex gap-4 mb-2">
                      <span className="text-slate-600 w-6">{Math.floor(i/2) + 1}.</span>
                      <span className="text-white w-12">{move}</span>
                      <span className="text-white w-12">{chess.history()[i+1] || ''}</span>
                    </div>
                  );
                }
                return null;
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
