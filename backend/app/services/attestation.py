"""Registro del hash del plan en Monad (PlanRegistry.sol).

Si no hay contrato desplegado, hace fallback a enviar el hash en el calldata
de una transaccion hacia la propia wallet — igualmente valido como prueba
de existencia e integridad on-chain.
"""
import hashlib
import json

from web3 import Web3

from app.config import settings
from app.models import ContingencyPlan

REGISTRY_ABI = [
    {
        "name": "registerPlan",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "planHash", "type": "bytes32"},
            {"name": "planId", "type": "string"},
            {"name": "version", "type": "uint256"},
        ],
        "outputs": [],
    },
    {
        "name": "PlanRegistered",
        "type": "event",
        "inputs": [
            {"name": "planHash", "type": "bytes32", "indexed": True},
            {"name": "planId", "type": "string", "indexed": False},
            {"name": "owner", "type": "address", "indexed": True},
            {"name": "version", "type": "uint256", "indexed": False},
            {"name": "timestamp", "type": "uint256", "indexed": False},
        ],
    },
]

EXPLORER = "https://testnet.monadexplorer.com/tx/"


def compute_plan_hash(plan: ContingencyPlan) -> str:
    canonical = json.dumps(
        {
            "company": plan.company.model_dump(),
            "sections": [s.model_dump(exclude={"version"}) for s in plan.sections],
            "tier": plan.tier.value,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return "0x" + hashlib.sha256(canonical.encode()).hexdigest()


def attest(plan: ContingencyPlan, version: int = 1) -> str | None:
    """Devuelve el tx hash, o None si falta configuracion."""
    if not settings.attester_private_key:
        return None

    w3 = Web3(Web3.HTTPProvider(settings.monad_rpc_url))
    acct = w3.eth.account.from_key(settings.attester_private_key)
    plan_hash_bytes = bytes.fromhex(plan.plan_hash.removeprefix("0x"))

    base_tx = {
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "gas": 200_000,
        "gasPrice": w3.eth.gas_price,
        "chainId": w3.eth.chain_id,
    }

    if settings.plan_registry_address:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(settings.plan_registry_address),
            abi=REGISTRY_ABI,
        )
        tx = contract.functions.registerPlan(
            plan_hash_bytes, plan.id, version
        ).build_transaction(base_tx)
    else:
        tx = {**base_tx, "to": acct.address, "value": 0, "data": plan_hash_bytes}

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    return "0x" + tx_hash.hex()
