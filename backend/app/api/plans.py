from fastapi import APIRouter, HTTPException

from app.models import (
    AttestResponse,
    GeneratePlanRequest,
    PlanTier,
    UpdatePlanRequest,
)
from app.services import attestation, monitor_agent, plan_generator, rag, store

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/plans/generate")
async def generate_free(req: GeneratePlanRequest):
    """Plan basico gratuito (tier free)."""
    plan = await plan_generator.generate_plan(req.company, PlanTier.free)
    store.save_plan(plan)
    return plan


@router.post("/plans/generate-premium")
async def generate_premium(req: GeneratePlanRequest):
    """Plan premium — protegido por x402 ($0.01 USDC en Monad testnet)."""
    plan = await plan_generator.generate_plan(req.company, PlanTier.premium)
    store.save_plan(plan)
    return plan


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan no encontrado")
    return plan


@router.get("/plans")
async def list_plans():
    return store.list_plans()


@router.post("/plans/{plan_id}/attest", response_model=AttestResponse)
async def attest_plan(plan_id: str):
    """Registra el hash del plan on-chain (PlanRegistry en Monad)."""
    plan = store.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan no encontrado")

    plan.plan_hash = attestation.compute_plan_hash(plan)
    tx = attestation.attest(plan, version=1)
    plan.attestation_tx = tx
    store.save_plan(plan)

    return AttestResponse(
        plan_id=plan.id,
        plan_hash=plan.plan_hash,
        tx_hash=tx,
        explorer_url=f"{attestation.EXPLORER}{tx}" if tx else None,
    )


@router.post("/plans/update-premium")
async def update_premium(req: UpdatePlanRequest):
    """Regenera secciones afectadas por cambio normativo — protegido por x402."""
    plan = store.get_plan(req.plan_id)
    if not plan:
        raise HTTPException(404, "Plan no encontrado")

    updates = [u for u in store.list_updates() if req.plan_id in u.affected_plan_ids]
    if not updates:
        raise HTTPException(400, "No hay cambios normativos pendientes para este plan")

    manifest = {law["id"]: law for law in rag.load_manifest()["laws"]}
    affected_sections = {
        section
        for u in updates
        for tag in manifest.get(u.law_id, {}).get("tags", [])
        for section in monitor_agent.TAG_TO_SECTION.get(tag, [])
    } or {s.id for s in plan.sections}

    for i, section in enumerate(plan.sections):
        if section.id in affected_sections:
            new_section = await plan_generator._gen_section(
                section.id, plan.company, plan.tier
            )
            new_section.version = section.version + 1
            plan.sections[i] = new_section

    store.save_plan(plan)
    return plan
