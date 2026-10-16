import React, { useState, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import {
  Sliders,
  Database,
  Cpu,
  ScanSearch,
  Shield,
  Building,
  User,
  Plus,
  Lock,
  Layers,
  Save,
  Loader2,
  ToggleLeft,
  ToggleRight,
  Sparkles,
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import api from '../lib/api';
import { settingsApi, type SettingItem, type CatalogItem } from '../lib/settingsApi';

export default function Settings() {
  const { user, setUser } = useAuthStore();
  const role = user?.role || 'student';
  const isSuperAdmin = role === 'super_admin';
  const isCenterAdmin = role === 'center_admin' || role === 'admin';
  const isStaff = isSuperAdmin || isCenterAdmin;

  // Determine initial active tab based on role
  const defaultTab = isSuperAdmin
    ? 'general'
    : isCenterAdmin
    ? 'center_info'
    : 'profile';

  const [activeTab, setActiveTab] = useState(defaultTab);
  const [loading, setLoading] = useState(false);

  // Profile form state
  const [profileFullName, setProfileFullName] = useState(user?.full_name || '');
  const [profilePhone, setProfilePhone] = useState(user?.phone || '');
  const [profileBio, setProfileBio] = useState(user?.bio || '');
  const [profilePassword, setProfilePassword] = useState('');
  const [profileConfirmPassword, setProfileConfirmPassword] = useState('');
  const [profileUpdating, setProfileUpdating] = useState(false);

  useEffect(() => {
    if (user) {
      setProfileFullName(user.full_name || '');
      setProfilePhone(user.phone || '');
      setProfileBio(user.bio || '');
    }
  }, [user]);

  // Handle Profile Update
  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profileFullName.trim()) {
      toast.error('Họ và tên không được để trống');
      return;
    }

    if (profilePassword) {
      if (profilePassword.length < 6) {
        toast.error('Mật khẩu mới phải có ít nhất 6 ký tự');
        return;
      }
      if (profilePassword !== profileConfirmPassword) {
        toast.error('Mật khẩu xác nhận không khớp');
        return;
      }
    }

    setProfileUpdating(true);
    try {
      const payload: Record<string, any> = {
        full_name: profileFullName.trim(),
        phone: profilePhone.trim() || null,
        bio: profileBio.trim() || null,
      };

      if (profilePassword) {
        payload.password = profilePassword;
      }

      const res = await api.put('/users/me', payload);
      setUser(res.data);
      setProfilePassword('');
      setProfileConfirmPassword('');
      toast.success('Cập nhật hồ sơ thành công!');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Cập nhật hồ sơ thất bại');
    } finally {
      setProfileUpdating(false);
    }
  };

  // Settings state
  const [settingsList, setSettingsList] = useState<SettingItem[]>([]);
  const [savingKeys, setSavingKeys] = useState<Record<string, boolean>>({});
  const [editedValues, setEditedValues] = useState<Record<string, string>>({});

  // Catalogs state
  const [catalogsList, setCatalogsList] = useState<CatalogItem[]>([]);
  const [selectedCatalogType, setSelectedCatalogType] = useState<string>('all');
  const [isAddingCatalog, setIsAddingCatalog] = useState(false);
  const [newCatCode, setNewCatCode] = useState('');
  const [newCatLabel, setNewCatLabel] = useState('');
  const [newCatType, setNewCatType] = useState('course_level');
  const [newCatOrder, setNewCatOrder] = useState(0);

  // Profile / Password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);

  // Center info state
  const [centerInfo, setCenterInfo] = useState<{
    id?: string;
    name?: string;
    address?: string;
    phone?: string;
    email?: string;
  }>({});

  // Load settings
  const fetchSettings = async () => {
    if (!isStaff) return;
    try {
      setLoading(true);
      const data = await settingsApi.getSettings();
      setSettingsList(data);
      const vals: Record<string, string> = {};
      data.forEach((s) => {
        vals[s.key] = s.value;
      });
      setEditedValues(vals);
    } catch (err) {
      toast.error('Không thể tải cấu hình hệ thống');
    } finally {
      setLoading(false);
    }
  };

  // Load catalogs
  const fetchCatalogs = async () => {
    if (!isStaff) return;
    try {
      const data = await settingsApi.getCatalogs(undefined, false);
      setCatalogsList(data);
    } catch (err) {
      toast.error('Không thể tải danh mục');
    }
  };

  useEffect(() => {
    if (isStaff) {
      fetchSettings();
      fetchCatalogs();
    }
    if (user?.center_name) {
      setCenterInfo({
        name: user.center_name,
        id: user.center_id,
      });
    }
  }, [user]);

  // Save single setting
  const handleSaveSetting = async (key: string) => {
    const val = editedValues[key];
    if (val === undefined) return;
    setSavingKeys((prev) => ({ ...prev, [key]: true }));
    try {
      await settingsApi.updateSetting(key, val);
      toast.success(`Đã lưu cấu hình: ${key}`);
      await fetchSettings();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Lỗi khi lưu cấu hình');
    } finally {
      setSavingKeys((prev) => ({ ...prev, [key]: false }));
    }
  };

  // Add catalog item
  const handleCreateCatalog = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCatCode.trim() || !newCatLabel.trim()) {
      toast.error('Vui lòng nhập đầy đủ mã và nhãn');
      return;
    }
    try {
      await settingsApi.createCatalogItem({
        catalog_type: newCatType,
        code: newCatCode.trim(),
        label: newCatLabel.trim(),
        order_index: Number(newCatOrder) || 0,
        is_active: true,
      });
      toast.success('Đã thêm danh mục mới');
      setIsAddingCatalog(false);
      setNewCatCode('');
      setNewCatLabel('');
      await fetchCatalogs();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Không thể tạo danh mục');
    }
  };

  // Toggle active catalog item
  const handleToggleCatalogActive = async (item: CatalogItem) => {
    try {
      if (item.is_active) {
        await settingsApi.deactivateCatalogItem(item.id);
        toast.success(`Đã vô hiệu hóa: ${item.label}`);
      } else {
        await settingsApi.updateCatalogItem(item.id, { is_active: true });
        toast.success(`Đã kích hoạt: ${item.label}`);
      }
      await fetchCatalogs();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Không thể cập nhật danh mục');
    }
  };

  // Change password
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 6) {
      toast.error('Mật khẩu mới phải có ít nhất 6 ký tự');
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error('Mật khẩu xác nhận không khớp');
      return;
    }
    setPasswordLoading(true);
    try {
      await api.patch('/users/me/password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success('Đổi mật khẩu thành công');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Đổi mật khẩu thất bại');
    } finally {
      setPasswordLoading(false);
    }
  };

  // Catalog types options
  const catalogTypes = Array.from(
    new Set(catalogsList.map((c) => c.catalog_type))
  );

  const filteredCatalogs = catalogsList.filter((c) =>
    selectedCatalogType === 'all' ? true : c.catalog_type === selectedCatalogType
  );

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              {isSuperAdmin
                ? 'Cài đặt hệ thống'
                : isCenterAdmin
                ? 'Cài đặt trung tâm'
                : 'Cài đặt cá nhân'}
            </h1>
            {loading && (
              <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
            )}
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
              {isSuperAdmin
                ? 'Toàn hệ thống'
                : user?.center_name || 'Cơ sở đào tạo'}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Quản trị tham số động, danh mục chuẩn hóa và phân quyền theo trung tâm.
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-3">
        {isSuperAdmin && (
          <>
            <button
              onClick={() => setActiveTab('general')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'general'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow-lg shadow-amber-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Sliders className="w-4 h-4" />
              Chung
            </button>
            <button
              onClick={() => setActiveTab('catalogs')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'catalogs'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow-lg shadow-amber-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Database className="w-4 h-4" />
              Danh mục hệ thống
            </button>
            <button
              onClick={() => setActiveTab('engine')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'engine'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow-lg shadow-amber-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Cpu className="w-4 h-4" />
              Chấm điểm & Engine
            </button>
            <button
              onClick={() => setActiveTab('scanner')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'scanner'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow-lg shadow-amber-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <ScanSearch className="w-4 h-4" />
              AI Scanner
            </button>
          </>
        )}

        {isCenterAdmin && (
          <>
            <button
              onClick={() => setActiveTab('center_info')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'center_info'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow-lg shadow-amber-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Building className="w-4 h-4" />
              Thông tin trung tâm
            </button>
            <button
              onClick={() => setActiveTab('catalogs')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'catalogs'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow-lg shadow-amber-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Layers className="w-4 h-4" />
              Danh mục trung tâm
            </button>
            <button
              onClick={() => setActiveTab('engine')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'engine'
                  ? 'bg-amber-500 text-slate-950 font-bold shadow-lg shadow-amber-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              Hạn mức & Động cơ
            </button>
          </>
        )}

        {/* Profile and Security available for all roles */}
        <button
          onClick={() => setActiveTab('profile')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeTab === 'profile'
              ? 'bg-amber-500 text-slate-950 font-bold shadow-lg shadow-amber-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <User className="w-4 h-4" />
          Hồ sơ cá nhân
        </button>

        <button
          onClick={() => setActiveTab('security')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeTab === 'security'
              ? 'bg-amber-500 text-slate-950 font-bold shadow-lg shadow-amber-500/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <Shield className="w-4 h-4" />
          Bảo mật & Mật khẩu
        </button>
      </div>

      {/* Tab 1: General & Engine & Scanner Settings */}
      {(activeTab === 'general' || activeTab === 'engine' || activeTab === 'scanner') && (
        <div className="space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-xl">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Sliders className="w-5 h-5 text-amber-400" />
              {activeTab === 'general'
                ? 'Cấu hình chung hệ thống'
                : activeTab === 'engine'
                ? 'Tham số động cơ Stockfish & Đánh giá Elo'
                : 'Giới hạn & Cấu hình AI Scanner'}
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {settingsList
                .filter((s) => {
                  if (activeTab === 'general') return s.category === 'general' || s.category === 'security';
                  if (activeTab === 'engine') return s.category === 'engine' || s.category === 'rating';
                  if (activeTab === 'scanner') return s.category === 'scanner';
                  return true;
                })
                .map((s) => {
                  const isSaving = savingKeys[s.key] || false;
                  return (
                    <div
                      key={s.key}
                      className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/80 flex flex-col justify-between space-y-3"
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-semibold text-white">
                            {s.key}
                          </span>
                          {s.center_id ? (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                              Trung tâm ghi đè
                            </span>
                          ) : (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                              Hệ thống
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400 mt-1">
                          {s.description || 'Tham số cấu hình'}
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        {s.value_type === 'bool' ? (
                          <button
                            type="button"
                            onClick={() => {
                              const nextVal = editedValues[s.key] === 'true' ? 'false' : 'true';
                              setEditedValues((prev) => ({ ...prev, [s.key]: nextVal }));
                            }}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                              editedValues[s.key] === 'true'
                                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                                : 'bg-slate-800 text-slate-400 border-slate-700'
                            }`}
                          >
                            {editedValues[s.key] === 'true' ? (
                              <>
                                <ToggleRight className="w-4 h-4 text-emerald-400" /> BẬT
                              </>
                            ) : (
                              <>
                                <ToggleLeft className="w-4 h-4 text-slate-500" /> TẮT
                              </>
                            )}
                          </button>
                        ) : (
                          <input
                            type={s.value_type === 'int' || s.value_type === 'float' ? 'number' : 'text'}
                            value={editedValues[s.key] ?? s.value}
                            onChange={(e) =>
                              setEditedValues((prev) => ({
                                ...prev,
                                [s.key]: e.target.value,
                              }))
                            }
                            className="flex-1 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:border-amber-400 focus:outline-none"
                          />
                        )}

                        <button
                          onClick={() => handleSaveSetting(s.key)}
                          disabled={isSaving}
                          className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-all disabled:opacity-50"
                        >
                          {isSaving ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Save className="w-3.5 h-3.5" />
                          )}
                          Lưu
                        </button>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Catalogs Manager */}
      {activeTab === 'catalogs' && (
        <div className="space-y-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Database className="w-5 h-5 text-amber-400" />
                  Quản lý danh mục chuẩn hóa
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Không hard-code giá trị. Mọi dropdown và cấp bậc học đều tải từ danh mục này.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <select
                  value={selectedCatalogType}
                  onChange={(e) => setSelectedCatalogType(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:border-amber-400 focus:outline-none"
                >
                  <option value="all">Tất cả danh mục ({catalogsList.length})</option>
                  {catalogTypes.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>

                <button
                  onClick={() => setIsAddingCatalog(!isAddingCatalog)}
                  className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-all"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Thêm mục
                </button>
              </div>
            </div>

            {/* Add catalog inline form */}
            {isAddingCatalog && (
              <form
                onSubmit={handleCreateCatalog}
                className="p-4 rounded-xl bg-slate-950/80 border border-amber-500/30 grid grid-cols-1 sm:grid-cols-4 gap-3 animate-fadeIn"
              >
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">
                    Loại danh mục
                  </label>
                  <input
                    type="text"
                    value={newCatType}
                    onChange={(e) => setNewCatType(e.target.value)}
                    placeholder="vd: course_level"
                    className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-700 text-white text-xs focus:border-amber-400 focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">
                    Mã kỹ thuật (Code bất biến)
                  </label>
                  <input
                    type="text"
                    value={newCatCode}
                    onChange={(e) => setNewCatCode(e.target.value)}
                    placeholder="vd: beginner_plus"
                    className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-700 text-white text-xs focus:border-amber-400 focus:outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-400 block mb-1">
                    Nhãn hiển thị (Label)
                  </label>
                  <input
                    type="text"
                    value={newCatLabel}
                    onChange={(e) => setNewCatLabel(e.target.value)}
                    placeholder="vd: Tiền nâng cao"
                    className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-700 text-white text-xs focus:border-amber-400 focus:outline-none"
                    required
                  />
                </div>
                <div className="flex items-end gap-2">
                  <div className="flex-1">
                    <label className="text-[11px] font-semibold text-slate-400 block mb-1">
                      Thứ tự
                    </label>
                    <input
                      type="number"
                      value={newCatOrder}
                      onChange={(e) => setNewCatOrder(Number(e.target.value))}
                      className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-700 text-white text-xs focus:border-amber-400 focus:outline-none"
                    />
                  </div>
                  <button
                    type="submit"
                    className="px-4 py-1.5 rounded bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs"
                  >
                    Tạo
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsAddingCatalog(false)}
                    className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 text-xs"
                  >
                    Hủy
                  </button>
                </div>
              </form>
            )}

            {/* Catalogs Table */}
            <div className="overflow-x-auto rounded-lg border border-slate-800">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/80 uppercase text-[10px] tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="py-2.5 px-3">Loại danh mục</th>
                    <th className="py-2.5 px-3">Mã code</th>
                    <th className="py-2.5 px-3">Nhãn hiển thị</th>
                    <th className="py-2.5 px-3">Thứ tự</th>
                    <th className="py-2.5 px-3">Phạm vi</th>
                    <th className="py-2.5 px-3">Trạng thái</th>
                    <th className="py-2.5 px-3 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredCatalogs.map((item) => (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="py-2.5 px-3 font-mono text-slate-400">
                        {item.catalog_type}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-amber-400 font-semibold">
                        {item.code}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-white">
                        {item.label}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">
                        {item.order_index}
                      </td>
                      <td className="py-2.5 px-3">
                        {item.center_id ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                            Cơ sở
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400">
                            Toàn cục
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        {item.is_active ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            Đang hoạt động
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                            Đã tắt
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          onClick={() => handleToggleCatalogActive(item)}
                          className={`px-2 py-1 rounded text-[11px] font-semibold transition-all ${
                            item.is_active
                              ? 'text-rose-400 hover:bg-rose-500/20'
                              : 'text-emerald-400 hover:bg-emerald-500/20'
                          }`}
                        >
                          {item.is_active ? 'Tắt' : 'Bật'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Center Info (for center admin) */}
      {activeTab === 'center_info' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Building className="w-5 h-5 text-amber-400" />
            Hồ sơ cơ sở đào tạo
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
              <span className="text-xs text-slate-400">Tên trung tâm</span>
              <p className="text-sm font-semibold text-white">
                {centerInfo.name || user?.center_name || 'Trung tâm Cờ Vua CAMS'}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
              <span className="text-xs text-slate-400">Mã trung tâm (Center ID)</span>
              <p className="text-xs font-mono text-amber-400">
                {centerInfo.id || user?.center_id || 'N/A'}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
              <span className="text-xs text-slate-400">Vai trò người quản trị</span>
              <p className="text-sm font-semibold text-emerald-400 capitalize">
                {user?.role?.replace('_', ' ')}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 space-y-1">
              <span className="text-xs text-slate-400">Chính sách cách ly</span>
              <p className="text-xs text-slate-300">
                Toàn bộ dữ liệu lớp học, bài tập, ngân hàng thế cờ và job AI Scanner được cô lập chặt chẽ cho cơ sở này.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Profile */}
      {activeTab === 'profile' && (
        <div className="space-y-6 animate-fadeIn">
          {/* Read-only Metadata Badges / Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-lg space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Email đăng nhập
              </span>
              <p className="text-sm font-semibold text-white truncate" title={user?.email}>
                {user?.email || 'N/A'}
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-lg space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Vai trò
              </span>
              <p className="text-sm font-semibold text-amber-400 capitalize">
                {user?.role === 'super_admin'
                  ? 'Quản trị cấp cao'
                  : user?.role === 'center_admin'
                  ? 'Admin trung tâm'
                  : user?.role === 'teacher'
                  ? 'Giáo viên'
                  : user?.role === 'student'
                  ? 'Học sinh'
                  : user?.role === 'parent'
                  ? 'Phụ huynh'
                  : user?.role?.replace('_', ' ')}
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-lg space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Cơ sở trực thuộc
              </span>
              <p className="text-sm font-semibold text-blue-400 truncate">
                {user?.role === 'super_admin' ? 'Toàn hệ thống' : user?.center_name || 'Trung tâm'}
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-lg space-y-1">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Điểm Elo / Rating
              </span>
              <p className="text-sm font-bold text-emerald-400">
                {user?.elo_rating || 800}
              </p>
            </div>
          </div>

          {/* Interactive Profile Edit Form */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center">
                <User className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">Chỉnh sửa hồ sơ cá nhân</h2>
                <p className="text-xs text-slate-400">
                  Cập nhật họ và tên, số điện thoại, tiểu sử hoặc đặt mật khẩu mới cho tài khoản.
                </p>
              </div>
            </div>

            <form onSubmit={handleUpdateProfile} className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Họ và tên */}
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                    Họ và tên <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={profileFullName}
                    onChange={(e) => setProfileFullName(e.target.value)}
                    placeholder="Nguyễn Văn A"
                    className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:border-amber-400 focus:outline-none transition-colors"
                    required
                  />
                </div>

                {/* Số điện thoại */}
                <div>
                  <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                    Số điện thoại
                  </label>
                  <input
                    type="tel"
                    value={profilePhone}
                    onChange={(e) => setProfilePhone(e.target.value)}
                    placeholder="vd: 0988888888"
                    className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm placeholder:text-slate-500 focus:border-amber-400 focus:outline-none transition-colors"
                  />
                </div>
              </div>

              {/* Tiểu sử */}
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Tiểu sử (Bio)
                </label>
                <textarea
                  value={profileBio}
                  onChange={(e) => setProfileBio(e.target.value)}
                  rows={3}
                  placeholder="Giới thiệu ngắn về bản thân, phong cách chơi cờ hoặc kinh nghiệm..."
                  className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm placeholder:text-slate-500 focus:border-amber-400 focus:outline-none resize-none transition-colors"
                />
              </div>

              {/* Đổi mật khẩu trong Profile */}
              <div className="pt-4 border-t border-slate-800 space-y-4">
                <div className="flex items-center gap-2">
                  <Lock className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-bold text-slate-200">
                    Đặt lại mật khẩu mới (Tùy chọn)
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div>
                    <label className="text-xs font-medium text-slate-400 block mb-1.5">
                      Mật khẩu mới
                    </label>
                    <input
                      type="password"
                      value={profilePassword}
                      onChange={(e) => setProfilePassword(e.target.value)}
                      placeholder="Để trống nếu không muốn đổi"
                      minLength={6}
                      className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm placeholder:text-slate-500 focus:border-amber-400 focus:outline-none transition-colors"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium text-slate-400 block mb-1.5">
                      Xác nhận mật khẩu mới
                    </label>
                    <input
                      type="password"
                      value={profileConfirmPassword}
                      onChange={(e) => setProfileConfirmPassword(e.target.value)}
                      placeholder="Xác nhận lại mật khẩu mới"
                      className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm placeholder:text-slate-500 focus:border-amber-400 focus:outline-none transition-colors"
                    />
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <div className="flex justify-end pt-4 border-t border-slate-800">
                <button
                  type="submit"
                  disabled={profileUpdating}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm transition-all shadow-lg shadow-amber-500/20 disabled:opacity-50"
                >
                  {profileUpdating ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  {profileUpdating ? 'Đang lưu...' : 'Lưu thay đổi'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tab 5: Security / Change Password */}
      {activeTab === 'security' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-xl max-w-xl space-y-4">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Shield className="w-5 h-5 text-amber-400" />
            Đổi mật khẩu tài khoản
          </h2>

          <form onSubmit={handleChangePassword} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1.5">
                Mật khẩu hiện tại
              </label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:border-amber-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1.5">
                Mật khẩu mới
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:border-amber-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 block mb-1.5">
                Xác nhận mật khẩu mới
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-sm focus:border-amber-400 focus:outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={passwordLoading}
              className="px-5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm flex items-center gap-2 transition-all disabled:opacity-50"
            >
              {passwordLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Lock className="w-4 h-4" />
              )}
              Cập nhật mật khẩu
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
