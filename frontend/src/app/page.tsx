"use client";

import { useState } from "react";
import { useAccount, useConnect, useWalletClient } from "wagmi";
import { fetchJson, paidPost } from "@/lib/api";

type Plan = {
  id: string;
  tier: string;
  plan_hash?: string;
  attestation_tx?: string;
  laws_cited: string[];
  sections: { id: string; title: string; content: string; legal_refs: string[]; version: number }[];
};

type Update = {
  law_id: string;
  title: string;
  old_version: string;
  new_version: string;
  summary: string;
  affected_plan_ids: string[];
};

export default function Home() {
  const { isConnected } = useAccount();
  const { connect, connectors, error: connectError, isPending: isConnecting } = useConnect();
  const { data: walletClient } = useWalletClient();

  const [company, setCompany] = useState({
    name: "Acme SA",
    industry: "logistica",
    size: "pyme",
    province: "Buenos Aires",
    handles_personal_data: true,
    critical_suppliers: ["transporte", "nube"],
    has_on_premise_infra: true,
    risks: ["fallo_proveedores", "ciberataque", "desastre_natural"],
  });
  const [plan, setPlan] = useState<Plan | null>(null);
  const [updates, setUpdates] = useState<Update[]>([]);
  const [attest, setAttest] = useState<{ plan_hash: string; tx_hash?: string; explorer_url?: string } | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const run = async (label: string, fn: () => Promise<void>) => {
    setBusy(label);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy("");
    }
  };

  return (
    <main>
      <h1>Plan Contingencia</h1>
      <p>Planes de continuidad de negocio — micropagos x402 en Monad testnet.</p>

      {!isConnected ? (
        <section>
          {connectors.map((c) => (
            <button key={c.uid} disabled={isConnecting} onClick={() => connect({ connector: c })}>
              {isConnecting ? "Conectando..." : `Conectar ${c.name}`}
            </button>
          ))}
          {connectError && <p style={{ color: "crimson" }}>{connectError.message}</p>}
          {typeof window !== "undefined" && !(window as { ethereum?: unknown }).ethereum && (
            <p>
              No se detecto una wallet inyectada en el navegador. Instala{" "}
              <a href="https://metamask.io" target="_blank" rel="noreferrer">
                MetaMask
              </a>{" "}
              u otra wallet compatible y recarga la pagina.
            </p>
          )}
        </section>
      ) : (
        <section style={{ border: "1px solid #ccc", padding: 16, borderRadius: 8 }}>
          <h2>Empresa</h2>
          <label>
            Nombre:{" "}
            <input value={company.name} onChange={(e) => setCompany({ ...company, name: e.target.value })} />
          </label>{" "}
          <label>
            Industria:{" "}
            <input value={company.industry} onChange={(e) => setCompany({ ...company, industry: e.target.value })} />
          </label>{" "}
          <label>
            Provincia:{" "}
            <input value={company.province} onChange={(e) => setCompany({ ...company, province: e.target.value })} />
          </label>

          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              disabled={!!busy}
              onClick={() =>
                run("Generando plan gratis...", async () => {
                  const p = await fetchJson("/plans/generate", {
                    method: "POST",
                    body: JSON.stringify({ company, tier: "free" }),
                  });
                  setPlan(p);
                })
              }
            >
              Generar plan (gratis)
            </button>

            <button
              disabled={!!busy || !walletClient}
              onClick={() =>
                run("Pagando $0.01 USDC y generando premium...", async () => {
                  if (!walletClient) throw new Error("Conecta tu wallet");
                  const p = await paidPost(walletClient, "/plans/generate-premium", {
                    company,
                    tier: "premium",
                  });
                  setPlan(p);
                })
              }
            >
              Generar plan premium ($0.01 USDC)
            </button>

            {plan && (
              <button
                disabled={!!busy}
                onClick={() =>
                  run("Registrando hash on-chain...", async () => {
                    setAttest(await fetchJson(`/plans/${plan.id}/attest`, { method: "POST" }));
                  })
                }
              >
                Attest on-chain
              </button>
            )}

            <button
              disabled={!!busy}
              onClick={() =>
                run("Buscando cambios normativos...", async () => {
                  await fetchJson("/regulations/check", { method: "POST" });
                  setUpdates(await fetchJson("/regulations/updates"));
                })
              }
            >
              Chequear cambios normativos
            </button>
          </div>
          {busy && <p>{busy}</p>}
          {error && <p style={{ color: "crimson" }}>{error}</p>}
        </section>
      )}

      {updates.length > 0 && (
        <section style={{ border: "1px solid orange", padding: 16, borderRadius: 8, marginTop: 16 }}>
          <h2>Cambios normativos detectados</h2>
          {updates.map((u) => (
            <div key={u.law_id + u.new_version} style={{ marginBottom: 8 }}>
              <strong>{u.title}</strong>: {u.old_version} → {u.new_version}
              <br />
              <small>{u.summary}</small>
              {plan && u.affected_plan_ids.includes(plan.id) && walletClient && (
                <div>
                  <button
                    disabled={!!busy}
                    onClick={() =>
                      run("Pagando update $0.005 USDC...", async () => {
                        setPlan(await paidPost(walletClient, "/plans/update-premium", { plan_id: plan.id }));
                      })
                    }
                  >
                    Actualizar plan ($0.005 USDC)
                  </button>
                </div>
              )}
            </div>
          ))}
        </section>
      )}

      {attest && (
        <section style={{ border: "1px solid green", padding: 16, borderRadius: 8, marginTop: 16 }}>
          <h2>Attestacion on-chain</h2>
          <p>
            Hash: <code>{attest.plan_hash}</code>
          </p>
          {attest.explorer_url ? (
            <a href={attest.explorer_url} target="_blank" rel="noreferrer">
              Ver transaccion en explorer
            </a>
          ) : (
            <p>(Sin tx — falta ATTESTER_PRIVATE_KEY en el backend)</p>
          )}
        </section>
      )}

      {plan && (
        <section style={{ marginTop: 16 }}>
          <h2>
            Plan {plan.id} ({plan.tier})
          </h2>
          <p>
            <small>Leyes citadas: {plan.laws_cited.join(", ") || "—"}</small>
          </p>
          {plan.sections.map((s) => (
            <details key={s.id} style={{ marginBottom: 8 }}>
              <summary>
                {s.title} (v{s.version})
              </summary>
              <p style={{ whiteSpace: "pre-wrap" }}>{s.content}</p>
              {s.legal_refs.length > 0 && <small>Refs: {s.legal_refs.join(", ")}</small>}
            </details>
          ))}
        </section>
      )}
    </main>
  );
}
