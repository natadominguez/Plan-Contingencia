import { wrapFetchWithPayment } from "@x402/fetch";
import { x402Client } from "@x402/core/client";
import { ExactEvmScheme } from "@x402/evm";
import type { WalletClient } from "viem";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export async function fetchJson(path: string, init?: RequestInit) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

/** fetch que paga automaticamente cuando el server responde 402 (x402 v2). */
export function paidFetch(walletClient: WalletClient) {
  const client = new x402Client();
  // ExactEvmScheme espera un signer; segun la version del SDK puede requerir
  // un adapter sobre el WalletClient de viem (ver docs.x402.org).
  client.register("eip155:10143", new ExactEvmScheme(walletClient as never));
  return wrapFetchWithPayment(fetch, client);
}

export async function paidPost(
  walletClient: WalletClient,
  path: string,
  body: unknown
) {
  const res = await paidFetch(walletClient)(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
