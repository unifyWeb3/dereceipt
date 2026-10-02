/**
 * The one path to the contract. Every read and every write in the app goes
 * through this file, so there is exactly one place where a chain id, an
 * identifier type or a lifecycle rule can be got wrong.
 *
 * Three rules are enforced here rather than at each call site, because each one
 * fails silently otherwise:
 *
 * 1. **The chain is asserted, not assumed.** A wallet on the wrong chain is the
 *    most common way a demo fails, and on GenLayer it fails as an opaque
 *    `code=-32000`. We refuse before sending rather than papering over it.
 * 2. **`program_id` is a string and `entry_index` is a number.** Asserted on the
 *    way in. See `lib/identifiers.js` for the measurement.
 * 3. **A transaction is not done when it is submitted.** `writeAndWait` polls
 *    the protocol lifecycle to `FINALIZED` and *throws* on `UNDETERMINED` or
 *    `CANCELED`, because a jury that could not agree is a real outcome this
 *    product exists to record — not a timeout to be swallowed.
 */

import { createClient } from "genlayer-js";
import { studioDevnet } from "genlayer-js/chains";

import {
  CHAIN_ID,
  CHAIN_ID_HEX,
  CONTRACT_ADDRESS,
  RPC,
} from "../config.js";
import { assertEntryIndex, assertProgramId } from "./identifiers.js";

let client = null;

export function getClient() {
  if (!client) {
    client = createClient({ chain: studioDevnet, rpcUrl: RPC });
  }
  return client;
}

/**
 * Confirm the node really is the chain we claim to be talking to.
 *
 * Throws with both ids if it is not. Called before anything is sent, so a
 * misconfigured build variable fails loudly at boot instead of producing a
 * screen of zeroes.
 */
export async function assertPinnedChain() {
  const reported = await getClient().request({
    method: "eth_chainId",
    params: [],
  });
  const hex =
    typeof reported === "string" ? reported : `0x${Number(reported).toString(16)}`;
  if (Number.parseInt(hex, 16) !== CHAIN_ID) {
    throw new Error(
      `RPC reports chain ${hex}, expected ${CHAIN_ID_HEX} (${CHAIN_ID}). ` +
        `Refusing to pretend — reads from the wrong chain return nothing and ` +
        `writes would be signed for a network this app does not target.`,
    );
  }
  return hex;
}

// ---------------------------------------------------------------------------
// Reads
// ---------------------------------------------------------------------------

/**
 * Read one view. `programId` is validated, so no call site can pass an integer.
 *
 * A refusal is returned, not thrown. The contract refuses in two different ways
 * and the UI shows both differently: a *return* is `{"ok": false, "error": …}`
 * from a write, while a *view* that reverts fails the call outright.
 */
export async function read(method, args = []) {
  const checked = args.map((value, index) =>
    typeof value === "string" && looksLikeProgramId(method, index, args)
      ? assertProgramId(value)
      : typeof value === "number" && looksLikeEntryIndex(method, index, args)
        ? assertEntryIndex(value)
        : value,
  );
  return getClient().readContract({
    address: CONTRACT_ADDRESS,
    functionName: method,
    args: checked,
  });
}

function looksLikeProgramId(method, index, args) {
  // Program-scoped views take program_id first.
  return index === 0 && /^get_(program|entry|receipt|accuracy)/.test(method) && args.length > 0;
}

function looksLikeEntryIndex(method, index, args) {
  // Entry-scoped views take program_id then entry_index.
  return index === 1 && args.length >= 2;
}

/** Convenience wrappers, so call sites read as prose. */
export const readProgram = (programId) => read("get_program", [assertProgramId(programId)]);
export const readEntry = (programId, index) =>
  read("get_entry", [assertProgramId(programId), assertEntryIndex(index)]);
export const readReceipt = (programId, index) =>
  read("get_receipt", [assertProgramId(programId), assertEntryIndex(index)]);
export const readAccuracy = (programId) => read("get_accuracy", [assertProgramId(programId)]);
export const readDigest = (programId) => read("get_receipt_digest", [assertProgramId(programId)]);
export const readBalance = () => read("get_contract_balance", []);

// ---------------------------------------------------------------------------
// Writes
// ---------------------------------------------------------------------------

/**
 * The only write path. There is no second code path, by design.
 *
 * Returns the transaction hash plus the lifecycle that was observed. Throws on
 * `Undetermined` or `Canceled` — both are real outcomes that the product must
 * surface rather than render as success.
 */
export async function writeAndWait(method, args = [], options = {}) {
  await assertPinnedChain();

  const account = options.account;
  if (!account) {
    throw new Error(
      "No account. Connect a wallet first — this app never holds a key.",
    );
  }

  const payload = {
    address: CONTRACT_ADDRESS,
    functionName: method,
    args,
    account,
  };
  if (options.value !== undefined) payload.value = options.value;

  const hash = await getClient().writeContract(payload);
  const txHash = typeof hash === "string" ? hash : hash?.hash;
  if (!txHash) {
    throw new Error(`${method} returned no transaction id.`);
  }

  const transaction = await getClient().waitForFinalization({
    hash: txHash,
    interval: 3000,
    retries: 120,
    fullTransaction: true,
  });

  return { hash: txHash, transaction, lifecycle: readLifecycle(transaction) };
}

/**
 * Pull the protocol lifecycle out of a transaction record.
 *
 * GenLayer's lifecycle is a separate layer from business state, and the two are
 * rendered in separate regions for exactly that reason. `ACCEPTED` is not
 * finality; only `FINALIZED` is.
 */
export function readLifecycle(transaction) {
  const raw = transaction?.lifecycle ?? transaction?.protocolLifecycle ?? {};
  const state = String(raw.state ?? raw.storedStatus ?? "UNKNOWN").toUpperCase();
  const outcome = String(raw.outcome ?? "").toUpperCase();
  const failed = state === "UNDETERMINED" || state === "CANCELED";

  return {
    state,
    outcome,
    failed,
    // The two states a jury can reach that are not success.
    undetermined: state === "UNDETERMINED",
    canceled: state === "CANCELED",
    votes: raw.votes ?? null,
    round: raw.currentRound ?? null,
    rounds: raw.rounds ?? null,
  };
}

/**
 * Wait for finalization, throwing on the two states that are not success.
 *
 * Exported for the lifecycle panel, which polls a transaction it did not send.
 */
export async function waitForFinalizedLifecycle(hash) {
  const transaction = await getClient().waitForFinalization({
    hash,
    interval: 3000,
    retries: 120,
    fullTransaction: true,
  });
  const lifecycle = readLifecycle(transaction);
  if (lifecycle.undetermined) {
    throw new Error(
      `Transaction ${hash} reached UNDETERMINED. The validators could not agree — ` +
        `that is a real outcome and is recorded as one, not retried into a pass.`,
    );
  }
  if (lifecycle.canceled) {
    throw new Error(`Transaction ${hash} was CANCELED. No state change was applied.`);
  }
  return { transaction, lifecycle };
}

/** Is a transaction still moving? Used to keep polling without a fixed sleep. */
export async function readLifecycleOf(hash) {
  const transaction = await getClient().getTransaction({ hash });
  return readLifecycle(transaction);
}

// ---------------------------------------------------------------------------
// Contract presence
// ---------------------------------------------------------------------------

/**
 * Does the configured address still hold a contract?
 *
 * Studio-dev resets. After a reset the address is empty and every read fails
 * with the same opaque `-32000` a wrong argument produces. Checking the code
 * lets the UI say "Studio-dev reset this deployment" instead of showing an
 * empty dashboard that looks like a product with no data.
 */
export async function contractExists() {
  try {
    const code = await getClient().getContractCode(CONTRACT_ADDRESS);
    return typeof code === "string" && code.length > 2;
  } catch {
    return false;
  }
}

export async function readSchema() {
  return getClient().getContractSchema(CONTRACT_ADDRESS);
}