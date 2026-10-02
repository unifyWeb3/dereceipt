/**
 * Formatting. Small, pure, and the one place that decides what a number looks
 * like — because a receipt that prints `1000000000000000000` where it should
 * print `1` is a receipt nobody trusts.
 */

/** GEN amounts arrive as integers in the smallest unit used by Studio-dev. */
export function gen(value) {
  const asNumber = typeof value === "bigint" ? Number(value) : Number(value ?? 0);
  if (!Number.isFinite(asNumber)) return "—";
  return asNumber.toLocaleString("en-US");
}

/** A unix second, as an absolute date. Returns a dash if it is absent. */
export function dateFromUnix(seconds) {
  const asNumber = Number(seconds);
  if (!Number.isFinite(asNumber) || asNumber <= 0) return "—";
  return new Date(asNumber * 1000).toISOString().replace("T", " ").slice(0, 19) + "Z";
}

/** GitHub's committer date, verbatim. It is the evidence, so it is not localised. */
export function isoDate(value) {
  if (!value || typeof value !== "string") return "—";
  return value;
}

/** A digest is 64 hex characters. Show enough to compare, not enough to fit. */
export function digest(value, lead = 10, tail = 8) {
  if (typeof value !== "string" || value.length < lead + tail) return value || "—";
  return `${value.slice(0, lead)}…${value.slice(-tail)}`;
}

export function shortAddress(value, lead = 6, tail = 4) {
  if (typeof value !== "string" || value.length <= lead + tail + 2) return value || "—";
  return `${value.slice(0, lead)}…${value.slice(-tail)}`;
}

/** A percentage in basis points, without pretending to more precision than bps. */
export function basisPoints(value) {
  const asNumber = Number(value ?? 0);
  if (!Number.isFinite(asNumber)) return "—";
  return `${(asNumber / 100).toFixed(2)}%`;
}

/** Turn `commit_predates_deadline` into `Commit predates deadline`. */
export function humaniseCriterion(key) {
  if (typeof key !== "string") return String(key ?? "");
  const words = key.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Turn `repository_not_found` into `repository not found`. */
export function humaniseReason(reason) {
  if (typeof reason !== "string" || !reason) return "—";
  const words = reason.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** Verdict tokens as a single word a reader can act on. */
export const VERDICT_LABEL = {
  PASS: "Pass",
  FAIL: "Fail",
  UNDETERMINED: "Undetermined",
  NOT_JUDGED: "Not judged",
};

export function verdictLabel(verdict) {
  return VERDICT_LABEL[verdict] || String(verdict ?? "—");
}

/** Programme and entry statuses, phrased as what they mean for the reader. */
export const STATUS_MEANING = {
  OPEN: "Accepting entries",
  CLOSED: "Closed and adjudicated",
  CLOSED_NO_WINNER: "Closed, nothing survived",
  CANCELLED: "Cancelled and refunded",
  SUBMITTED: "Awaiting evidence",
  FROZEN: "Evidence frozen, no verdict yet",
  UNDER_REVIEW: "Validators reviewing",
  STANDING: "Standing",
  DISQUALIFIED: "Disqualified",
  PAYOUT_READY: "Payout ready",
  PAID: "Paid",
  FILED: "Filed",
  UPHELD: "Upheld",
  DENIED: "Denied",
  EXPIRED: "Expired",
};

export function statusMeaning(status) {
  return STATUS_MEANING[status] || "";
}

/** Copy to clipboard, reporting honestly when the browser refuses. */
export async function copyText(text) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fall through to the manual path rather than reporting a false failure.
  }
  try {
    const field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(field);
    return ok;
  } catch {
    return false;
  }
}