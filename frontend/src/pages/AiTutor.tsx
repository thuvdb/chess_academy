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
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Loader2,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../lib/api';
import { API_BASE_URL } from '../config';
import { useAuthStore } from '../store/authStore';
import BoardPreview, { type BoardData } from '../components/ai/BoardPreview';
import PuzzleCard, { type PuzzleData } from '../components/ai/PuzzleCard';
import useSpeechInput from '../hooks/useSpeechInput';
import { stripBoardTags } from '../utils/aiTutor';
import { appendTranscriptToBase } from '../utils/speech';

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
  puzzle_data?: PuzzleData[] | null;
  created_at?: string;
}

const QUICK_SUGGESTIONS = [
  'Cho em 2 bài tập về đòn Ghim quân',
  'Em muốn giải thế cờ chiếu hết 2 nước',
  'Giải thích đòn chiếu mở và cho ví dụ',
  'Khai cuộc Ý đi như thế nào?',
  'Tiểu sử Magnus Carlsen',
];

const SUPPORTED_VOICES = [
  { id: 'vi-VN-HoaiMyNeural', label: 'Giọng Nữ (Hoài My)' },
  { id: 'vi-VN-NamMinhNeural', label: 'Giọng Nam (Nam Minh)' },
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
  const [lastFailedQuestion, setLastFailedQuestion] = useState<string | null>(null);
  const [isRetryableError, setIsRetryableError] = useState<boolean>(false);

  // Audio / TTS state
  const [autoSpeak, setAutoSpeak] = useState<boolean>(() => {
    try {
      return localStorage.getItem('cams_ai_auto_speak') === 'true';
    } catch {
      return false;
    }
  });
  const [selectedVoice, setSelectedVoice] = useState<string>(() => {
    try {
      return localStorage.getItem('cams_ai_voice') || 'vi-VN-HoaiMyNeural';
    } catch {
      return 'vi-VN-HoaiMyNeural';
    }
  });
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [loadingAudioId, setLoadingAudioId] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const autoSpeakRef = useRef<boolean>(autoSpeak);
  useEffect(() => {
    autoSpeakRef.current = autoSpeak;
  }, [autoSpeak]);

  // Base text when recording started (so existing text is not wiped out)
  const speechBaseInputRef = useRef<string>('');

  // STT hook
  const {
    isSupported: isSpeechSupported,
    isListening,
    toggleListening,
    stopListening,
  } = useSpeechInput({
    lang: 'vi-VN',
    onTranscript: (spokenText) => {
      setInputMessage(appendTranscriptToBase(speechBaseInputRef.current, spokenText));
    },
    onError: (err) => {
      toast.error(err);
    },
  });

  const handleToggleListening = () => {
    if (!isListening) {
      speechBaseInputRef.current = inputMessage;
    }
    toggleListening();
  };

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

  // Stop currently playing audio
  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setPlayingMessageId(null);
    setLoadingAudioId(null);
  };

  // Play audio for a specific assistant message
  const playAudioForMessage = async (messageId: string) => {
    if (playingMessageId === messageId) {
      stopAudio();
      return;
    }

    stopAudio();
    setLoadingAudioId(messageId);

    try {
      const res = await api.post(
        '/ai-tutor/tts',
        { message_id: messageId, voice: selectedVoice },
        { responseType: 'blob' }
      );

      const blobUrl = URL.createObjectURL(new Blob([res.data], { type: 'audio/mpeg' }));
      const audio = new Audio(blobUrl);
      audioRef.current = audio;

      audio.onended = () => {
        URL.revokeObjectURL(blobUrl);
        setPlayingMessageId(null);
        audioRef.current = null;
      };

      audio.onerror = () => {
        URL.revokeObjectURL(blobUrl);
        setPlayingMessageId(null);
        audioRef.current = null;
        toast.error('Không thể phát âm thanh.');
      };

      await audio.play();
      setPlayingMessageId(messageId);
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'Không thể tạo giọng đọc lúc này.';
      toast.error(detail);
    } finally {
      setLoadingAudioId(null);
    }
  };

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
    return () => {
      stopAudio();
    };
  }, []);

  // Fetch messages when current session changes
  const loadSessionMessages = async (sessionId: string) => {
    stopAudio();
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
    stopAudio();
    if (isStreaming && abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    stopListening();
    speechBaseInputRef.current = '';
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
    stopAudio();
    if (isListening) {
      stopListening();
    }

    const text = (textToSend || inputMessage).trim();
    if (!text || isStreaming) return;

    speechBaseInputRef.current = '';
    setInputMessage('');
    setErrorMessage(null);
    setIsRetryableError(false);
    setLastFailedQuestion(text);

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
      puzzle_data: null,
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
              } else if (currentEvent === 'puzzles' && data.puzzles) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const lastIdx = updated.length - 1;
                  if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                    updated[lastIdx] = {
                      ...updated[lastIdx],
                      puzzle_data: data.puzzles,
                    };
                  }
                  return updated;
                });
              } else if (currentEvent === 'done') {
                if (data.error) {
                  // Stream gracefully closed following error
                  setIsRetryableError(true);
                  // Remove empty assistant placeholder if no content was received
                  setMessages((prev) => {
                    const last = prev[prev.length - 1];
                    if (last && last.role === 'assistant' && !last.content?.trim()) {
                      return prev.slice(0, -1);
                    }
                    return prev;
                  });
                } else {
                  setLastFailedQuestion(null);
                  setIsRetryableError(false);
                }

                if (data.session_id && !currentSessionId) {
                  setCurrentSessionId(data.session_id);
                  fetchSessions();
                }

                if (data.message_id) {
                  setMessages((prev) => {
                    const updated = [...prev];
                    const lastIdx = updated.length - 1;
                    if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                      updated[lastIdx] = {
                        ...updated[lastIdx],
                        id: data.message_id,
                        content: stripBoardTags(updated[lastIdx].content, false),
                      };
                    }
                    return updated;
                  });

                  // If auto-speak is enabled, automatically play audio
                  if (autoSpeakRef.current) {
                    playAudioForMessage(data.message_id);
                  }
                }
              } else if (currentEvent === 'error') {
                const isOverloaded = data.code === 'overloaded' || data.error?.toLowerCase().includes('quá tải');
                const friendlyMsg = data.error
                  ? data.error
                  : (isOverloaded
                    ? 'AI đang quá tải do lượng truy cập cao. Vui lòng bấm Thử lại sau vài giây.'
                    : 'Có lỗi xảy ra trong quá trình trao đổi.');

                setErrorMessage(friendlyMsg);
                setIsRetryableError(Boolean(data.retryable ?? true));

                // Clean up empty assistant placeholder
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last && last.role === 'assistant' && !last.content?.trim()) {
                    return prev.slice(0, -1);
                  }
                  return prev;
                });
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
        const isNetworkOrDrop =
          err.message?.includes('fetch') ||
          err.message?.includes('Network') ||
          err.message?.includes('chunked') ||
          err.message?.includes('ERR_INCOMPLETE') ||
          err.name === 'TypeError';

        const displayMsg = isNetworkOrDrop
          ? 'AI đang quá tải hoặc kết nối bị gián đoạn. Vui lòng bấm Thử lại sau vài giây.'
          : (err.message || 'Lỗi kết nối đến Huấn luyện viên AI.');

        setErrorMessage(displayMsg);
        setIsRetryableError(true);
        toast.error(displayMsg);

        // Remove empty assistant placeholder
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last && last.role === 'assistant' && !last.content?.trim()) {
            return prev.slice(0, -1);
          }
          return prev;
        });
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleRetryLastQuestion = () => {
    if (lastFailedQuestion && !isStreaming) {
      const q = lastFailedQuestion;
      setErrorMessage(null);
      setIsRetryableError(false);
      handleSendMessage(q);
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
            onClick={() => setIsMobileHistoryOpen(false)}
            className="fixed inset-0 bg-black/60 z-40 transition-opacity backdrop-blur-xs"
            aria-hidden="true"
          />
        )}

        {/* Drawer content */}
        <aside
          role="dialog"
          aria-modal="true"
          aria-label="Lịch sử hỏi đáp AI"
          className={`fixed top-0 left-0 bottom-0 z-50 w-72 max-w-[80vw] bg-slate-900 border-r border-slate-800 flex flex-col transform transition-transform duration-200 ease-out shadow-2xl ${
            isMobileHistoryOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          {/* Drawer Header */}
          <div className="p-3 border-b border-slate-800 flex items-center justify-between gap-2">
            <button
              onClick={() => {
                setIsMobileHistoryOpen(false);
                handleNewChat();
              }}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-medium text-xs rounded-xl shadow-lg shadow-blue-900/30 transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Cuộc trò chuyện mới</span>
            </button>
            <button
              onClick={() => setIsMobileHistoryOpen(false)}
              className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
              aria-label="Đóng lịch sử"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Drawer Sessions list */}
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-2 space-y-1">
            <div className="text-[11px] font-semibold text-slate-400 px-3 py-1.5 uppercase tracking-wider">
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
                    onClick={() => {
                      loadSessionMessages(s.id);
                      setIsMobileHistoryOpen(false);
                    }}
                    className={`group flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer text-xs transition ${
                      isSelected
                        ? 'bg-slate-800 text-white font-medium border border-slate-700'
                        : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate pr-2">
                      <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-blue-400' : 'text-slate-500'}`} />
                      <span className="truncate">{s.title}</span>
                    </div>
                    <button
                      onClick={(e) => handleDeleteSession(e, s.id)}
                      className="p-1 hover:text-red-400 text-slate-500 rounded transition"
                      title="Xóa phiên này"
                      aria-label={`Xóa phiên ${s.title}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>

          <div className="p-3 border-t border-slate-800 text-[11px] text-slate-500 text-center flex items-center justify-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Trợ lý Huấn luyện viên CAMS AI</span>
          </div>
        </aside>
      </div>

      {/* ── DESKTOP SIDEBAR: SESSION LIST (≥ 768px) ───────────────────────── */}
      <aside
        aria-label="Lịch sử hỏi đáp AI"
        className={`hidden md:flex bg-slate-900 border-r border-slate-800 flex-col shrink-0 transition-all duration-200 ease-in-out ${
          isHistoryCollapsed ? 'w-14' : 'w-72'
        }`}
      >
        {isHistoryCollapsed ? (
          /* Collapsed state (icon-only mode) */
          <div className="flex flex-col h-full items-center py-3">
            <button
              onClick={toggleHistoryCollapse}
              className="p-2.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition mb-2"
              title="Mở rộng lịch sử"
              aria-label="Mở rộng lịch sử trò chuyện"
            >
              <PanelLeftOpen className="w-4 h-4" />
            </button>
            <button
              onClick={handleNewChat}
              className="p-2.5 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white rounded-xl shadow-md shadow-blue-900/30 transition mb-3"
              title="Cuộc trò chuyện mới"
              aria-label="Tạo cuộc trò chuyện mới"
            >
              <Plus className="w-4 h-4" />
            </button>
            <div className="flex-1 w-full overflow-y-auto custom-scrollbar flex flex-col items-center gap-1.5 px-1.5">
              {sessions.map((s) => {
                const isSelected = s.id === currentSessionId;
                return (
                  <button
                    key={s.id}
                    onClick={() => loadSessionMessages(s.id)}
                    className={`p-2 rounded-lg transition text-slate-400 hover:text-white ${
                      isSelected
                        ? 'bg-slate-800 text-blue-400 border border-slate-700'
                        : 'hover:bg-slate-800/60'
                    }`}
                    title={s.title}
                    aria-label={s.title}
                  >
                    <MessageSquare className="w-4 h-4" />
                  </button>
                );
              })}
            </div>
            <div className="pt-2 text-slate-500" title="CAMS AI">
              <Sparkles className="w-4 h-4 text-amber-400" />
            </div>
          </div>
        ) : (
          /* Expanded state */
          <div className="flex flex-col h-full">
            <div className="p-3 border-b border-slate-800 flex items-center gap-2">
              <button
                onClick={handleNewChat}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-medium text-xs rounded-xl shadow-lg shadow-blue-900/30 transition"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Cuộc trò chuyện mới</span>
              </button>
              <button
                onClick={toggleHistoryCollapse}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition shrink-0"
                title="Thu gọn lịch sử"
                aria-label="Thu gọn lịch sử trò chuyện"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>

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
                        aria-label={`Xóa phiên ${s.title}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  );
                })
              )}
            </div>

            <div className="p-3 border-t border-slate-800 text-[11px] text-slate-500 text-center flex items-center justify-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Trợ lý Huấn luyện viên CAMS AI</span>
            </div>
          </div>
        )}
      </aside>

      {/* ── RIGHT MAIN CHAT AREA ────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col bg-slate-950 min-w-0">
        {/* Chat Header */}
        <div className="h-16 px-4 sm:px-6 border-b border-slate-800 flex items-center justify-between bg-slate-900/60 backdrop-blur-md shrink-0">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            {/* Mobile History toggle button */}
            <button
              onClick={() => setIsMobileHistoryOpen(true)}
              className="md:hidden p-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition shrink-0"
              title="Mở lịch sử trò chuyện"
              aria-label="Mở lịch sử trò chuyện"
            >
              <History className="w-5 h-5 text-blue-400" />
            </button>

            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-linear-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-md shadow-blue-500/20 text-white shrink-0">
              <Bot className="w-5 h-5 sm:w-6 sm:h-6" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="font-semibold text-white text-sm sm:text-base truncate">
                  Thầy AI Huấn Luyện Viên CAMS
                </h1>
                <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Trực tuyến
                </span>
              </div>
              <p className="text-xs text-slate-400 truncate hidden sm:block">
                Hỏi đáp lý thuyết, khai cuộc, chiến thuật & minh họa nước đi FIDE
              </p>
            </div>
          </div>

          {/* Voice Toolbar & Actions */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Voice Selector */}
            <select
              value={selectedVoice}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedVoice(val);
                try {
                  localStorage.setItem('cams_ai_voice', val);
                } catch (_) {}
              }}
              className="bg-slate-800 text-[11px] sm:text-xs text-slate-300 border border-slate-700 rounded-lg px-2 py-1 outline-hidden hover:border-slate-600 transition"
              title="Chọn giọng đọc AI"
            >
              {SUPPORTED_VOICES.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>

            {/* Auto-read Toggle Switch */}
            <button
              type="button"
              onClick={() => {
                const next = !autoSpeak;
                setAutoSpeak(next);
                try {
                  localStorage.setItem('cams_ai_auto_speak', String(next));
                } catch (_) {}
                toast.success(next ? 'Đã bật tự động đọc câu trả lời' : 'Đã tắt tự động đọc');
              }}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition ${
                autoSpeak
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
              }`}
              title="Tự động đọc to phản hồi của AI khi hoàn thành"
            >
              <Volume2 className={`w-3.5 h-3.5 ${autoSpeak ? 'text-amber-400' : 'text-slate-400'}`} />
              <span className="hidden lg:inline">Tự động đọc</span>
            </button>

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
                Thầy là Huấn luyện viên Cờ vua ảo của Học viện CAMS. Thầy có thể hướng dẫn khai cuộc, giải thích chiến thuật hoặc minh họa nước đi trực tiếp trên bàn cờ ảo cho con. Con có thể bấm Micro để nói hoặc bấm Loa để nghe thầy đọc nhé!
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
              const isPlayingThis = playingMessageId === msg.id;
              const isLoadingThis = loadingAudioId === msg.id;

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
                          <ReactMarkdown>
                            {stripBoardTags(
                              msg.content || '',
                              isStreaming && index === messages.length - 1
                            ) || (isStreaming && index === messages.length - 1 ? '...' : '')}
                          </ReactMarkdown>
                          {isStreaming && index === messages.length - 1 && (
                            <span className="inline-block w-2 h-4 ml-1 bg-blue-400 animate-pulse align-middle" />
                          )}
                        </div>
                      )}
                    </div>

                    {/* Speaker Button for AI message */}
                    {!isUser && msg.id && msg.content && (
                      <div className="mt-1.5 flex items-center gap-2">
                        <button
                          onClick={() => playAudioForMessage(msg.id!)}
                          disabled={isLoadingThis}
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition ${
                            isPlayingThis
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 ring-1 ring-amber-400/50'
                              : 'bg-slate-900 hover:bg-slate-850 text-slate-400 hover:text-slate-200 border border-slate-800'
                          }`}
                          title={isPlayingThis ? 'Dừng đọc' : 'Nghe thầy đọc'}
                        >
                          {isLoadingThis ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
                              <span className="text-[11px]">Đang tải âm thanh...</span>
                            </>
                          ) : isPlayingThis ? (
                            <>
                              <VolumeX className="w-3.5 h-3.5 text-amber-400" />
                              <span className="text-[11px] font-semibold text-amber-300">Dừng đọc</span>
                              {/* Animated soundwave bars */}
                              <span className="flex items-center gap-0.5 ml-1">
                                <span className="w-1 h-3 bg-amber-400 rounded-full animate-bounce" />
                                <span className="w-1 h-2 bg-amber-400 rounded-full animate-bounce [animation-delay:0.15s]" />
                                <span className="w-1 h-3.5 bg-amber-400 rounded-full animate-bounce [animation-delay:0.3s]" />
                              </span>
                            </>
                          ) : (
                            <>
                              <Volume2 className="w-3.5 h-3.5 text-slate-400" />
                              <span className="text-[11px]">Nghe đọc</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}

                    {/* Interactive Chessboard (if valid board_data exists) */}
                    {!isUser && msg.board_data && (
                      <BoardPreview data={msg.board_data} />
                    )}

                    {/* Interactive Puzzle Cards (if puzzle_data exists) */}
                    {!isUser && msg.puzzle_data && msg.puzzle_data.length > 0 && (
                      <div className="flex flex-wrap gap-3 mt-3 w-full">
                        {msg.puzzle_data.map((p) => (
                          <PuzzleCard key={p.id} puzzle={p} sessionId={currentSessionId} />
                        ))}
                      </div>
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

          {/* Rate limit or error alert with Retry button */}
          {errorMessage && (
            <div className="p-3 bg-red-950/70 border border-red-800/80 rounded-xl text-red-200 text-xs flex items-center justify-between gap-3 max-w-xl mx-auto shadow-lg shadow-red-950/40">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                <span>{errorMessage}</span>
              </div>
              {lastFailedQuestion && isRetryableError && !isStreaming && (
                <button
                  type="button"
                  onClick={handleRetryLastQuestion}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-800/80 hover:bg-red-700 text-white rounded-lg text-xs font-medium transition shrink-0 border border-red-600/50 cursor-pointer shadow-sm active:scale-95"
                  title="Thử lại câu hỏi vừa gửi"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Thử lại</span>
                </button>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar with Microphone & Send */}
        <div className="shrink-0 p-3 sm:p-4 border-t border-slate-800 bg-slate-900/80 backdrop-blur-md">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2 max-w-4xl mx-auto relative"
          >
            {/* Microphone Button (Speech to Text) */}
            {isSpeechSupported ? (
              <button
                type="button"
                onClick={handleToggleListening}
                disabled={isStreaming}
                className={`p-3 rounded-xl transition shrink-0 ${
                  isListening
                    ? 'bg-red-600 hover:bg-red-500 text-white animate-pulse ring-2 ring-red-400 shadow-lg shadow-red-600/30'
                    : 'bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white'
                }`}
                title={isListening ? 'Đang lắng nghe... bấm để dừng' : 'Bấm để nói câu hỏi (Micro)'}
                aria-label={isListening ? 'Dừng thu âm' : 'Nói câu hỏi'}
              >
                {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>
            ) : (
              <button
                type="button"
                disabled
                className="p-3 rounded-xl transition shrink-0 bg-slate-800/40 text-slate-600 cursor-not-allowed opacity-50"
                title="Trình duyệt không hỗ trợ nhận diện giọng nói (SpeechRecognition). Vui lòng dùng Google Chrome trên máy tính."
                aria-label="Trình duyệt không hỗ trợ micro"
              >
                <MicOff className="w-4 h-4" />
              </button>
            )}

            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder={
                isListening
                  ? 'Đang lắng nghe con nói...'
                  : isStreaming
                  ? 'Thầy AI đang trả lời...'
                  : 'Hỏi thầy về cờ vua (VD: Khai cuộc Ý, đòn chiếu mở, luật phong cấp...)'
              }
              disabled={isStreaming}
              className={`flex-1 bg-slate-950 border focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 outline-hidden transition ${
                isListening ? 'border-red-500/60 ring-1 ring-red-500/40' : 'border-slate-800'
              }`}
            />

            {isStreaming ? (
              <button
                type="button"
                onClick={handleStopStream}
                className="px-4 py-3 bg-red-600 hover:bg-red-500 text-white font-medium rounded-xl flex items-center gap-1.5 text-xs transition shrink-0"
                title="Dừng sinh câu trả lời"
              >
                <Square className="w-3.5 h-3.5 fill-current" />
                <span>Dừng</span>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!inputMessage.trim()}
                className="px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-30 disabled:hover:bg-blue-600 text-white rounded-xl transition shadow-md shadow-blue-900/20 shrink-0"
                title="Gửi câu hỏi"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </form>

          <div className="text-[11px] text-slate-500 text-center mt-2 flex items-center justify-center gap-2">
            <span>Thầy AI CAMS chỉ tập trung về bộ môn Cờ vua.</span>
            {isListening && (
              <span className="text-red-400 font-medium animate-pulse">
                • Đang thu âm giọng nói...
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AiTutor;
