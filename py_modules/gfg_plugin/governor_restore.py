"""Interpret restore results without confusing no-op with a failed undo.

CPU restore returns 'anything written', not 'success'. Power returns a structured
result. Keep those contracts separate; neither external takeover nor a no-op
requires a write over the new owner.
"""
from typing import Any, Dict, Optional


def power_restore_error(result: Any) -> Optional[str]:
    if not isinstance(result, dict) or result.get("success") is not True:
        return str((result or {}).get("error") or "power restore did not confirm success") if isinstance(result, dict) else "invalid power restore result"
    state = result.get("state") or {}
    if state.get("owned") or state.get("restore_pending"):
        return str(state.get("error") or "power ownership/restore remains pending")
    return None


def cpu_restore_error(status: Dict[str, Any]) -> Optional[str]:
    if status.get("owned") or status.get("restore_pending"):
        return str(status.get("error") or "CPU restore remains pending")
    return None
