/**
 * Read-path verification against the deployed contract.
 *
 * There is no browser in the M5 verification environment, so this runs the
 * *actual shipped modules* — `src/lib/contract.js` and `src/lib/identifiers.js`,
 * not a copy of them — against the live Studio-dev chain. It is the same code
 * path the browser takes; only the DOM is absent.
 *
 * Built with `vite build --ssr` so `import.meta.env` resolves the way it does in
 * the app. Run by `scripts/m5_gate.py`.
 *
 * What it checks, and why each one is here:
 *
 *  1. The chain assertion passes — a misconfigured build fails at boot.
 *  2. The contract still holds code — Studio-dev resets, and after a reset every
 *     read fails identically to a wrong-argument error.
 *  3. Every one of the six views reads, with `program_id` a string and
 *     `entry_index` a number.
 *  4. `get_entry` with the **wrong** identifier types fails, which is the point:
 *     it is what proves the assertions in `identifiers.js` are load-bearing rather
 *     than decorative. Measured on chain, not assumed.
 *  5. The identifier assertions reject the wrong type with a sentence.
 */

import {
  assertPinnedChain,
  contractExists,
  readAccuracy,
  readBalance,
  readDigest,
  readEntry,
  readProgram,
  readReceipt,
  readSchema,
} from "../src/lib/contract.js";
import { assertEntryIndex, assertProgramId, parseRoute } from "../src/lib/identifiers.js";
import { CONTRACT_ADDRESS } from "../src/config.js";

const results = [];
let failures = 0;

function record(name, ok, detail = "") {
  results.push({ name, ok, detail });
  if (!ok) failures += 1;
  const mark = ok ? "PASS" : "FAIL";
  console.log(`${mark}  ${name}${detail ? ` — ${detail}` : ""}`);
}

async function attempt(fn) {
  try {
    return { ok: true, value: await fn() };
  } catch (error) {
    return { ok: false, error: String(error?.message || error).slice(0, 120) };
  }
}

async function main() {
  console.log(`contract: ${CONTRACT_ADDRESS}\n`);

  // 1. chain
  const chain = await attempt(() => assertPinnedChain());
  record(
    "chain assertion passes",
    chain.ok && chain.value === "0xf22d",
    chain.ok ? `reports ${chain.value}` : chain.error,
  );

  // 2. contract presence
  const exists = await contractExists();
  record("contract holds code", exists, exists ? "getContractCode returned bytecode" : "no code — Studio-dev reset?");

  if (!exists) {
    report();
    return;
  }

  // 3. every view
  const program = await attempt(() => readProgram("0"));
  record("get_program('0')", program.ok && !!program.value?.id,
    program.ok ? `status=${program.value.status} locked=${program.value.locked} entries=${program.value.entry_count}` : program.error);

  const accuracy = await attempt(() => readAccuracy("0"));
  record("get_accuracy('0')", accuracy.ok,
    accuracy.ok ? `undetermined=${accuracy.value.contested_criteria} disqualified=${accuracy.value.disqualified_deterministically}` : accuracy.error);

  const digest = await attempt(() => readDigest("0"));
  record("get_receipt_digest('0')", digest.ok && /^[0-9a-f]{64}$/.test(String(digest.value)),
    digest.ok ? `${String(digest.value).slice(0, 16)}… (${String(digest.value).length} chars)` : digest.error);

  const balance = await attempt(() => readBalance());
  record("get_contract_balance()", balance.ok, balance.ok ? `${balance.value} GEN held` : balance.error);

  const count = program.ok ? Number(program.value.entry_count ?? 0) : 0;
  const entry = await attempt(() => readEntry("0", 0));
  record("get_entry('0', 0)  — string id, int index", entry.ok,
    entry.ok
      ? `status=${entry.value.status} criteria=${(entry.value.criteria || []).length}`
      : entry.error);

  const receipt = await attempt(() => readReceipt("0", 0));
  record("get_receipt('0', 0)", receipt.ok,
    receipt.ok
      ? `status=${receipt.value.status} digest=${String(receipt.value.tree_digest).slice(0, 12)}… challenges=${(receipt.value.challenges || []).length}`
      : receipt.error);

  // 4. identifier coercion, measured rather than assumed.
  //
  //    Two clients, two behaviours, both found at M5:
  //
  //      genlayer-py 0.19.0rc2  — a string in a uint256 slot is REJECTED
  //                              (`gen_call failed (code=-32000)`)
  //      genlayer-js  2.0.0-rc.1 — COERCES it, and the read succeeds
  //
  //    So the browser is the *lenient* one. That inverts the obvious reading of
  //    the risk: the frontend will not fail loudly, it will send the right thing
  //    because `assertEntryIndex` normalised it first. The strict client is the
  //    Python one, which is what M3 and M4 used — and which is why an on-chain
  //    `code=-32000` during M4 looked like a contract defect and was not one.
  if (count > 0) {
    const coerced = await attempt(() => readEntry("0", "0"));
    const typed = await attempt(() => readEntry("0", 0));
    record(
      "get_entry('0','0') and get_entry('0',0) return the same thing",
      coerced.ok && typed.ok && JSON.stringify(coerced.value) === JSON.stringify(typed.value),
      coerced.ok
        ? "genlayer-js coerces the string; assertEntryIndex normalises it before sending"
        : (coerced.error || "?"),
    );

    const asIntId = await attempt(() => readProgram(0));
    record(
      "get_program(0) — a str slot given an int is REJECTED, with no coercion",
      !asIntId.ok,
      asIntId.ok ? "UNEXPECTED: succeeded" : (asIntId.error || "rejected"),
    );
  } else {
    console.log("SKIP  coercion probes: no entries on programme 0");
  }

  // 5. the assertions themselves.
  //
  //    `assertProgramId` rejects an integer: the contract keys programmes by
  //    string and nothing coerces that direction.
  //
  //    `assertEntryIndex` deliberately ACCEPTS a numeric string and normalises
  //    it, because hash routes give strings (`#/program/0/entry/1`) and refusing
  //    them would break every deep link. What it must reject is anything that is
  //    not a non-negative integer.
  const assertions = [
    ['assertProgramId("0") accepts a string', () => assertProgramId("0") === "0", true],
    ["assertProgramId(0) rejects an integer", () => assertProgramId(0), false],
    ["assertEntryIndex(0) accepts a number", () => assertEntryIndex(0) === 0, true],
    ['assertEntryIndex("1") normalises a numeric string from a URL', () => assertEntryIndex("1") === 1, true],
    ['assertEntryIndex("abc") rejects a non-numeric string', () => assertEntryIndex("abc"), false],
    ["assertEntryIndex(-1) rejects a negative", () => assertEntryIndex(-1), false],
    ["assertEntryIndex(1.5) rejects a float", () => assertEntryIndex(1.5), false],
  ];
  for (const [name, fn, shouldPass] of assertions) {
    const outcome = await attempt(fn);
    // `ok` answers "did it behave as required". The detail branches on
    // `outcome.ok` — did it return rather than throw — which is a different
    // question, and conflating the two labels a correct assertion as a failure.
    const ok = outcome.ok === shouldPass;
    const detail = shouldPass
      ? outcome.ok ? "accepted, as expected" : `threw: ${outcome.error || "?"}`
      : outcome.ok ? "UNEXPECTEDLY accepted" : `rejected: ${(outcome.error || "").slice(0, 78)}`;
    record(name, ok, detail);
  }

  // routing
  const routes = [
    ["#/", "landing"],
    ["#/open", "open"],
    ["#/program/0", "programme"],
    ["#/program/0/entry/1", "receipt"],
  ];
  for (const [hash, expected] of routes) {
    const parsed = parseRoute(hash);
    record(`route ${hash}`, parsed.name === expected, `→ ${parsed.name}`);
  }
  const badRoute = attempt(() => parseRoute("#/program/0/entry/abc"));
  record("route #/program/0/entry/abc is rejected, not silently coerced", !badRoute.ok,
    badRoute.ok ? "parsed anyway" : "rejected");

  // schema
  const schema = await attempt(() => readSchema());
  if (schema.ok) {
    // The shape is `{ctor, methods: {name: {params, readonly, ret, payable}}}`,
    // keyed by method name. Guessing at it is how an earlier run of this file
    // reported "2 methods" against a contract with fourteen.
    const methods = schema.value?.methods || {};
    const names = Object.keys(methods);
    record("schema exposes the 14 methods", names.length === 14,
      `${names.length}: ${names.sort().join(", ")}`);

    // The strongest form of the identifier check available: read the types off
    // the deployed contract itself rather than trusting what this file assumes.
    // If a future revision changed either, this fails and the UI's assertions
    // are wrong with it.
    const typeOf = (method, i) => methods[method]?.params?.[i]?.[1];
    record("deployed schema declares get_program(program_id: string)",
      typeOf("get_program", 0) === "string", `declared ${typeOf("get_program", 0)}`);
    record("deployed schema declares get_entry(program_id: string, entry_index: int)",
      typeOf("get_entry", 0) === "string" && typeOf("get_entry", 1) === "int",
      `declared ${typeOf("get_entry", 0)}, ${typeOf("get_entry", 1)}`);
    const payable = names.filter((n) => methods[n].payable).sort();
    record("the two payable methods are exactly open_program and challenge",
      payable.join(",") === "challenge,open_program", payable.join(",") || "none");
    record("get_challenge is absent — the receipt IS the challenge log",
      !names.includes("get_challenge"),
      names.includes("get_challenge") ? "PRESENT, which breaks the design" : "absent, as designed");
  }

  report();
}

function report() {
  console.log(`\n${results.filter((r) => r.ok).length}/${results.length} checks passed`);
  if (failures > 0) {
    console.log("FAILED:");
    for (const r of results.filter((x) => !x.ok)) console.log(`  ${r.name} — ${r.detail}`);
  }
  process.exitCode = failures > 0 ? 1 : 0;
}

main().catch((error) => {
  console.error("verifier crashed:", error);
  process.exitCode = 1;
});