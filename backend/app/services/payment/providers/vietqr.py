from app.core.config import settings

class VietQRProvider:
    """
    Generate static QR code according to VietQR (EMVCo QR Code Standard).
    No API key needed, uses napas.com.vn standard URL format via img.vietqr.io.
    """
    BASE_URL = "https://img.vietqr.io/image"

    def __init__(self):
        # We assume settings has these defined
        self.bank_id = getattr(settings, "VIETQR_BANK_ID", "MB")
        self.account_no = getattr(settings, "VIETQR_ACCOUNT_NO", "1234567890")
        self.account_name = getattr(settings, "VIETQR_ACCOUNT_NAME", "CAMS CHESS ACADEMY")

    def generate_static_qr(
        self,
        amount: int,
        description: str,
        template: str = "compact"
    ) -> str:
        """Return the URL of the QR image."""
        url = (
            f"{self.BASE_URL}/{self.bank_id}-{self.account_no}-{template}.jpg"
            f"?amount={amount}"
            f"&addInfo={description}"
            f"&accountName={self.account_name.replace(' ', '%20')}"
        )
        return url
