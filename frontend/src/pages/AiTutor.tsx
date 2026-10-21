import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Bot,
  User as UserIcon,
  Send,
  Plus,
  Trash2,
  Sparkles,
  AlertCircle,
  Square,
  MessageSquare,
  RefreshCw,
  PanelLeftClose,
  PanelLeftOpen,
  History,
  X,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../lib/api';
import { API_BASE_URL } from '../config';
import { useAuthStore } from '../store/authStore';
import BoardPreview, { type BoardData } from '../components/ai/BoardPreview';

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
}

interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  board_data?: BoardData | null;
  created_at?: string;
}

const QUICK_SUGGESTIONS = [
  'Giải thích đòn chiếu mở và cho ví dụ',
  'Khai cuộc Ý đi như thế nào?',
  'Tiểu sử Magnus Carlsen',
  'Cách phòng thủ trước đòn Scholar\'s Mate (chiếu hết 4 nước)',
];

export const AiTutor: React.FC = () => {
  const { accessToken } = useAuthStore();

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Collapse state for history panel (persisted in localStorage)
  const [isHistoryCollapsed, setIsHistoryCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem('cams_ai_tutor_history_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  // Mobile drawer state (< 768px)
  const [isMobileHistoryOpen, setIsMobileHistoryOpen] = useState(false);

  const toggleHistoryCollapse = () => {
    setIsHistoryCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem('cams_ai_tutor_history_collapsed', String(next));
      } catch (e) {
        console.warn('Failed to save history collapse state:', e);
      }
      return next;
    });
  };

  // Close mobile drawer on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMobileHistoryOpen) {
        setIsMobileHistoryOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMobileHistoryOpen]);

  // Lock background scroll when mobile drawer is open
  useEffect(() => {
    if (isMobileHistoryOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobileHistoryOpen]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom of messages
  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    scrollToBottom(isStreaming ? 'auto' : 'smooth');
  }, [messages, isStreaming]);

  // Fetch session list
  const fetchSessions = async () => {
    try {
      const res = await api.get('/ai-tutor/sessions');
      setSessions(res.data);
    } catch (err: any) {
      console.error('Failed to load chat sessions:', err);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  // Fetch messages when current session changes
  const loadSessionMessages = async (sessionId: string) => {
    setIsLoadingHistory(true);
    setErrorMessage(null);
    try {
      const res = await api.get(`/ai-tutor/sessions/${sessionId}/messages`);
      setMessages(res.data);
      setCurrentSessionId(sessionId);
    } catch (err: any) {
      toast.error('Không thể tải lịch sử cuộc trò chuyện.');
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // Start a new conversation
  const handleNewChat = () => {
    if (isStreaming && abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setCurrentSessionId(null);
    setMessages([]);
    setErrorMessage(null);
    setInputMessage('');
  };

  // Delete a session
  const handleDeleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (!window.confirm('Bạn có chắc muốn xóa cuộc trò chuyện này không?')) return;

    try {
      await api.delete(`/ai-tutor/sessions/${sessionId}`);
      toast.success('Đã xóa cuộc trò chuyện.');
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        handleNewChat();
      }
    } catch (err) {
      toast.error('Không thể xóa cuộc trò chuyện.');
    }
  };

  // Send message with SSE streaming
  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputMessage).trim();
    if (!text || isStreaming) return;

    setInputMessage('');
    setErrorMessage(null);

    // Optimistically append user message
    const tempUserMsg: ChatMessage = {
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };

    // Placeholder for incoming assistant message
    const tempAssistantMsg: ChatMessage = {
      role: 'assistant',
      content: '',
      board_data: null,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg, tempAssistantMsg]);
    setIsStreaming(true);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const token = accessToken || useAuthStore.getState().accessToken;
      const response = await fetch(`${API_BASE_URL}/ai-tutor/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: text,
          session_id: currentSessionId,
        }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        let errDetail = 'Không thể gửi yêu cầu đến AI.';
        try {
          const errData = await response.json();
          errDetail = errData.detail || errDetail;
        } catch (_) {}

        if (response.status === 429) {
          setErrorMessage(errDetail);
        }
        throw new Error(errDetail);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('Không thể đọc luồng phản hồi từ máy chủ.');

      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = 'message';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.replace('event:', '').trim();
          } else if (trimmed.startsWith('data:')) {
            const jsonStr = trimmed.replace('data:', '').trim();
            try {
              const data = JSON.parse(jsonStr);

              if (currentEvent === 'message' && data.chunk) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const lastIdx = updated.length - 1;
                  if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                    updated[lastIdx] = {
                      ...updated[lastIdx],
                      content: updated[lastIdx].content + data.chunk,
                    };
                  }
                  return updated;
                });
              } else if (currentEvent === 'board' && data.board_data) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const lastIdx = updated.length - 1;
                  if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                    updated[lastIdx] = {
                      ...updated[lastIdx],
                      board_data: data.board_data,
                    };
                  }
                  return updated;
                });
              } else if (currentEvent === 'done') {
                if (data.session_id && !currentSessionId) {
                  setCurrentSessionId(data.session_id);
                  fetchSessions();
                }
              } else if (currentEvent === 'error') {
                setErrorMessage(data.error || 'Có lỗi xảy ra trong quá trình trao đổi.');
              }
            } catch (parseErr) {
              console.warn('Failed to parse SSE JSON chunk:', jsonStr);
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Stream stopped by user.');
      } else {
        const msg = err.message || 'Lỗi kết nối đến Huấn luyện viên AI.';
        setErrorMessage(msg);
        toast.error(msg);
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleStopStream = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  return (
    <div className="flex h-[calc(100dvh-57px)] md:h-dvh w-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* ── MOBILE DRAWER: SESSION LIST (< 768px) ────────────────────────── */}
      <div className="md:hidden">
        {/* Backdrop */}
        {isMobileHistoryOpen && (
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 transition-opacity"
            onClick={() => setIsMobileHistoryOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Sliding Drawer */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] bg-slate-900 border-r border-slate-800 flex flex-col shadow-2xl transition-all duration-200 ease-in-out ${
            isMobileHistoryOpen
              ? 'translate-x-0 opacity-100 visible'
              : '-translate-x-full opacity-0 invisible pointer-events-none'
          }`}
          aria-label="Lịch sử hỏi đáp AI"
        >
          {/* Header Mobile Drawer */}
          <div className="flex items-center justify-between p-4 border-b border-slate-800 shrink-0">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-blue-400" />
              <span className="font-semibold text-sm text-white">Lịch sử hỏi đáp</span>
            </div>
            <button
              type="button"
              onClick={() => setIsMobileHistoryOpen(false)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition focus:outline-hidden"
              aria-label="Đóng lịch sử"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* New Chat Button */}
          <div className="p-3 border-b border-slate-800 shrink-0">
            <button
              onClick={() => {
                handleNewChat();
                setIsMobileHistoryOpen(false);
              }}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white text-sm font-medium rounded-xl shadow-lg shadow-blue-900/30 transition"
            >
              <Plus className="w-4 h-4" />
              <span>Cuộc trò chuyện mới</span>
            </button>
          </div>

          {/* Sessions list */}
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-3 space-y-1">
            {sessions.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500 px-4">
                Chưa có phiên trò chuyện nào. Hãy đặt câu hỏi cho Thầy AI nhé!
              </div>
            ) : (
              sessions.map((s) => {
                const isSelected = s.id === currentSessionId;
                return (
                  <div
                    key={s.id}
                    onClick={() => {
                      loadSessionMessages(s.id);
                      setIsMobileHistoryOpen(false);
                    }}
                    className={`group flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer text-sm transition ${
                      isSelected
                        ? 'bg-slate-800 text-white font-medium border border-slate-700'
                        : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate pr-2">
                      <MessageSquare className={`w-4 h-4 shrink-0 ${isSelected ? 'text-blue-400' : 'text-slate-500'}`} />
                      <span className="truncate">{s.title}</span>
                    </div>
                    <button
                      onClick={(e) => handleDeleteSession(e, s.id)}
                      className="p-1 hover:text-red-400 text-slate-500 rounded transition"
                      title="Xóa phiên này"
                      aria-label="Xóa phiên này"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer info */}
          <div className="p-3 border-t border-slate-800 shrink-0 text-[11px] text-slate-500 text-center flex items-center justify-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Trợ lý Huấn luyện viên CAMS AI</span>
          </div>
        </aside>
      </div>

      {/* ── LEFT SIDEBAR: SESSION LIST (DESKTOP) ─────────────────────────── */}
      <div
        className={`bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 hidden md:flex h-full min-h-0 transition-all duration-200 ease-in-out overflow-hidden ${
          isHistoryCollapsed ? 'w-0 border-r-0 opacity-0 pointer-events-none' : 'w-72 opacity-100'
        }`}
      >
        <div className="w-72 flex flex-col h-full min-h-0">
          {/* Header & New Chat + Collapse button */}
          <div className="p-3.5 border-b border-slate-800 shrink-0 flex items-center gap-2">
            <button
              onClick={handleNewChat}
              className="flex-1 flex items-center justify-center gap-2 px-3.5 py-2.5 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white text-sm font-medium rounded-xl shadow-lg shadow-blue-900/30 transition"
              title="Cuộc trò chuyện mới"
            >
              <Plus className="w-4 h-4 shrink-0" />
              <span className="truncate">Cuộc trò chuyện mới</span>
            </button>
            <button
              type="button"
              onClick={toggleHistoryCollapse}
              className="p-2.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800 transition shrink-0 focus:outline-hidden"
              title="Thu gọn lịch sử hỏi đáp"
              aria-label="Thu gọn lịch sử hỏi đáp"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          {/* Sessions list */}
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-3 space-y-1">
            <div className="text-xs font-semibold text-slate-400 px-3 py-1.5 uppercase tracking-wider">
              Lịch sử hỏi đáp
            </div>

            {sessions.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500 px-4">
                Chưa có phiên trò chuyện nào. Hãy đặt câu hỏi cho Thầy AI nhé!
              </div>
            ) : (
              sessions.map((s) => {
                const isSelected = s.id === currentSessionId;
                return (
                  <div
                    key={s.id}
                    onClick={() => loadSessionMessages(s.id)}
                    className={`group flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer text-sm transition ${
                      isSelected
                        ? 'bg-slate-800 text-white font-medium border border-slate-700'
                        : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate pr-2">
                      <MessageSquare className={`w-4 h-4 shrink-0 ${isSelected ? 'text-blue-400' : 'text-slate-500'}`} />
                      <span className="truncate">{s.title}</span>
                    </div>
                    <button
                      onClick={(e) => handleDeleteSession(e, s.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 text-slate-500 rounded transition"
                      title="Xóa phiên này"
                      aria-label="Xóa phiên này"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer info */}
          <div className="p-3 border-t border-slate-800 shrink-0 text-[11px] text-slate-500 text-center flex items-center justify-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Trợ lý Huấn luyện viên CAMS AI</span>
          </div>
        </div>
      </div>

      {/* ── RIGHT MAIN CHAT AREA ────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col bg-slate-950 min-w-0 h-full min-h-0">
        {/* Chat Header */}
        <div className="h-16 px-4 sm:px-6 border-b border-slate-800 shrink-0 flex items-center justify-between bg-slate-900/60 backdrop-blur-md">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            {/* Mobile History Drawer trigger (< 768px) */}
            <button
              type="button"
              onClick={() => setIsMobileHistoryOpen(true)}
              className="md:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800 transition shrink-0 focus:outline-hidden"
              title="Lịch sử hỏi đáp"
              aria-label="Mở lịch sử hỏi đáp"
            >
              <History className="w-4 h-4" />
            </button>

            {/* Desktop uncollapse & new chat button (when history is collapsed) */}
            {isHistoryCollapsed && (
              <div className="hidden md:flex items-center gap-1.5 shrink-0 mr-1">
                <button
                  type="button"
                  onClick={toggleHistoryCollapse}
                  className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800 transition shrink-0 focus:outline-hidden"
                  title="Mở lịch sử hỏi đáp"
                  aria-label="Mở lịch sử hỏi đáp"
                >
                  <PanelLeftOpen className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={handleNewChat}
                  className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800 transition shrink-0 focus:outline-hidden"
                  title="Cuộc trò chuyện mới"
                  aria-label="Cuộc trò chuyện mới"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            )}

            <div className="w-10 h-10 rounded-xl bg-linear-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-md shadow-blue-500/20 text-white shrink-0">
              <Bot className="w-6 h-6" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="font-semibold text-white text-base truncate">Thầy AI Huấn Luyện Viên CAMS</h1>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Trực tuyến
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block truncate">
                Hỏi đáp lý thuyết, khai cuộc, đòn chiến thuật & minh họa nước đi FIDE
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleNewChat}
              className="md:hidden flex items-center gap-1 text-xs px-2.5 py-1.5 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white rounded-lg transition shadow-sm"
              title="Cuộc trò chuyện mới"
            >
              <Plus className="w-3.5 h-3.5" /> Mới
            </button>
          </div>
        </div>

        {/* Messages Body */}
        <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-4 sm:p-6 space-y-6">
          {isLoadingHistory ? (
            <div className="flex items-center justify-center h-full text-slate-500 gap-2">
              <RefreshCw className="w-5 h-5 animate-spin" />
              <span>Đang tải lịch sử trò chuyện...</span>
            </div>
          ) : messages.length === 0 ? (
            /* Welcome screen with Quick suggestions */
            <div className="h-full flex flex-col items-center justify-center max-w-lg mx-auto text-center px-4">
              <div className="w-16 h-16 rounded-2xl bg-linear-to-tr from-blue-600/30 to-indigo-600/30 border border-blue-500/30 flex items-center justify-center mb-4 text-blue-400 shadow-xl shadow-blue-500/10">
                <Bot className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-bold text-white mb-2">
                Chào mừng con đến với Trợ lý Cờ vua AI!
              </h2>
              <p className="text-sm text-slate-400 mb-6 leading-relaxed">
                Thầy là Huấn luyện viên Cờ vua ảo của Học viện CAMS. Thầy có thể hướng dẫn khai cuộc, giải thích chiến thuật hoặc minh họa nước đi trực tiếp trên bàn cờ ảo cho con.
              </p>

              {/* Suggestions Grid */}
              <div className="w-full space-y-2">
                <div className="text-xs font-semibold text-slate-400 text-left mb-1 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  Gợi ý câu hỏi nhanh:
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                  {QUICK_SUGGESTIONS.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(q)}
                      className="p-3 bg-slate-900 hover:bg-slate-800/80 border border-slate-800 hover:border-slate-700 rounded-xl text-xs text-slate-300 hover:text-white transition shadow-sm"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Message list */
            messages.map((msg, index) => {
              const isUser = msg.role === 'user';
              return (
                <div
                  key={index}
                  className={`flex gap-3.5 ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  {!isUser && (
                    <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shrink-0 shadow-md">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div className={`max-w-2xl flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
                    <div
                      className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                        isUser
                          ? 'bg-blue-600 text-white rounded-tr-xs shadow-md shadow-blue-900/20'
                          : 'bg-slate-900 text-slate-200 rounded-tl-xs border border-slate-800 shadow-md'
                      }`}
                    >
                      {isUser ? (
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      ) : (
                        <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-slate-950 prose-pre:border prose-pre:border-slate-800">
                          <ReactMarkdown>{msg.content || (isStreaming && index === messages.length - 1 ? '...' : '')}</ReactMarkdown>
                          {isStreaming && index === messages.length - 1 && (
                            <span className="inline-block w-2 h-4 ml-1 bg-blue-400 animate-pulse align-middle" />
                          )}
                        </div>
                      )}
                    </div>

                    {/* Interactive Chessboard (if valid board_data exists) */}
                    {!isUser && msg.board_data && (
                      <BoardPreview data={msg.board_data} />
                    )}
                  </div>

                  {isUser && (
                    <div className="w-8 h-8 rounded-lg bg-blue-600/30 border border-blue-500/30 flex items-center justify-center text-blue-300 shrink-0">
                      <UserIcon className="w-4 h-4" />
                    </div>
                  )}
                </div>
              );
            })
          )}

          {/* Rate limit or error alert */}
          {errorMessage && (
            <div className="p-3 bg-red-950/50 border border-red-800/60 rounded-xl text-red-200 text-xs flex items-center gap-2 max-w-xl mx-auto">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="shrink-0 p-3 sm:p-4 border-t border-slate-800 bg-slate-900/80 backdrop-blur-md">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2 max-w-4xl mx-auto relative"
          >
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder={isStreaming ? 'Thầy AI đang trả lời...' : 'Hỏi thầy về cờ vua (VD: Khai cuộc Ý, đòn chiếu mở, luật phong cấp...)'}
              disabled={isStreaming}
              className="flex-1 bg-slate-950 border border-slate-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 outline-hidden transition"
            />

            {isStreaming ? (
              <button
                type="button"
                onClick={handleStopStream}
                className="px-4 py-3 bg-red-600 hover:bg-red-500 text-white font-medium rounded-xl flex items-center gap-1.5 text-xs transition"
                title="Dừng sinh câu trả lời"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                <span>Dừng</span>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!inputMessage.trim()}
                className="px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-30 disabled:hover:bg-blue-600 text-white rounded-xl transition shadow-md shadow-blue-900/20"
                title="Gửi câu hỏi"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </form>
          <div className="text-[11px] text-slate-500 text-center mt-2">
            Thầy AI CAMS chỉ tập trung về bộ môn Cờ vua. Vui lòng tuân thủ nội quy học viện.
          </div>
        </div>
      </div>
    </div>
  );
};

export default AiTutor;
