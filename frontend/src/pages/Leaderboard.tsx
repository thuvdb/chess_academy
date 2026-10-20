import { useState, useEffect } from 'react';
import {
  Trophy, Medal, Star
} from 'lucide-react';
import toast from 'react-hot-toast';
import { getLeaderboard, type LeaderboardUser } from '../lib/puzzleApi';
import { resolveMediaUrl } from '../config';

export default function Leaderboard() {
  const [users, setUsers] = useState<LeaderboardUser[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await getLeaderboard();
        setUsers(data);
      } catch {
        toast.error('Failed to load leaderboard');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const getRankBadge = (index: number) => {
    if (index === 0) {
      return (
        <span className="w-8 h-8 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/40 flex items-center justify-center font-bold text-sm shadow-lg shadow-amber-500/20">
          <Trophy className="w-4 h-4 fill-current" />
        </span>
      );
    }
    if (index === 1) {
      return (
        <span className="w-8 h-8 rounded-full bg-slate-300/20 text-slate-300 border border-slate-300/40 flex items-center justify-center font-bold text-sm">
          <Medal className="w-4 h-4 fill-current" />
        </span>
      );
    }
    if (index === 2) {
      return (
        <span className="w-8 h-8 rounded-full bg-amber-700/20 text-amber-600 border border-amber-700/40 flex items-center justify-center font-bold text-sm">
          <Medal className="w-4 h-4 fill-current" />
        </span>
      );
    }
    return (
      <span className="w-8 h-8 rounded-full bg-slate-800 text-slate-400 border border-slate-700 flex items-center justify-center font-semibold text-xs">
        #{index + 1}
      </span>
    );
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
          <Trophy className="w-7 h-7 text-amber-400" />
          Bảng xếp hạng Học sinh
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Vinh danh các học viên có điểm tích lũy và Puzzle Rating cao nhất học viện
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-24">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
        </div>
      ) : users.length === 0 ? (
        <div className="bg-slate-800/40 border border-slate-700/40 rounded-2xl p-12 text-center">
          <Trophy className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-slate-300">Chưa có dữ liệu bảng xếp hạng</h3>
          <p className="text-slate-500 text-sm mt-1">
            Bảng xếp hạng sẽ cập nhật ngay khi các học viên hoàn thành bài tập giải cờ.
          </p>
        </div>
      ) : (
        <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl overflow-hidden shadow-xl">
          <div className="p-4 bg-slate-900/60 border-b border-slate-700/60 grid grid-cols-12 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            <div className="col-span-1 text-center">Hạng</div>
            <div className="col-span-6">Học sinh</div>
            <div className="col-span-2 text-center">Bài đã giải</div>
            <div className="col-span-3 text-right">Puzzle Rating & Điểm</div>
          </div>

          <div className="divide-y divide-slate-700/40">
            {users.map((user, idx) => (
              <div
                key={user.student_id}
                className="p-4 grid grid-cols-12 items-center hover:bg-slate-700/30 transition text-sm"
              >
                <div className="col-span-1 flex justify-center">
                  {getRankBadge(idx)}
                </div>
                <div className="col-span-6 flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-slate-700 flex items-center justify-center font-bold text-white border border-slate-600 shrink-0">
                    {user.avatar_url ? (
                      <img src={resolveMediaUrl(user.avatar_url)} alt="" className="w-full h-full rounded-full object-cover" />
                    ) : (
                      user.full_name.charAt(0).toUpperCase()
                    )}
                  </div>
                  <div>
                    <h4 className="font-semibold text-white">{user.full_name}</h4>
                    <span className="text-xs text-slate-400">Học viên</span>
                  </div>
                </div>
                <div className="col-span-2 text-center text-slate-300 font-mono">
                  {user.puzzles_solved} bài
                </div>
                <div className="col-span-3 text-right">
                  <div className="text-amber-400 font-bold flex items-center justify-end gap-1">
                    <Star className="w-3.5 h-3.5 fill-current" />
                    {user.rating} Elo
                  </div>
                  <div className="text-xs text-indigo-400 font-medium">
                    +{user.points} điểm tích lũy
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
