import { useState, useEffect } from 'react';
import api from '../lib/api';
import toast from 'react-hot-toast';

interface FeePlan {
  id: string;
  name: string;
  amount: number;
  currency: string;
}

interface GenerateInvoiceModalProps {
  classId: string;
  centerId: string;
  onClose: (refresh?: boolean) => void;
}

export default function GenerateInvoiceModal({ classId, centerId, onClose }: GenerateInvoiceModalProps) {
  const [feePlans, setFeePlans] = useState<FeePlan[]>([]);
  const [feePlanId, setFeePlanId] = useState('');
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Fetch fee plans for center
    const fetchFeePlans = async () => {
      try {
        const res = await api.get(`/fee-plans/center/${centerId}`);
        setFeePlans(res.data.filter((p: any) => p.is_active));
        if (res.data.length > 0) {
          setFeePlanId(res.data[0].id);
        }
      } catch (err) {
        toast.error('Failed to load fee plans');
      }
    };
    fetchFeePlans();
  }, [centerId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feePlanId || !periodStart || !periodEnd || !dueDate) {
      toast.error('Please fill all fields');
      return;
    }
    
    setLoading(true);
    try {
      await api.post('/invoices/generate', {
        class_id: classId,
        fee_plan_id: feePlanId,
        period_start: new Date(periodStart).toISOString(),
        period_end: new Date(periodEnd).toISOString(),
        due_date: new Date(dueDate).toISOString(),
      });
      toast.success('Invoices generated successfully');
      onClose(true);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to generate invoices');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-slate-800 rounded-2xl border border-slate-700 w-full max-w-md overflow-hidden shadow-2xl">
        <div className="p-6 border-b border-slate-700 flex justify-between items-center bg-slate-800/50">
          <h2 className="text-xl font-bold text-white">Generate Class Invoices</h2>
          <button 
            onClick={() => onClose()}
            className="text-slate-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Select Fee Plan</label>
            <select
              required
              value={feePlanId}
              onChange={(e) => setFeePlanId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors appearance-none"
            >
              <option value="" disabled>Select a fee plan</option>
              {feePlans.map(plan => (
                <option key={plan.id} value={plan.id}>
                  {plan.name} - {plan.amount.toLocaleString()} {plan.currency}
                </option>
              ))}
            </select>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Period Start</label>
              <input
                type="date"
                required
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Period End</label>
              <input
                type="date"
                required
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Due Date</label>
            <input
              type="date"
              required
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>

          <div className="pt-2 flex gap-3">
            <button
              type="button"
              onClick={() => onClose()}
              className="flex-1 px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-white rounded-xl font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2.5 bg-linear-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-medium transition-all shadow-lg shadow-blue-900/20 disabled:opacity-50"
            >
              {loading ? 'Generating...' : 'Generate Invoices'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
