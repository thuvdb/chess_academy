import React, { useState, useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'react-hot-toast';
import api from '../lib/api';
import { Camera, Save, Loader2 } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { DEFAULT_TIMEZONE, resolveMediaUrl } from '../config';

interface ProfileForm {
  full_name: string;
  username: string;
  phone?: string;
  bio: string;
  location: string;
  country: string;
  language: string;
  timezone: string;
  avatar_url: string;
}

const Profile = () => {
  const { user, setUser } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const { register, handleSubmit, reset, setValue, watch } = useForm<ProfileForm>();
  const rawAvatar = watch('avatar_url') || user?.avatar_url;
  const currentAvatar = rawAvatar
    ? resolveMediaUrl(rawAvatar)
    : 'https://ui-avatars.com/api/?name=' + (user?.full_name || 'User') + '&background=random';

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const { data } = await api.get('/auth/me');
        reset({
          full_name: data.full_name || '',
          username: data.username || '',
          phone: data.phone || '',
          bio: data.bio || '',
          location: data.location || '',
          country: data.country || 'Vietnam',
          language: data.language || 'Vietnamese',
          timezone: data.timezone || DEFAULT_TIMEZONE,
          avatar_url: data.avatar_url || '',
        });
      } catch (error) {
        toast.error('Failed to load profile');
      }
    };
    fetchProfile();
  }, [reset]);

  const onSubmit = async (data: ProfileForm) => {
    setLoading(true);
    try {
      const resp = await api.put('/users/me', data);
      setUser(resp.data);
      toast.success('Profile updated successfully');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Update failed');
    } finally {
      setLoading(false);
    }
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    try {
      // For avatar upload, we use multipart/form-data
      const res = await api.post('/users/me/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setValue('avatar_url', res.data.avatar_url);
      toast.success('Avatar uploaded successfully! Make sure to save profile.');
    } catch (error) {
      toast.error('Failed to upload avatar');
    } finally {
      setUploading(false);
      // Reset input
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold text-white mb-6">Public Profile</h1>
      
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl flex flex-col md:flex-row gap-8">
        
        {/* Avatar Section */}
        <div className="flex flex-col items-center space-y-4 md:w-1/3">
          <div className="relative group cursor-pointer" onClick={handleAvatarClick}>
            {uploading ? (
              <div className="w-40 h-40 rounded-xl border-4 border-slate-700 bg-slate-800 flex flex-col items-center justify-center gap-2">
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                <span className="text-sm text-slate-400">Uploading...</span>
              </div>
            ) : (
              <>
                <img 
                  src={currentAvatar} 
                  alt="Avatar" 
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = 'https://ui-avatars.com/api/?name=' + (user?.full_name || 'User') + '&background=random';
                  }}
                  className="w-40 h-40 rounded-xl object-cover border-4 border-slate-700 bg-slate-800"
                />
                <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity rounded-xl">
                  <Camera className="w-8 h-8 text-white" />
                </div>
              </>
            )}
          </div>
          <p className="text-sm text-slate-400">Click avatar to upload</p>
          <input 
            type="file" 
            accept="image/*"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
          />
          <div className="w-full">
            <p className="text-xs text-slate-500 mb-1 text-center">Or paste image URL:</p>
            <input 
              type="text" 
              placeholder="https://..." 
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-sm text-white"
              {...register('avatar_url')}
            />
          </div>
        </div>

        {/* Form Section */}
        <div className="flex-1">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Username</label>
                <input 
                  type="text" 
                  {...register('username')}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Full Name</label>
                <input 
                  type="text" 
                  {...register('full_name')}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Phone</label>
                <input 
                  type="tel" 
                  {...register('phone')}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Location</label>
                <input 
                  type="text" 
                  {...register('location')}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Country</label>
                <select 
                  {...register('country')}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  <option value="Vietnam">Vietnam</option>
                  <option value="United States">United States</option>
                  <option value="United Kingdom">United Kingdom</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Language</label>
                <select 
                  {...register('language')}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  <option value="Vietnamese">Vietnamese</option>
                  <option value="English">English</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Timezone</label>
                <select 
                  {...register('timezone')}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  <option value="Asia/Ho_Chi_Minh">Asia/Ho_Chi_Minh (+07:00)</option>
                  <option value="UTC">UTC (00:00)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">About Me (Bio)</label>
              <textarea 
                {...register('bio')}
                rows={4}
                placeholder="Your short bio will appear next to your avatar..."
                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
              ></textarea>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-700">
              <button 
                type="submit" 
                disabled={loading}
                className="flex items-center gap-2 px-6 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                <Save className="w-5 h-5" />
                {loading ? 'Saving...' : 'Save Profile'}
              </button>
            </div>
            
          </form>
        </div>

      </div>
    </div>
  );
};

export default Profile;
