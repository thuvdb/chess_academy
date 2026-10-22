import test from 'node:test';
import assert from 'node:assert/strict';

// Import pure function to test
import { stripBoardTags } from '../src/utils/aiTutor.ts';

test('1. Normal text without <board> tags is preserved', () => {
  const input = 'Xin chào bạn! Hôm nay chúng ta sẽ học về Khai cuộc Italia.';
  assert.equal(stripBoardTags(input), input);
});

test('2. Strips <board> tag with newline before closing tag (exact issue from screenshot)', () => {
  const input = `Con hãy quan sát thế trận sau 3 nước đi đầu tiên nhé:
<board>{"moves":["e4","e5","Nf3","Nc6","Bc4"],"caption":"Thế cờ Khai cuộc Italia sau nước đi 3. Bc4"}
</board>
Con đã từng thử chơi khai cuộc Italia trong ván đấu thực tế bao giờ chưa? Con thích chọn cầm Trắng hay Đen ở thế trận này nào?`;

  const expected = `Con hãy quan sát thế trận sau 3 nước đi đầu tiên nhé:

Con đã từng thử chơi khai cuộc Italia trong ván đấu thực tế bao giờ chưa? Con thích chọn cầm Trắng hay Đen ở thế trận này nào?`;

  assert.equal(stripBoardTags(input), expected);
});

test('3. Strips <board> tag placed at the middle and end of text', () => {
  const atMiddle = 'Đoạn đầu. <board>{"moves":["e4"]}</board> Đoạn cuối.';
  assert.equal(stripBoardTags(atMiddle), 'Đoạn đầu.  Đoạn cuối.');

  const atEnd = 'Xem bàn cờ sau: <board>{"moves":["d4"]}</board>';
  assert.equal(stripBoardTags(atEnd), 'Xem bàn cờ sau:');
});

test('4. Handles multiple <board> tags in a single message', () => {
  const input = `Thế 1:
<board>{"moves":["e4","e5"]}</board>
Thế 2:
<board>
{"moves":["d4","d5"]}
</board>
Hết bài học.`;

  const expected = `Thế 1:

Thế 2:

Hết bài học.`;

  assert.equal(stripBoardTags(input), expected);
});

test('5. Handles tag case-insensitivity and extra attributes', () => {
  const input = 'Xem thế cờ: <BOARD>{"moves":["e4"]}</BOARD> hoặc <board class="custom">{"moves":["d4"]}</board>';
  assert.equal(stripBoardTags(input), 'Xem thế cờ:  hoặc');
});

test('6. Streaming mode hides incomplete opening tags and unclosed board content', () => {
  const basePrompt = 'Con hãy quan sát thế trận sau nhé:\n';

  // Incomplete tag prefix: "<b", "<boa", "<board"
  assert.equal(stripBoardTags(basePrompt + '<b', true), 'Con hãy quan sát thế trận sau nhé:');
  assert.equal(stripBoardTags(basePrompt + '<boa', true), 'Con hãy quan sát thế trận sau nhé:');
  assert.equal(stripBoardTags(basePrompt + '<board', true), 'Con hãy quan sát thế trận sau nhé:');

  // Incomplete tag opening: "<board>" or partial JSON
  assert.equal(stripBoardTags(basePrompt + '<board>', true), 'Con hãy quan sát thế trận sau nhé:');
  assert.equal(
    stripBoardTags(basePrompt + '<board>{"moves":["e4","e5"]', true),
    'Con hãy quan sát thế trận sau nhé:'
  );
  assert.equal(
    stripBoardTags(basePrompt + '<board>{"moves":["e4"]}\n', true),
    'Con hãy quan sát thế trận sau nhé:'
  );

  // Once fully closed with </board>, following stream chunks appear immediately
  const streamWithClosed = basePrompt + '<board>{"moves":["e4"]}</board>\nBạn thấy thế nào?';
  assert.equal(
    stripBoardTags(streamWithClosed, true),
    'Con hãy quan sát thế trận sau nhé:\n\nBạn thấy thế nào?'
  );
});

test('7. Cleans up excessive 3+ newlines after removal', () => {
  const input = 'Đoạn 1\n\n\n<board>{"moves":["e4"]}</board>\n\n\nĐoạn 2';
  assert.equal(stripBoardTags(input), 'Đoạn 1\n\nĐoạn 2');
});
