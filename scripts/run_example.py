import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.contract_service import ContractRequest, client_from_environment, sign_marketplace_contract


SAMPLE_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


def main() -> None:
    request = ContractRequest(
        order_id=os.environ.get("MARKETPLACE_ORDER_ID", "demo-order"),
        seller_asset="seller-listing-7",
        buyer_email="buyer@example.test",
        buyer_note="Ship on Friday",
        pdf_base64=base64.b64encode(SAMPLE_PDF).decode(),
        cert_pem=os.environ["MARKETPLACE_CERT_PEM"],
        key_pem=os.environ["MARKETPLACE_KEY_PEM"],
    )
    result = sign_marketplace_contract(request, client_from_environment())
    print(result.signed_download_url)


if __name__ == "__main__":
    main()
