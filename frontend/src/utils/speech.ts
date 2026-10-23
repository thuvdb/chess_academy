/**
 * Speech Recognition and Web Speech API utilities for CAMS AI Tutor.
 * Handles mobile/desktop continuous mode configuration, deduplication
 * of repeated speech tokens/phrases, and error message mapping.
 */

export interface ProcessedSpeechResults {
  finalAccumulated: string;
  interimCurrent: string;
  fullTranscript: string;
  isCompleteFinal: boolean;
}

/**
 * Detects whether the current environment is a mobile or Android device.
 * Used to tune Web Speech API properties (e.g. Chrome Android duplicates transcripts when continuous = true).
 */
export function isMobileOrAndroid(userAgent?: string): boolean {
  if (userAgent !== undefined) {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile/i.test(userAgent);
  }
  if (typeof navigator !== 'undefined') {
    const ua = navigator.userAgent || navigator.vendor || (typeof window !== 'undefined' && (window as any).opera) || '';
    const isTouch = Boolean(navigator.maxTouchPoints && navigator.maxTouchPoints > 2);
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile/i.test(ua) || (isTouch && /Macintosh/i.test(ua));
  }
  return false;
}

/**
 * Returns whether speech recognition should run in continuous mode.
 * On Chrome Android and mobile browsers, continuous mode causes duplicate result loops.
 * Desktop browsers run in continuous mode without duplicating.
 */
export function getSpeechRecognitionContinuous(userAgent?: string): boolean {
  return !isMobileOrAndroid(userAgent);
}

/**
 * Merges two segments if the end of `prev` overlaps with the beginning of `next`.
 * E.g. "nước cờ tốt" and "tốt nhất" -> "nước cờ tốt nhất"
 */
export function mergeOverlappingSegments(prev: string, next: string): string | null {
  const pWords = prev.trim().split(/\s+/);
  const nWords = next.trim().split(/\s+/);

  const maxOverlap = Math.min(pWords.length, nWords.length);
  for (let k = maxOverlap; k >= 1; k--) {
    const pSuffix = pWords.slice(pWords.length - k).join(' ').toLowerCase();
    const nPrefix = nWords.slice(0, k).join(' ').toLowerCase();
    if (pSuffix === nPrefix) {
      return [...pWords, ...nWords.slice(k)].join(' ');
    }
  }
  return null;
}

/**
 * Deduplicates immediately repeated phrases within a transcript string.
 * Handles repeated multi-word phrases (e.g. "khai cuộc Ý khai cuộc Ý" -> "khai cuộc Ý")
 * as well as duplicated consecutive words (e.g. "Mã Mã f3" -> "Mã f3").
 */
export function deduplicateRepeatedPhrases(text: string): string {
  if (!text || typeof text !== 'string') return '';
  const trimmed = text.trim();
  if (!trimmed) return '';

  const words = trimmed.split(/\s+/);
  if (words.length <= 1) return trimmed;

  let changed = true;
  while (changed) {
    changed = false;
    const n = words.length;

    for (let len = Math.floor(n / 2); len >= 1; len--) {
      for (let i = 0; i <= n - 2 * len; i++) {
        const phrase1 = words.slice(i, i + len).join(' ').toLowerCase();
        const phrase2 = words.slice(i + len, i + 2 * len).join(' ').toLowerCase();

        if (phrase1 === phrase2) {
          words.splice(i + len, len);
          changed = true;
          break;
        }
      }
      if (changed) break;
    }
  }

  return words.join(' ');
}

/**
 * Accumulates and deduplicates speech recognition results from Web Speech API.
 * Solves Chrome Android issues where results are duplicated across consecutive final tokens
 * or where subsequent results re-emit earlier segments as prefixes.
 */
export function processSpeechRecognitionResults(
  results: any,
  options: { deduplicate?: boolean } = { deduplicate: true }
): ProcessedSpeechResults {
  if (!results || results.length === 0) {
    return {
      finalAccumulated: '',
      interimCurrent: '',
      fullTranscript: '',
      isCompleteFinal: false,
    };
  }

  const finalSegments: string[] = [];
  let interimCurrent = '';

  for (let i = 0; i < results.length; ++i) {
    const item = results[i];
    if (!item || !item[0]) continue;
    const rawTranscript = item[0].transcript || '';

    if (item.isFinal) {
      const trimmed = rawTranscript.trim();
      if (!trimmed) continue;

      if (options.deduplicate !== false) {
        if (finalSegments.length > 0) {
          const prev = finalSegments[finalSegments.length - 1];

          // 1. Exact duplicate segment
          if (prev.toLowerCase() === trimmed.toLowerCase()) {
            continue;
          }

          // 2. New segment already contains previous segment as prefix
          if (trimmed.toLowerCase().startsWith(prev.toLowerCase())) {
            finalSegments[finalSegments.length - 1] = trimmed;
            continue;
          }

          // 3. Previous segment already contains new segment
          if (prev.toLowerCase().startsWith(trimmed.toLowerCase())) {
            continue;
          }

          // 4. Word boundary overlap (e.g. "nước cờ tốt" + "tốt nhất" -> "nước cờ tốt nhất")
          const merged = mergeOverlappingSegments(prev, trimmed);
          if (merged) {
            finalSegments[finalSegments.length - 1] = merged;
            continue;
          }
        }
      }

      finalSegments.push(trimmed);
    } else {
      interimCurrent += rawTranscript;
    }
  }

  let finalAccumulated = finalSegments.join(' ').trim();
  interimCurrent = interimCurrent.trim();

  // Deduplicate repeated phrases inside finalAccumulated
  if (options.deduplicate !== false && finalAccumulated) {
    finalAccumulated = deduplicateRepeatedPhrases(finalAccumulated);
  }

  // Handle interim overlapping with final
  if (interimCurrent && finalAccumulated) {
    const lowerFinal = finalAccumulated.toLowerCase();
    const lowerInterim = interimCurrent.toLowerCase();

    if (lowerFinal.endsWith(lowerInterim) || lowerFinal === lowerInterim) {
      interimCurrent = '';
    } else if (lowerInterim.startsWith(lowerFinal)) {
      interimCurrent = interimCurrent.slice(finalAccumulated.length).trim();
    }
  }

  let fullTranscript = '';
  if (finalAccumulated && interimCurrent) {
    fullTranscript = `${finalAccumulated} ${interimCurrent}`.trim();
  } else {
    fullTranscript = (finalAccumulated || interimCurrent).trim();
  }

  if (options.deduplicate !== false && fullTranscript) {
    fullTranscript = deduplicateRepeatedPhrases(fullTranscript);
  }

  const hasFinal = Boolean(finalAccumulated);
  const isCompleteFinal = interimCurrent.length === 0 && hasFinal;

  return {
    finalAccumulated,
    interimCurrent,
    fullTranscript,
    isCompleteFinal,
  };
}

/**
 * Maps Web Speech API error codes to user-friendly Vietnamese messages.
 */
export function mapSpeechErrorToVietnamese(errorType: string): string | null {
  let message = 'Có lỗi xảy ra khi nhận diện giọng nói.';
  switch (errorType) {
    case 'not-allowed':
    case 'service-not-allowed':
      message = 'Chưa cấp quyền Microphone. Vui lòng cho phép quyền microphone trong cài đặt trình duyệt.';
      break;
    case 'no-speech':
      message = 'Không nghe thấy giọng nói. Vui lòng nói to và rõ hơn.';
      break;
    case 'network':
      message = 'Không kết nối được dịch vụ nhận dạng giọng nói. Vui lòng kiểm tra kết nối mạng.';
      break;
    case 'audio-capture':
      message = 'Không tìm thấy microphone. Vui lòng kiểm tra thiết bị thu âm.';
      break;
    case 'language-not-supported':
      message = 'Ngôn ngữ tiếng Việt (vi-VN) không được trình duyệt này hỗ trợ.';
      break;
    case 'aborted':
      return null;
    default:
      message = `Lỗi nhận diện giọng nói: ${errorType || 'không xác định'}`;
  }
  return message;
}

/**
 * Appends spoken transcript to existing input text without overwriting it.
 * Properly manages whitespace between the base and spoken text.
 */
export function appendTranscriptToBase(baseText: string, spokenText: string): string {
  if (baseText && baseText.trim().length > 0) {
    const separator = baseText.endsWith(' ') ? '' : ' ';
    return `${baseText}${separator}${spokenText.trimStart()}`;
  }
  return spokenText;
}
