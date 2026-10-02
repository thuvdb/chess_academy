import { useState, useEffect } from 'react';
import { useAuthStore } from '../store/authStore';
import api from '../lib/api';
import toast from 'react-hot-toast';

interface Invoice {
  id: string;
  invoice_number: string;
  status: string;
  amount: number;
  currency: string;
  description: string;
  due_date: string | null;
  student_id: string;
}

export default function Invoices() {
  const { user } = useAuthStore();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [qrModal, setQrModal] = useState<{show: boolean, url: string, invoiceId: string | null}>({show: false, url: '', invoiceId: null});
  
  const isAdmin = user?.role === 'admin' || user?.role === 'center_admin';

  useEffect(() => {
    fetchInvoices();
  }, []);

  const fetchInvoices = async () => {
    try {
      const endpoint = isAdmin ? '/invoices/center' : '/invoices/my';
      const res = await api.get(endpoint);
      setInvoices(res.data);
    } catch (err) {
      toast.error('Failed to load invoices');
    } finally {
      setLoading(false);
    }
  };

  const handleShowQR = async (invoiceId: string) => {
    try {
      const res = await api.get(`/invoices/${invoiceId}/qr`);
      setQrModal({ show: true, url: res.data.qr_url, invoiceId });
    } catch (err) {
      toast.error('Failed to load QR code');
    }
  };

  const handleConfirmPayment = async (invoiceId: string) => {
    try {
      await api.post('/payments/confirm', {
        invoice_id: invoiceId,
        notes: 'Confirmed via dashboard'
      });
      toast.success('Payment confirmed successfully');
      fetchInvoices();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to confirm payment');
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto text-slate-200">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-linear-to-r from-blue-400 to-indigo-400">
            Invoices
          </h1>
          <p className="text-slate-400 mt-2">Manage tuition and payments</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <div className="bg-slate-800 border border-slate-700 rounded-2xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/50 text-slate-400 uppercase text-xs font-semibold">
              <tr>
                <th className="px-6 py-4">Invoice No</th>
                {isAdmin && <th className="px-6 py-4">Student ID</th>}
                <th className="px-6 py-4">Description</th>
                <th className="px-6 py-4">Amount</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-slate-700/30 transition-colors">
                  <td className="px-6 py-4 font-medium text-white">{inv.invoice_number}</td>
                  {isAdmin && (
                     <td className="px-6 py-4 text-slate-400 font-mono text-xs">
                       {inv.student_id.substring(0, 8)}...
                     </td>
                  )}
                  <td className="px-6 py-4 text-slate-300">{inv.description}</td>
                  <td className="px-6 py-4 font-bold text-blue-400">
                    {inv.amount.toLocaleString()} <span className="text-xs text-slate-400">{inv.currency}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${
                      inv.status === 'paid' 
                        ? 'bg-green-500/10 text-green-400 border border-green-500/20' 
                        : inv.status === 'pending' || inv.status === 'published'
                        ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                        : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                    }`}>
                      {inv.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right flex justify-end gap-2">
                    {inv.status !== 'paid' && (
                      <button
                        onClick={() => handleShowQR(inv.id)}
                        className="px-3 py-1.5 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 border border-blue-500/20 rounded-lg text-xs font-medium transition-colors"
                      >
                        {isAdmin ? 'View QR' : 'Pay Now'}
                      </button>
                    )}
                    {isAdmin && inv.status !== 'paid' && (
                      <button
                        onClick={() => handleConfirmPayment(inv.id)}
                        className="px-3 py-1.5 bg-green-500/10 text-green-400 hover:bg-green-500/20 border border-green-500/20 rounded-lg text-xs font-medium transition-colors"
                      >
                        Confirm
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {invoices.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-slate-400">
                    No invoices found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* QR Code Modal */}
      {qrModal.show && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl w-full max-w-sm overflow-hidden shadow-2xl relative">
            <button 
              onClick={() => setQrModal({show: false, url: '', invoiceId: null})}
              className="absolute top-4 right-4 text-slate-500 hover:text-slate-900 bg-slate-100 rounded-full w-8 h-8 flex items-center justify-center transition-colors"
            >
              ✕
            </button>
            <div className="p-6 pt-10 text-center">
              <h3 className="text-xl font-bold text-slate-900 mb-2">Scan to Pay</h3>
              <p className="text-slate-500 text-sm mb-6">Open your banking app and scan this VietQR code to transfer</p>
              
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 flex justify-center mb-6">
                <img src={qrModal.url} alt="VietQR" className="w-full h-auto rounded-lg" />
              </div>
              
              <div className="text-sm text-slate-500">
                Payment will be confirmed automatically or manually by admin.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
