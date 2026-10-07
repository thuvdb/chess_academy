import { useState, useEffect } from 'react';
import { X, Plus, Trash2 } from 'lucide-react';
import { createClass, updateClass, type ClassItem, type ClassCreatePayload } from '../lib/classApi';
import toast from 'react-hot-toast';

const LEVELS = ['beginner', 'intermediate', 'advanced', 'tournament'];
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

interface Props {
  initialData?: ClassItem | null;
  onClose: (refresh?: boolean) => void;
}

interface ScheduleSlot {
  day: string;
  start_time: string;
  end_time: string;
}

export default function ClassForm({ initialData, onClose }: Props) {
  const isEdit = Boolean(initialData);

  const [formData, setFormData] = useState({
    name: '',
    level: 'beginner',
    max_students: 30,
    teacher_id: '',
  });
  const [slots, setSlots] = useState<ScheduleSlot[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (initialData) {
      setFormData({
        name: initialData.name,
        level: initialData.level ?? 'beginner',
        max_students: initialData.max_students,
        teacher_id: initialData.teacher_id ?? '',
      });
      // Convert schedule_json to slots
      if (initialData.schedule_json) {
        const parsed: ScheduleSlot[] = [];
        Object.entries(initialData.schedule_json).forEach(([day, times]) => {
          times.forEach(timeStr => {
            const [start, end] = timeStr.split('-');
            parsed.push({ day, start_time: start || '', end_time: end || '' });
          });
        });
        setSlots(parsed);
      }
    }
  }, [initialData]);

  const addSlot = () => setSlots(prev => [...prev, { day: 'Mon', start_time: '18:00', end_time: '19:30' }]);
  const removeSlot = (i: number) => setSlots(prev => prev.filter((_, idx) => idx !== i));
  const updateSlot = (i: number, field: keyof ScheduleSlot, value: string) =>
    setSlots(prev => prev.map((s, idx) => idx === i ? { ...s, [field]: value } : s));

  const buildScheduleJson = (): Record<string, string[]> => {
    const result: Record<string, string[]> = {};
    slots.forEach(({ day, start_time, end_time }) => {
      if (!result[day]) result[day] = [];
      const timeStr = end_time ? `${start_time}-${end_time}` : start_time;
      if (!result[day].includes(timeStr)) result[day].push(timeStr);
    });
    return result;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error('Class name is required');
      return;
    }
    setLoading(true);
    try {
      const payload: ClassCreatePayload = {
        name: formData.name.trim(),
        level: formData.level,
        max_students: formData.max_students,
        schedule_json: slots.length > 0 ? buildScheduleJson() : undefined,
        teacher_id: formData.teacher_id || undefined,
      };

      if (isEdit && initialData) {
        await updateClass(initialData.id, payload);
        toast.success('Class updated successfully!');
      } else {
        await createClass(payload);
        toast.success('Class created successfully!');
      }
      onClose(true);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      toast.error(axiosErr.response?.data?.detail ?? 'Failed to save class');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-800">
          <h2 className="text-white font-bold text-lg">
            {isEdit ? 'Edit Class' : 'Create New Class'}
          </h2>
          <button
            onClick={() => onClose()}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto">
          {/* Name */}
          <div>
            <label className="block text-slate-300 text-sm font-medium mb-1.5">Class Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={e => setFormData(p => ({ ...p, name: e.target.value }))}
              placeholder="e.g. Junior Chess - Group A"
              className="w-full bg-slate-800 border border-slate-700 text-white rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-amber-500 transition-colors placeholder-slate-500"
            />
          </div>

          {/* Level + Max Students */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1.5">Level</label>
              <select
                value={formData.level}
                onChange={e => setFormData(p => ({ ...p, level: e.target.value }))}
                className="w-full bg-slate-800 border border-slate-700 text-white rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-amber-500 transition-colors"
              >
                {LEVELS.map(l => (
                  <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-slate-300 text-sm font-medium mb-1.5">Max Students</label>
              <input
                type="number"
                min={1}
                max={100}
                value={formData.max_students}
                onChange={e => setFormData(p => ({ ...p, max_students: parseInt(e.target.value) || 30 }))}
                className="w-full bg-slate-800 border border-slate-700 text-white rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-amber-500 transition-colors"
              />
            </div>
          </div>

          {/* Schedule */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-slate-300 text-sm font-medium">Schedule</label>
              <button
                type="button"
                onClick={addSlot}
                className="flex items-center gap-1 text-amber-400 hover:text-amber-300 text-xs font-medium"
              >
                <Plus className="w-3.5 h-3.5" /> Add Time Slot
              </button>
            </div>
            {slots.length === 0 && (
              <p className="text-slate-500 text-xs italic py-2">No schedule set — click "Add Time Slot" to add sessions</p>
            )}
            <div className="space-y-2">
              {slots.map((slot, i) => (
                <div key={i} className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3 bg-slate-800 border border-slate-700 rounded-xl p-3">
                  <div className="flex items-center justify-between w-full sm:w-auto gap-2">
                    <select
                      value={slot.day}
                      onChange={e => updateSlot(i, 'day', e.target.value)}
                      className="bg-slate-700/50 text-white text-sm rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer w-28"
                    >
                      {DAYS.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                    <button type="button" onClick={() => removeSlot(i)} className="sm:hidden text-slate-500 hover:text-red-400 transition-colors p-1">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="flex items-center flex-1 w-full gap-2 sm:border-l sm:border-slate-700 sm:pl-3">
                    <input
                      type="time"
                      value={slot.start_time}
                      onChange={e => updateSlot(i, 'start_time', e.target.value)}
                      className="bg-slate-700/50 text-white text-sm rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer flex-1 min-w-[100px]"
                    />
                    <span className="text-slate-500 text-xs font-medium">to</span>
                    <input
                      type="time"
                      value={slot.end_time}
                      onChange={e => updateSlot(i, 'end_time', e.target.value)}
                      className="bg-slate-700/50 text-white text-sm rounded-lg px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer flex-1 min-w-[100px]"
                    />
                  </div>
                  <button type="button" onClick={() => removeSlot(i)} className="hidden sm:block text-slate-500 hover:text-red-400 transition-colors ml-1 p-1">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-800">
          <button
            type="button"
            onClick={() => onClose()}
            className="px-4 py-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition-all text-sm"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center gap-2 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 disabled:cursor-not-allowed text-slate-900 font-semibold px-6 py-2 rounded-xl transition-all text-sm"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-slate-900/30 border-t-slate-900 rounded-full animate-spin" />
            ) : null}
            {isEdit ? 'Update Class' : 'Create Class'}
          </button>
        </div>
      </div>
    </div>
  );
}
