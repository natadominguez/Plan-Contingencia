from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class RiskCategory(str, Enum):
    proveedores = "fallo_proveedores"
    ciberataque = "ciberataque"
    desastre = "desastre_natural"


class PlanTier(str, Enum):
    free = "free"
    premium = "premium"


class CompanyProfile(BaseModel):
    name: str
    industry: str
    size: str = Field(description="micro | pyme | mediana | grande")
    province: str = "Buenos Aires"
    handles_personal_data: bool = True
    critical_suppliers: list[str] = []
    has_on_premise_infra: bool = False
    risks: list[RiskCategory] = list(RiskCategory)


class PlanSection(BaseModel):
    id: str
    title: str
    content: str
    legal_refs: list[str] = []
    version: int = 1


class ContingencyPlan(BaseModel):
    id: str
    company: CompanyProfile
    tier: PlanTier = PlanTier.free
    sections: list[PlanSection] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    laws_cited: list[str] = []
    plan_hash: str | None = None
    attestation_tx: str | None = None


class GeneratePlanRequest(BaseModel):
    company: CompanyProfile
    tier: PlanTier = PlanTier.free


class UpdatePlanRequest(BaseModel):
    plan_id: str


class RegulationUpdate(BaseModel):
    law_id: str
    title: str
    old_version: str
    new_version: str
    summary: str
    affected_plan_ids: list[str] = []
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class AttestResponse(BaseModel):
    plan_id: str
    plan_hash: str
    tx_hash: str | None = None
    explorer_url: str | None = None
