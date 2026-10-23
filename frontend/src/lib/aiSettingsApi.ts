import api from './api';

export interface AIProvider {
  id: string;
  name: string;
  type: 'gemini' | 'openai_compatible';
  base_url?: string | null;
  models: string[];
  enabled: boolean;
  api_key_masked: string;
  has_key: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface AISettings {
  id: string;
  default_provider_id?: string | null;
  default_model: string;
  fallback_provider_id?: string | null;
  fallback_model?: string | null;
  temperature: number;
  max_output_tokens: number;
  request_timeout_seconds: number;
  max_retries: number;
  updated_at: string;
}

export interface AdminAISettingsOverview {
  settings: AISettings;
  providers: AIProvider[];
}

export interface AIProviderCreatePayload {
  name: string;
  type: 'gemini' | 'openai_compatible';
  base_url?: string | null;
  models: string[];
  enabled?: boolean;
  api_key?: string;
}

export interface AIProviderUpdatePayload {
  name?: string;
  type?: 'gemini' | 'openai_compatible';
  base_url?: string | null;
  models?: string[];
  enabled?: boolean;
  api_key?: string;
}

export interface AISettingsUpdatePayload {
  default_provider_id?: string | null;
  default_model?: string;
  fallback_provider_id?: string | null;
  fallback_model?: string | null;
  temperature?: number;
  max_output_tokens?: number;
  request_timeout_seconds?: number;
  max_retries?: number;
}

export interface AIProviderTestResponse {
  success: boolean;
  latency_ms: number;
  response?: string | null;
  error?: string | null;
}

export interface AIModelsResponse {
  models: string[];
  source: 'remote' | 'stored';
  error?: string | null;
}

export interface AISettingsAudit {
  id: string;
  user_id?: string | null;
  user_name?: string | null;
  action: string;
  details: Record<string, any>;
  created_at: string;
}

export const aiSettingsApi = {
  async getOverview(): Promise<AdminAISettingsOverview> {
    const res = await api.get<AdminAISettingsOverview>('/admin/ai-settings');
    return res.data;
  },

  async updateSettings(payload: AISettingsUpdatePayload): Promise<AISettings> {
    const res = await api.put<AISettings>('/admin/ai-settings', payload);
    return res.data;
  },

  async createProvider(payload: AIProviderCreatePayload): Promise<AIProvider> {
    const res = await api.post<AIProvider>('/admin/ai-settings/providers', payload);
    return res.data;
  },

  async updateProvider(id: string, payload: AIProviderUpdatePayload): Promise<AIProvider> {
    const res = await api.put<AIProvider>(`/admin/ai-settings/providers/${id}`, payload);
    return res.data;
  },

  async deleteProvider(id: string): Promise<{ message: string }> {
    const res = await api.delete<{ message: string }>(`/admin/ai-settings/providers/${id}`);
    return res.data;
  },

  async testProvider(id: string): Promise<AIProviderTestResponse> {
    const res = await api.post<AIProviderTestResponse>(`/admin/ai-settings/providers/${id}/test`);
    return res.data;
  },

  async listProviderModels(id: string): Promise<AIModelsResponse> {
    const res = await api.get<AIModelsResponse>(`/admin/ai-settings/providers/${id}/models`);
    return res.data;
  },

  async getAuditLogs(limit: number = 20): Promise<AISettingsAudit[]> {
    const res = await api.get<AISettingsAudit[]>('/admin/ai-settings/audit', {
      params: { limit },
    });
    return res.data;
  },
};
