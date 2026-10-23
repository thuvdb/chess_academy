import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';
import {
  Bot,
  Plus,
  Edit2,
  Trash2,
  Play,
  RotateCw,
  CheckCircle2,
  XCircle,
  Clock,
  Eye,
  EyeOff,
  AlertTriangle,
  Server,
  Sliders,
  History,
  X,
  Loader2,
  ShieldAlert,
  Sparkles,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react';
import {
  aiSettingsApi,
  type AIProvider,
  type AISettings,
  type AISettingsAudit,
  type AIProviderTestResponse,
} from '../../lib/aiSettingsApi';

export default function AISettingsTab() {
  const [loading, setLoading] = useState(true);
  const [settings, setSettings] = useState<AISettings | null>(null);
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [auditLogs, setAuditLogs] = useState<AISettingsAudit[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);

  // Default settings form state
  const [defaultProviderId, setDefaultProviderId] = useState<string>('');
  const [defaultModel, setDefaultModel] = useState<string>('gemini-3.8-flash');
  const [fallbackProviderId, setFallbackProviderId] = useState<string>('none');
  const [fallbackModel, setFallbackModel] = useState<string>('');
  const [temperature, setTemperature] = useState<number>(0.7);
  const [maxOutputTokens, setMaxOutputTokens] = useState<number>(1500);
  const [requestTimeoutSeconds, setRequestTimeoutSeconds] = useState<number>(30);
  const [maxRetries, setMaxRetries] = useState<number>(2);
  const [savingSettings, setSavingSettings] = useState(false);
  const [isConfirmSaveOpen, setIsConfirmSaveOpen] = useState(false);

  // Test states per provider id
  const [testStates, setTestStates] = useState<
    Record<string, { testing: boolean; result?: AIProviderTestResponse }>
  >({});

  // Provider Modal state (Add / Edit)
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<AIProvider | null>(null);
  const [formName, setFormName] = useState('');
  const [formType, setFormType] = useState<'gemini' | 'openai_compatible'>('gemini');
  const [formBaseUrl, setFormBaseUrl] = useState('');
  const [formApiKey, setFormApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [formModels, setFormModels] = useState<string[]>([]);
  const [newModelInput, setNewModelInput] = useState('');
  const [formEnabled, setFormEnabled] = useState(true);
  const [savingProvider, setSavingProvider] = useState(false);
  const [fetchingModels, setFetchingModels] = useState(false);

  // Delete confirmation
  const [deletingProvider, setDeletingProvider] = useState<AIProvider | null>(null);
  const [deletingLoading, setDeletingLoading] = useState(false);

  // 1. Fetch overview and audit data
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const overview = await aiSettingsApi.getOverview();
      setSettings(overview.settings);
      setProviders(overview.providers);

      // Populate form state
      setDefaultProviderId(overview.settings.default_provider_id || '');
      setDefaultModel(overview.settings.default_model || 'gemini-3.8-flash');
      setFallbackProviderId(overview.settings.fallback_provider_id || 'none');
      setFallbackModel(overview.settings.fallback_model || '');
      setTemperature(overview.settings.temperature ?? 0.7);
      setMaxOutputTokens(overview.settings.max_output_tokens ?? 1500);
      setRequestTimeoutSeconds(overview.settings.request_timeout_seconds ?? 30);
      setMaxRetries(overview.settings.max_retries ?? 2);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Không thể tải cấu hình AI');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAuditLogs = useCallback(async () => {
    try {
      setAuditLoading(true);
      const logs = await aiSettingsApi.getAuditLogs(20);
      setAuditLogs(logs);
    } catch {
      // Non-blocking
    } finally {
      setAuditLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    fetchAuditLogs();
  }, [fetchData, fetchAuditLogs]);

  // Models available for selected default & fallback providers
  const selectedDefaultProvider = providers.find((p) => p.id === defaultProviderId);
  const selectedFallbackProvider = providers.find((p) => p.id === fallbackProviderId);

  // Auto-sync default model if selected provider changes
  const handleDefaultProviderChange = (newProvId: string) => {
    setDefaultProviderId(newProvId);
    const prov = providers.find((p) => p.id === newProvId);
    if (prov && prov.models.length > 0 && !prov.models.includes(defaultModel)) {
      setDefaultModel(prov.models[0]);
    }
  };

  const handleFallbackProviderChange = (newProvId: string) => {
    setFallbackProviderId(newProvId);
    if (newProvId === 'none') {
      setFallbackModel('');
    } else {
      const prov = providers.find((p) => p.id === newProvId);
      if (prov && prov.models.length > 0 && !prov.models.includes(fallbackModel)) {
        setFallbackModel(prov.models[0]);
      }
    }
  };

  // 2. Test Provider
  const handleTestProvider = async (providerId: string) => {
    setTestStates((prev) => ({
      ...prev,
      [providerId]: { testing: true },
    }));

    try {
      const res = await aiSettingsApi.testProvider(providerId);
      setTestStates((prev) => ({
        ...prev,
        [providerId]: { testing: false, result: res },
      }));

      if (res.success) {
        toast.success(`Kết nối thành công (${res.latency_ms}ms)`);
      } else {
        toast.error(`Kiểm tra thất bại: ${res.error || 'Lỗi không xác định'}`);
      }
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || err.message || 'Lỗi kết nối';
      setTestStates((prev) => ({
        ...prev,
        [providerId]: {
          testing: false,
          result: { success: false, latency_ms: 0, error: errMsg },
        },
      }));
      toast.error(`Kiểm tra thất bại: ${errMsg}`);
    }
  };

  // 3. Quick Toggle Enable/Disable
  const handleToggleEnable = async (provider: AIProvider) => {
    try {
      const updated = await aiSettingsApi.updateProvider(provider.id, {
        enabled: !provider.enabled,
      });
      setProviders((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      toast.success(
        `Đã ${updated.enabled ? 'bật' : 'vô hiệu hóa'} nhà cung cấp "${updated.name}"`
      );
      fetchAuditLogs();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Không thể cập nhật trạng thái');
    }
  };

  // 4. Save Default Settings
  const handleSaveSettings = async () => {
    if (!defaultProviderId) {
      toast.error('Vui lòng chọn một nhà cung cấp mặc định');
      return;
    }

    try {
      setSavingSettings(true);
      const updated = await aiSettingsApi.updateSettings({
        default_provider_id: defaultProviderId,
        default_model: defaultModel,
        fallback_provider_id: fallbackProviderId === 'none' ? null : fallbackProviderId,
        fallback_model: fallbackProviderId === 'none' ? null : fallbackModel,
        temperature,
        max_output_tokens: maxOutputTokens,
        request_timeout_seconds: requestTimeoutSeconds,
        max_retries: maxRetries,
      });

      setSettings(updated);
      setIsConfirmSaveOpen(false);
      toast.success('Cập nhật cấu hình AI thành công (có hiệu lực ngay lập tức)');
      fetchAuditLogs();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Lỗi khi lưu cấu hình');
    } finally {
      setSavingSettings(false);
    }
  };

  // 5. Open Add / Edit Modal
  const handleOpenAddModal = () => {
    setEditingProvider(null);
    setFormName('');
    setFormType('gemini');
    setFormBaseUrl('');
    setFormApiKey('');
    setShowApiKey(false);
    setFormModels(['gemini-3.8-flash', 'gemini-2.5-flash', 'gemini-2.5-pro']);
    setNewModelInput('');
    setFormEnabled(true);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (provider: AIProvider) => {
    setEditingProvider(provider);
    setFormName(provider.name);
    setFormType(provider.type);
    setFormBaseUrl(provider.base_url || '');
    setFormApiKey(''); // Sensitive: left blank when editing
    setShowApiKey(false);
    setFormModels([...provider.models]);
    setNewModelInput('');
    setFormEnabled(provider.enabled);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    // SECURITY: strictly scrub key from state immediately
    setFormApiKey('');
    setShowApiKey(false);
    setIsModalOpen(false);
    setEditingProvider(null);
  };

  // Add / Remove model chips
  const handleAddModelChip = () => {
    const trimmed = newModelInput.trim();
    if (!trimmed) return;
    if (formModels.includes(trimmed)) {
      toast.error('Model này đã có trong danh sách');
      return;
    }
    setFormModels((prev) => [...prev, trimmed]);
    setNewModelInput('');
  };

  const handleRemoveModelChip = (modelName: string) => {
    if (formModels.length <= 1) {
      toast.error('Phải giữ lại ít nhất 1 model');
      return;
    }
    setFormModels((prev) => prev.filter((m) => m !== modelName));
  };

  // Fetch Remote Models (OpenAI-compatible)
  const handleFetchModels = async () => {
    if (!editingProvider) {
      toast.error('Vui lòng lưu provider trước khi lấy danh sách model từ xa');
      return;
    }
    try {
      setFetchingModels(true);
      const res = await aiSettingsApi.listProviderModels(editingProvider.id);
      if (res.models && res.models.length > 0) {
        setFormModels(res.models);
        toast.success(`Đã lấy ${res.models.length} model từ ${res.source === 'remote' ? 'máy chủ từ xa' : 'bộ nhớ'}`);
      } else {
        toast.error('Không tìm thấy model nào từ nhà cung cấp');
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Lỗi khi lấy danh sách models');
    } finally {
      setFetchingModels(false);
    }
  };

  // Submit Provider Form
  const handleSubmitProvider = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) {
      toast.error('Tên nhà cung cấp không được để trống');
      return;
    }
    if (formModels.length === 0) {
      toast.error('Vui lòng thêm ít nhất một model');
      return;
    }
    if (formType === 'openai_compatible' && !formBaseUrl.trim()) {
      toast.error('Nhà cung cấp OpenAI-compatible cần có Base URL');
      return;
    }

    try {
      setSavingProvider(true);

      if (editingProvider) {
        // Update
        const payload: any = {
          name: formName.trim(),
          type: formType,
          base_url: formType === 'openai_compatible' ? formBaseUrl.trim() : null,
          models: formModels,
          enabled: formEnabled,
        };
        if (formApiKey.trim()) {
          payload.api_key = formApiKey.trim();
        }

        const updated = await aiSettingsApi.updateProvider(editingProvider.id, payload);
        setProviders((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
        toast.success(`Đã cập nhật nhà cung cấp "${updated.name}"`);
      } else {
        // Create
        const payload: any = {
          name: formName.trim(),
          type: formType,
          base_url: formType === 'openai_compatible' ? formBaseUrl.trim() : null,
          models: formModels,
          enabled: formEnabled,
        };
        if (formApiKey.trim()) {
          payload.api_key = formApiKey.trim();
        }

        const created = await aiSettingsApi.createProvider(payload);
        setProviders((prev) => [...prev, created]);
        toast.success(`Đã thêm nhà cung cấp "${created.name}" thành công`);
      }

      handleCloseModal();
      fetchAuditLogs();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Lỗi lưu nhà cung cấp AI');
    } finally {
      // SECURITY: ensure sensitive key is always cleared
      setFormApiKey('');
      setSavingProvider(false);
    }
  };

  // 6. Delete Provider
  const handleConfirmDelete = async () => {
    if (!deletingProvider) return;

    if (settings?.default_provider_id === deletingProvider.id) {
      toast.error('Không thể xóa nhà cung cấp đang làm mặc định! Hãy đổi mặc định trước.');
      setDeletingProvider(null);
      return;
    }

    try {
      setDeletingLoading(true);
      await aiSettingsApi.deleteProvider(deletingProvider.id);
      setProviders((prev) => prev.filter((p) => p.id !== deletingProvider.id));
      toast.success(`Đã xóa nhà cung cấp "${deletingProvider.name}"`);
      setDeletingProvider(null);
      fetchAuditLogs();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Lỗi khi xóa nhà cung cấp');
    } finally {
      setDeletingLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <Loader2 className="w-10 h-10 animate-spin text-amber-400" />
        <p className="text-sm text-slate-400">Đang tải cấu hình AI hệ thống...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12 animate-fadeIn">
      {/* 1. Header & Security Notice */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-xl space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Bot className="w-5 h-5 text-amber-400" />
              Cấu hình AI & Nhà cung cấp LLM
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Quản lý định tuyến mô hình AI, khóa API bảo mật (Fernet encrypted), và cơ chế dự phòng tự động.
            </p>
          </div>
          <button
            onClick={fetchData}
            title="Làm mới dữ liệu"
            className="self-start sm:self-center flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
          >
            <RotateCw className="w-3.5 h-3.5" />
            Làm mới
          </button>
        </div>

        {/* Security Warning Notice */}
        <div className="flex items-start gap-3 p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs leading-relaxed">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Lưu ý bảo mật:</span> Mọi nội dung trao đổi qua AI Tutor sẽ đi qua nhà cung cấp bạn chọn. Với dịch vụ bên thứ ba (relay / proxy), hãy cân nhắc về dữ liệu học viên.
          </div>
        </div>
      </div>

      {/* 2. Providers List Section */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Server className="w-4 h-4 text-amber-400" />
              Danh sách Nhà cung cấp ({providers.length})
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Cấu hình các API Provider (Google Gemini hoặc chuẩn OpenAI-compatible).
            </p>
          </div>
          <button
            onClick={handleOpenAddModal}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-lg shadow-amber-500/20 transition self-start sm:self-center"
          >
            <Plus className="w-4 h-4" />
            Thêm nhà cung cấp
          </button>
        </div>

        {providers.length === 0 ? (
          <div className="p-8 text-center bg-slate-950/40 border border-slate-800 rounded-lg space-y-2">
            <Server className="w-10 h-10 text-slate-600 mx-auto" />
            <p className="text-xs text-slate-400">Chưa có nhà cung cấp AI nào được cấu hình.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {providers.map((prov) => {
              const isDefault = settings?.default_provider_id === prov.id;
              const isFallback = settings?.fallback_provider_id === prov.id;
              const testState = testStates[prov.id];

              return (
                <div
                  key={prov.id}
                  className={`p-4 rounded-xl border transition-all ${
                    prov.enabled
                      ? isDefault
                        ? 'bg-slate-900/90 border-amber-500/60 shadow-md shadow-amber-500/10'
                        : 'bg-slate-900/70 border-slate-800 hover:border-slate-700'
                      : 'bg-slate-950/40 border-slate-850 opacity-70'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    {/* Left: Info */}
                    <div className="space-y-2 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-bold text-white text-sm">{prov.name}</span>

                        {/* Type badge */}
                        <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                          {prov.type === 'gemini' ? 'Google Gemini' : 'OpenAI-Compatible'}
                        </span>

                        {/* Status badge */}
                        <span
                          className={`px-2 py-0.5 rounded-full text-[11px] font-semibold flex items-center gap-1 ${
                            prov.enabled
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                              : 'bg-slate-800 text-slate-400 border border-slate-750'
                          }`}
                        >
                          {prov.enabled ? 'Đang bật' : 'Đã tắt'}
                        </span>

                        {/* Role Tags */}
                        {isDefault && (
                          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/50 flex items-center gap-1">
                            <Sparkles className="w-3 h-3" /> Mặc định
                          </span>
                        )}
                        {isFallback && (
                          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-sky-500/20 text-sky-300 border border-sky-500/40">
                            Dự phòng
                          </span>
                        )}
                      </div>

                      {/* Base URL (for OpenAI compatible) */}
                      {prov.base_url && (
                        <div className="text-xs text-slate-400 font-mono truncate">
                          <span className="text-slate-500">Base URL: </span>
                          {prov.base_url}
                        </div>
                      )}

                      {/* Masked Key */}
                      <div className="text-xs text-slate-400 font-mono flex items-center gap-2">
                        <span className="text-slate-500">API Key:</span>
                        {prov.has_key ? (
                          <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-amber-300/90 font-mono">
                            {prov.api_key_masked || '••••••••'}
                          </span>
                        ) : (
                          <span className="text-rose-400/90 italic text-[11px]">
                            Chưa nhập khóa (sẽ dùng env fallback)
                          </span>
                        )}
                      </div>

                      {/* Models chips */}
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <span className="text-[11px] text-slate-500 font-medium">Models:</span>
                        {prov.models && prov.models.length > 0 ? (
                          prov.models.map((m) => (
                            <span
                              key={m}
                              className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-950/70 border border-slate-800 text-slate-300"
                            >
                              {m}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-slate-500 italic">Chưa có model</span>
                        )}
                      </div>
                    </div>

                    {/* Right: Actions */}
                    <div className="flex flex-wrap sm:flex-nowrap items-center gap-1.5 self-end sm:self-start shrink-0">
                      {/* Test Button */}
                      <button
                        onClick={() => handleTestProvider(prov.id)}
                        disabled={testState?.testing}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition border border-slate-700 disabled:opacity-50"
                        title="Kiểm tra kết nối và độ trễ"
                      >
                        {testState?.testing ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />
                        ) : (
                          <Play className="w-3.5 h-3.5 text-emerald-400" />
                        )}
                        Test
                      </button>

                      {/* Toggle Enable */}
                      <button
                        onClick={() => handleToggleEnable(prov)}
                        className={`p-1.5 rounded-lg border text-xs transition ${
                          prov.enabled
                            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
                            : 'bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700'
                        }`}
                        title={prov.enabled ? 'Bấm để tắt' : 'Bấm để bật'}
                      >
                        {prov.enabled ? (
                          <ToggleRight className="w-4 h-4" />
                        ) : (
                          <ToggleLeft className="w-4 h-4" />
                        )}
                      </button>

                      {/* Edit Button */}
                      <button
                        onClick={() => handleOpenEditModal(prov)}
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                        title="Sửa cấu hình"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>

                      {/* Delete Button */}
                      <button
                        onClick={() => setDeletingProvider(prov)}
                        disabled={isDefault}
                        className={`p-1.5 rounded-lg border transition ${
                          isDefault
                            ? 'bg-slate-900 border-slate-800 text-slate-600 cursor-not-allowed'
                            : 'bg-rose-500/10 border-rose-500/20 text-rose-400 hover:bg-rose-500/20'
                        }`}
                        title={isDefault ? 'Không thể xóa nhà cung cấp mặc định' : 'Xóa nhà cung cấp'}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* Test Result Message Box */}
                  {testState?.result && (
                    <div
                      className={`mt-3 p-2.5 rounded-lg text-xs flex items-start gap-2 border ${
                        testState.result.success
                          ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300'
                          : 'bg-rose-950/30 border-rose-500/30 text-rose-300'
                      }`}
                    >
                      {testState.result.success ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1 space-y-0.5">
                        <div className="font-semibold">
                          {testState.result.success
                            ? `Kiểm tra thành công (độ trễ: ${testState.result.latency_ms}ms)`
                            : `Kiểm tra thất bại (${testState.result.latency_ms}ms)`}
                        </div>
                        {testState.result.response && (
                          <div className="font-mono text-[11px] opacity-90">
                            Phản hồi: &quot;{testState.result.response}&quot;
                          </div>
                        )}
                        {testState.result.error && (
                          <div className="font-mono text-[11px] opacity-90 text-rose-300">
                            Lỗi: {testState.result.error}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() =>
                          setTestStates((prev) => {
                            const next = { ...prev };
                            delete next[prov.id];
                            return next;
                          })
                        }
                        className="text-slate-400 hover:text-white"
                        title="Đóng kết quả"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 3. Default AI Settings Section */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-xl space-y-5">
        <div className="pb-3 border-b border-slate-800">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Sliders className="w-4 h-4 text-amber-400" />
            Cài đặt Mặc định & Dự phòng (Routing)
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Quy định mô hình AI chính sẽ phục vụ học viên, và nhà cung cấp dự phòng khi xảy ra sự cố hạn ngạch (429 / Overload).
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Primary Provider */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 block">
              Nhà cung cấp Chính <span className="text-amber-400">*</span>
            </label>
            <select
              value={defaultProviderId}
              onChange={(e) => handleDefaultProviderChange(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400"
            >
              <option value="" disabled>
                -- Chọn nhà cung cấp chính --
              </option>
              {providers
                .filter((p) => p.enabled)
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.type === 'gemini' ? 'Gemini' : 'OpenAI-compat'})
                  </option>
                ))}
            </select>
          </div>

          {/* Primary Model */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 block">
              Mô hình Chính (Model ID) <span className="text-amber-400">*</span>
            </label>
            {selectedDefaultProvider && selectedDefaultProvider.models.length > 0 ? (
              <select
                value={defaultModel}
                onChange={(e) => setDefaultModel(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400 font-mono"
              >
                {selectedDefaultProvider.models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={defaultModel}
                onChange={(e) => setDefaultModel(e.target.value)}
                placeholder="vd: gemini-3.8-flash"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400 font-mono"
              />
            )}
          </div>

          {/* Fallback Provider */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 block">
              Nhà cung cấp Dự phòng (Fallback)
            </label>
            <select
              value={fallbackProviderId}
              onChange={(e) => handleFallbackProviderChange(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400"
            >
              <option value="none">-- Không dùng dự phòng (None) --</option>
              {providers
                .filter((p) => p.enabled && p.id !== defaultProviderId)
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.type === 'gemini' ? 'Gemini' : 'OpenAI-compat'})
                  </option>
                ))}
            </select>
          </div>

          {/* Fallback Model */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 block">
              Mô hình Dự phòng (Fallback Model)
            </label>
            {fallbackProviderId === 'none' ? (
              <input
                type="text"
                disabled
                value="Chưa kích hoạt dự phòng"
                className="w-full px-3 py-2 bg-slate-950/50 border border-slate-800 rounded-lg text-sm text-slate-500 italic cursor-not-allowed"
              />
            ) : selectedFallbackProvider && selectedFallbackProvider.models.length > 0 ? (
              <select
                value={fallbackModel}
                onChange={(e) => setFallbackModel(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400 font-mono"
              >
                {selectedFallbackProvider.models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={fallbackModel}
                onChange={(e) => setFallbackModel(e.target.value)}
                placeholder="vd: gpt-4o-mini"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400 font-mono"
              />
            )}
          </div>
        </div>

        {/* Hyperparameters & Limits */}
        <div className="pt-2 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 border-t border-slate-800">
          {/* Temperature */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs text-slate-300">
              <span className="font-semibold">Temperature:</span>
              <span className="font-mono font-bold text-amber-400">{temperature}</span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full accent-amber-500 cursor-pointer"
            />
            <p className="text-[10px] text-slate-500">Thấp: chính xác; Cao: sáng tạo</p>
          </div>

          {/* Max Output Tokens */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 block">Max Tokens</label>
            <input
              type="number"
              min="100"
              max="8192"
              step="100"
              value={maxOutputTokens}
              onChange={(e) => setMaxOutputTokens(parseInt(e.target.value, 10) || 1000)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400 font-mono"
            />
            <p className="text-[10px] text-slate-500">Giới hạn token trả về</p>
          </div>

          {/* Timeout */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 block">Timeout (giây)</label>
            <input
              type="number"
              min="5"
              max="120"
              value={requestTimeoutSeconds}
              onChange={(e) => setRequestTimeoutSeconds(parseInt(e.target.value, 10) || 30)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400 font-mono"
            />
            <p className="text-[10px] text-slate-500">Thời gian chờ tối đa</p>
          </div>

          {/* Max Retries */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 block">Số lần thử lại</label>
            <input
              type="number"
              min="0"
              max="5"
              value={maxRetries}
              onChange={(e) => setMaxRetries(parseInt(e.target.value, 10) || 0)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400 font-mono"
            />
            <p className="text-[10px] text-slate-500">Thử lại khi gặp lỗi 429</p>
          </div>
        </div>

        {/* Action Button */}
        <div className="pt-3 border-t border-slate-800 flex justify-end">
          <button
            onClick={() => setIsConfirmSaveOpen(true)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm shadow-lg shadow-amber-500/20 transition"
          >
            Lưu cấu hình mặc định
          </button>
        </div>
      </div>

      {/* 4. Audit History Section */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <History className="w-4 h-4 text-amber-400" />
              Lịch sử thay đổi Cấu hình AI
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Ghi nhận các thao tác quản trị trên nhà cung cấp và thông số mô hình (không lưu khóa API).
            </p>
          </div>
          <button
            onClick={fetchAuditLogs}
            disabled={auditLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
          >
            <RotateCw className={`w-3.5 h-3.5 ${auditLoading ? 'animate-spin' : ''}`} />
            Tải lại
          </button>
        </div>

        {auditLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-amber-400" />
          </div>
        ) : auditLogs.length === 0 ? (
          <div className="p-6 text-center bg-slate-950/40 border border-slate-800 rounded-lg">
            <p className="text-xs text-slate-500">Chưa có nhật ký thay đổi nào.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <div className="space-y-2.5">
              {auditLogs.map((log) => {
                const dateStr = new Date(log.created_at).toLocaleString('vi-VN', {
                  hour: '2-digit',
                  minute: '2-digit',
                  day: '2-digit',
                  month: '2-digit',
                  year: 'numeric',
                });

                return (
                  <div
                    key={log.id}
                    className="p-3 rounded-lg bg-slate-950/60 border border-slate-850 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded font-mono font-bold text-[11px] bg-slate-800 text-amber-300 border border-slate-700">
                          {log.action}
                        </span>
                        <span className="font-semibold text-slate-200">
                          {log.user_name || 'Super Admin'}
                        </span>
                      </div>
                      {log.details && Object.keys(log.details).length > 0 && (
                        <div className="text-[11px] text-slate-400 font-mono break-all">
                          {Object.entries(log.details)
                            .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
                            .join(' | ')}
                        </div>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-500 flex items-center gap-1 shrink-0">
                      <Clock className="w-3.5 h-3.5" />
                      {dateStr}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* MODAL: Thêm / Sửa Provider */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-5 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Server className="w-4 h-4 text-amber-400" />
                {editingProvider ? 'Chỉnh sửa Nhà cung cấp AI' : 'Thêm Nhà cung cấp AI Mới'}
              </h3>
              <button
                onClick={handleCloseModal}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmitProvider} className="space-y-4">
              {/* Name */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300 block">
                  Tên hiển thị <span className="text-amber-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="vd: Google Gemini, AgentRouter DeepSeek..."
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400"
                />
              </div>

              {/* Type */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-300 block">
                  Loại kết nối <span className="text-amber-400">*</span>
                </label>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value as any)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400"
                >
                  <option value="gemini">Google Gemini (Native SDK)</option>
                  <option value="openai_compatible">OpenAI-Compatible (SSE Streaming)</option>
                </select>
              </div>

              {/* Base URL (only for OpenAI-compatible) */}
              {formType === 'openai_compatible' && (
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-300 block">
                    Base URL <span className="text-amber-400">*</span>
                  </label>
                  <input
                    type="url"
                    required
                    value={formBaseUrl}
                    onChange={(e) => setFormBaseUrl(e.target.value)}
                    placeholder="https://api.openai.com/v1 hoặc https://agentrouter.org/v1"
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400 font-mono"
                  />
                  <p className="text-[10px] text-slate-500">
                    Endpoint tương thích chuẩn OpenAI Chat Completions
                  </p>
                </div>
              )}

              {/* API Key */}
              <div className="space-y-1">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-semibold text-slate-300 block">
                    API Key {editingProvider ? '(để trống nếu giữ nguyên)' : ''}
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="text-[11px] text-amber-400 hover:underline flex items-center gap-1"
                  >
                    {showApiKey ? (
                      <>
                        <EyeOff className="w-3 h-3" /> Ẩn
                      </>
                    ) : (
                      <>
                        <Eye className="w-3 h-3" /> Hiện
                      </>
                    )}
                  </button>
                </div>
                <div className="relative">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={formApiKey}
                    onChange={(e) => setFormApiKey(e.target.value)}
                    placeholder={
                      editingProvider
                        ? `Khóa hiện tại: ${editingProvider.api_key_masked || 'đã lưu'} (nhập mới để thay đổi)`
                        : 'Nhập API key bí mật'
                    }
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400 font-mono pr-10"
                  />
                </div>
                <p className="text-[10px] text-slate-500">
                  Khóa được mã hóa bằng Fernet 256-bit trong DB, không bao giờ lộ trên log hay phản hồi API.
                </p>
              </div>

              {/* Models List Management */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-300 block">
                    Danh sách Models ({formModels.length})
                  </label>
                  {formType === 'openai_compatible' && editingProvider && (
                    <button
                      type="button"
                      onClick={handleFetchModels}
                      disabled={fetchingModels}
                      className="text-[11px] text-amber-400 hover:underline flex items-center gap-1"
                    >
                      {fetchingModels ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <RotateCw className="w-3 h-3" />
                      )}
                      Lấy danh sách model
                    </button>
                  )}
                </div>

                {/* Chips */}
                <div className="flex flex-wrap gap-1.5 p-2 bg-slate-950 rounded-lg border border-slate-800 min-h-[42px] max-h-32 overflow-y-auto">
                  {formModels.map((m) => (
                    <span
                      key={m}
                      className="px-2 py-0.5 rounded text-xs font-mono bg-slate-900 border border-slate-700 text-slate-200 flex items-center gap-1"
                    >
                      {m}
                      <button
                        type="button"
                        onClick={() => handleRemoveModelChip(m)}
                        className="text-slate-500 hover:text-rose-400"
                        title="Xóa model"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>

                {/* Add model manually */}
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={newModelInput}
                    onChange={(e) => setNewModelInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddModelChip();
                      }
                    }}
                    placeholder="Nhập tên model (vd: deepseek-chat, gpt-4o-mini...)"
                    className="flex-1 px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:border-amber-400 font-mono"
                  />
                  <button
                    type="button"
                    onClick={handleAddModelChip}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
                  >
                    Thêm
                  </button>
                </div>
              </div>

              {/* Enabled toggle */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="providerEnabled"
                  checked={formEnabled}
                  onChange={(e) => setFormEnabled(e.target.checked)}
                  className="rounded border-slate-700 text-amber-500 focus:ring-amber-400"
                />
                <label htmlFor="providerEnabled" className="text-xs text-slate-300 font-medium">
                  Kích hoạt nhà cung cấp này
                </label>
              </div>

              {/* Modal Actions */}
              <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={savingProvider}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-lg shadow-amber-500/20 disabled:opacity-50"
                >
                  {savingProvider ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : null}
                  {editingProvider ? 'Cập nhật' : 'Thêm mới'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CONFIRMATION MODAL: Lưu Cấu hình Mặc định */}
      {isConfirmSaveOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-5 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-amber-400">
              <AlertTriangle className="w-6 h-6 shrink-0" />
              <h3 className="text-base font-bold text-white">Xác nhận cập nhật Cấu hình AI</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Bạn có chắc chắn muốn thay đổi nhà cung cấp chính thành{' '}
              <strong className="text-amber-300 font-mono">{selectedDefaultProvider?.name}</strong>{' '}
              với model <strong className="text-amber-300 font-mono">{defaultModel}</strong>?
              Thay đổi sẽ có hiệu lực ngay lập tức cho toàn bộ học viên mà không cần khởi động lại server.
            </p>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsConfirmSaveOpen(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                onClick={handleSaveSettings}
                disabled={savingSettings}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-lg shadow-amber-500/20 disabled:opacity-50"
              >
                {savingSettings && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Xác nhận lưu
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CONFIRMATION MODAL: Xóa Provider */}
      {deletingProvider && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-5 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-rose-400">
              <AlertTriangle className="w-6 h-6 shrink-0" />
              <h3 className="text-base font-bold text-white">Xóa Nhà cung cấp AI</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Bạn có chắc chắn muốn xóa nhà cung cấp{' '}
              <strong className="text-white">&quot;{deletingProvider.name}&quot;</strong>?
              Thao tác này không thể hoàn tác.
            </p>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setDeletingProvider(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={deletingLoading}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-rose-500 hover:bg-rose-400 text-white font-bold text-xs shadow-lg shadow-rose-500/20 disabled:opacity-50"
              >
                {deletingLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Xác nhận xóa
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
