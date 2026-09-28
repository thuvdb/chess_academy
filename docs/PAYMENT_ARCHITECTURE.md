# PAYMENT_ARCHITECTURE.md — Kiến trúc Payment Service CAMS

> **CAMS — Chess Academy Management System**
> Tài liệu con của [SDLC.md](./SDLC.md)
> **Phiên bản:** 1.0 | **Ngày tạo:** 2026-09-20

---

## Tổng quan

CAMS triển khai thanh toán theo **3 cấp độ (Level)**, từ MVP đơn giản nhất cho đến tích hợp cổng thanh toán đầy đủ. Thiết kế đảm bảo **không phải đập đi làm lại** khi nâng cấp từ Level 1 → Level 2 → Level 3.

```
Level 1 — MVP
QR chuyển khoản VietQR + mã hóa đơn + Admin xác nhận

Level 2 — Automation
QR chuyển khoản + dịch vụ nhận diện giao dịch + Webhook + CAMS tự động PAID

Level 3 — Full Gateway
VNPay / MoMo / ZaloPay / VietQR / Bank → Payment Service → Unified API
```

---

## Cấu trúc thư mục Payment Service

```
backend/app/services/payment/
├── payment_service.py          # Interface chính — Frontend gọi vào đây
├── providers/
│   ├── base.py                 # Abstract base class
│   ├── payos.py                # PayOS integration (Level 2: QR + webhook auto)
│   ├── vnpay.py                # VNPay integration (Level 3)
│   ├── momo.py                 # MoMo integration (Level 3)
│   ├── zalopay.py              # ZaloPay integration (Level 3)
│   └── vietqr.py               # VietQR / Bank transfer (Level 1)
├── webhook/
│   ├── payos.py                # Xử lý webhook callback từ PayOS
│   ├── vnpay.py                # Xử lý IPN callback từ VNPay
│   ├── momo.py                 # Xử lý IPN callback từ MoMo
│   └── zalopay.py
├── signature/
│   ├── payos.py                # Checksum verification PayOS
│   ├── vnpay.py                # HMAC-SHA512 signature VNPay
│   └── momo.py                 # HMAC-SHA256 signature MoMo
└── reconciliation.py           # Đối soát giao dịch
```

---

## Payment State Machine

```
                         ┌─────────────────────────────┐
                         │         INVOICE              │
                         │    invoice_number: INV-001   │
                         │    amount: 500,000 VND       │
                         │    due_date: 2026-10-01      │
                         └──────────────┬──────────────┘
                                        │ tạo payment record
                                        ▼
                                   ┌─────────┐
                                   │ PENDING │  ← trạng thái ban đầu
                                   └────┬────┘
                                        │
             ┌──────────────────────────┼────────────────────────┐
             │                          │                        │
      Level 1: Admin confirm    Level 2: Webhook auto   Level 3: Gateway
             │                          │                        │
             ▼                          ▼                        ▼
        ┌─────────┐              ┌─────────────┐          ┌─────────────┐
        │ SUCCESS │              │   SUCCESS   │          │   SUCCESS   │
        └─────────┘              └─────────────┘          └─────────────┘
             │                                                    │
             │                    ┌─────────┐                    │
             └───────────────────►│  FAILED │◄───────────────────┘
                                  └────┬────┘
                                       │ refund request
                                       ▼
                                  ┌──────────┐
                                  │ REFUNDED │
                                  └──────────┘
                    
   Nếu quá due_date và vẫn PENDING:
   PENDING → (cron job) → OVERDUE (cập nhật invoice.status)
```

---

## Level 1 — MVP: QR VietQR + Admin Confirm

### Flow

```
CAMS Admin
   │
   ├── 1. Tạo hóa đơn hàng loạt cho lớp
   │      invoice_number = "INV-2026-001"
   │      amount = 500,000 VND
   │      qr_code_url = VietQR static QR
   │
   ▼
Phụ huynh nhận notification (email + app)
   │
   ├── 2. Mở app → xem QR + mã hóa đơn "INV-2026-001"
   │
   ├── 3. Chuyển khoản qua banking app
   │      Nội dung: "INV-2026-001 ho va ten"
   │
   ▼
Ngân hàng gửi SMS/email cho Admin
   │
   ▼
Admin mở CAMS → Finance Tab
   │
   ├── 4. Thấy danh sách hóa đơn PENDING
   │      Tìm theo invoice_number khớp với nội dung chuyển khoản
   │
   ├── 5a. Khớp đúng → Click "Xác nhận đã thu"
   │        payment.status = "success"
   │        payment.confirmed_by = admin_id
   │        invoice.status = "paid"
   │        invoice.paid_at = NOW()
   │        → Gửi notification cho phụ huynh: "Đã nhận thanh toán ✓"
   │
   └── 5b. Không rõ → "Xử lý tay" (ghi chú, liên hệ phụ huynh)
```

### VietQR Generation

```python
# providers/vietqr.py
import httpx

class VietQRProvider:
    """
    Tạo QR tĩnh theo chuẩn VietQR (EMVCo QR Code Standard).
    Không cần API key — dùng URL format chuẩn của napas.com.vn
    """
    BASE_URL = "https://img.vietqr.io/image"

    def generate_static_qr(
        self,
        bank_id: str,          # Ví dụ: "MB", "VCB", "TCB"
        account_no: str,
        account_name: str,
        amount: int,
        description: str,      # invoice_number làm nội dung CK
        template: str = "compact"
    ) -> str:
        """Trả về URL QR image."""
        url = (
            f"{self.BASE_URL}/{bank_id}-{account_no}-{template}.jpg"
            f"?amount={amount}"
            f"&addInfo={description}"
            f"&accountName={account_name}"
        )
        return url
```

---

## Level 2 — Webhook Auto

> ⚠️ Chỉ triển khai sau khi Level 1 đã ổn định và có lượng giao dịch thật.

### Flow

```
PayOS (hoặc dịch vụ tương tự)
   │  Tạo payment link + QR dynamic
   │  Nhận webhook khi phụ huynh thanh toán xong
   ▼
Webhook → POST /api/payments/webhook/payos
   │
   ├── Verify checksum (PayOS signature)
   ├── Parse transaction: orderCode, amount, description
   ├── Idempotency check (provider_transaction_id đã xử lý chưa?)
   ├── Match với invoice (theo orderCode = invoice_number)
   ├── Validate amount khớp
   └── Auto update: pending → success
```

### PayOS Integration

```python
# providers/payos.py
import httpx

class PayOSProvider(BasePaymentProvider):
    """
    PayOS — Payment gateway Việt Nam hỗ trợ VietQR + webhook tự động.
    Thay thế Sepay/OpenBanking cho Level 2.
    """
    BASE_URL = "https://api-merchant.payos.vn"
    
    def __init__(self):
        self.client_id = settings.PAYOS_CLIENT_ID
        self.api_key = settings.PAYOS_API_KEY
        self.checksum_key = settings.PAYOS_CHECKSUM_KEY
    
    def create_payment_link(
        self,
        invoice: Invoice,
        return_url: str,
        cancel_url: str
    ) -> dict:
        """Tạo payment link + QR dynamic."""
        body = {
            "orderCode": int(invoice.invoice_number.replace("INV-", "").replace("-", "")),
            "amount": int(invoice.amount),
            "description": f"Hoc phi {invoice.invoice_number}",
            "returnUrl": return_url,
            "cancelUrl": cancel_url,
        }
        body["signature"] = self._create_checksum(body)
        
        response = httpx.post(
            f"{self.BASE_URL}/v2/payment-requests",
            json=body,
            headers={"x-client-id": self.client_id, "x-api-key": self.api_key}
        )
        return response.json()  # {"checkoutUrl": "...", "qrCode": "..."}
    
    def verify_webhook(self, data: dict) -> bool:
        """Verify webhook checksum từ PayOS."""
        received_signature = data.pop("signature", "")
        expected_signature = self._create_checksum(data)
        return hmac.compare_digest(received_signature, expected_signature)
```

---

## Level 3 — Full Payment Gateway

### VNPay Integration

```python
# providers/vnpay.py
class VNPayProvider(BasePaymentProvider):
    
    def create_payment_url(self, invoice: Invoice, return_url: str) -> str:
        """Tạo URL redirect đến trang thanh toán VNPay."""
        params = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": settings.VNPAY_TMN_CODE,
            "vnp_Amount": int(invoice.amount * 100),  # VNPay nhân 100
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": invoice.invoice_number,
            "vnp_OrderInfo": f"Hoc phi {invoice.invoice_number}",
            "vnp_OrderType": "education",
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": return_url,
            "vnp_IpAddr": ...,
            "vnp_CreateDate": datetime.now().strftime("%Y%m%d%H%M%S"),
        }
        params["vnp_SecureHash"] = self._sign(params)
        return f"{settings.VNPAY_URL}?{urlencode(params)}"
    
    def verify_webhook(self, data: dict) -> bool:
        """Verify IPN callback từ VNPay."""
        received_hash = data.pop("vnp_SecureHash")
        expected_hash = self._sign(data)
        return hmac.compare_digest(received_hash, expected_hash)
```

### MoMo Integration

```python
# providers/momo.py
class MoMoProvider(BasePaymentProvider):
    
    def create_payment(self, invoice: Invoice) -> dict:
        """Tạo payment request lên MoMo API."""
        request_id = f"{invoice.invoice_number}-{int(time.time())}"
        body = {
            "partnerCode": settings.MOMO_PARTNER_CODE,
            "requestId": request_id,
            "amount": int(invoice.amount),
            "orderId": invoice.invoice_number,
            "orderInfo": f"Hoc phi {invoice.invoice_number}",
            "redirectUrl": settings.MOMO_REDIRECT_URL,
            "ipnUrl": settings.MOMO_IPN_URL,
            "requestType": "payWithMethod",
            "lang": "vi",
        }
        body["signature"] = self._sign_momo(body)
        response = httpx.post(settings.MOMO_ENDPOINT, json=body)
        return response.json()
```

---

## Payment Service Interface (Frontend không quan tâm provider)

```python
# payment_service.py
class PaymentService:
    """
    Abstraction layer — Frontend/API gọi class này, không gọi trực tiếp provider.
    Dễ dàng thêm provider mới mà không sửa code hiện có.
    """
    
    def __init__(self):
        self.providers = {
            "vietqr": VietQRProvider(),
            "payos": PayOSProvider(),       # Level 2
            "vnpay": VNPayProvider(),       # Level 3
            "momo": MoMoProvider(),         # Level 3
            "zalopay": ZaloPayProvider(),   # Level 3
        }
    
    def create_payment(
        self,
        invoice: Invoice,
        payment_method: str,   # "bank_transfer" | "cash" | "card" | "ewallet"
        payment_provider: str, # "vietqr" | "payos" | "vnpay" | "momo" | "zalopay"
        **kwargs
    ) -> PaymentResult:
        provider = self.providers.get(payment_provider)
        if not provider:
            raise ValueError(f"Unsupported payment provider: {payment_provider}")
        return provider.create_payment(invoice, **kwargs)
    
    def handle_webhook(self, provider_name: str, data: dict) -> WebhookResult:
        provider = self.providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        # Idempotency: kiểm tra provider_transaction_id đã xử lý chưa
        # Lớp 1 (nhanh): Redis cache với TTL 24h
        # Lớp 2 (sự thật cuối cùng): DB UNIQUE(payment_provider, provider_transaction_id)
        transaction_id = data.get("transaction_id") or data.get("vnp_TransactionNo") or data.get("orderCode")
        if self._is_processed(transaction_id):
            return WebhookResult(status="already_processed")
        
        return provider.handle_webhook(data)
    
    def admin_confirm(self, invoice_id: str, admin_id: str) -> PaymentResult:
        """Level 1: Admin xác nhận chuyển khoản thủ công."""
        # Update invoice + payment status
        ...
```

---

## Các vấn đề cần xử lý

### Idempotency
```python
# Mỗi payment request phải có idempotency_key
# Dùng (invoice_number + timestamp) làm unique request_id
#
# Lớp 1 (tối ưu): Lưu processed transaction_ids vào Redis với TTL 24h
# Lớp 2 (source of truth): DB UNIQUE(payment_provider, provider_transaction_id)
#
# Redis chỉ là cache — nếu Redis restart, mất data, DB constraint
# vẫn bảo vệ chống duplicate payment.
# Nếu cùng transaction_id gọi lại → return result cũ, không xử lý lại
```

### Signature Verification
```python
# VNPay: HMAC-SHA512
# MoMo: HMAC-SHA256
# Luôn verify signature TRƯỚC khi xử lý bất kỳ webhook nào
# Reject ngay nếu signature không khớp (HTTP 400)
```

### Timeout & Retry
```python
# Payment request timeout: 30 giây
# Nếu timeout: status = "pending" (không phải "failed")
# User có thể retry sau 5 phút
# Tự động cancel payment sau 15 phút không có response
```

### Duplicate Callback
```python
# Cổng thanh toán có thể gọi webhook nhiều lần
# PHẢI dùng idempotency key để ngăn xử lý trùng
# Log tất cả webhook calls (raw data) để audit
```

### Refund
```python
# Level 1: Admin refund thủ công (chuyển khoản lại)
# Level 3: Gọi API refund của cổng thanh toán
# Lưu refund record: payment.status = "refunded"
# Gửi notification cho phụ huynh
```

### Reconciliation (Đối soát)
```python
# reconciliation.py
# Chạy hàng ngày (cron job 23:59)
# So sánh payments trong CAMS với báo cáo giao dịch từ cổng thanh toán
# Flag các giao dịch không khớp để admin review
# Output: reconciliation_report_{date}.csv
```

---

## Test Cases Payment

| # | Test Case | Method | Expected |
|---|---|---|---|
| 1 | Tạo hóa đơn → sinh QR VietQR đúng format | Unit | URL QR hợp lệ |
| 2 | Admin xác nhận → invoice.status = "paid" | Integration | status = paid, notification gửi |
| 3 | VNPay webhook signature hợp lệ | Unit | verify = True |
| 4 | VNPay webhook signature sai | Unit | HTTP 400 |
| 5 | Duplicate webhook (cùng transaction_id) | Integration | Chỉ xử lý 1 lần |
| 6 | Webhook timeout 30s | Integration | status = pending, retry sau |
| 7 | Payment thành công → ELO/invoice cập nhật đúng | E2E | invoice = paid |
| 8 | Refund → payment.status = "refunded" | Integration | refund recorded |
| 9 | Reconciliation report đúng | Unit | report khớp với mock data |
| 10 | Sandbox → Production env switch | Manual | Đúng endpoint, đúng key |

---

## Roadmap Payment

| Sprint | Milestone |
|---|---|
| Sprint 5 | Level 1: VietQR + Admin confirm (MVP) |
| Sprint 5.5 | Level 2: Webhook auto (sau khi MVP ổn định) |
| Sprint 6+ | Level 3: VNPay + MoMo (sau khi có lượng giao dịch thật) |
| v3.0 | ZaloPay, Paypal, Stripe (dành cho học viên quốc tế) |
