from fastapi import APIRouter

from app.services import monitor_agent, store

router = APIRouter()


@router.get("/regulations/updates")
async def list_updates():
    """Cambios normativos detectados por el agente."""
    return store.list_updates()


@router.post("/regulations/check")
async def trigger_check():
    """Fuerza un chequeo inmediato (util para la demo en vivo)."""
    detected = monitor_agent.check_for_updates()
    return {"detected": len(detected), "updates": detected}


@router.get("/regulations/status")
async def status():
    from app.services import rag
    manifest = rag.load_manifest()
    return {
        "laws_tracked": len(manifest["laws"]),
        "corpus_fingerprint": rag.corpus_fingerprint(),
        "monitor_interval_seconds": None,
    }
