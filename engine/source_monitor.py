"""Detect changes in explicitly listed public sources without publishing them."""

import hashlib


def observe(state, doc_id, content, retrieved_at, source_url, content_type):
    digest = hashlib.sha256(content).hexdigest()
    previous = state.get(doc_id, {}).get("sha256")
    event = {
        "doc_id": doc_id, "source_url": source_url, "retrieved_at": retrieved_at,
        "sha256": digest, "previous_sha256": previous, "content_type": content_type,
        "status": "baseline" if previous is None else "changed" if previous != digest else "unchanged",
        "review_status": "needs_human_review" if previous and previous != digest else None,
    }
    next_state = dict(state)
    next_state[doc_id] = {"sha256": digest, "retrieved_at": retrieved_at,
                          "source_url": source_url, "content_type": content_type}
    return next_state, event
