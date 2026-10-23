import api from './api';

export interface Center {
  id: string;
  name: string;
  address?: string | null;
  logo_url?: string | null;
  phone?: string | null;
  email?: string | null;
  facebook_page_url?: string | null;
  subscription_plan: 'free' | 'basic' | 'premium' | string;
  created_at?: string;
  updated_at?: string;
  branches_count: number;
  members_count: number;
  classes_count: number;
}

export interface CenterCreatePayload {
  name: string;
  address?: string;
  logo_url?: string;
  phone?: string;
  email?: string;
  facebook_page_url?: string;
  subscription_plan?: string;
}

export interface CenterUpdatePayload {
  name?: string;
  address?: string;
  logo_url?: string;
  phone?: string;
  email?: string;
  facebook_page_url?: string;
  subscription_plan?: string;
}

export const centerApi = {
  getCenters: async (search?: string): Promise<Center[]> => {
    const res = await api.get<Center[]>('/centers', {
      params: search ? { search } : undefined,
    });
    return res.data;
  },

  getCenter: async (id: string): Promise<Center> => {
    const res = await api.get<Center>(`/centers/${id}`);
    return res.data;
  },

  createCenter: async (payload: CenterCreatePayload): Promise<Center> => {
    const res = await api.post<Center>('/centers', payload);
    return res.data;
  },

  updateCenter: async (id: string, payload: CenterUpdatePayload): Promise<Center> => {
    const res = await api.put<Center>(`/centers/${id}`, payload);
    return res.data;
  },

  deleteCenter: async (id: string): Promise<{ message: string; id: string }> => {
    const res = await api.delete(`/centers/${id}`);
    return res.data;
  },

  cleanupTestCenters: async (): Promise<{ deleted_count: number; message: string }> => {
    const res = await api.post('/centers/cleanup-test-centers');
    return res.data;
  },
};
