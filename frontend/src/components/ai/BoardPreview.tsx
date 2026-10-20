import React, { useState, useEffect } from 'react';
import { Chessboard } from 'react-chessboard';
import { Play, Pause, SkipBack, SkipForward, ChevronLeft, ChevronRight } from 'lucide-react';

export interface BoardData {
  initial_fen: string;
  caption: string;
  total_moves: number;
  moves: string[];
  positions: string[];
  steps?: Array<{ move_number: number; san: string; fen: string }>;
  is_checkmate?: boolean;
  is_stalemate?: boolean;
}

interface BoardPreviewProps {
  data: BoardData;
}

export const BoardPreview: React.FC<BoardPreviewProps> = ({ data }) => {
  const positions = data.positions || [data.initial_fen];
  const moves = data.moves || [];
  const maxStep = positions.length - 1;

  const [currentStep, setCurrentStep] = useState<number>(maxStep);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // Auto-play moves sequence
  useEffect(() => {
    let timer: any = null;
    if (isPlaying) {
      timer = setInterval(() => {
        setCurrentStep((prev) => {
          if (prev >= maxStep) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1200);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlaying, maxStep]);

  const currentFen = positions[currentStep] || data.initial_fen;
  const currentSan = currentStep > 0 && currentStep <= moves.length ? moves[currentStep - 1] : null;

  return (
    <div className="mt-3 p-3 bg-slate-900/90 border border-slate-700/80 rounded-xl max-w-sm shadow-xl flex flex-col items-center">
      {/* Caption & Status */}
      {data.caption && (
        <div className="text-xs font-semibold text-amber-400 mb-2 text-center px-1 leading-snug">
          {data.caption}
        </div>
      )}

      {/* Mini Interactive Chessboard */}
      <div className="w-64 h-64 relative rounded-lg overflow-hidden border border-slate-800 shadow-md">
        <Chessboard
          options={{
            position: currentFen,
            boardOrientation: 'white',
            allowDragging: false,
            boardStyle: {
              borderRadius: '6px',
            },
          }}
        />
      </div>

      {/* Current Step Info */}
      <div className="mt-2 text-xs text-slate-300 font-mono flex items-center justify-between w-full px-1">
        <span>
          Nước: <strong className="text-white">{currentStep}/{maxStep}</strong>
        </span>
        {currentSan ? (
          <span className="px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold border border-blue-500/30">
            {currentSan}
          </span>
        ) : (
          <span className="text-slate-500 text-[11px] italic">Thế xuất phát</span>
        )}
      </div>

      {/* Interactive Playback Controls */}
      <div className="flex items-center justify-center gap-1.5 mt-2.5 w-full bg-slate-800/80 py-1.5 px-2 rounded-lg border border-slate-700/50">
        <button
          onClick={() => {
            setIsPlaying(false);
            setCurrentStep(0);
          }}
          disabled={currentStep === 0}
          className="p-1.5 text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400 rounded transition"
          title="Về nước đầu tiên"
        >
          <SkipBack className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={() => {
            setIsPlaying(false);
            setCurrentStep((prev) => Math.max(0, prev - 1));
          }}
          disabled={currentStep === 0}
          className="p-1.5 text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400 rounded transition"
          title="Lùi 1 nước"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <button
          onClick={() => {
            if (currentStep >= maxStep) {
              setCurrentStep(0);
              setIsPlaying(true);
            } else {
              setIsPlaying(!isPlaying);
            }
          }}
          className={`px-3 py-1 rounded text-xs font-semibold flex items-center gap-1 transition ${
            isPlaying
              ? 'bg-amber-600 hover:bg-amber-500 text-white'
              : 'bg-blue-600 hover:bg-blue-500 text-white'
          }`}
        >
          {isPlaying ? (
            <>
              <Pause className="w-3 h-3" /> Tạm dừng
            </>
          ) : (
            <>
              <Play className="w-3 h-3" /> Phát
            </>
          )}
        </button>

        <button
          onClick={() => {
            setIsPlaying(false);
            setCurrentStep((prev) => Math.min(maxStep, prev + 1));
          }}
          disabled={currentStep >= maxStep}
          className="p-1.5 text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400 rounded transition"
          title="Tiến 1 nước"
        >
          <ChevronRight className="w-4 h-4" />
        </button>

        <button
          onClick={() => {
            setIsPlaying(false);
            setCurrentStep(maxStep);
          }}
          disabled={currentStep >= maxStep}
          className="p-1.5 text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400 rounded transition"
          title="Đến nước cuối"
        >
          <SkipForward className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Move Pills Bar */}
      {moves.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2.5 max-h-20 overflow-y-auto w-full px-0.5 justify-start">
          {moves.map((m, idx) => {
            const stepNum = idx + 1;
            const isSelected = currentStep === stepNum;
            const isWhite = idx % 2 === 0;
            const movePrefix = isWhite ? `${Math.floor(idx / 2) + 1}.` : '';

            return (
              <button
                key={idx}
                onClick={() => {
                  setIsPlaying(false);
                  setCurrentStep(stepNum);
                }}
                className={`text-[10px] px-1.5 py-0.5 rounded transition font-mono ${
                  isSelected
                    ? 'bg-blue-600 text-white font-bold ring-1 ring-blue-400'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {movePrefix}
                {m}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default BoardPreview;
