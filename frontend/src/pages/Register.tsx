import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { UserPlus, Mail, Lock, User, ShieldAlert, ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../lib/api';

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [checkingConfig, setCheckingConfig] = useState(true);
  const [allowRegister, setAllowRegister] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    async function fetchAuthConfig() {
      try {
        const res = await api.get('/auth/config');
        setAllowRegister(Boolean(res.data?.allow_public_register));
      } catch (err) {
        // Fallback default secure: false
        setAllowRegister(false);
      } finally {
        setCheckingConfig(false);
      }
    }
    fetchAuthConfig();
  }, []);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post('/auth/register', {
        email,
        password,
        full_name: fullName,
      });
      toast.success('Đăng ký thành công! Vui lòng đăng nhập.');
      navigate('/login');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Đăng ký thất bại');
    } finally {
      setLoading(false);
    }
  };

  if (checkingConfig) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="animate-spin h-8 w-8 border-4 border-purple-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      {/* Background Decor */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0">
        <div className="absolute top-[20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-purple-600/20 blur-[120px]"></div>
        <div className="absolute bottom-[-20%] left-[-10%] w-[40%] h-[40%] rounded-full bg-blue-600/20 blur-[100px]"></div>
      </div>

      <div className="relative z-10 w-full max-w-md bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-8 shadow-2xl">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-linear-to-tr from-purple-500 to-blue-600 mb-4 shadow-lg shadow-purple-500/30">
            {allowRegister ? (
              <UserPlus className="w-8 h-8 text-white" />
            ) : (
              <ShieldAlert className="w-8 h-8 text-amber-300" />
            )}
          </div>
          <h2 className="text-3xl font-bold text-white tracking-tight">
            {allowRegister ? 'Tạo Tài Khoản' : 'Đăng Ký Đã Khóa'}
          </h2>
          <p className="text-slate-400 mt-2 text-sm">
            {allowRegister
              ? 'Tham gia CAMS để nâng cao kỹ năng cờ vua'
              : 'Hệ thống CAMS áp dụng mô hình quản trị đa trung tâm có kiểm soát.'}
          </p>
        </div>

        {!allowRegister ? (
          <div className="space-y-6">
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-5 text-amber-200 text-sm leading-relaxed">
              <p className="font-semibold text-amber-300 mb-1">Thông báo bảo mật</p>
              Đăng ký công khai hiện đang tắt. Tài khoản của Học viên, Giáo viên và Phụ huynh được tạo và cấp quyền trực tiếp bởi <strong>Quản trị viên Trung tâm</strong>.
            </div>

            <Link
              to="/login"
              className="w-full bg-linear-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-xl py-3.5 hover:opacity-90 active:scale-[0.98] transition-all flex items-center justify-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" /> Quay lại Đăng nhập
            </Link>
          </div>
        ) : (
          <form onSubmit={handleRegister} className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-300 ml-1">Họ và Tên</label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full bg-slate-800/50 border border-slate-700 text-white rounded-xl py-3 pl-12 pr-4 focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all placeholder:text-slate-500"
                  placeholder="Nguyễn Văn A"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-300 ml-1">Email</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-800/50 border border-slate-700 text-white rounded-xl py-3 pl-12 pr-4 focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all placeholder:text-slate-500"
                  placeholder="name@example.com"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-slate-300 ml-1">Mật khẩu</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-800/50 border border-slate-700 text-white rounded-xl py-3 pl-12 pr-4 focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all placeholder:text-slate-500"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-linear-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-xl py-3.5 mt-6 hover:opacity-90 active:scale-[0.98] transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <span className="animate-spin h-5 w-5 border-2 border-white/30 border-t-white rounded-full"></span>
              ) : (
                'Đăng Ký'
              )}
            </button>

            <p className="text-center text-slate-400 mt-8 text-sm">
              Đã có tài khoản?{' '}
              <Link to="/login" className="text-purple-400 hover:text-purple-300 font-medium transition-colors">
                Đăng nhập
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}

