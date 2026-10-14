import api from './api';

export interface SettingItem {
  id: string;
  key: string;
  value: string;
  value_type: string;
  description?: string;
  category: string;
  is_overridable: boolean;
  center_id?: string | null;
}

export interface CatalogItem {
  id: string;
  catalog_type: string;
  code: string;
  label: string;
  order_index: number;
  is_active: boolean;
  center_id?: string | null;
}

export const settingsApi = {
  getSettings: async (category?: string): Promise<SettingItem[]> => {
    const res = await api.get<SettingItem[]>('/settings', {
      params: category ? { category } : undefined,
    });
    return res.data;
  },

  updateSetting: async (key: string, value: string): Promise<SettingItem> => {
    const res = await api.put<SettingItem>(`/settings/${key}`, { value });
    return res.data;
  },

  getCatalogs: async (catalogType?: string, activeOnly: boolean = false): Promise<CatalogItem[]> => {
    const res = await api.get<CatalogItem[]>('/catalogs', {
      params: {
        ...(catalogType ? { catalog_type: catalogType } : {}),
        active_only: activeOnly,
      },
    });
    return res.data;
  },

  createCatalogItem: async (data: {
    catalog_type: string;
    code: string;
    label: string;
    order_index?: number;
    is_active?: boolean;
    center_id?: string | null;
  }): Promise<CatalogItem> => {
    const res = await api.post<CatalogItem>('/catalogs', data);
    return res.data;
  },

  updateCatalogItem: async (
    id: string,
    data: { label?: string; order_index?: number; is_active?: boolean }
  ): Promise<CatalogItem> => {
    const res = await api.put<CatalogItem>(`/catalogs/${id}`, data);
    return res.data;
  },

  deactivateCatalogItem: async (id: string): Promise<CatalogItem> => {
    const res = await api.delete<CatalogItem>(`/catalogs/${id}`);
    return res.data;
  },
};
