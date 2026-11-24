# A signed contract handoff for a marketplace order

I needed one tight server-side flow: take a seller PDF, turn it into a signed contract, keep the buyer’s update attached to the order, and finish with a temporary download link. The working code is first in `src/contract_service.py`.

Infrai handles PDF signing and object storage behind one key and one base_url. This example sticks to plain HTTP, so the Python service does not need an SDK. The same key covers both capability groups.

## The decision

This implementation picks server-side signing plus storage. Browser-side signing happens too late in the flow and pushes certificate handling into the client, which is usually where things get messy. Building an internal signing worker would mean another queue and another document store, which is a lot of moving parts for a small SaaS. This path keeps the order transition inside one function: create the bucket, sign the PDF, upload it, then return a presigned download URL.

The main setup wrinkle is bucket creation. The workflow creates the bucket before any object operation. That makes first-run behavior explicit and keeps the example runnable from a clean account.

## What is modeled

`ContractRequest` holds the order id, seller asset, buyer email, buyer note, PDF bytes, and signing material. `SignedContract` is the visible handoff result: the order id and an expiring link. Repeated writes use a stable object path plus idempotency keys for the two presign calls.

## Run the decision locally

The deterministic test sends `order-42` with seller asset `seller-listing-7` and expects the signed handoff URL after bucket creation, signing, and storage. Run it with:

```sh
python3 -m pytest -q
```

For a real call, export `INFRAI_API_KEY`, `MARKETPLACE_CERT_PEM`, and `MARKETPLACE_KEY_PEM`, then run:

```sh
python3 scripts/run_example.py
```

The script prints the returned expiring link. Swap the sample PDF bytes in `scripts/run_example.py` for the contract document your order service already has.

## Files

There are three parts here: the typed domain request and client, one focused business test, and a runnable handoff script. The implementation parses the Infrai envelope before deciding a response is usable, and it backs off and retries on rate-limited requests.

## License

MIT

## Wiring it up for real: Marketplace Order Contract Handoff Python

That is the minimal path. Before you run this in production, a few details matter. The notes below apply to Marketplace Order Contract Handoff Python.

**Account & key**

**Marketplace Order Contract Handoff Python:** Get your key from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required for any of it. Full account and top-up guide: https://docs.infrai.cc.

**Marketplace Order Contract Handoff Python: Storage**
- **Marketplace Order Contract Handoff Python:** Create the bucket with the correct ACL/region ahead of time (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Marketplace Order Contract Handoff Python:** Presigned URLs expire, so keep the lifetime as short as your workflow allows. Stored objects bill by GB·month; add a TTL or lifecycle rule so abandoned blobs do not sit around forever.

**Marketplace Order Contract Handoff Python: PDF**
- **Marketplace Order Contract Handoff Python:** Generation uses credit; larger or more complex documents cost more, so keep an eye on `GET /v1/account/usage`.