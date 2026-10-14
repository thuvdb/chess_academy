import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import api from '../lib/api';
import {
  Search,
  Users,
  Shield,
  User,
  Plus,
  X,
  Building,
  Mail,
  Lock,
  Phone,
  UserCheck,
  Loader2,
  Edit2,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';

interface Member {
  id: string;
  email: string;
  full_name: string;
  username: string | null;
  role: string;
  phone?: string | null;
  center_id: string | null;
  center_name?: string | null;
  avatar_url: string | null;
  is_active?: boolean;
}

interface CenterOption {
  id: string;
  name: string;
  address?: string | null;
  phone?: string | null;
}

const Members = () => {
  const { user } = useAuthStore();
  const role = user?.role;
  const isSuperAdmin = role === 'super_admin';
  const isCenterAdmin = role === 'center_admin' || role === 'admin';
  const canManage = isSuperAdmin || isCenterAdmin;

  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  // Centers list for selection (super_admin)
  const [centers, setCenters] = useState<CenterOption[]>([]);

  // Add Member Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [formFullName, setFormFullName] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formPassword, setFormPassword] = useState('');
  const [formPhone, setFormPhone] = useState('');
  const [formRole, setFormRole] = useState(isSuperAdmin ? 'center_admin' : 'student');
  const [formCenterId, setFormCenterId] = useState(user?.center_id || '');

  // Edit Member Modal State
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<Member | null>(null);
  const [editFullName, setEditFullName] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editRole, setEditRole] = useState('');
  const [editCenterId, setEditCenterId] = useState('');
  const [editPassword, setEditPassword] = useState('');
  const [editIsActive, setEditIsActive] = useState(true);
  const [updating, setUpdating] = useState(false);

  const fetchMembers = async (searchQuery = '') => {
    try {
      setLoading(true);
      const { data } = await api.get(`/users/members?search=${encodeURIComponent(searchQuery)}&limit=100`);
      setMembers(data);
    } catch (error) {
      toast.error('Không thể tải danh sách thành viên');
    } finally {
      setLoading(false);
    }
  };

  const fetchCenters = async () => {
    try {
      const { data } = await api.get('/users/centers');
      setCenters(data);
      if (data.length > 0 && !formCenterId) {
        setFormCenterId(data[0].id);
      }
    } catch (error) {
      console.error('Failed to load centers', error);
    }
  };

  useEffect(() => {
    if (canManage) {
      fetchMembers();
      fetchCenters();
    }
  }, [user]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchMembers(search);
  };

  // Open Create Modal
  const handleOpenModal = () => {
    setFormFullName('');
    setFormEmail('');
    setFormPassword('');
    setFormPhone('');
    setFormRole(isSuperAdmin ? 'center_admin' : 'teacher');
    setFormCenterId(user?.center_id || (centers[0]?.id || ''));
    setIsModalOpen(true);
    fetchCenters();
  };

  // Submit Create Member
  const handleCreateMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formFullName.trim() || !formEmail.trim() || !formPassword.trim()) {
      toast.error('Vui lòng điền đầy đủ các thông tin bắt buộc');
      return;
    }
    if (formPassword.length < 6) {
      toast.error('Mật khẩu phải có ít nhất 6 ký tự');
      return;
    }

    const targetCenterId = isSuperAdmin ? formCenterId : user?.center_id;
    if (formRole !== 'super_admin' && !targetCenterId) {
      toast.error('Vui lòng chọn cơ sở/trung tâm cho thành viên này');
      return;
    }

    setCreating(true);
    try {
      const payload: Record<string, any> = {
        full_name: formFullName.trim(),
        email: formEmail.trim().toLowerCase(),
        password: formPassword,
        role: formRole,
        phone: formPhone.trim() || undefined,
      };

      if (formRole !== 'super_admin') {
        payload.center_id = targetCenterId;
      }

      await api.post('/users', payload);
      toast.success(
        formRole === 'center_admin'
          ? 'Đã tạo tài khoản Admin trung tâm thành công!'
          : 'Đã thêm thành viên mới thành công!'
      );
      setIsModalOpen(false);
      await fetchMembers(search);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Lỗi khi tạo thành viên');
    } finally {
      setCreating(false);
    }
  };

  // Open Edit Modal
  const handleOpenEditModal = (member: Member) => {
    setEditingMember(member);
    setEditFullName(member.full_name || '');
    setEditEmail(member.email || '');
    setEditPhone(member.phone || '');
    setEditRole(member.role);
    setEditCenterId(member.center_id || '');
    setEditPassword('');
    setEditIsActive(member.is_active ?? true);
    setIsEditModalOpen(true);
    fetchCenters();
  };

  // Submit Edit Member
  const handleUpdateMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMember) return;
    if (!editFullName.trim() || !editEmail.trim()) {
      toast.error('Vui lòng điền đầy đủ họ tên và email');
      return;
    }
    if (editPassword && editPassword.length < 6) {
      toast.error('Mật khẩu mới phải có ít nhất 6 ký tự');
      return;
    }

    setUpdating(true);
    try {
      const payload: Record<string, any> = {
        full_name: editFullName.trim(),
        email: editEmail.trim().toLowerCase(),
        role: editRole,
        phone: editPhone.trim() || undefined,
        is_active: editIsActive,
      };

      if (editPassword) {
        payload.password = editPassword;
      }

      if (isSuperAdmin && editRole !== 'super_admin') {
        payload.center_id = editCenterId || undefined;
      }

      await api.patch(`/users/${editingMember.id}`, payload);
      toast.success('Cập nhật thông tin thành viên thành công!');
      setIsEditModalOpen(false);
      await fetchMembers(search);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Lỗi khi cập nhật thành viên');
    } finally {
      setUpdating(false);
    }
  };

  // Determine if caller can edit a given member
  const canEditMember = (target: Member) => {
    if (isSuperAdmin) return true;
    if (isCenterAdmin) {
      const isTargetAdmin =
        target.role === 'super_admin' ||
        target.role === 'center_admin' ||
        target.role === 'admin';
      return !isTargetAdmin && target.center_id === user?.center_id;
    }
    return false;
  };

  if (!canManage) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-slate-400">Bạn không có quyền truy cập trang này.</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Users className="w-6 h-6 text-amber-500" />
              Quản lý thành viên & Nhân sự
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
              {isSuperAdmin
                ? 'Toàn hệ thống'
                : user?.center_name || 'Cơ sở trực thuộc'}
            </span>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            {isSuperAdmin
              ? 'Super Admin có toàn quyền tạo, sửa, gán cơ sở cho Admin trung tâm, Giáo viên và Học sinh.'
              : `Admin trung tâm quản lý, thêm mới và chỉnh sửa thông tin Giáo viên, Học sinh cho ${user?.center_name || 'cơ sở'}.`}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
          {/* Search bar */}
          <form onSubmit={handleSearch} className="relative w-full sm:w-64">
            <input
              type="text"
              placeholder="Tìm theo tên, email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-white text-xs placeholder:text-slate-500 focus:outline-none focus:border-amber-500"
            />
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          </form>

          {/* Add member button */}
          <button
            onClick={handleOpenModal}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-all shadow-lg shadow-amber-500/20 shrink-0"
          >
            <Plus className="w-4 h-4" />
            {isSuperAdmin ? 'Tạo tài khoản / Admin' : 'Thêm thành viên'}
          </button>
        </div>
      </div>

      {/* Members Table */}
      <div className="bg-slate-900/60 rounded-xl border border-slate-800 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-slate-400 text-[10px] uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="px-5 py-3 font-semibold">Thành viên</th>
                <th className="px-5 py-3 font-semibold">Email & Liên hệ</th>
                <th className="px-5 py-3 font-semibold">Vai trò</th>
                <th className="px-5 py-3 font-semibold">Cơ sở trực thuộc</th>
                <th className="px-5 py-3 font-semibold text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-400">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
                      <span>Đang tải danh sách thành viên...</span>
                    </div>
                  </td>
                </tr>
              ) : members.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-400">
                    Chưa có thành viên nào phù hợp với tìm kiếm.
                  </td>
                </tr>
              ) : (
                members.map((member) => (
                  <tr key={member.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        {member.avatar_url ? (
                          <img
                            src={member.avatar_url}
                            alt="Avatar"
                            className="w-9 h-9 rounded-full object-cover border border-slate-700"
                          />
                        ) : (
                          <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 font-bold">
                            {member.full_name?.charAt(0)?.toUpperCase() || <User className="w-4 h-4 text-slate-400" />}
                          </div>
                        )}
                        <div>
                          <div className="font-semibold text-white text-sm flex items-center gap-2">
                            <span>{member.full_name}</span>
                            {member.is_active === false && (
                              <span className="px-1.5 py-0.2 rounded text-[10px] bg-rose-500/20 text-rose-400 border border-rose-500/30">
                                Đã khóa
                              </span>
                            )}
                          </div>
                          {member.username && (
                            <div className="text-[11px] text-slate-400">@{member.username}</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="text-slate-300 font-medium">{member.email}</div>
                      {member.phone && <div className="text-[11px] text-slate-500">{member.phone}</div>}
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                          member.role === 'super_admin'
                            ? 'bg-purple-500/15 text-purple-400 border-purple-500/30'
                            : member.role === 'center_admin' || member.role === 'admin'
                            ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                            : member.role === 'teacher'
                            ? 'bg-blue-500/15 text-blue-400 border-blue-500/30'
                            : member.role === 'parent'
                            ? 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30'
                            : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                        }`}
                      >
                        {member.role === 'super_admin' || member.role === 'center_admin' || member.role === 'admin' ? (
                          <Shield className="w-3 h-3" />
                        ) : (
                          <UserCheck className="w-3 h-3" />
                        )}
                        {member.role === 'super_admin'
                          ? 'Super Admin'
                          : member.role === 'center_admin' || member.role === 'admin'
                          ? 'Admin trung tâm'
                          : member.role === 'teacher'
                          ? 'Giáo viên'
                          : member.role === 'parent'
                          ? 'Phụ huynh'
                          : 'Học sinh'}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      {member.role === 'super_admin' ? (
                        <span className="text-slate-400 italic">Toàn hệ thống</span>
                      ) : (
                        <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700">
                          {member.center_name ||
                            centers.find((c) => c.id === member.center_id)?.name ||
                            (member.center_id ? `Cơ sở ${member.center_id.slice(0, 8)}...` : 'Chưa gán')}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      {canEditMember(member) && (
                        <button
                          onClick={() => handleOpenEditModal(member)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-400 hover:text-amber-300 text-xs font-semibold border border-slate-700 hover:border-amber-500/40 transition-all shadow-sm"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                          Sửa
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal 1: Tạo thành viên */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/40">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center">
                  <Plus className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">
                    {isSuperAdmin ? 'Tạo tài khoản người dùng' : 'Thêm thành viên mới'}
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    {isSuperAdmin
                      ? 'Super Admin có thể tạo Admin trung tâm, Giáo viên, Học sinh'
                      : `Tạo tài khoản giáo viên, học sinh cho ${user?.center_name || 'cơ sở'}`}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateMember} className="p-6 space-y-4 overflow-y-auto">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Vai trò (Role) <span className="text-rose-400">*</span>
                </label>
                <select
                  value={formRole}
                  onChange={(e) => setFormRole(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:border-amber-400 focus:outline-none"
                  required
                >
                  {isSuperAdmin ? (
                    <>
                      <option value="center_admin">Admin trung tâm (Center Admin)</option>
                      <option value="teacher">Giáo viên (Teacher)</option>
                      <option value="student">Học sinh (Student)</option>
                      <option value="parent">Phụ huynh (Parent)</option>
                    </>
                  ) : (
                    <>
                      <option value="teacher">Giáo viên (Teacher)</option>
                      <option value="student">Học sinh (Student)</option>
                      <option value="parent">Phụ huynh (Parent)</option>
                    </>
                  )}
                </select>
                {!isSuperAdmin && (
                  <p className="text-[11px] text-slate-400 mt-1">
                    * Admin trung tâm có quyền tạo Giáo viên, Học sinh và Phụ huynh cho cơ sở của mình.
                  </p>
                )}
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center gap-1.5">
                  <Building className="w-3.5 h-3.5 text-amber-400" />
                  Cơ sở / Trung tâm <span className="text-rose-400">*</span>
                </label>
                {isSuperAdmin ? (
                  <select
                    value={formCenterId}
                    onChange={(e) => setFormCenterId(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:border-amber-400 focus:outline-none"
                    required
                  >
                    {centers.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} {c.address ? `(${c.address})` : ''}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-amber-400 font-semibold text-xs flex items-center justify-between">
                    <span>{user?.center_name || 'Cơ sở của bạn'}</span>
                    <span className="text-[10px] text-slate-500 font-normal">Cố định theo tài khoản của bạn</span>
                  </div>
                )}
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Họ và tên đầy đủ <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={formFullName}
                    onChange={(e) => setFormFullName(e.target.value)}
                    placeholder="vd: Nguyễn Văn A"
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs placeholder:text-slate-500 focus:border-amber-400 focus:outline-none"
                    required
                  />
                  <User className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Email đăng nhập <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <input
                    type="email"
                    value={formEmail}
                    onChange={(e) => setFormEmail(e.target.value)}
                    placeholder="email@example.com"
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs placeholder:text-slate-500 focus:border-amber-400 focus:outline-none"
                    required
                  />
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Mật khẩu khởi tạo <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <input
                    type="password"
                    value={formPassword}
                    onChange={(e) => setFormPassword(e.target.value)}
                    placeholder="Tối thiểu 6 ký tự"
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs placeholder:text-slate-500 focus:border-amber-400 focus:outline-none"
                    required
                    minLength={6}
                  />
                  <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Số điện thoại
                </label>
                <div className="relative">
                  <input
                    type="tel"
                    value={formPhone}
                    onChange={(e) => setFormPhone(e.target.value)}
                    placeholder="vd: 0988888888"
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs placeholder:text-slate-500 focus:border-amber-400 focus:outline-none"
                  />
                  <Phone className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex items-center gap-2 px-5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-all shadow-lg shadow-amber-500/20 disabled:opacity-50"
                >
                  {creating && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {creating ? 'Đang tạo...' : 'Tạo tài khoản'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 2: Chỉnh sửa thành viên (Edit Member Modal) */}
      {isEditModalOpen && editingMember && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/40">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center">
                  <Edit2 className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Chỉnh sửa thông tin thành viên</h3>
                  <p className="text-[11px] text-slate-400">
                    Cập nhật họ tên, email đăng nhập, số điện thoại hoặc đặt lại mật khẩu.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsEditModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateMember} className="p-6 space-y-4 overflow-y-auto">
              {/* Họ và tên */}
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Họ và tên đầy đủ <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={editFullName}
                    onChange={(e) => setEditFullName(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:border-amber-400 focus:outline-none"
                    required
                  />
                  <User className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                </div>
              </div>

              {/* Email đăng nhập */}
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Email đăng nhập <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <input
                    type="email"
                    value={editEmail}
                    onChange={(e) => setEditEmail(e.target.value)}
                    placeholder="email@example.com"
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:border-amber-400 focus:outline-none"
                    required
                  />
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                </div>
                <p className="text-[11px] text-amber-400/90 mt-1">
                  * Chỉnh sửa email chính xác để giáo viên/học sinh có thể đăng nhập.
                </p>
              </div>

              {/* Số điện thoại */}
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Số điện thoại
                </label>
                <div className="relative">
                  <input
                    type="tel"
                    value={editPhone}
                    onChange={(e) => setEditPhone(e.target.value)}
                    placeholder="vd: 0988888888"
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs placeholder:text-slate-500 focus:border-amber-400 focus:outline-none"
                  />
                  <Phone className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                </div>
              </div>

              {/* Vai trò */}
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Vai trò (Role)
                </label>
                {isSuperAdmin ? (
                  <select
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:border-amber-400 focus:outline-none"
                  >
                    <option value="center_admin">Admin trung tâm</option>
                    <option value="teacher">Giáo viên</option>
                    <option value="student">Học sinh</option>
                    <option value="parent">Phụ huynh</option>
                  </select>
                ) : (
                  <select
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:border-amber-400 focus:outline-none"
                  >
                    <option value="teacher">Giáo viên</option>
                    <option value="student">Học sinh</option>
                    <option value="parent">Phụ huynh</option>
                  </select>
                )}
              </div>

              {/* Cơ sở (chỉ Super Admin mới đổi được cơ sở) */}
              {isSuperAdmin && editRole !== 'super_admin' && (
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center gap-1.5">
                    <Building className="w-3.5 h-3.5 text-amber-400" />
                    Cơ sở trực thuộc
                  </label>
                  <select
                    value={editCenterId}
                    onChange={(e) => setEditCenterId(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:border-amber-400 focus:outline-none"
                  >
                    <option value="">-- Chưa gán cơ sở --</option>
                    {centers.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} {c.address ? `(${c.address})` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Mật khẩu mới (tùy chọn) */}
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Đặt lại mật khẩu mới (Tùy chọn)
                </label>
                <div className="relative">
                  <input
                    type="password"
                    value={editPassword}
                    onChange={(e) => setEditPassword(e.target.value)}
                    placeholder="Bỏ trống nếu không muốn đổi mật khẩu"
                    className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs placeholder:text-slate-500 focus:border-amber-400 focus:outline-none"
                    minLength={6}
                  />
                  <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                </div>
              </div>

              {/* Trạng thái hoạt động */}
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Trạng thái tài khoản
                </label>
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 cursor-pointer text-xs text-white">
                    <input
                      type="radio"
                      checked={editIsActive === true}
                      onChange={() => setEditIsActive(true)}
                      className="accent-emerald-500"
                    />
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    <span>Đang hoạt động</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-xs text-white">
                    <input
                      type="radio"
                      checked={editIsActive === false}
                      onChange={() => setEditIsActive(false)}
                      className="accent-rose-500"
                    />
                    <XCircle className="w-4 h-4 text-rose-400" />
                    <span>Khóa tài khoản</span>
                  </label>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={updating}
                  className="flex items-center gap-2 px-5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-all shadow-lg shadow-amber-500/20 disabled:opacity-50"
                >
                  {updating && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {updating ? 'Đang lưu...' : 'Lưu thay đổi'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Members;
