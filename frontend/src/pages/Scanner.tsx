import { useState, useCallback, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Chessboard } from 'react-chessboard';
import { Upload, Search, CheckCircle, XCircle, AlertTriangle, FileText, Loader2, RefreshCw, Eye, Trash2, BookOpen, Play, ZoomIn, ZoomOut, Maximize2, X, RotateCcw, ChevronLeft, ChevronRight, Filter } from 'lucide-react';
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
  puzzle_id: string | null;
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
  const [savingApproved, setSavingApproved] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [filterStatus, setFilterStatus] = useState<'all' | 'pending' | 'approved' | 'rejected' | 'needs_review'>('all');
  const [pageSearch, setPageSearch] = useState('');
  const pageSize = 20;
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Zoom Modal State ────────────────────────────────────
  const [zoomModal, setZoomModal] = useState<{
    imageUrl: string;
    title: string;
    fen: string | null;
    pageNumber: number;
    boardIndex: number;
    confidence: number | null;
  } | null>(null);
  const [zoomScale, setZoomScale] = useState(1);

  // Close zoom modal on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setZoomModal(null);
      }
    };
    if (zoomModal) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [zoomModal]);

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

  // ── Delete Job ─────────────────────────────────────────
  const deleteJob = async (e: React.MouseEvent, jobId: string) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this scan job? This action cannot be undone.')) return;
    
    try {
      await api.delete(`/scan/jobs/${jobId}`);
      toast.success('Scan job deleted');
      setJobs(prev => prev.filter(j => j.id !== jobId));
      if (selectedJob?.id === jobId) setSelectedJob(null);
    } catch {
      toast.error('Failed to delete scan job');
    }
  };

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
    setCurrentPage(1);
    setFilterStatus('all');
    setPageSearch('');
    setLoadingResults(true);
    try {
      const { data } = await api.get(`/scan/jobs/${job.id}/results`);
      setResults(data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      const detail = axiosErr.response?.data?.detail || axiosErr.message || 'Lỗi kết nối hoặc phản hồi quá chậm';
      toast.error(`Không thể tải kết quả: ${detail}`);
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
      if (data.puzzle_id) {
        toast.success('Đã duyệt và tạo bài tập vào Thư viện Puzzle Bank!');
      } else {
        toast.success('Đã duyệt kết quả scan');
      }
    } catch {
      toast.error('Failed to approve');
    }
  };

  const saveSingleToPuzzle = async (result: ScanResult) => {
    const fen = result.fen_final || result.fen_candidate;
    if (!fen) return;
    try {
      const { data } = await api.post('/puzzles/from-scan', {
        scan_result_id: result.id,
        title: `${selectedJob?.file_name || 'Scan'} - Trang ${result.page_number} / Bàn ${result.board_index}`,
        description: `Bài tập từ sách ${selectedJob?.file_name || ''} (Trang ${result.page_number}, Bàn ${result.board_index})`,
        difficulty: 'easy',
      });
      setResults(prev => prev.map(r => r.id === result.id ? { ...r, puzzle_id: data.id } : r));
      toast.success('Đã lưu bài tập vào Thư viện Puzzle Bank!');
    } catch {
      toast.error('Không thể tạo bài tập từ kết quả scan này');
    }
  };

  const handleSaveAllApproved = async () => {
    if (!selectedJob) return;
    const approvedWithoutPuzzle = results.filter(
      r => r.review_status === 'approved' && !r.puzzle_id
    );
    if (approvedWithoutPuzzle.length === 0) {
      toast('Tất cả các thế cờ đã duyệt đều đã được lưu vào Puzzle Bank!');
      return;
    }

    setSavingApproved(true);
    try {
      const { data } = await api.post(`/scan/jobs/${selectedJob.id}/save-approved`);
      toast.success(data.message || `Đã lưu thành công ${data.saved_count} bài tập vào Puzzle Bank!`);
      const { data: updatedResults } = await api.get(`/scan/jobs/${selectedJob.id}/results`);
      setResults(updatedResults);
    } catch {
      toast.error('Có lỗi khi lưu các bài tập đã duyệt');
    } finally {
      setSavingApproved(false);
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

  // ── Filtered & Paginated Results ────────────────────────
  const filteredResults = results.filter(r => {
    if (pageSearch.trim()) {
      const targetPage = parseInt(pageSearch.trim(), 10);
      if (!isNaN(targetPage) && r.page_number !== targetPage) {
        return false;
      }
    }
    if (filterStatus === 'pending') return r.review_status === 'pending';
    if (filterStatus === 'approved') return r.review_status === 'approved';
    if (filterStatus === 'rejected') return r.review_status === 'rejected';
    if (filterStatus === 'needs_review') {
      const lowConf = getLowConfCells(r);
      return lowConf.length > 0 || (r.confidence_board != null && r.confidence_board < 0.70);
    }
    return true;
  });

  const totalPages = Math.max(1, Math.ceil(filteredResults.length / pageSize));
  const paginatedResults = filteredResults.slice((currentPage - 1) * pageSize, currentPage * pageSize);

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
                    <div className="flex items-center gap-2">
                      <StatusBadge status={job.status} />
                      <button 
                        onClick={(e) => deleteJob(e, job.id)}
                        className="text-slate-500 hover:text-red-400 p-1 rounded-md hover:bg-red-500/10 transition-colors"
                        title="Delete scan job"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
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
              <div className="px-5 py-4 border-b border-slate-700/50 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <h2 className="text-sm font-semibold text-slate-300">
                    Results — {selectedJob.file_name}
                  </h2>
                  <StatusBadge status={selectedJob.status} />
                </div>

                <div className="flex items-center gap-3">
                  {results.some(r => r.review_status === 'approved') && (
                    <button
                      onClick={handleSaveAllApproved}
                      disabled={savingApproved}
                      className="flex items-center gap-2 px-3.5 py-1.5 bg-linear-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-medium transition shadow-lg shadow-emerald-600/20 disabled:opacity-50"
                      title="Lưu tất cả các thế cờ đã duyệt vào Thư viện Puzzle Bank"
                    >
                      {savingApproved ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <BookOpen className="w-3.5 h-3.5" />
                      )}
                      Save Approved ({results.filter(r => r.review_status === 'approved').length} đã duyệt)
                    </button>
                  )}
                </div>
              </div>

              {/* Filter and Pagination Toolbar */}
              {results.length > 0 && !loadingResults && (
                <div className="px-5 py-2.5 bg-slate-900/60 border-b border-slate-700/50 flex flex-wrap items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-slate-400 font-medium mr-1 flex items-center gap-1">
                      <Filter className="w-3.5 h-3.5" /> Lọc:
                    </span>
                    {(['all', 'pending', 'approved', 'rejected', 'needs_review'] as const).map(st => (
                      <button
                        key={st}
                        onClick={() => { setFilterStatus(st); setCurrentPage(1); }}
                        className={`px-2.5 py-1 rounded-lg font-medium transition ${
                          filterStatus === st
                            ? 'bg-purple-600 text-white'
                            : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
                        }`}
                      >
                        {st === 'all' && `Tất cả (${results.length})`}
                        {st === 'pending' && `Chờ duyệt (${results.filter(r => r.review_status === 'pending').length})`}
                        {st === 'approved' && `Đã duyệt (${results.filter(r => r.review_status === 'approved').length})`}
                        {st === 'rejected' && `Từ chối (${results.filter(r => r.review_status === 'rejected').length})`}
                        {st === 'needs_review' && `Cần chú ý (${results.filter(r => getLowConfCells(r).length > 0).length})`}
                      </button>
                    ))}
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400">Trang sách:</span>
                      <input
                        type="number"
                        placeholder="Số trang..."
                        value={pageSearch}
                        onChange={e => { setPageSearch(e.target.value); setCurrentPage(1); }}
                        className="w-20 px-2 py-1 bg-slate-800 border border-slate-700 rounded-lg text-white text-xs outline-none focus:border-purple-500"
                      />
                    </div>
                  </div>
                </div>
              )}

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
                <>
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 p-5 max-h-[calc(100vh-320px)] overflow-y-auto">
                    {paginatedResults.map(result => {
                    const lowConf = getLowConfCells(result);
                    const fen = result.fen_final || result.fen_candidate;

                    return (
                      <div
                        key={result.id}
                        className="bg-slate-900/60 border border-slate-700/50 rounded-xl overflow-hidden flex flex-col justify-between"
                      >
                        {/* Board Visuals: Crop Image + Virtual Chessboard side-by-side */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 p-2 bg-slate-950/80 border-b border-slate-800">
                          {/* Col 1: Cropped PDF Image */}
                          <div className="aspect-square bg-slate-900 rounded-lg flex items-center justify-center relative overflow-hidden group">
                            {result.board_image_url ? (
                              <img
                                src={result.board_image_url}
                                alt={`Board page ${result.page_number}`}
                                className="w-full h-full object-contain cursor-pointer hover:opacity-95 transition-opacity"
                                onClick={() => {
                                  setZoomScale(1);
                                  setZoomModal({
                                    imageUrl: result.board_image_url!,
                                    title: `Trang ${result.page_number} — Bàn cờ #${result.board_index}`,
                                    fen,
                                    pageNumber: result.page_number,
                                    boardIndex: result.board_index,
                                    confidence: result.confidence_board,
                                  });
                                }}
                              />
                            ) : (
                              <div className="text-slate-600 text-xs">No image</div>
                            )}
                            <div className="absolute top-2 left-2 pointer-events-none">
                              <span className="bg-slate-900/80 text-slate-300 text-[10px] px-1.5 py-0.5 rounded">
                                P{result.page_number} / B{result.board_index}
                              </span>
                            </div>
                            {result.confidence_board != null && (
                              <div className="absolute top-2 right-2 pointer-events-none">
                                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${result.confidence_board >= 0.90 ? 'bg-green-900/80 text-green-300' : result.confidence_board >= 0.70 ? 'bg-amber-900/80 text-amber-300' : 'bg-red-900/80 text-red-300'}`}>
                                  {(result.confidence_board * 100).toFixed(0)}%
                                </span>
                              </div>
                            )}

                            {/* Nút phóng to ảnh ở góc ảnh gốc */}
                            {result.board_image_url && (
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setZoomScale(1);
                                  setZoomModal({
                                    imageUrl: result.board_image_url!,
                                    title: `Trang ${result.page_number} — Bàn cờ #${result.board_index}`,
                                    fen,
                                    pageNumber: result.page_number,
                                    boardIndex: result.board_index,
                                    confidence: result.confidence_board,
                                  });
                                }}
                                className="absolute bottom-2 right-2 p-1.5 bg-slate-900/85 hover:bg-purple-600 text-slate-200 hover:text-white rounded-lg border border-white/10 shadow-md backdrop-blur-xs transition-all flex items-center gap-1 text-[11px]"
                                title="Phóng to ảnh để so sánh chi tiết"
                                aria-label="Phóng to ảnh bàn cờ"
                              >
                                <ZoomIn className="w-3.5 h-3.5" />
                                <span className="hidden sm:inline text-[10px] font-medium pr-0.5">Phóng to</span>
                              </button>
                            )}
                          </div>

                          {/* Col 2: Virtual Chessboard */}
                          <div className="aspect-square bg-slate-900 rounded-lg flex items-center justify-center p-1 relative overflow-hidden">
                            {fen ? (
                              <div className="w-full h-full aspect-square pointer-events-none">
                                <Chessboard
                                  options={{
                                    id: `preview-${result.id}`,
                                    position: fen,
                                    allowDragging: false,
                                    boardOrientation: (fen.split(' ')[1] === 'b') ? 'black' : 'white',
                                    showNotation: true,
                                    boardStyle: { borderRadius: '6px' },
                                  }}
                                />
                              </div>
                            ) : (
                              <div className="text-slate-600 text-xs">Chưa có FEN</div>
                            )}
                          </div>
                        </div>

                        {/* Info */}
                        <div className="p-4 space-y-3 flex-1 flex flex-col justify-between">
                          <div className="space-y-3">
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
                                    title="Click to edit FEN"
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
                          </div>

                          {/* Actions */}
                          <div className="flex items-center justify-between pt-3 border-t border-slate-800/80">
                            <div className="flex items-center gap-2">
                              <StatusBadge status={result.review_status} />
                              {result.puzzle_id && (
                                <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                                  <BookOpen className="w-3 h-3" />
                                  Đã tạo Puzzle
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-2">
                              {result.puzzle_id ? (
                                <Link
                                  to={`/practice?puzzleId=${result.puzzle_id}`}
                                  className="flex items-center gap-1 px-2.5 py-1.5 bg-indigo-600/30 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/30 rounded-lg text-xs font-medium transition"
                                >
                                  <Play className="w-3 h-3 fill-current" />
                                  Luyện tập ngay
                                </Link>
                              ) : result.review_status === 'approved' ? (
                                <button
                                  onClick={() => saveSingleToPuzzle(result)}
                                  className="flex items-center gap-1 px-2.5 py-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-medium transition shadow-sm"
                                >
                                  <BookOpen className="w-3.5 h-3.5" />
                                  Lưu vào Puzzle Bank
                                </button>
                              ) : result.review_status === 'pending' ? (
                                <>
                                  <button
                                    onClick={() => approveResult(result.id)}
                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-medium hover:bg-emerald-600/30 transition-all"
                                  >
                                    <CheckCircle className="w-3.5 h-3.5" />
                                    Approve & Tạo Puzzle
                                  </button>
                                  <button
                                    onClick={() => rejectResult(result.id)}
                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600/20 text-red-400 border border-red-500/30 rounded-lg text-xs font-medium hover:bg-red-600/30 transition-all"
                                  >
                                    <XCircle className="w-3.5 h-3.5" />
                                    Reject
                                  </button>
                                </>
                              ) : null}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Pagination Controls Footer */}
                {filteredResults.length > pageSize && (
                  <div className="px-5 py-3 border-t border-slate-700/50 bg-slate-900/60 flex items-center justify-between text-xs">
                    <span className="text-slate-400">
                      Hiển thị <span className="text-white font-medium">{(currentPage - 1) * pageSize + 1} - {Math.min(currentPage * pageSize, filteredResults.length)}</span> trên tổng số <span className="text-white font-medium">{filteredResults.length}</span> thế cờ
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition"
                      >
                        <ChevronLeft className="w-3.5 h-3.5" /> Trước
                      </button>
                      <span className="px-2 font-medium text-purple-400">
                        Trang {currentPage} / {totalPages}
                      </span>
                      <button
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition"
                      >
                        Sau <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
            </div>
          )}
        </div>
      </div>

      {/* ── Zoom Modal ─────────────────────────────────────── */}
      {zoomModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-sm"
          onClick={() => setZoomModal(null)}
          role="dialog"
          aria-modal="true"
          aria-label="Phóng to ảnh bàn cờ"
        >
          <div
            className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-800 bg-slate-950/70">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-xl">
                  <Maximize2 className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    {zoomModal.title}
                    {zoomModal.confidence != null && (
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${zoomModal.confidence >= 0.90 ? 'bg-green-900/80 text-green-300' : 'bg-amber-900/80 text-amber-300'}`}>
                        Độ chính xác: {(zoomModal.confidence * 100).toFixed(0)}%
                      </span>
                    )}
                  </h3>
                  <p className="text-xs text-slate-400">So sánh chi tiết ảnh gốc trích xuất từ PDF và bàn cờ số hóa</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* Image Zoom Scale Controls */}
                <div className="flex items-center gap-1 bg-slate-800/80 border border-slate-700/80 rounded-xl p-1 text-xs">
                  <button
                    type="button"
                    onClick={() => setZoomScale(s => Math.max(parseFloat((s - 0.25).toFixed(2)), 0.5))}
                    className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700/60 transition"
                    title="Thu nhỏ ảnh (-)"
                    aria-label="Thu nhỏ ảnh"
                  >
                    <ZoomOut className="w-4 h-4" />
                  </button>
                  <span className="px-2 font-mono text-slate-300 select-none min-w-[3.5rem] text-center text-[11px]">
                    {Math.round(zoomScale * 100)}%
                  </span>
                  <button
                    type="button"
                    onClick={() => setZoomScale(s => Math.min(parseFloat((s + 0.25).toFixed(2)), 3.5))}
                    className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700/60 transition"
                    title="Phóng to ảnh (+)"
                    aria-label="Phóng to ảnh"
                  >
                    <ZoomIn className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setZoomScale(1)}
                    className="p-1 text-slate-400 hover:text-purple-400 rounded-lg hover:bg-slate-700/60 transition"
                    title="Đặt lại tỉ lệ (100%)"
                    aria-label="Đặt lại tỉ lệ"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Close Button */}
                <button
                  type="button"
                  onClick={() => setZoomModal(null)}
                  className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition"
                  title="Đóng (Esc)"
                  aria-label="Đóng phóng to ảnh"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body: Split view comparing Original and Digitized Board */}
            <div className="p-4 overflow-y-auto flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-950/40">
              {/* Left: Original Crop with interactive Zoom/Pan */}
              <div className="flex flex-col bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-inner">
                <div className="px-3 py-2 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between text-xs text-slate-300 font-medium">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                    Ảnh gốc trích xuất từ PDF
                  </span>
                  <span className="text-slate-500 text-[11px]">Cuộn / kéo để di chuyển ảnh</span>
                </div>
                <div className="flex-1 min-h-[350px] max-h-[520px] overflow-auto flex items-center justify-center p-4 bg-slate-950 relative select-none">
                  <div
                    style={{
                      transform: `scale(${zoomScale})`,
                      transformOrigin: 'center center',
                      transition: 'transform 0.15s ease-out'
                    }}
                    className="flex items-center justify-center"
                  >
                    <img
                      src={zoomModal.imageUrl}
                      alt={zoomModal.title}
                      className="max-w-full max-h-[460px] object-contain rounded-md shadow-2xl pointer-events-none"
                    />
                  </div>
                </div>
              </div>

              {/* Right: Digitized Virtual Chessboard */}
              <div className="flex flex-col bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-inner">
                <div className="px-3 py-2 bg-slate-800/60 border-b border-slate-800 flex items-center justify-between text-xs text-slate-300 font-medium">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                    Bàn cờ số hóa (Digital Board)
                  </span>
                  {zoomModal.fen && (
                    <span className="text-purple-400 text-[11px] font-mono truncate max-w-[200px]" title={zoomModal.fen}>
                      {zoomModal.fen}
                    </span>
                  )}
                </div>
                <div className="flex-1 min-h-[350px] max-h-[520px] flex items-center justify-center p-4 bg-slate-950">
                  {zoomModal.fen ? (
                    <div className="w-full max-w-[360px] aspect-square">
                      <Chessboard
                        options={{
                          id: 'zoom-modal-board',
                          position: zoomModal.fen,
                          allowDragging: false,
                          boardOrientation: (zoomModal.fen.split(' ')[1] === 'b') ? 'black' : 'white',
                          showNotation: true,
                          boardStyle: { borderRadius: '8px' },
                        }}
                      />
                    </div>
                  ) : (
                    <div className="text-slate-500 text-sm">Chưa có FEN số hóa</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
