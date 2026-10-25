"""Team SourceTag on every XRPL L1 transaction we sign.

XRPL Commons counts a team's on-chain activity by SourceTag. Rather than tag each of the ~30 call
sites, this wraps xrpl-py's autofill, which every sign path here goes through (autofill_and_sign,
submit_and_wait, and the explicit autofill before a multisign). A tx that already carries a
SourceTag keeps it. XRPL_SOURCE_TAG overrides the tag; XRPL_SOURCE_TAG=off turns tagging off.
"""
from __future__ import annotations

import os

from xrpl.models.transactions.transaction import Transaction

DEFAULT = "2610250016"


def source_tag() -> int | None:
    raw = os.environ.get("XRPL_SOURCE_TAG", DEFAULT).strip()
    return None if raw.lower() in ("", "off", "none", "0") else int(raw)


def tagged(tx: Transaction) -> Transaction:
    tag = source_tag()
    if tag is None or tx.source_tag is not None:
        return tx
    return type(tx).from_dict({**tx.to_dict(), "source_tag": tag})


def install() -> None:
    from xrpl.asyncio.transaction import main, reliable_submission
    if getattr(main.autofill, "_agentrail_tagged", False):
        return
    inner = main.autofill

    async def autofill(transaction, client, *a, **kw):
        return await inner(tagged(transaction), client, *a, **kw)

    autofill._agentrail_tagged = True
    main.autofill = autofill                    # async autofill_and_sign and the sync wrappers look it up here
    reliable_submission._autofill = autofill    # submit_and_wait imported it by name


install()
