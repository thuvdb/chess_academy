import test from 'node:test';
import assert from 'node:assert/strict';

// Test 1: Helper test logic xử lý tích lũy transcript từ SpeechRecognitionEvent
function processSpeechRecognitionResults(results) {
  let finalAccumulated = '';
  let interimCurrent = '';

  for (let i = 0; i < results.length; ++i) {
    const item = results[i];
    if (!item || !item[0]) continue;
    if (item.isFinal) {
      finalAccumulated += item[0].transcript;
    } else {
      interimCurrent += item[0].transcript;
    }
  }

  const fullTranscript = (finalAccumulated + interimCurrent).trim();
  const hasFinal = Boolean(finalAccumulated);
  const isCompleteFinal = interimCurrent.length === 0 && hasFinal;

  return {
    finalAccumulated: finalAccumulated.trim(),
    interimCurrent,
    fullTranscript,
    isCompleteFinal,
  };
}

// Test 2: Helper test dịch lỗi onerror sang tiếng Việt
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
      return null; // Silent abort
    default:
      message = `Lỗi nhận diện giọng nói: ${errorType || 'không xác định'}`;
  }
  return message;
}

// Test 3: Helper test logic ghép transcript vào ô nhập (append không đè text cũ)
function appendTranscriptToBase(baseText, spokenText) {
  if (baseText && baseText.trim().length > 0) {
    const separator = baseText.endsWith(' ') ? '' : ' ';
    return `${baseText}${separator}${spokenText.trimStart()}`;
  }
  return spokenText;
}

test('1. SpeechRecognition result accumulator handles interim and final segments accurately', () => {
  // Giả lập lần 1: Chỉ có kết quả tạm (interim)
  const step1 = [
    { isFinal: false, 0: { transcript: 'nước cờ' } },
  ];
  const res1 = processSpeechRecognitionResults(step1);
  assert.equal(res1.fullTranscript, 'nước cờ');
  assert.equal(res1.isCompleteFinal, false);

  // Giả lập lần 2: Câu 1 chốt final, đang nói tiếp interim câu 2
  const step2 = [
    { isFinal: true, 0: { transcript: 'nước cờ tốt nhất ' } },
    { isFinal: false, 0: { transcript: 'cho bên trắng' } },
  ];
  const res2 = processSpeechRecognitionResults(step2);
  assert.equal(res2.finalAccumulated, 'nước cờ tốt nhất');
  assert.equal(res2.interimCurrent, 'cho bên trắng');
  assert.equal(res2.fullTranscript, 'nước cờ tốt nhất cho bên trắng');
  assert.equal(res2.isCompleteFinal, false);

  // Giả lập lần 3: Cả hai câu đều đã chốt final
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
  // Trường hợp 1: Ô nhập ban đầu trống
  assert.equal(appendTranscriptToBase('', 'xin chào AI'), 'xin chào AI');
  assert.equal(appendTranscriptToBase('   ', 'xin chào AI'), 'xin chào AI');

  // Trường hợp 2: Ô nhập đã có chữ, chưa có dấu cách cuối
  assert.equal(
    appendTranscriptToBase('Hãy phân tích ván đấu', 'của Magnus Carlsen'),
    'Hãy phân tích ván đấu của Magnus Carlsen'
  );

  // Trường hợp 3: Ô nhập đã có dấu cách ở cuối
  assert.equal(
    appendTranscriptToBase('Hãy phân tích ván đấu ', 'của Magnus Carlsen'),
    'Hãy phân tích ván đấu của Magnus Carlsen'
  );
});

test('4. Mock SpeechRecognition lifecycle with mock callbacks', () => {
  let isListening = false;
  let receivedTranscript = '';
  let receivedFinal = false;
  let loggedError = null;

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
    abort() {
      isListening = false;
      if (this.onend) this.onend();
    }
  }

  const rec = new MockSpeechRecognition();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = 'vi-VN';

  rec.onstart = () => {
    isListening = true;
  };

  rec.onresult = (e) => {
    const res = processSpeechRecognitionResults(e.results);
    receivedTranscript = res.fullTranscript;
    receivedFinal = res.isCompleteFinal;
  };

  rec.onerror = (e) => {
    loggedError = mapSpeechErrorToVietnamese(e.error);
  };

  rec.onend = () => {
    isListening = false;
  };

  // 1. Bật mic
  rec.start();
  assert.equal(isListening, true);

  // 2. Nhận kết quả interim
  rec.onresult({
    resultIndex: 0,
    results: [{ isFinal: false, 0: { transcript: 'Khai cuộc Ruy Lopez' } }],
  });
  assert.equal(receivedTranscript, 'Khai cuộc Ruy Lopez');
  assert.equal(receivedFinal, false);

  // 3. Chốt kết quả final
  rec.onresult({
    resultIndex: 0,
    results: [{ isFinal: true, 0: { transcript: 'Khai cuộc Ruy Lopez có mạnh không?' } }],
  });
  assert.equal(receivedTranscript, 'Khai cuộc Ruy Lopez có mạnh không?');
  assert.equal(receivedFinal, true);

  // 4. Dừng mic
  rec.stop();
  assert.equal(isListening, false);

  // 5. Thử lỗi permission
  rec.onerror({ error: 'not-allowed' });
  assert.match(loggedError, /Chưa cấp quyền Microphone/);
});
