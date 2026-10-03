/**
 * Identifier types. The two identifiers in this contract have different types,
 * and getting them backwards fails silently in a way that costs a whole
 * debugging session.
 *
 * Measured on Studio-dev at M5, not assumed:
 *
 *     readContract({ args: ["0", 0]  })  →  the receipt
 *     readContract({ args: ["0", "0"] }) →  gen_call failed (code=-32000)
 *
 * The ABI rejects a string in a `uint256` slot. `program_id` is a `str` and
 * `entry_index` is an `int`, and neither coerces to the other.
 *
 * A reviewer hit exactly this at M3 and recorded it as a contract defect. It
 * was a caller defect. The assertion below exists so the next person gets a
 * sentence that says which one they passed, instead of `code=-32000`.
 */

/** `program_id` is a string. The contract stores `str(int(program_count))`. */
export function assertProgramId(value) {
  if (typeof value !== "string") {
    throw new TypeError(
      `program_id must be a string, got ${typeof value} (${JSON.stringify(value)}). ` +
        `The contract stores ids as str(int(n)), so "0" and 0 are different ` +
        `keys and the integer spelling is refused as an unknown programme.`,
    );
  }
  return value;
}

/** `entry_index` is a number. It indexes a loop; it is not a key. */
export function assertEntryIndex(value) {
  const asNumber = typeof value === "number" ? value : Number(value);
  if (!Number.isInteger(asNumber) || asNumber < 0) {
    throw new TypeError(
      `entry_index must be a non-negative integer, got ${JSON.stringify(value)}. ` +
        `It occupies a uint256 slot; passing the string "0" fails the ABI with ` +
        `code=-32000 rather than coercing.`,
    );
  }
  return asNumber;
}

/**
 * Parse a route into a validated shape, or return null for the landing page.
 *
 * Two forms are accepted, and both are first-class:
 *
 *   /program/0/entry/1        a real path — shareable, and what a link in the
 *                             submission notes or a demo script should use
 *   #/program/0/entry/1       a hash — what this app shipped with first, kept so
 *                             an already-bookmarked URL still lands somewhere
 *
 * A path is preferred when there is one. The hash is only consulted when the
 * path is the site root, which is what a fresh load of `/` looks like.
 */
export function parseRoute(input) {
  const source = String(input ?? "");
  const fromHash = source.includes("#") ? source.slice(source.indexOf("#")) : "";
  const path = source.split("#")[0] || "";
  const raw = (path && path !== "/")
    ? path
    : fromHash.replace(/^#/, "") || "";
  const parts = raw.split("/").filter(Boolean);

  if (parts.length === 0) return { name: "landing" };
  if (parts[0] === "open" && parts.length === 1) return { name: "open" };
  if (parts[0] === "program" && parts.length === 2) {
    return { name: "programme", programId: assertProgramId(parts[1]) };
  }
  if (parts[0] === "program" && parts.length === 4 && parts[2] === "entry") {
    return {
      name: "receipt",
      programId: assertProgramId(parts[1]),
      entryIndex: assertEntryIndex(parts[3]),
    };
  }
  return { name: "not-found", path: raw };
}

/** Build a route path from a validated shape. */
export function buildRoute(route) {
  switch (route.name) {
    case "landing":
      return "/";
    case "open":
      return "/open";
    case "programme":
      return `/program/${assertProgramId(route.programId)}`;
    case "receipt":
      return `/program/${assertProgramId(route.programId)}/entry/${assertEntryIndex(route.entryIndex)}`;
    default:
      return "/";
  }
}