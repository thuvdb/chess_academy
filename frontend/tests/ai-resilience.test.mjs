import test from 'node:test';
import assert from 'node:assert/strict';

// Helper mô phỏng logic filter message assistant rỗng trong AiTutor.tsx
function cleanEmptyAssistantMessages(messages) {
  return messages.filter(
    (m) => !(m.role === 'assistant' && !m.content.trim() && !m.board_data)
  );
}

// Helper mô phỏng logic ánh xạ mã lỗi sang thông báo thân thiện
function getFriendlyErrorMessage(code, serverMsg) {
  if (code === 'overloaded') {
    return 'Hệ thống AI hiện đang chịu tải cao từ Google. Vui lòng bấm "Thử lại" sau vài giây hoặc hỏi lại sau ít phút.';
  }
  if (code === 'quota') {
    return 'Hệ thống AI tạm thời vượt hạn ngạch yêu cầu. Vui lòng chờ ít phút rồi thử lại.';
  }
  if (code === 'timeout') {
    return 'Kết nối tới AI bị quá thời gian phản hồi (timeout). Vui lòng bấm "Thử lại".';
  }
  return serverMsg || 'Không thể nhận phản hồi từ AI. Vui lòng thử lại sau.';
}

test('cleanEmptyAssistantMessages removes empty assistant placeholder without content or board', () => {
  const initialMessages = [
    { role: 'user', content: 'Xin chào AI' },
    { role: 'assistant', content: 'Chào bạn! Tôi có thể giúp gì?' },
    { role: 'user', content: 'Gemini bị lỗi 503' },
    { role: 'assistant', content: '', board_data: null }, // placeholder rỗng khi bắt đầu stream
  ];

  const cleaned = cleanEmptyAssistantMessages(initialMessages);
  assert.equal(cleaned.length, 3);
  assert.equal(cleaned[cleaned.length - 1].role, 'user');
  assert.equal(cleaned[cleaned.length - 1].content, 'Gemini bị lỗi 503');
});

test('cleanEmptyAssistantMessages preserves assistant messages with content or board_data', () => {
  const messagesWithBoard = [
    { role: 'user', content: 'Thế cờ này thế nào?' },
    { role: 'assistant', content: '', board_data: { moves: ['e4', 'e5'] } },
    { role: 'user', content: 'Còn thế này?' },
    { role: 'assistant', content: 'Nước tốt là Nf3', board_data: null },
  ];

  const cleaned = cleanEmptyAssistantMessages(messagesWithBoard);
  assert.equal(cleaned.length, 4);
});

test('getFriendlyErrorMessage maps known codes appropriately', () => {
  const overloadedMsg = getFriendlyErrorMessage('overloaded', 'Google is busy');
  assert.match(overloadedMsg, /chịu tải cao/);
  assert.match(overloadedMsg, /Thử lại/);

  const quotaMsg = getFriendlyErrorMessage('quota', 'Quota exceeded');
  assert.match(quotaMsg, /hạn ngạch/);

  const timeoutMsg = getFriendlyErrorMessage('timeout', 'Read timed out');
  assert.match(timeoutMsg, /quá thời gian phản hồi/);

  const otherMsg = getFriendlyErrorMessage('other', 'Custom server error');
  assert.equal(otherMsg, 'Custom server error');
});
