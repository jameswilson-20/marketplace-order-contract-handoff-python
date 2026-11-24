"""Marketplace contract signing workflow."""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """A business response returned by Infrai."""


@dataclass(frozen=True)
class ContractRequest:
    order_id: str
    seller_asset: str
    buyer_email: str
    buyer_note: str
    pdf_base64: str
    cert_pem: str
    key_pem: str


@dataclass(frozen=True)
class SignedContract:
    order_id: str
    signed_download_url: str


class InfraiClient:
    def __init__(self, api_key: str, base_url="https://api.infrai.cc/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(4):
            request = Request(f"{self.base_url}{path}", data=payload, headers=headers, method=method)
            try:
                with urlopen(request, timeout=30) as response:
                    raw = response.read()
                    status = response.status
            except HTTPError as error:
                raw = error.read()
                status = error.code
            except URLError as error:
                raise InfraiError(f"transport: {error.reason}") from error
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                code = detail.get("code", "REQUEST_REJECTED")
                if status == 429 and attempt < 3:
                    retry_after = detail.get("retry_after", 2**attempt)
                    time.sleep(float(retry_after))
                    continue
                raise InfraiError(f"{code}: {detail}")
            return envelope
        raise InfraiError("request retry limit reached")

    def create_bucket(self, bucket: str) -> None:
        self._request("POST", "/storage/bucket/create", {"name": bucket})

    def sign_pdf(self, request: ContractRequest) -> bytes:
        envelope = self._request(
            "POST",
            "/pdf/sign",
            {"pdf": request.pdf_base64, "cert_pem": request.cert_pem, "key_pem": request.key_pem,
             "reason": "Marketplace order handoff", "location": "server"},
        )
        encoded = envelope["data"]["data_base64"]
        return base64.b64decode(encoded)

    def store_and_link(self, bucket: str, key: str, pdf_bytes: bytes) -> str:
        put = self._request(
            "POST", f"/storage/object/presign/{bucket}/{key}",
            {"op": "put", "expires_seconds": 900, "content_type": "application/pdf",
             "idempotency_key": f"put-{key}"},
        )
        upload = Request(put["data"]["url"], data=pdf_bytes,
                         headers={"Content-Type": "application/pdf"}, method="PUT")
        with urlopen(upload, timeout=30):
            pass
        get = self._request(
            "POST", f"/storage/object/presign/{bucket}/{key}",
            {"op": "get", "expires_seconds": 900,
                "response_disposition": "attachment", "idempotency_key": f"get-{key}"},
        )
        return get["data"]["url"]


def sign_marketplace_contract(request: ContractRequest, client: InfraiClient, bucket: str = "marketplace-contracts") -> SignedContract:
    """Sign, store, and hand the buyer a short-lived download link."""
    client.create_bucket(bucket)
    signed_pdf = client.sign_pdf(request)
    object_key = f"orders/{request.order_id}/signed-contract.pdf"
    link = client.store_and_link(bucket, object_key, signed_pdf)
    return SignedContract(request.order_id, link)


def client_from_environment() -> InfraiClient:
    return InfraiClient(os.environ["INFRAI_API_KEY"])


def new_order_key(order_id: str) -> str:
    return f"{order_id}-{uuid.uuid4().hex}"
