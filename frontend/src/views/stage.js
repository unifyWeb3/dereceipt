/**
 * The receipt stage: the product's own output, replayed.
 *
 * The competitive review's central finding was that the reference builds lead
 * with the product doing something, not with a noun. `mrnetwork0001/Judr` loops a
 * **saved real run** in its hero and captions it with its own provenance; the
 * other five open with a paragraph.
 *
 * So this component takes the record read from `get_receipt` on the live chain
 * and plays it back as five beats — submitted, evidence frozen, each criterion
 * decided with its reason, the challenge record, finalization — with no invented
 * content anywhere. If the chain has no frozen receipt, it says so rather than
 * substituting a mock. A labelled fixture is honest; an unlabelled one is not,
 * and `docs/ARCHITECTURE.md` rule 11 exists to stop exactly that.
 */

import { el, badge, explorerLink } from "../lib/dom.js";
import {
  digest,
  gen,
  humaniseCriterion,
  humaniseReason,
  isoDate,
  verdictLabel,
} from "../lib/format.js";
import { EXPLORER } from "../config.js";

const BEATS = [
  { id: "submitted", label: "Submitted", detail: "A repository pinned to an immutable commit. Cheap, local, and reversible to retry." },
  { id: "frozen", label: "Evidence frozen", detail: "Validators read the commit, the manifest and the signed committer date from GitHub. Nothing is decided yet." },
  { id: "verdicts", label: "Verdicts derived", detail: "Each criterion gets a verdict and the observation that produced it. Arithmetic, not a model." },
  { id: "challenge", label: "Challenge window", detail: "One bond, one named criterion, re-derived deterministically. The original verdict is never overwritten." },
  { id: "closed", label: "Payout scheduled", detail: "The locked balance is allocated exactly. Value moves only after finalization is observed." },
];

/**
 * Which of the five beats the record on chain has actually reached.
 *
 * Derived from the receipt, not from a timer — so the animation cannot claim a
 * stage the chain has not reached. A record that is only submitted shows one
 * beat and says what is missing.
 */
export function reachedBeats(receipt) {
  if (!receipt) return [];
  const beats = ["submitted"];
  const digestPresent = Boolean(receipt.tree_digest);
  const verdicts = receipt.verdicts || {};
  const judged = Object.values(verdicts).filter((v) => v && v !== "NOT_JUDGED");
  if (digestPresent) beats.push("frozen");
  if (judged.length > 0) beats.push("verdicts");
  if ((receipt.challenges || []).length > 0 || ["CLOSED", "CLOSED_NO_WINNER"].includes(receipt.status)) {
    beats.push("challenge");
  }
  if (["PAYOUT_READY", "PAID"].includes(receipt.status)) beats.push("closed");
  return beats;
}

/** One criterion's row, as it appears on the receipt. */
function criterionRow(criterion) {
  const verdict = criterion.verdict || "NOT_JUDGED";
  // UNDETERMINED is `warn`, never `bad`. A criterion the jury could not settle
  // is the product working; rendering it as a failure would misreport what
  // happened and would quietly reintroduce the bug M4 found and fixed.
  const tone =
    verdict === "PASS" ? "ok" : verdict === "FAIL" ? "bad" : verdict === "UNDETERMINED" ? "warn" : "muted";

  return el(
    "li",
    { class: `criterion criterion--${tone}` },
    el(
      "div",
      { class: "criterion__head" },
      el("span", { class: "criterion__name" }, humaniseCriterion(criterion.criterion)),
      badge(verdictLabel(verdict), tone, criterion.reason || ""),
    ),
    el(
      "div",
      { class: "criterion__body" },
      el("span", { class: "criterion__reason" }, humaniseReason(criterion.reason)),
      el("span", { class: "criterion__weight" }, `weight ${criterion.weight}`),
    ),
  );
}

/**
 * Build the stage for one receipt.
 *
 * @param {object|null} receipt  a live `get_receipt` result, or null
 * @param {object} receiptWithCriteria  the same receipt with its criterion list
 *   from `get_entry`, because `get_receipt` returns verdicts as a map and the
 *   reasons live on the entry.
 * @param {object} programme  the parent `get_program` result, for pool figures
 */
export function receiptStage(receipt, receiptWithCriteria, programme) {
  if (!receipt) {
    return el(
      "div",
      { class: "stage stage--empty" },
      el("p", { class: "stage__empty-title" }, "No receipt to replay"),
      el(
        "p",
        { class: "stage__empty-detail" },
        "Open a programme and freeze an entry against the live GitHub API. " +
          "This stage plays back whatever the chain actually holds — it will " +
          "not substitute a mock.",
      ),
    );
  }

  const criteria = receiptWithCriteria?.criteria || [];
  const reached = new Set(reachedBeats(receipt));
  const live = reached.size >= 3;

  return el(
    "figure",
    { class: "stage" },
    el(
      "ol",
      { class: "stage__beats" },
      ...BEATS.map((beat) => {
        const done = reached.has(beat.id);
        return el(
          "li",
          {
            class: `beat${done ? " beat--done" : ""}${live && !done ? " beat--pending" : ""}`,
          },
          el("span", { class: "beat__dot", "aria-hidden": "true" }),
          el(
            "span",
            { class: "beat__text" },
            el("span", { class: "beat__label" }, beat.label),
            done ? el("span", { class: "beat__detail" }, beat.detail) : null,
          ),
        );
      }),
    ),

    el(
      "div",
      { class: "stage__card" },
      el(
        "header",
        { class: "stage__head" },
        el(
          "div",
          {},
          el("p", { class: "eyebrow" }, "Receipt"),
          el("p", { class: "stage__repo" }, receipt.repo || "—"),
        ),
        badge(receipt.status || "UNKNOWN", toneForStatus(receipt.status), statusHint(receipt.status)),
      ),

      el(
        "dl",
        { class: "stage__facts" },
        fact("Commit", digest(receipt.commit, 8, 6)),
        fact("Committed", isoDate(receipt.committer_date)),
        fact("Tree digest", digest(receipt.tree_digest, 10, 8)),
        programme ? fact("Locked", gen(programme.locked)) : null,
        programme ? fact("Entry count", String(programme.entry_count ?? 0)) : null,
        fact("Finalized at", receipt.finalized_at || "not finalized"),
      ),

      criteria.length > 0
        ? el(
            "div",
            { class: "stage__verdicts" },
            el("p", { class: "eyebrow" }, `Criteria · ${criteria.length}`),
            el("ul", { class: "criteria" }, ...criteria.map(criterionRow)),
          )
        : null,

      (receipt.challenges || []).length > 0
        ? el(
            "div",
            { class: "stage__challenges" },
            el("p", { class: "eyebrow" }, "Challenge log"),
            el(
              "ul",
              { class: "challenges" },
              ...receipt.challenges.map((challenge) =>
                el(
                  "li",
                  { class: "challenge" },
                  el(
                    "div",
                    { class: "challenge__head" },
                    el("span", { class: "challenge__ground" }, humaniseCriterion(challenge.ground)),
                    badge(challenge.status, toneForStatus(challenge.status)),
                  ),
                  el(
                    "p",
                    { class: "challenge__detail" },
                    `contested ${humaniseCriterion(challenge.criterion)} · original verdict ` +
                      `${verdictLabel(challenge.original_verdict)}`,
                  ),
                  el(
                    "p",
                    { class: "challenge__detail" },
                    `bond ${gen(challenge.bond)} · resolved: ${humaniseReason(challenge.result) || "not yet"}`,
                  ),
                ),
              ),
            ),
          )
        : null,

      el(
        "figcaption",
        { class: "stage__caption" },
        live
          ? "Read live from the deployed contract. Every figure above is the chain's own state, including the reasons."
          : "Read live from the deployed contract. This entry has not been frozen yet, so there are no verdicts to replay.",
      ),
    ),
  );
}

function fact(label, value) {
  return el("div", { class: "fact" }, el("dt", {}, label), el("dd", {}, value));
}

function toneForStatus(status) {
  if (["STANDING", "OPEN", "PAID", "PAYOUT_READY", "CLOSED"].includes(status)) return "ok";
  if (["DISQUALIFIED", "CANCELED", "CANCELLED"].includes(status)) return "bad";
  if (["FROZEN", "UNDER_REVIEW", "FILED", "SUBMITTED"].includes(status)) return "open";
  return "muted";
}

function statusHint(status) {
  if (status === "STANDING") return "Adjudicated and still in contention for the pool";
  if (status === "DISQUALIFIED") return "A criterion failed, or a challenge was upheld";
  if (status === "FROZEN") return "Evidence captured; the jury could not settle every criterion";
  if (status === "SUBMITTED") return "Awaiting evidence capture";
  return "";
}

/**
 * A link out to the explorer for a transaction, rendered without ever being
 * awaited. The explorer 503s intermittently and must not gate a render.
 */
export function txLink(hash, label = "transaction") {
  return explorerLink(EXPLORER, "tx", hash, label);
}