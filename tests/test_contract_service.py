import base64

from src.contract_service import ContractRequest, SignedContract, sign_marketplace_contract


class RecordingClient:
    def __init__(self):
        self.calls = []

    def create_bucket(self, bucket):
        self.calls.append(("bucket", bucket))

    def sign_pdf(self, request):
        self.calls.append(("sign", request.order_id, request.seller_asset, request.buyer_note))
        return base64.b64decode(request.pdf_base64)

    def store_and_link(self, bucket, key, pdf_bytes):
        self.calls.append(("store", bucket, key, pdf_bytes))
        return "https://download.example.test/signed-contract.pdf"


def test_order_handoff_signs_seller_asset_and_returns_link():
    request = ContractRequest("order-42", "seller-listing-7", "buyer@example.test", "Ship on Friday", base64.b64encode(b"pdf").decode(), "CERT", "KEY")
    client = RecordingClient()

    result = sign_marketplace_contract(request, client)

    assert result == SignedContract("order-42", "https://download.example.test/signed-contract.pdf")
    assert client.calls == [
        ("bucket", "marketplace-contracts"),
        ("sign", "order-42", "seller-listing-7", "Ship on Friday"),
        ("store", "marketplace-contracts", "orders/order-42/signed-contract.pdf", b"pdf"),
    ]
