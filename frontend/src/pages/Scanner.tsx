import { useState, useCallback, useRef, useEffect } from 'react';
import { Upload, Search, CheckCircle, XCircle, AlertTriangle, FileText, Loader2, RefreshCw, Eye } from 'lucide-react';
import api from '../lib/api';
import toast from 'react-hot-toast';
import { useAuthStore } from '../store/authStore';

// ── Types ──────────────────────────────────────────────────
interface ScanJob {
  id: string;
  file_name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_pages: number | null;
  boards_found: number;
  boards_approved: number;
  error_message: string | null;
  processing_time_ms: number | null;
  created_at: string;
}

interface ScanResult {
  id: string;
  page_number: number;
  board_index: number;
  board_image_url: string | null;
  bounding_box: { x: number; y: number; width: number; height: number } | null;
  confidence_board: number | null;
  fen_candidate: string | null;
  fen_final: string | null;
  review_status: 'pending' | 'approved' | 'corrected' | 'rejected';
  cell_confidence: Record<string, { piece: string; confidence: number }> | null;
}

// ── Status Badges ──────────────────────────────────────────
const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  processing: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  completed: 'bg-green-500/15 text-green-400 border-green-500/30',
  failed: 'bg-red-500/15 text-red-400 border-red-500/30',
  approved: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  corrected: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  rejected: 'bg-red-500/15 text-red-400 border-red-500/30',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${STATUS_STYLES[status] ?? 'bg-slate-500/15 text-slate-400 border-slate-500/30'}`}>
      {status === 'processing' && <Loader2 className="w-3 h-3 animate-spin" />}
      {status === 'completed' && <CheckCircle className="w-3 h-3" />}
      {status === 'failed' && <XCircle className="w-3 h-3" />}
      {status === 'approved' && <CheckCircle className="w-3 h-3" />}
      {status === 'rejected' && <XCircle className="w-3 h-3" />}
      {status}
    </span>
  );
}


export default function Scanner() {
  const { user } = useAuthStore();
  const [jobs, setJobs] = useState<ScanJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<ScanJob | null>(null);
  const [results, setResults] = useState<ScanResult[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [loadingResults, setLoadingResults] = useState(false);
  const [editingFen, setEditingFen] = useState<string | null>(null);
  const [editFenValue, setEditFenValue] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Load Jobs ──────────────────────────────────────────
  const fetchJobs = useCallback(async () => {
    setLoadingJobs(true);
    try {
      const { data } = await api.get('/scan/jobs');
      setJobs(data);
    } catch {
      toast.error('Failed to load scan jobs');
    } finally {
      setLoadingJobs(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // ── Poll processing jobs ───────────────────────────────
  useEffect(() => {
    const hasProcessing = jobs.some(j => j.status === 'pending' || j.status === 'processing');
    if (hasProcessing) {
      pollRef.current = setInterval(fetchJobs, 3000);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobs, fetchJobs]);

  // ── Upload PDF ─────────────────────────────────────────
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Only PDF files are accepted');
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      toast.error('File too large (max 50 MB)');
      return;
    }

    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      // Append user's center_id if assigned; otherwise backend defaults for super_admin
      if (user?.center_id) {
        form.append('center_id', user.center_id);
      }

      const { data } = await api.post('/scan/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast.success(`Uploaded: ${file.name}`);
      setJobs(prev => [data, ...prev]);
    } catch (err) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      toast.error(axiosErr.response?.data?.detail ?? 'Upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // ── Load Results ───────────────────────────────────────
  const loadResults = async (job: ScanJob) => {
    setSelectedJob(job);
    setLoadingResults(true);
    try {
      const { data } = await api.get(`/scan/jobs/${job.id}/results`);
      setResults(data);
    } catch {
      toast.error('Failed to load results');
      setResults([]);
    } finally {
      setLoadingResults(false);
    }
  };

  // ── Review Actions ─────────────────────────────────────
  const approveResult = async (resultId: string) => {
    try {
      const { data } = await api.post(`/scan/results/${resultId}/approve`);
      setResults(prev => prev.map(r => r.id === resultId ? data : r));
      toast.success('Result approved');
    } catch {
      toast.error('Failed to approve');
    }
  };

  const rejectResult = async (resultId: string) => {
    try {
      const { data } = await api.post(`/scan/results/${resultId}/reject`);
      setResults(prev => prev.map(r => r.id === resultId ? data : r));
      toast.success('Result rejected');
    } catch {
      toast.error('Failed to reject');
    }
  };

  const submitFenEdit = async (resultId: string) => {
    if (!editFenValue.trim()) return;
    try {
      const { data } = await api.put(`/scan/results/${resultId}/review`, {
        fen_final: editFenValue.trim(),
        side_to_move: 'w',
        castling_rights: '-',
        en_passant: '-',
      });
      setResults(prev => prev.map(r => r.id === resultId ? data : r));
      setEditingFen(null);
      toast.success('FEN updated');
    } catch {
      toast.error('Failed to update FEN');
    }
  };

  // ── Low Confidence Helper ──────────────────────────────
  const getLowConfCells = (result: ScanResult) => {
    if (!result.cell_confidence) return [];
    return Object.entries(result.cell_confidence)
      .filter(([, v]) => v.piece !== 'empty' && v.confidence < 0.70)
      .map(([sq, v]) => ({ square: sq, piece: v.piece, confidence: v.confidence }))
      .sort((a, b) => a.confidence - b.confidence);
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-linear-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-purple-500/25">
              <Search className="w-5 h-5 text-white" />
            </div>
            AI Scanner
          </h1>
          <p className="text-slate-400 mt-1">Upload chess book PDFs and review detected positions</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchJobs}
            disabled={loadingJobs}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 border border-slate-700 transition-all text-sm font-medium"
          >
            <RefreshCw className={`w-4 h-4 ${loadingJobs ? 'animate-spin' : ''}`} />
            Refresh
          </button>

          <label className={`flex items-center gap-2 px-5 py-2.5 rounded-xl cursor-pointer transition-all text-sm font-medium shadow-lg ${uploading ? 'bg-slate-700 text-slate-400 cursor-wait' : 'bg-linear-to-r from-violet-600 to-purple-600 text-white hover:from-violet-500 hover:to-purple-500 shadow-purple-500/25'}`}>
            {uploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
            {uploading ? 'Uploading...' : 'Upload PDF'}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Job List */}
        <div className="lg:col-span-1">
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-700/50">
              <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Scan Jobs ({jobs.length})
              </h2>
            </div>

            <div className="max-h-[calc(100vh-280px)] overflow-y-auto">
              {jobs.length === 0 && !loadingJobs && (
                <div className="p-8 text-center">
                  <Upload className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-500 text-sm">No scans yet. Upload a PDF to get started.</p>
                </div>
              )}

              {jobs.map(job => (
                <button
                  key={job.id}
                  onClick={() => loadResults(job)}
                  className={`w-full text-left px-5 py-4 border-b border-slate-700/30 transition-all hover:bg-slate-700/30 ${selectedJob?.id === job.id ? 'bg-slate-700/40 border-l-2 border-l-purple-500' : ''}`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-white text-sm font-medium truncate max-w-45">{job.file_name}</span>
                    <StatusBadge status={job.status} />
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    {job.total_pages != null && <span>{job.total_pages} pages</span>}
                    <span>{job.boards_found} boards</span>
                    {job.processing_time_ms != null && <span>{(job.processing_time_ms / 1000).toFixed(1)}s</span>}
                  </div>
                  <p className="text-xs text-slate-600 mt-1">{new Date(job.created_at).toLocaleString()}</p>
                  {job.error_message && (
                    <p className="text-xs text-red-400 mt-1 truncate">{job.error_message}</p>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Results */}
        <div className="lg:col-span-2">
          {!selectedJob ? (
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-12 text-center">
              <Eye className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-slate-400">Select a scan job</h3>
              <p className="text-slate-500 text-sm mt-1">Click a job on the left to view detected boards</p>
            </div>
          ) : (
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-700/50 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-300">
                  Results — {selectedJob.file_name}
                </h2>
                <StatusBadge status={selectedJob.status} />
              </div>

              {loadingResults ? (
                <div className="p-12 text-center">
                  <Loader2 className="w-8 h-8 text-purple-400 mx-auto animate-spin mb-3" />
                  <p className="text-slate-400 text-sm">Loading results...</p>
                </div>
              ) : results.length === 0 ? (
                <div className="p-12 text-center">
                  <Search className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-500 text-sm">
                    {selectedJob.status === 'processing'
                      ? 'Processing... Boards will appear here when ready.'
                      : 'No boards detected.'}
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 p-5 max-h-[calc(100vh-280px)] overflow-y-auto">
                  {results.map(result => {
                    const lowConf = getLowConfCells(result);
                    const fen = result.fen_final || result.fen_candidate;

                    return (
                      <div
                        key={result.id}
                        className="bg-slate-900/60 border border-slate-700/50 rounded-xl overflow-hidden"
                      >
                        {/* Board Image */}
                        <div className="aspect-square bg-slate-950 flex items-center justify-center relative">
                          {result.board_image_url ? (
                            <img
                              src={result.board_image_url}
                              alt={`Board page ${result.page_number}`}
                              className="w-full h-full object-contain"
                            />
                          ) : (
                            <div className="text-slate-600 text-sm">No image</div>
                          )}
                          <div className="absolute top-2 left-2">
                            <span className="bg-slate-900/80 text-slate-300 text-xs px-2 py-1 rounded-lg">
                              P{result.page_number} / B{result.board_index}
                            </span>
                          </div>
                          {result.confidence_board != null && (
                            <div className="absolute top-2 right-2">
                              <span className={`text-xs px-2 py-1 rounded-lg ${result.confidence_board >= 0.90 ? 'bg-green-900/80 text-green-300' : result.confidence_board >= 0.70 ? 'bg-amber-900/80 text-amber-300' : 'bg-red-900/80 text-red-300'}`}>
                                {(result.confidence_board * 100).toFixed(0)}%
                              </span>
                            </div>
                          )}
                        </div>

                        {/* Info */}
                        <div className="p-4 space-y-3">
                          {/* FEN */}
                          {fen && (
                            <div>
                              <label className="text-xs font-medium text-slate-500 mb-1 block">FEN</label>
                              {editingFen === result.id ? (
                                <div className="flex gap-2">
                                  <input
                                    value={editFenValue}
                                    onChange={e => setEditFenValue(e.target.value)}
                                    className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:ring-1 focus:ring-purple-500 focus:border-purple-500 outline-none"
                                  />
                                  <button
                                    onClick={() => submitFenEdit(result.id)}
                                    className="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-xs hover:bg-purple-500"
                                  >
                                    Save
                                  </button>
                                  <button
                                    onClick={() => setEditingFen(null)}
                                    className="px-3 py-1.5 bg-slate-700 text-slate-300 rounded-lg text-xs hover:bg-slate-600"
                                  >
                                    Cancel
                                  </button>
                                </div>
                              ) : (
                                <p
                                  onClick={() => { setEditingFen(result.id); setEditFenValue(fen); }}
                                  className="text-xs font-mono text-slate-300 bg-slate-800/60 px-3 py-2 rounded-lg cursor-pointer hover:bg-slate-700/60 transition-colors break-all"
                                  title="Click to edit"
                                >
                                  {fen}
                                </p>
                              )}
                            </div>
                          )}

                          {/* Low confidence warning */}
                          {lowConf.length > 0 && (
                            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
                              <div className="flex items-center gap-2 mb-2">
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                                <span className="text-xs font-medium text-amber-400">
                                  {lowConf.length} cell(s) need review
                                </span>
                              </div>
                              {lowConf.map(lc => (
                                <div key={lc.square} className="flex items-center justify-between text-xs py-0.5">
                                  <span className="text-slate-300 font-mono">{lc.square}</span>
                                  <span className="text-slate-400">{lc.piece}</span>
                                  <span className={`font-medium ${lc.confidence < 0.50 ? 'text-red-400' : 'text-amber-400'}`}>
                                    {(lc.confidence * 100).toFixed(0)}%
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Actions */}
                          <div className="flex items-center justify-between pt-2">
                            <StatusBadge status={result.review_status} />

                            {result.review_status === 'pending' && (
                              <div className="flex gap-2">
                                <button
                                  onClick={() => approveResult(result.id)}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-medium hover:bg-emerald-600/30 transition-all"
                                >
                                  <CheckCircle className="w-3.5 h-3.5" />
                                  Approve
                                </button>
                                <button
                                  onClick={() => rejectResult(result.id)}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600/20 text-red-400 border border-red-500/30 rounded-lg text-xs font-medium hover:bg-red-600/30 transition-all"
                                >
                                  <XCircle className="w-3.5 h-3.5" />
                                  Reject
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
