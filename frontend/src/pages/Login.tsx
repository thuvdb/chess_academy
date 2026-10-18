import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogIn, Mail, Lock, Eye, EyeOff } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../lib/api';
import { useAuthStore } from '../store/authStore';

export default function Login() {
  const [rememberMe, setRememberMe] = useState(() => {
    return localStorage.getItem('cams_remember_me') === 'true';
  });
  const [email, setEmail] = useState(() => {
    return localStorage.getItem('cams_remember_email') || '';
  });
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setTokens, setUser } = useAuthStore();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      // 1. Get tokens
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      
      const tokenRes = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      setTokens(tokenRes.data.access_token, tokenRes.data.refresh_token);

      // Save or clear remember me credentials in localStorage
      if (rememberMe) {
        localStorage.setItem('cams_remember_me', 'true');
        localStorage.setItem('cams_remember_email', email);
      } else {
        localStorage.removeItem('cams_remember_me');
        localStorage.removeItem('cams_remember_email');
      }
      
      // 2. Fetch user profile
      const userRes = await api.get('/auth/me');
      setUser(userRes.data);
      
      toast.success('Logged in successfully!');
      navigate('/');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 overflow-hidden relative">
      {/* Ambient background light */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none"></div>

      <div className="relative z-10 w-full max-w-[400px] bg-slate-900/40 backdrop-blur-2xl border border-white/10 rounded-[2rem] shadow-2xl overflow-hidden flex flex-col">
        <form onSubmit={handleLogin} className="flex flex-col w-full h-full">
          
          {/* PART 1: Top (Welcome & Email) */}
          <div className="p-6 pb-4 flex flex-col gap-4">
            <div className="text-center mb-2">
              <h2 className="text-3xl font-bold text-transparent bg-clip-text bg-linear-to-r from-blue-400 to-purple-400 tracking-tight">CAMS</h2>
              <p className="text-slate-400 text-sm mt-1">Authenticate your session</p>
            </div>
            
            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-400 uppercase tracking-widest ml-1">Email</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-black/40 border border-white/5 text-white rounded-xl py-3 pl-12 pr-4 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all placeholder:text-slate-600"
                  placeholder="name@example.com"
                />
              </div>
            </div>
          </div>

          {/* PART 2: Middle (Chessboard with LED border) */}
          <div className="relative w-full aspect-square max-w-[260px] mx-auto my-2 rounded-2xl overflow-hidden p-[2px] shadow-[0_0_40px_rgba(59,130,246,0.15)] flex-shrink-0">
            {/* LED Running Border - Blue */}
            <div className="absolute inset-[-50%] animate-[spin_4s_linear_infinite] bg-[conic-gradient(from_0deg,transparent_0_270deg,#3b82f6_360deg)]"></div>
            {/* LED Running Border - Purple (Reverse) */}
            <div className="absolute inset-[-50%] animate-[spin_4s_linear_infinite_reverse] bg-[conic-gradient(from_0deg,transparent_0_270deg,#a855f7_360deg)]"></div>
            
            {/* Inner Transparent Chessboard */}
            <div className="absolute inset-[2px] bg-slate-950/80 backdrop-blur-xl rounded-[14px] z-10 flex items-center justify-center overflow-hidden">
              {/* 8x8 Chessboard Grid - Using 25% background size which maps exactly to an 8x8 layout across 100% */}
              <div 
                className="absolute inset-0 opacity-20" 
                style={{ 
                  backgroundImage: 'repeating-conic-gradient(#ffffff 0% 25%, transparent 0% 50%)', 
                  backgroundSize: '25% 25%' 
                }}
              ></div>
              
              {/* Center Decoration */}
              <div className="w-20 h-20 bg-blue-500/20 rounded-full blur-xl absolute pointer-events-none"></div>
              <LogIn className="w-12 h-12 text-blue-400/80 z-20 drop-shadow-[0_0_15px_rgba(59,130,246,0.5)] pointer-events-none" />
            </div>
          </div>

          {/* PART 3: Bottom (Password & Submit) */}
          <div className="p-6 pt-4 flex flex-col gap-5">
            <div className="space-y-1">
              <div className="flex items-center justify-between ml-1">
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Password</label>
                <a href="#" className="text-xs text-blue-400 hover:text-blue-300 transition-colors">Forgot?</a>
              </div>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-black/40 border border-white/5 text-white rounded-xl py-3 pl-12 pr-12 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all placeholder:text-slate-600"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Remember Me Checkbox */}
            <div className="flex items-center justify-between ml-1">
              <label className="flex items-center gap-2.5 cursor-pointer select-none group">
                <input
                  type="checkbox"
                  id="remember-me"
                  name="remember-me"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded border border-white/20 bg-black/50 text-blue-600 accent-blue-600 focus:ring-blue-500/50 focus:ring-offset-0 cursor-pointer transition-colors"
                />
                <span className="text-xs text-slate-400 group-hover:text-slate-300 transition-colors">
                  Nhớ mật khẩu (Remember me)
                </span>
              </label>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-linear-to-r from-blue-600 to-purple-600 text-white font-bold rounded-xl py-3.5 hover:shadow-[0_0_20px_rgba(59,130,246,0.4)] active:scale-[0.98] transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? <span className="animate-spin h-5 w-5 border-2 border-white/30 border-t-white rounded-full"></span> : 'Sign In'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
