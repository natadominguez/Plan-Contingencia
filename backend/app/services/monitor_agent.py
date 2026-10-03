"""Agente proactivo: detecta cambios normativos y marca planes afectados.

Estrategia MVP: el corpus tiene manifest.json con la version de cada ley.
El agente compara contra un snapshot previo (versions_snapshot.json). Cuando
una ley cambia de version, mapea sus tags -> planes que citaron esa ley ->
genera una RegulationUpdate. El endpoint /plans/{id}/update-premium (pago
x402) regenera las secciones afectadas.

Para la demo basta editar "version" en manifest.json (o dropear un archivo
nuevo en corpus/argentina/) y el agente lo detecta en el proximo tick.
"""
import json
import logging
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.models import RegulationUpdate
from app.services import rag, store

log = logging.getLogger("monitor")

CORPUS_DIR = Path(__file__).resolve().parents[2] / "corpus" / "argentina"
SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "corpus" / "versions_snapshot.json"

TAG_TO_SECTION = {
    "datos_personales": ["marco_legal_aplicable", "protocolo_ciberataque"],
    "seguridad_informatica": ["protocolo_ciberataque"],
    "delitos_informaticos": ["protocolo_ciberataque", "cumplimiento_y_evidencias"],
    "emergencias": ["protocolo_desastre", "procedimientos_basicos"],
    "proteccion_civil": ["protocolo_desastre"],
    "seguridad_laboral": ["protocolo_desastre", "marco_legal_aplicable"],
    "proveedores": ["continuidad_proveedores"],
    "contratos": ["continuidad_proveedores", "marco_legal_aplicable"],
    "fuerza_mayor": ["continuidad_proveedores", "marco_legal_aplicable"],
    "continuidad": ["marco_legal_aplicable"],
}


def _load_snapshot() -> dict[str, str]:
    if not SNAPSHOT_PATH.exists():
        return {}
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def _save_snapshot(versions: dict[str, str]) -> None:
    SNAPSHOT_PATH.write_text(json.dumps(versions, indent=2), encoding="utf-8")


def check_for_updates() -> list[RegulationUpdate]:
    manifest = rag.load_manifest()
    previous = _load_snapshot()
    current = {law["id"]: law["version"] for law in manifest["laws"]}
    detected: list[RegulationUpdate] = []

    for law in manifest["laws"]:
        old = previous.get(law["id"])
        new = law["version"]
        if old is None or old == new:
            continue

        affected_tags = set(law.get("tags", []))
        affected_sections = {
            s for tag in affected_tags for s in TAG_TO_SECTION.get(tag, [])
        }

        # Planes afectados: los que citan la ley o tienen secciones mapeadas.
        affected_plan_ids = []
        for plan in store.list_plans():
            plan_law_ids = {ref.split(" ")[0] for ref in plan.laws_cited}
            has_law = law["id"] in plan_law_ids or any(
                law["title"].split(",")[0] in ref for ref in plan.laws_cited
            )
            has_section = any(s.id in affected_sections for s in plan.sections)
            if has_law or has_section:
                affected_plan_ids.append(plan.id)

        update = RegulationUpdate(
            law_id=law["id"],
            title=law["title"],
            old_version=old,
            new_version=new,
            summary=law.get("change_summary", f"Nueva version {new} de {law['title']}"),
            affected_plan_ids=affected_plan_ids,
        )
        store.save_update(update)
        detected.append(update)
        log.info("Cambio normativo detectado: %s %s -> %s (%d planes)",
                 law["id"], old, new, len(affected_plan_ids))

    if current != previous:
        _save_snapshot(current)

    return detected


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_for_updates,
        "interval",
        seconds=settings.monitor_interval_seconds,
        id="regulation-monitor",
    )
    scheduler.start()
    return scheduler
