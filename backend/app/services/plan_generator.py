"""Generacion del plan de contingencia via LLM + contexto RAG."""
import json
import uuid

from openai import AsyncOpenAI

from app.config import settings
from app.models import (
    CompanyProfile,
    ContingencyPlan,
    PlanSection,
    PlanTier,
    RiskCategory,
)
from app.services import rag

RISK_TAGS = {
    RiskCategory.proveedores: ["proveedores", "contratos", "fuerza_mayor"],
    RiskCategory.ciberataque: ["datos_personales", "seguridad_informatica", "delitos_informaticos"],
    RiskCategory.desastre: ["emergencias", "proteccion_civil", "seguridad_laboral"],
}

FREE_SECTIONS = ["objetivo_y_alcance", "roles", "procedimientos_basicos"]
PREMIUM_SECTIONS = [
    "analisis_de_riesgos",
    "marco_legal_aplicable",
    "protocolo_ciberataque",
    "protocolo_desastre",
    "continuidad_proveedores",
    "comunicacion_crisis",
    "cumplimiento_y_evidencias",
]

PROMPT = """Sos un consultor experto en continuidad de negocio para empresas argentinas.
Genera la seccion "{section}" de un plan de contingencia para esta empresa:

{company}

Contexto legal relevante (cita articulos especificos cuando corresponda):
{context}

Respondé SOLO con JSON: {{"title": "...", "content": "...", "legal_refs": ["Ley X art Y", ...]}}
El contenido debe ser accionable, en espanol rioplatense, con pasos concretos.
Inclui el disclaimer de que no sustituye asesoria legal profesional en la seccion marco_legal_aplicable."""


def _all_tags(profile: CompanyProfile) -> list[str]:
    tags = ["continuidad"]
    for risk in profile.risks:
        tags += RISK_TAGS[risk]
    if profile.handles_personal_data:
        tags.append("datos_personales")
    return tags


async def _gen_section(section_id: str, profile: CompanyProfile, tier: PlanTier) -> PlanSection:
    query = f"plan de continuidad de negocio {section_id} empresa {profile.industry} Argentina"
    context_chunks = await rag.retrieve(query, tags=_all_tags(profile), k=6)
    context = "\n\n".join(
        f"[{c['law_title']} v{c['version']}]\n{c['text']}" for c in context_chunks
    )

    if not settings.openai_api_key:
        return PlanSection(
            id=section_id,
            title=section_id.replace("_", " ").title(),
            content=f"[stub sin LLM] Contexto recuperado: {len(context_chunks)} fragmentos.",
            legal_refs=sorted({c["law_title"] for c in context_chunks}),
        )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.llm_model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": PROMPT.format(
                    section=section_id,
                    company=profile.model_dump_json(indent=2),
                    context=context or "(sin contexto legal recuperado)",
                ),
            }
        ],
        temperature=0.3,
    )
    data = json.loads(resp.choices[0].message.content)
    return PlanSection(
        id=section_id,
        title=data["title"],
        content=data["content"],
        legal_refs=data.get("legal_refs", []),
    )


async def generate_plan(profile: CompanyProfile, tier: PlanTier) -> ContingencyPlan:
    section_ids = FREE_SECTIONS + (PREMIUM_SECTIONS if tier == PlanTier.premium else [])
    sections = [await _gen_section(s, profile, tier) for s in section_ids]
    laws = sorted({ref for s in sections for ref in s.legal_refs})
    return ContingencyPlan(
        id=uuid.uuid4().hex[:12],
        company=profile,
        tier=tier,
        sections=sections,
        laws_cited=laws,
    )
