import test from 'node:test';
import assert from 'node:assert/strict';

// Helper 1: Nhận diện môi trường di động / Android
function isMobileOrAndroid(userAgent) {
  if (userAgent !== undefined) {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile/i.test(userAgent);
  }
  if (typeof navigator !== 'undefined') {
    const ua = navigator.userAgent || '';
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile/i.test(ua);
  }
  return false;
}

function getSpeechRecognitionContinuous(userAgent) {
  return !isMobileOrAndroid(userAgent);
}

// Helper 2: Ghép hai đoạn có phần trùng lặp ở biên
function mergeOverlappingSegments(prev, next) {
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

// Helper 3: Khử lặp cụm từ hoặc từ liên tiếp
function deduplicateRepeatedPhrases(text) {
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

// Helper 4: Tích lũy và khử duplicate kết quả từ SpeechRecognitionEvent
function processSpeechRecognitionResults(results, options = { deduplicate: true }) {
  if (!results || results.length === 0) {
    return {
      finalAccumulated: '',
      interimCurrent: '',
      fullTranscript: '',
      isCompleteFinal: false,
    };
  }

  const finalSegments = [];
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

          // 1. Trùng lặp hoàn toàn
          if (prev.toLowerCase() === trimmed.toLowerCase()) {
            continue;
          }

          // 2. Kết quả mới chứa kết quả cũ dạng prefix (Chrome Android re-emission)
          if (trimmed.toLowerCase().startsWith(prev.toLowerCase())) {
            finalSegments[finalSegments.length - 1] = trimmed;
            continue;
          }

          // 3. Kết quả cũ đã bao hàm kết quả mới
          if (prev.toLowerCase().startsWith(trimmed.toLowerCase())) {
            continue;
          }

          // 4. Overlap ở biên từ
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

  if (options.deduplicate !== false && finalAccumulated) {
    finalAccumulated = deduplicateRepeatedPhrases(finalAccumulated);
  }

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

// Helper 5: Dịch lỗi onerror sang tiếng Việt
function mapSpeechErrorToVietnamese(errorType) {
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

// Helper 6: Ghép transcript vào ô nhập (append không đè text cũ)
function appendTranscriptToBase(baseText, spokenText) {
  if (baseText && baseText.trim().length > 0) {
    const separator = baseText.endsWith(' ') ? '' : ' ';
    return `${baseText}${separator}${spokenText.trimStart()}`;
  }
  return spokenText;
}

// =================== TEST SUITE ===================

test('1. SpeechRecognition result accumulator handles interim and final segments accurately', () => {
  const step1 = [
    { isFinal: false, 0: { transcript: 'nước cờ' } },
  ];
  const res1 = processSpeechRecognitionResults(step1);
  assert.equal(res1.fullTranscript, 'nước cờ');
  assert.equal(res1.isCompleteFinal, false);

  const step2 = [
    { isFinal: true, 0: { transcript: 'nước cờ tốt nhất ' } },
    { isFinal: false, 0: { transcript: 'cho bên trắng' } },
  ];
  const res2 = processSpeechRecognitionResults(step2);
  assert.equal(res2.finalAccumulated, 'nước cờ tốt nhất');
  assert.equal(res2.interimCurrent, 'cho bên trắng');
  assert.equal(res2.fullTranscript, 'nước cờ tốt nhất cho bên trắng');
  assert.equal(res2.isCompleteFinal, false);

  const step3 = [
    { isFinal: true, 0: { transcript: 'nước cờ tốt nhất ' } },
    { isFinal: true, 0: { transcript: 'cho bên trắng là gì?' } },
  ];
  const res3 = processSpeechRecognitionResults(step3);
  assert.equal(res3.finalAccumulated, 'nước cờ tốt nhất cho bên trắng là gì?');
  assert.equal(res3.interimCurrent, '');
  assert.equal(res3.fullTranscript, 'nước cờ tốt nhất cho bên trắng là gì?');
  assert.equal(res3.isCompleteFinal, true);
});

test('2. SpeechRecognition error mapper translates standard errors to helpful Vietnamese messages', () => {
  assert.match(mapSpeechErrorToVietnamese('not-allowed'), /Chưa cấp quyền Microphone/);
  assert.match(mapSpeechErrorToVietnamese('no-speech'), /Không nghe thấy giọng nói/);
  assert.match(mapSpeechErrorToVietnamese('network'), /Không kết nối được dịch vụ nhận dạng giọng nói/);
  assert.match(mapSpeechErrorToVietnamese('audio-capture'), /Không tìm thấy microphone/);
  assert.match(mapSpeechErrorToVietnamese('language-not-supported'), /Ngôn ngữ tiếng Việt/);
  assert.equal(mapSpeechErrorToVietnamese('aborted'), null);
  assert.match(mapSpeechErrorToVietnamese('other-error'), /Lỗi nhận diện giọng nói: other-error/);
});

test('3. Transcript appending preserves existing user input in AiTutor text box', () => {
  assert.equal(appendTranscriptToBase('', 'xin chào AI'), 'xin chào AI');
  assert.equal(appendTranscriptToBase('   ', 'xin chào AI'), 'xin chào AI');

  assert.equal(
    appendTranscriptToBase('Hãy phân tích ván đấu', 'của Magnus Carlsen'),
    'Hãy phân tích ván đấu của Magnus Carlsen'
  );

  assert.equal(
    appendTranscriptToBase('Hãy phân tích ván đấu ', 'của Magnus Carlsen'),
    'Hãy phân tích ván đấu của Magnus Carlsen'
  );
});

test('4. Chrome Android deduplication: eliminates duplicate consecutive final tokens', () => {
  const duplicateEvents = [
    { isFinal: true, 0: { transcript: 'Khai cuộc Ruy Lopez' } },
    { isFinal: true, 0: { transcript: 'Khai cuộc Ruy Lopez' } }, // Exact duplicate token
  ];
  const res = processSpeechRecognitionResults(duplicateEvents);
  assert.equal(res.finalAccumulated, 'Khai cuộc Ruy Lopez');
  assert.equal(res.fullTranscript, 'Khai cuộc Ruy Lopez');
  assert.equal(res.isCompleteFinal, true);
});

test('5. Chrome Android deduplication: handles prefix expansion and word boundary overlap', () => {
  // Case A: Prefix expansion (Android sends cumulative sentence in subsequent item)
  const prefixEvents = [
    { isFinal: true, 0: { transcript: 'nước cờ tốt' } },
    { isFinal: true, 0: { transcript: 'nước cờ tốt nhất cho bên trắng' } },
  ];
  const resPrefix = processSpeechRecognitionResults(prefixEvents);
  assert.equal(resPrefix.finalAccumulated, 'nước cờ tốt nhất cho bên trắng');

  // Case B: Boundary overlap
  const overlapEvents = [
    { isFinal: true, 0: { transcript: 'phân tích ván' } },
    { isFinal: true, 0: { transcript: 'ván cờ của Magnus' } },
  ];
  const resOverlap = processSpeechRecognitionResults(overlapEvents);
  assert.equal(resOverlap.finalAccumulated, 'phân tích ván cờ của Magnus');
});

test('6. Phrase deduplication eliminates repeated multi-word phrases and stuttered tokens', () => {
  assert.equal(
    deduplicateRepeatedPhrases('khai cuộc Ý khai cuộc Ý làm sao để thắng'),
    'khai cuộc Ý làm sao để thắng'
  );

  assert.equal(
    deduplicateRepeatedPhrases('nước cờ nước cờ tốt nhất'),
    'nước cờ tốt nhất'
  );

  assert.equal(
    deduplicateRepeatedPhrases('Mã Mã f3'),
    'Mã f3'
  );

  assert.equal(
    deduplicateRepeatedPhrases('chiếu hết chiếu hết chiếu hết'),
    'chiếu hết'
  );
});

test('7. Continuous mode flag disabled on Chrome Android / Mobile, enabled on Desktop', () => {
  const androidChromeUA =
    'Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36';
  assert.equal(isMobileOrAndroid(androidChromeUA), true);
  assert.equal(getSpeechRecognitionContinuous(androidChromeUA), false);

  const iphoneSafariUA =
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1';
  assert.equal(isMobileOrAndroid(iphoneSafariUA), true);
  assert.equal(getSpeechRecognitionContinuous(iphoneSafariUA), false);

  const desktopWindowsUA =
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36';
  assert.equal(isMobileOrAndroid(desktopWindowsUA), false);
  assert.equal(getSpeechRecognitionContinuous(desktopWindowsUA), true);

  const desktopMacUA =
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36';
  assert.equal(isMobileOrAndroid(desktopMacUA), false);
  assert.equal(getSpeechRecognitionContinuous(desktopMacUA), true);
});

test('8. Mock SpeechRecognition lifecycle with mock callbacks', () => {
  let isListening = false;
  let receivedTranscript = '';
  let receivedFinal = false;

  class MockSpeechRecognition {
    constructor() {
      this.continuous = false;
      this.interimResults = false;
      this.lang = 'vi-VN';
      this.onstart = null;
      this.onresult = null;
      this.onerror = null;
      this.onend = null;
    }
    start() {
      isListening = true;
      if (this.onstart) this.onstart();
    }
    stop() {
      isListening = false;
      if (this.onend) this.onend();
    }
  }

  const rec = new MockSpeechRecognition();
  rec.continuous = getSpeechRecognitionContinuous('Linux; Android');
  assert.equal(rec.continuous, false);

  rec.onstart = () => { isListening = true; };
  rec.onresult = (e) => {
    const res = processSpeechRecognitionResults(e.results);
    receivedTranscript = res.fullTranscript;
    receivedFinal = res.isCompleteFinal;
  };
  rec.onend = () => { isListening = false; };

  rec.start();
  assert.equal(isListening, true);

  // Chrome Android sends duplicate token event
  rec.onresult({
    resultIndex: 0,
    results: [
      { isFinal: true, 0: { transcript: 'Khai cuộc Ruy Lopez' } },
      { isFinal: true, 0: { transcript: 'Khai cuộc Ruy Lopez' } },
    ],
  });
  assert.equal(receivedTranscript, 'Khai cuộc Ruy Lopez');
  assert.equal(receivedFinal, true);

  rec.stop();
  assert.equal(isListening, false);
});
