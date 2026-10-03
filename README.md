# Plan Contingencia

Plataforma de planes de continuidad de negocio (BCP) para empresas argentinas:

- **Generacion personalizada** del plan segun perfil de empresa, usando un **RAG** sobre normativa argentina vigente.
- **Agente monitor proactivo** que detecta cambios normativos y marca que planes/secciones quedan desactualizados.
- **Micropagos con x402 sobre Monad** (USDC): plan basico gratis, plan premium y actualizaciones pagas por request.
- **Attestacion on-chain**: hash SHA-256 del plan registrado en un contrato `PlanRegistry` en Monad testnet — prueba inmutable de existencia/integridad del plan en una fecha dada (util para auditorias).

> **Disclaimer:** es una herramienta de organizacion y preparacion. **No sustituye asesoria legal profesional.** El corpus legal son resumenes curados, no texto oficial.

## Estado verificado

| Componente | Estado |
|---|---|
| Backend deps (`requirements.txt`) | Instalado OK en Python 3.14.8 |
| `GET /api/health`, `/api/regulations/status` | Probado OK |
| `POST /api/plans/generate` (free, modo stub sin LLM) | Probado OK — RAG recupera 6 fragmentos del corpus |
| Agente monitor: deteccion de cambio de version | Probado OK — detecta edit en `manifest.json` y mapea planes afectados |
| `POST /api/plans/{id}/attest` | Devuelve hash OK (sin tx: falta `ATTESTER_PRIVATE_KEY`) |
| `POST /api/plans/update-premium` | Probado OK |
| Cobro x402 E2E (`generate-premium`) | Pendiente: requiere `PAY_TO_ADDRESS` + wallet cliente con USDC testnet |
| Frontend `npm install` / `npm run dev` | Pendiente de verificar |
| Deploy `PlanRegistry.sol` | Pendiente |

## Arquitectura

```
frontend/   Next.js + wagmi + @x402/fetch  →  la wallet del usuario paga al recibir HTTP 402
backend/    FastAPI + x402[fastapi]        →  middleware de cobro, RAG, LLM, agente monitor, attestacion web3
contracts/  PlanRegistry.sol               →  registro de hashes en Monad testnet
corpus/     Leyes AR curadas y versionadas →  seed del RAG y fuente de verdad para el agente
```

```
Usuario ──► Frontend ──► POST /api/plans/generate-premium
                            │ 402 Payment Required + PaymentRequirements
   wallet firma autorizacion (off-chain, sin tx)
            retry con PAYMENT-SIGNATURE ──► backend ──► Facilitador Monad
                                              verify + settle (USDC on-chain)
                            ◄── 200 + plan premium
Plan ──► hash SHA-256 ──► PlanRegistry.registerPlan(bytes32, planId, version)
Agente monitor (scheduler) ──► diff versiones de leyes ──► RegulationUpdate
            ──► usuario paga /plans/update-premium ──► secciones regeneradas ──► nuevo hash
```

**Datos de red:**

- Testnet: `eip155:10143` · Mainnet: `eip155:143`
- Facilitador Monad: `https://x402-facilitator.molandak.org` (requiere **x402 v2+**)
- USDC testnet: `0x534b2f3A21130d7a60830c2Df862319e593943A3` (6 decimales)
- Explorer: `https://testnet.monadexplorer.com`
- Precios: premium `$0.01` USDC · update `$0.005` USDC · basico gratis

## Estructura

```
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py                  # FastAPI: lifespan (indice RAG + scheduler), middlewares
│   │   ├── config.py                # Settings (pydantic-settings, lee .env)
│   │   ├── models.py                # Pydantic: CompanyProfile, ContingencyPlan, RegulationUpdate...
│   │   ├── payments/x402_setup.py   # Facilitador + money parser USDC testnet + rutas pagas
│   │   ├── api/plans.py             # generate, generate-premium, attest, update-premium, CRUD
│   │   ├── api/monitor.py           # updates, check (fuerza tick del agente), status
│   │   └── services/
│   │       ├── rag.py               # Embeddings OpenAI + indice vectorial JSON; fallback por tags
│   │       ├── plan_generator.py    # LLM genera secciones con contexto RAG; stub sin API key
│   │       ├── monitor_agent.py     # Diff de versiones del manifest → RegulationUpdate
│   │       ├── attestation.py       # SHA-256 del plan → PlanRegistry (o calldata fallback)
│   │       └── store.py             # Persistencia JSON en backend/db.json
│   └── corpus/argentina/            # manifest.json (versionado) + 7 docs legales curados
├── contracts/PlanRegistry.sol
└── frontend/                        # Next.js 15 + wagmi + @x402/*
    └── src/app/page.tsx             # UI demo: form empresa, pagos, attest, alertas
```

## Prerequisitos

Probado en Windows 11 con:

- **Python 3.14.8** (funciona con 3.11+)
- **Node.js 24.21 / npm 11.19** (funciona con Node 20+)
- **Git 2.55**
- Wallet EVM (MetaMask) con Monad testnet configurada

Nota Windows: si `python`/`node` no estan en el PATH, usar `py -m venv` y
`C:\Program Files\nodejs\npm.cmd`. Los scripts postinstall de npm necesitan
`node` en el PATH: `$env:Path = "C:\Program Files\nodejs;$env:Path"`.

## Setup

### 1. Backend

```powershell
cd backend
py -m venv .venv                      # o: python -m venv .venv
.\.venv\Scripts\Activate.ps1          # o .venv\Scripts\python.exe directo
pip install -r requirements.txt
cp .env.example .env                  # completar variables (ver tabla abajo)
uvicorn app.main:app --reload --port 8000
```

API en `http://localhost:8000` · docs en `http://localhost:8000/docs`.

### 2. Variables de entorno (`backend/.env`)

| Variable | Obligatoria | Para que |
|---|---|---|
| `PAY_TO_ADDRESS` | Para cobrar | Wallet que recibe los USDC. Sin ella los endpoints premium quedan abiertos (modo demo sin cobro). |
| `X402_FACILITATOR_URL` | No | Default: `https://x402-facilitator.molandak.org` |
| `MONAD_NETWORK` | No | `eip155:10143` (testnet) o `eip155:143` (mainnet) |
| `MONAD_USDC_ADDRESS` | No | Default: USDC testnet. En mainnet el SDK lo resuelve solo. |
| `OPENAI_API_KEY` | Para LLM real | Sin ella genera secciones stub que muestran el contexto RAG recuperado. |
| `LLM_MODEL` / `EMBEDDING_MODEL` | No | Defaults `gpt-4o-mini` / `text-embedding-3-small` |
| `MONAD_RPC_URL` | Para attestar | Default `https://testnet-rpc.monad.xyz` |
| `ATTESTER_PRIVATE_KEY` | Para attestar | Clave de la wallet que paga gas. Sin ella `/attest` solo devuelve el hash. |
| `PLAN_REGISTRY_ADDRESS` | Para attestar | Si esta vacia, manda el hash en el calldata de una tx (fallback valido). |
| `MONITOR_INTERVAL_SECONDS` | No | Default 60. Intervalo del agente monitor. |

### 3. Contrato `PlanRegistry`

Opcion A — Remix: compilar `contracts/PlanRegistry.sol` (^0.8.24) en
[remix.ethereum.org](https://remix.ethereum.org), deploy con MetaMask
conectada a Monad testnet, copiar la direccion a `PLAN_REGISTRY_ADDRESS`.

Opcion B — Foundry: `forge create contracts/PlanRegistry.sol:PlanRegistry --rpc-url $MONAD_RPC_URL --private-key $KEY`.

### 4. Frontend

```powershell
cd frontend
cp .env.local.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:8000/api
npm install
npm run dev                           # http://localhost:3000
```

### 5. Fondos testnet

- **MON** (gas): https://faucet.monad.xyz — para la wallet `ATTESTER_PRIVATE_KEY` y la del cliente
- **USDC**: https://faucet.circle.com → "Monad Testnet" — para la wallet del cliente que paga

## Guion de demo

1. Levantar backend + frontend, conectar MetaMask (Monad testnet).
2. Completar perfil → **Generar plan (gratis)**: 3 secciones basicas.
3. **Generar plan premium**: el backend responde 402 → la wallet firma la
   autorizacion → el facilitador verifica y liquida $0.01 USDC → llega el plan
   completo con citas legales.
4. **Attest on-chain**: SHA-256 del plan → `PlanRegistry.registerPlan` → link al explorer.
5. **Simular cambio normativo:** editar `"version"` de una ley en
   `backend/corpus/argentina/manifest.json` (ej. `"2000-original"` → `"2026-reformada"`).
6. **Chequear cambios normativos** (o esperar el tick del agente): aparece la
   `RegulationUpdate` con los `affected_plan_ids`.
7. **Actualizar plan ($0.005)**: se regeneran las secciones mapeadas a los tags
   de esa ley (version +1) → nuevo attest.

## Como funciona el agente monitor

`monitor_agent.py` corre cada `MONITOR_INTERVAL_SECONDS` (APScheduler):

1. Lee `manifest.json` → version actual por ley.
2. Compara contra `corpus/versions_snapshot.json` (se crea solo en el primer arranque).
3. Si una version cambio → crea `RegulationUpdate` con los planes afectados
   (planes que citaron esa ley o tienen secciones en `TAG_TO_SECTION`).
4. `GET /api/regulations/updates` las lista; `POST /api/regulations/check` fuerza un tick.

Mapeo `tags → secciones` (en `monitor_agent.TAG_TO_SECTION`): `datos_personales`
→ marco legal + protocolo ciberataque; `emergencias`/`proteccion_civil` →
protocolo desastre + procedimientos basicos; `proveedores`/`contratos` →
continuidad proveedores; etc.

## API

| Metodo | Ruta | Cobro |
|---|---|---|
| GET | `/api/health` | - |
| POST | `/api/plans/generate` | gratis |
| POST | `/api/plans/generate-premium` | x402 $0.01 USDC |
| GET | `/api/plans` · `/api/plans/{id}` | gratis |
| POST | `/api/plans/{id}/attest` | gratis (solo gas) |
| POST | `/api/plans/update-premium` `{plan_id}` | x402 $0.005 USDC |
| GET | `/api/regulations/updates` · `/status` | gratis |
| POST | `/api/regulations/check` | gratis |

## Agregar una ley al corpus

1. Crear `backend/corpus/argentina/<archivo>.md` — los parrafos separados por
   linea en blanco son los chunks que se embedean.
2. Sumar entrada en `manifest.json` con `id`, `title`, `file`, `version`, `tags`.
3. Reiniciar el backend: el indice RAG se reconstruye en el arranque
   (`backend/corpus/index.json` es generado, no se commitea).

## Troubleshooting

- **`npm install` falla con `"node" no se reconoce`**: los postinstall
  (`bufferutil`) necesitan `node` en el PATH → exportarlo antes.
- **`EPERM rmdir node_modules` en OneDrive**: antivirus/OneDrive bloquea;
  reintentar, o mover el repo fuera de OneDrive.
- **`PAY_TO_ADDRESS no configurado`**: warning esperado sin cobro; endpoints
  premium quedan abiertos.
- **Money parser**: en x402 Python 2.25 los parsers son **sincronicos** y
  reciben el monto como string decimal — ver `payments/x402_setup.py`.
- **Client side**: `ExactEvmScheme(walletClient)` puede requerir un adapter
  segun version del SDK — ver `frontend/src/lib/api.ts` y docs.x402.org.
- **Attest sin tx**: falta `ATTESTER_PRIVATE_KEY` o `PLAN_REGISTRY_ADDRESS`.

## Git / GitHub

```powershell
git init -b main
git add -A && git commit -m "MVP: BCP + x402 en Monad"
# con GitHub CLI autenticado:
gh repo create plan-contingencia --public --source . --push
# o crear el repo en github.com y:
git remote add origin https://github.com/<user>/plan-contingencia.git
git push -u origin main
```

## Limitaciones / fase 2

- Corpus son **resumenes curados**, no texto oficial; sin garantia de vigencia.
- El agente compara versiones del manifest (fuente simulada). Fase 2: ingestion
  real del Boletin Oficial / InfoLeg.
- `store.py` usa `db.json` (archivo). Produccion: Postgres + auth (SIWE).
- Marketplace de planes entre empresas (ya disenado, fuera del MVP).
- Notificaciones push/email del agente.
