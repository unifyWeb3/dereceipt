/**
 * Contest Receipt — M2 skeleton.
 *
 * This is deliberately NOT the product yet. M2's gate is that the app builds
 * and serves; the real interface lands at M5. What M2 does fix, so that M5 is
 * not the first time these are discovered, is the three pieces every later
 * milestone depends on:
 *
 *   1. the pinned chain and explorer, asserted rather than assumed
 *   2. the real GenLayer lifecycle wait, which throws on Undetermined and
 *      Canceled instead of papering over them with a timeout
 *   3. business state and transaction lifecycle state, kept in SEPARATE
 *      regions, because "ACCEPTED is not finality" is a rubric criterion and
 *      it is cheapest to make visible by construction
 *
 * The three findings M1 established that shape M3 and M5 are recorded here as
 * comments rather than as code, because they are constraints on the contract
 * and the writer, not on this file:
 *
 *   - gl.vm.run_nondet, never run_nondet_unsafe. The published docs recommend
 *     run_nondet_unsafe; this runner does not export it, so docs-current code
 *     raises AttributeError at runtime.
 *   - The frontend reads VIEWS, never receipts. record["data"] is a write's
 *     input calldata; the accepted result is base64 in a format the SDK does
 *     not decode. A verdict must be readable from contract state.
 *   - A criterion that ends undetermined means "the jury could not settle
 *     this". It is never a count of validator objections: 1-2 of 5 validators
 *     were idle in every M1 run.
 */

import { createClient } from "genlayer-js";
import { studioDevnet } from "genlayer-js/chains";

/** Studio-dev, chain 61997. Temporary network: contracts here can vanish. */
export const CHAIN_ID = 61997;
export const CHAIN_ID_HEX = "0xf22d";
export const EXPLORER = "https://explorer-studio-dev.genlayer.com";
export const RPC = "https://studio-dev.genlayer.com/api";

/** Public build variable. The only one. Never a key. */
export const CONTRACT_ADDRESS =
  import.meta.env.VITE_CONTRACT_ADDRESS || "";

/**
 * Poll the GenLayer lifecycle until the transaction is final.
 *
 * Throws on `Undetermined` and `Canceled` rather than treating them as a slow
 * success. A jury that could not agree is a real outcome that the product
 * exists to record, so it must surface as a state, not be swallowed.
 */
export async function waitForFinalizedLifecycle(client, hash) {
  for (let attempt = 0; attempt < 200; attempt += 1) {
    const lifecycle = await client.request({
      method: "gen_getTransactionLifecycle",
      params: [{ txId: hash }],
    });
    const status = lifecycle?.storedStatus;
    if (status === "Finalized") return lifecycle;
    if (status === "Undetermined" || status === "Canceled") {
      throw new Error(`Transaction reached ${status}.`);
    }
    await new Promise((resolve) => setTimeout(resolve, 3000));
  }
  throw new Error(`Transaction ${hash} did not finalize in time.`);
}

/** Explorer deep link for a transaction ID. */
export function txLink(hash) {
  return `${EXPLORER}/tx/${hash}`;
}

/** Explorer deep link for a contract address. */
export function addressLink(address) {
  return `${EXPLORER}/address/${address}`;
}

const app = document.querySelector("#app");

app.innerHTML = `
  <header class="topbar">
    <div>
      <p class="eyebrow">GENLAYER BUILDER PROGRAM &middot; STUDIO-DEV PREVIEW</p>
      <h1>Contest Receipt</h1>
      <p class="lede">
        Auditable verdicts for AI-judged hackathons and grant rounds: evidence
        frozen at submission, every contested criterion kept on the record, and
        the programme's own overturn rate published.
      </p>
    </div>
    <div class="network-pill"><span class="dot"></span> Studio-dev &middot; chain ${CHAIN_ID}</div>
  </header>

  <main class="shell">
    <section class="notice">
      <strong>Skeleton build.</strong> The interface is wired at M5. This page
      exists to prove the build and the pinned chain, and it deliberately shows
      the two state regions the final app will keep separate.
    </section>

    <div class="columns">
      <section class="panel">
        <p class="eyebrow">REGION 1 &middot; BUSINESS STATE</p>
        <h2>Programme state</h2>
        <p class="hint">
          Contract state, read through views. Never decoded from a receipt.
        </p>
        <pre id="business">no contract connected</pre>
      </section>

      <section class="panel">
        <p class="eyebrow">REGION 2 &middot; TRANSACTION LIFECYCLE</p>
        <h2>Lifecycle state</h2>
        <p class="hint">
          Protocol lifecycle for one transaction. <code>ACCEPTED</code> is not
          finality; only <code>Finalized</code> is.
        </p>
        <pre id="lifecycle">idle</pre>
      </section>
    </div>

    <section class="panel">
      <p class="eyebrow">PINNED TARGET</p>
      <h2>Environment</h2>
      <dl class="facts">
        <dt>Chain id</dt><dd>${CHAIN_ID} (${CHAIN_ID_HEX})</dd>
        <dt>RPC</dt><dd>${RPC}</dd>
        <dt>Explorer</dt><dd><a href="${EXPLORER}" target="_blank" rel="noreferrer">${EXPLORER}</a></dd>
        <dt>Contract address</dt><dd>${CONTRACT_ADDRESS || "not set — VITE_CONTRACT_ADDRESS"}</dd>
        <dt>SDK</dt><dd>genlayer-js 2.0.0-rc.1</dd>
      </dl>
    </section>
  </main>
`;

/**
 * Prove the pinned chain is the one the SDK is actually pointed at, rather than
 * trusting a constant. A wallet on the wrong chain is the most common way a
 * demo fails silently.
 */
export async function assertPinnedChain() {
  const client = createClient({ chain: studioDevnet, rpcUrl: RPC });
  const reported = await client.request({ method: "eth_chainId", params: [] });
  const hex = typeof reported === "string" ? reported : `0x${Number(reported).toString(16)}`;
  if (Number.parseInt(hex, 16) !== CHAIN_ID) {
    throw new Error(
      `RPC reports chain ${hex}, expected ${CHAIN_ID_HEX}. Refusing to pretend.`
    );
  }
  return hex;
}

if (typeof window !== "undefined") {
  assertPinnedChain()
    .then((hex) => {
      document.querySelector("#business").textContent =
        `chain verified: ${hex}\nno contract deployed yet — the contract is written at M3`;
    })
    .catch((error) => {
      document.querySelector("#business").textContent = `chain check failed: ${error.message}`;
      document.querySelector("#lifecycle").textContent = "not reached";
    });
}
