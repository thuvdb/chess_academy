# CAMS — Chess Academy Management System

**CAMS (Chess Academy Management System)** là hệ thống quản lý học viện cờ vua toàn diện kết hợp Trí tuệ Nhân tạo (AI). Hệ thống hỗ trợ tự động số hóa bài tập từ sách PDF bằng Computer Vision, quản lý đào tạo (lớp học, học viên, lịch học, điểm danh), cổng thanh toán học phí VietQR, ngân hàng bài tập tương tác (Puzzle Bank) và tổ chức giải đấu cờ vua trực tuyến.

---

## 🌟 Tính năng chính

- **AI Scanner & Computer Vision**: Tự động nhận diện bàn cờ từ sách/tài liệu PDF, cắt ảnh, phân loại quân cờ bằng YOLOv8, trích xuất chuỗi FEN, phân tích nước đi với Stockfish và tự động đồng bộ sang ngân hàng bài tập.
- **Puzzle Bank & Luyện tập tương tác**: Thư viện bài tập chiến thuật phân loại theo chủ đề và độ khó, bàn cờ tương tác thông minh, giới hạn số lần gợi ý (Hint), tự động thu bài quá hạn và cập nhật ELO Rating.
- **Quản lý Đào tạo & Học viện**: Quản lý đa trung tâm (Multi-tenant isolation), phân quyền người dùng chặt chẽ (Super Admin, Center Admin, Giáo viên, Học sinh, Phụ huynh), quản lý lớp học, liên kết Phụ huynh – Học sinh và lịch học (`/schedule`).
- **Giải đấu Cờ vua (Tournaments)**: Tổ chức giải đấu cờ vua nội bộ theo hệ Thụy Sĩ (Swiss System) hoặc Vòng tròn (Round Robin), thi đấu cờ trực tiếp thời gian thực qua WebSocket.
- **Học phí & Tài chính**: Cấu hình gói học phí (Fee Plans), quản lý hóa đơn (Invoices) và tích hợp mã thanh toán VietQR tiêu chuẩn EMVCo.
- **Ứng dụng Di động**: Ứng dụng mobile đa nền tảng (React Native / Expo) dành cho học sinh và phụ huynh.

---

## 🏗️ Cấu trúc dự án & Công nghệ

| Thành phần               | Thư mục                 | Công nghệ sử dụng                                                                 |
| :----------------------- | :---------------------- | :-------------------------------------------------------------------------------- |
| **Backend API**          | `backend/`              | FastAPI (Python 3.11), SQLAlchemy 2 (Async), PostgreSQL 16, Stockfish Engine      |
| **Worker & Beat**        | `backend/`              | Celery 5.4, Redis 7 (Xử lý tác vụ nền cho AI Scan và tự động thu bài quá hạn)     |
| **AI / Computer Vision** | `backend/app/services/` | OpenCV, YOLOv8 (Ultralytics), PyMuPDF (fitz), Python-Chess                        |
| **AI Models**            | `backend/models/`       | Trọng số mô hình nhận diện bàn cờ & quân cờ (`*.pt`)                              |
| **Frontend Web**         | `frontend/`             | React 19, Vite 8, TypeScript, Tailwind CSS 4, Zustand, react-chessboard, chess.js |
| **Mobile App**           | `mobile/`               | React Native, Expo Router                                                         |
| **Tài liệu Dự án**       | `docs/`                 | Đặc tả yêu cầu, kiến trúc hệ thống, kịch bản kiểm thử UAT & hướng dẫn vận hành    |
| **Điều phối Dịch vụ**    | `docker-compose.yml`    | Quản lý 6 container (`backend`, `worker`, `beat`, `frontend`, `db`, `redis`)      |

---

## 📋 Yêu cầu môi trường

- **Docker** & **Docker Compose** (v2 trở lên)
- **Git**
- **Node.js** v20+ (chỉ cần nếu phát triển ngoài Docker hoặc chạy riêng ứng dụng `mobile`)

---

## 🚀 Hướng dẫn Cài đặt & Khởi động (Local & UAT Server)

### 1. Tải mã nguồn

```bash
git clone [https://github.com/thuvdb/chess_academy.git](https://github.com/thuvdb/chess_academy.git)
cd chess_academy
```
