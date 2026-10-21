# HƯỚNG DẪN TÍNH NĂNG VOICE: STT & TTS — CHESS AI TUTOR (CAMS-AI-02)

> **Mã công việc:** CAMS-AI-02 (Commits CAMS-0045 đến CAMS-0048)  
> **Chức năng:** Hỏi đáp cờ vua bằng giọng nói (STT) & AI phát âm thanh giảng dạy (TTS) kèm chuyển đổi ký hiệu FIDE.

---

## 1. TỔNG QUAN KIẾN TRÚC VOICE (GIAI ĐOẠN 2)

Hệ thống bổ sung 2 luồng xử lý giọng nói độc lập và bảo mật:
1. **Hỏi bằng lời (Speech to Text - STT):**
   - Chạy hoàn toàn tại trình duyệt client thông qua chuẩn Web Speech API (`webkitSpeechRecognition` / `SpeechRecognition`, ngôn ngữ `vi-VN`).
   - Kết quả nhận diện giọng nói được điền trực tiếp theo thời gian thực vào ô nhập câu hỏi để học viên kiểm tra, sửa lỗi (nếu có) trước khi bấm Gửi. Tuyệt đối **không tự động gửi** khi đang nói.
   - Logic được đóng gói trong custom hook [`useSpeechInput`](../frontend/src/hooks/useSpeechInput.ts) giúp dễ dàng hoán đổi sang OpenAI Whisper hoặc module Native cho Mobile App trong tương lai mà không ảnh hưởng UI.
2. **AI trả lời bằng giọng (Text to Speech - TTS):**
   - API `POST /api/ai-tutor/tts` nhận `message_id` (chỉ cho phép đọc tin nhắn của chính user, ngăn chặn nguy cơ bị lợi dụng làm cổng TTS miễn phí).
   - Bộ lọc [`speech_normalizer.py`](../backend/app/services/ai_tutor/speech_normalizer.py) loại bỏ thẻ `<board>`, định dạng Markdown, và chuyển đổi toàn bộ nước đi cờ vua sang tiếng Việt chuẩn sư phạm.
   - Thư viện `edge-tts` chạy bất đồng bộ (async non-blocking), hỗ trợ 2 giọng đọc:
     - `vi-VN-HoaiMyNeural` (Nữ - mặc định)
     - `vi-VN-NamMinhNeural` (Nam)
   - Lưu trữ cache file MP3 trên đĩa theo mã băm `SHA-256(voice + ":" + text)` với thời gian lưu 7 ngày, phục hồi tức thì với cờ `X-Cache: HIT`.

---

## 2. BẢNG ÁNH XẠ KÝ HIỆU CỜ VUA SANG TIẾNG VIỆT (FIDE TO VIETNAMESE)

Nhằm giúp học viên nhỏ tuổi nghe giảng tự nhiên và dễ hiểu, các ký hiệu cờ được chuyển đổi tự động trước khi đưa vào mô hình giọng đọc:

| Ký hiệu FIDE | Tiếng Việt đọc | Ví dụ FIDE | Lời đọc phát âm |
| :--- | :--- | :--- | :--- |
| `K` | Vua | `Ke2` | Vua e2 |
| `Q` | Hậu | `Qh5#` | Hậu h5 chiếu hết |
| `R` | Xe | `R1e2` | Xe 1 e2 |
| `B` | Tượng | `Bc4` | Tượng c4 |
| `N` | Mã | `Nf3`, `Nbd7` | Mã f3, Mã b d7 |
| `x` | ăn | `Bxf7+` | Tượng ăn f7 chiếu |
| `+` | chiếu | `e4+` | e4 chiếu |
| `#` | chiếu hết | `Qxf7#` | Hậu ăn f7 chiếu hết |
| `O-O` / `0-0` | nhập thành gần | `O-O` | nhập thành gần |
| `O-O-O` / `0-0-0` | nhập thành xa | `O-O-O` | nhập thành xa |
| `=Q` | phong cấp Hậu | `e8=Q#` | e8 phong cấp Hậu chiếu hết |
| `=R`, `=B`, `=N` | phong cấp Xe, Tượng, Mã | `g8=N` | g8 phong cấp Mã |
| `1.`, `2.`, `3.` | nước 1:, nước 2: | `1. e4 e5` | nước 1: e4 e5 |

---

## 3. CẤU HÌNH BIẾN MÔI TRƯỜNG MỚI

Bổ sung trong `.env` và `Settings` (`backend/app/core/config.py`):

| Tên biến | Mặc định | Ý nghĩa |
| :--- | :--- | :--- |
| `AI_TUTOR_TTS_VOICE` | `vi-VN-HoaiMyNeural` | Giọng đọc mặc định (`vi-VN-HoaiMyNeural` hoặc `vi-VN-NamMinhNeural`). |
| `AI_TUTOR_TTS_RATE_LIMIT_PER_MINUTE` | `15` | Giới hạn số lượt yêu cầu đọc audio mỗi phút trên từng người dùng. |
| `AI_TUTOR_TTS_MAX_CHARS` | `2000` | Số ký tự tối đa xử lý đọc mỗi lần (cắt gọn an toàn theo câu). |
| `AI_TUTOR_TTS_CACHE_DIR` | `storage/tts_cache` | Thư mục lưu cache file âm thanh MP3. |
| `AI_TUTOR_TTS_CACHE_TTL` | `604800` (7 ngày) | Thời gian hết hạn của cache MP3. |
| `AI_TUTOR_TTS_PROVIDER` | `edge_tts` | `edge_tts` (chính thức) hoặc `mock` (dành cho kiểm thử offline). |

---

## 4. HƯỚNG DẪN THỬ NGHIỆM THỦ CÔNG

### 4.1. Thử nghiệm trên Chrome Desktop (Windows / macOS)
1. Đăng nhập vào hệ thống tại `http://localhost:3000`.
2. Mở mục **"Hỏi đáp AI"** trên menu Sidebar.
3. **Thử Microphone (STT):**
   - Bấm vào nút biểu tượng Micro cạnh ô nhập tin nhắn.
   - Trình duyệt sẽ hiện popup yêu cầu cấp quyền: chọn **Allow** (Cho phép).
   - Nói bằng tiếng Việt: *"Khai cuộc Ý chơi như thế nào hả thầy?"*.
   - Chữ sẽ xuất hiện trong ô nhập; bạn có thể gõ thêm/sửa chữ rồi bấm nút **Gửi**.
4. **Thử Loa & Giọng đọc (TTS):**
   - Dưới câu trả lời của AI, bấm nút **"Nghe đọc"** (biểu tượng Loa).
   - Âm thanh MP3 sẽ phát với giọng Hoài My, nút Loa hiển thị hiệu ứng sóng âm đang nhảy.
   - Bấm lại nút Loa bất kỳ lúc nào để dừng phát.
   - Thử bật công tắc **"Tự động đọc"**: khi AI stream trả lời xong, âm thanh sẽ tự động phát.
   - Đổi sang giọng Nam Minh ở menu thả xuống góc trên bên phải để nghe giọng nam.

### 4.2. Thử nghiệm trên Mobile Web (Chrome Android)
- Chrome Android hỗ trợ đầy đủ Web Speech API.
- Cần cấp quyền Microphone khi được hỏi.
- Chế độ tự động đọc: Trình duyệt Android yêu cầu tối thiểu một thao tác chạm của người dùng trước khi trang web được phát âm thanh (User Activation Policy). Do người dùng đã bấm nút Gửi hoặc Micro, audio sẽ tự động phát bình thường.

### 4.3. Thử nghiệm trên iOS Safari (iPhone / iPad)
- Safari trên iOS 14.5+ đã hỗ trợ Web Speech API (`webkitSpeechRecognition`).
- **Lưu ý bảo mật của Apple:** Web Speech API và quyền Micro trên iOS chỉ hoạt động trên tên miền an toàn (`https://` hoặc `http://localhost`). Khi triển khai lên VPS UAT qua IP HTTP, Safari có thể tự động vô hiệu hóa Web Speech API; lúc này giao diện CAMS sẽ tự động ẩn nút Micro an toàn mà không gây lỗi giao diện.

---

## 5. GHI CHÚ NGOÀI PHẠM VI (EXPO MOBILE APP)

- **Web Speech API (`webkitSpeechRecognition`) không hỗ trợ bên trong WebView hoặc React Native core.**
- Khi đưa tính năng này lên ứng dụng mobile Expo trong giai đoạn tiếp theo:
  - Phía Mobile sẽ sử dụng thư viện chuyên dụng như `expo-speech-recognition` hoặc gửi file ghi âm qua endpoint Whisper.
  - Do hook `useSpeechInput` đã được thiết kế tách biệt hoàn toàn với giao diện `AiTutor.tsx`, toàn bộ giao diện chat hiện tại sẽ được tái sử dụng 100%.
