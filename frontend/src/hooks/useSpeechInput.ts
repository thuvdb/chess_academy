import { useState, useEffect, useRef, useCallback } from 'react';
import {
  getSpeechRecognitionContinuous,
  processSpeechRecognitionResults,
  mapSpeechErrorToVietnamese,
} from '../utils/speech';

// TypeScript declaration for Web Speech API
declare global {
  interface Window {
    SpeechRecognition?: any;
    webkitSpeechRecognition?: any;
  }
}

export interface UseSpeechInputOptions {
  lang?: string;
  continuous?: boolean;
  onTranscript?: (transcript: string, isFinal: boolean) => void;
  onError?: (errorMessage: string) => void;
}

export function useSpeechInput(options: UseSpeechInputOptions = {}) {
  const { lang = 'vi-VN', continuous, onTranscript, onError } = options;

  const [isSupported, setIsSupported] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
  });
  const [isListening, setIsListening] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<string>('');
  const [interimTranscript, setInterimTranscript] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);

  // Keep latest callbacks in refs to prevent useEffect from re-running and aborting recognition
  const onTranscriptRef = useRef(onTranscript);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  // Track intentional stops to handle onend gracefully
  const isIntentionalStopRef = useRef<boolean>(false);

  useEffect(() => {
    const SpeechRecognitionAPI =
      typeof window !== 'undefined'
        ? window.SpeechRecognition || window.webkitSpeechRecognition
        : null;

    if (!SpeechRecognitionAPI) {
      return;
    }

    let recognition: any;
    try {
      recognition = new SpeechRecognitionAPI();
    } catch (e) {
      console.error('[STT] Failed to initialize SpeechRecognition:', e);
      setIsSupported(false);
      return;
    }

    // Set continuous: false on mobile/Android to prevent looping/duplication, true on desktop
    const isContinuous =
      continuous !== undefined ? continuous : getSpeechRecognitionContinuous();

    recognition.continuous = isContinuous;
    recognition.interimResults = true;
    recognition.lang = lang;

    recognition.onaudiostart = () => {
      console.log('[STT] onaudiostart: Audio capture started');
    };

    recognition.onspeechstart = () => {
      console.log('[STT] onspeechstart: Speech detected');
    };

    recognition.onspeechend = () => {
      console.log('[STT] onspeechend: Speech ended');
    };

    recognition.onaudioend = () => {
      console.log('[STT] onaudioend: Audio capture ended');
    };

    recognition.onnomatch = (event: any) => {
      console.warn('[STT] onnomatch: No speech match found', event);
    };

    recognition.onstart = () => {
      console.log('[STT] onstart: Recognition started (continuous=' + isContinuous + ')');
      setIsListening(true);
      setErrorMessage(null);
    };

    recognition.onresult = (event: any) => {
      console.log(
        '[STT] onresult: resultIndex =',
        event.resultIndex,
        'results length =',
        event.results?.length
      );

      const { finalAccumulated, interimCurrent, fullTranscript, isCompleteFinal } =
        processSpeechRecognitionResults(event.results);

      console.log('[STT] Transcript update:', {
        finalAccumulated,
        interimCurrent,
        fullTranscript,
        isCompleteFinal,
      });

      if (finalAccumulated) {
        setTranscript(finalAccumulated);
      }
      setInterimTranscript(interimCurrent);

      if (fullTranscript) {
        onTranscriptRef.current?.(fullTranscript, isCompleteFinal);
      }
    };

    recognition.onerror = (event: any) => {
      console.error('[STT] onerror:', event.error, event.message, event);
      const message = mapSpeechErrorToVietnamese(event.error);
      if (!message) {
        console.log('[STT] Recognition aborted silently');
        return;
      }

      setErrorMessage(message);
      setIsListening(false);
      onErrorRef.current?.(message);
    };

    recognition.onend = () => {
      console.log('[STT] onend: Recognition ended, was intentional:', isIntentionalStopRef.current);
      setIsListening(false);
      setInterimTranscript('');
      isIntentionalStopRef.current = false;
    };

    recognitionRef.current = recognition;

    return () => {
      console.log('[STT] Cleanup: aborting recognition');
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore abort error on unmount
        }
        recognitionRef.current = null;
      }
    };
  }, [lang, continuous]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) {
      console.warn('[STT] startListening called but recognition is not initialized');
      return;
    }
    isIntentionalStopRef.current = false;
    setTranscript('');
    setInterimTranscript('');
    setErrorMessage(null);

    try {
      recognitionRef.current.start();
      console.log('[STT] recognition.start() called');
    } catch (e: any) {
      console.warn('[STT] start error:', e);
      if (e?.name !== 'InvalidStateError') {
        const msg = 'Không thể khởi động micro: ' + (e?.message || e);
        setErrorMessage(msg);
        onErrorRef.current?.(msg);
      }
    }
  }, []);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return;
    isIntentionalStopRef.current = true;
    try {
      recognitionRef.current.stop();
      console.log('[STT] recognition.stop() called');
    } catch (e) {
      console.warn('[STT] stop error:', e);
      try {
        recognitionRef.current.abort();
      } catch {
        // ignore secondary abort error
      }
    }
    setIsListening(false);
  }, []);

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
