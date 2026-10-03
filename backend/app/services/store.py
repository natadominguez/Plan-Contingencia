"""Persistencia minima para el MVP: JSON en disco.

Suficiente para la demo; migrar a Postgres/SQLite en produccion.
"""
import json
from pathlib import Path

from app.models import ContingencyPlan, RegulationUpdate

DB_PATH = Path(__file__).resolve().parents[2] / "db.json"


def _load() -> dict:
    if not DB_PATH.exists():
        return {"plans": {}, "updates": []}
    return json.loads(DB_PATH.read_text(encoding="utf-8"))


def _save(db: dict) -> None:
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def save_plan(plan: ContingencyPlan) -> None:
    db = _load()
    db["plans"][plan.id] = json.loads(plan.model_dump_json())
    _save(db)


def get_plan(plan_id: str) -> ContingencyPlan | None:
    raw = _load()["plans"].get(plan_id)
    return ContingencyPlan.model_validate(raw) if raw else None


def list_plans() -> list[ContingencyPlan]:
    return [ContingencyPlan.model_validate(p) for p in _load()["plans"].values()]


def save_update(update: RegulationUpdate) -> None:
    db = _load()
    db["updates"] = [
        u for u in db["updates"]
        if not (u["law_id"] == update.law_id and u["new_version"] == update.new_version)
    ]
    db["updates"].append(json.loads(update.model_dump_json()))
    _save(db)


def list_updates() -> list[RegulationUpdate]:
    return [RegulationUpdate.model_validate(u) for u in _load()["updates"]]
