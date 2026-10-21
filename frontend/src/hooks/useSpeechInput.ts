import { useState, useEffect, useRef, useCallback } from 'react';

// TypeScript declaration for Web Speech API
declare global {
  interface Window {
    SpeechRecognition?: any;
    webkitSpeechRecognition?: any;
  }
}

export interface UseSpeechInputOptions {
  lang?: string;
  onTranscript?: (transcript: string, isFinal: boolean) => void;
  onError?: (errorMessage: string) => void;
}

export function useSpeechInput(options: UseSpeechInputOptions = {}) {
  const { lang = 'vi-VN', onTranscript, onError } = options;

  const [isSupported, setIsSupported] = useState<boolean>(false);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<string>('');
  const [interimTranscript, setInterimTranscript] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const SpeechRecognitionAPI =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognitionAPI) {
      setIsSupported(true);
      const recognition = new SpeechRecognitionAPI();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = lang;

      recognition.onstart = () => {
        setIsListening(true);
        setErrorMessage(null);
      };

      recognition.onresult = (event: any) => {
        let finalTrans = '';
        let interimTrans = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const item = event.results[i];
          if (item.isFinal) {
            finalTrans += item[0].transcript;
          } else {
            interimTrans += item[0].transcript;
          }
        }

        if (finalTrans) {
          setTranscript((prev) => {
            const updated = prev ? `${prev} ${finalTrans}` : finalTrans;
            onTranscript?.(updated, true);
            return updated;
          });
          setInterimTranscript('');
        } else if (interimTrans) {
          setInterimTranscript(interimTrans);
          onTranscript?.(interimTrans, false);
        }
      };

      recognition.onerror = (event: any) => {
        let message = 'Có lỗi xảy ra khi nhận diện giọng nói.';
        if (event.error === 'not-allowed') {
          message = 'Chưa cấp quyền Microphone. Vui lòng cho phép quyền microphone trong cài đặt trình duyệt.';
        } else if (event.error === 'no-speech') {
          message = 'Không nghe thấy giọng nói. Vui lòng nói to và rõ hơn.';
        } else if (event.error === 'network') {
          message = 'Lỗi kết nối mạng dịch vụ nhận diện giọng nói.';
        } else if (event.error === 'aborted') {
          return;
        }

        setErrorMessage(message);
        setIsListening(false);
        onError?.(message);
      };

      recognition.onend = () => {
        setIsListening(false);
        setInterimTranscript('');
      };

      recognitionRef.current = recognition;
    } else {
      setIsSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (_) {}
      }
    };
  }, [lang, onTranscript, onError]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current || isListening) return;
    setTranscript('');
    setInterimTranscript('');
    setErrorMessage(null);
    try {
      recognitionRef.current.start();
    } catch (e) {
      console.warn('Recognition already started or error:', e);
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current || !isListening) return;
    try {
      recognitionRef.current.stop();
    } catch (_) {}
    setIsListening(false);
  }, [isListening]);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  const resetTranscript = useCallback(() => {
    setTranscript('');
    setInterimTranscript('');
  }, []);

  return {
    isSupported,
    isListening,
    transcript,
    interimTranscript,
    errorMessage,
    startListening,
    stopListening,
    toggleListening,
    resetTranscript,
  };
}

export default useSpeechInput;
