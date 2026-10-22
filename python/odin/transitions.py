"""Portable I0 transition semantics, exercised against the shared Go fixtures."""


def transition(kind, data):
    if kind == "revision":
        return "apply" if data["current"] == data["expected"] else "stale_revision"
    if kind == "dedupe":
        if not data["seen"]:
            return "apply"
        return "duplicate" if data["same_content"] else "identity_conflict"
    if kind == "delivery":
        state = data["lookup"]
        if state in ("completed", "failed", "superseded"):
            return {
                "completed": "delivered",
                "failed": "failed",
                "superseded": "superseded",
            }[state]
        if state == "absent" and data["idempotent"] and data["authorized"]:
            return "queued"
        return "unknown"
    raise ValueError(kind)
