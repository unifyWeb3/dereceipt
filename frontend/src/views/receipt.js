/**
 * The receipt view — the artefact the whole product exists to produce.
 *
 * A receipt is not a score. It is the record of what was read, what was decided
 * from it, and what anyone did about it afterwards. So the order on screen is
 * the order of the argument: the evidence, then each verdict with the
 * observation that produced it, then the disputes, then the digest that binds
 * all of it.
 */

import { el, badge, stat, stateBlock, copyable } from "../lib/dom.js";
import {
  dateFromUnix,
  digest,
  gen,
  humaniseCriterion,
  humaniseReason,
  isoDate,
  statusMeaning,
  verdictLabel,
} from "../lib/format.js";
import { EXPLORER } from "../config.js";

export function receiptView({ receipt, entry, accuracy, digestValue, programme, onRoute }) {
  if (!receipt) {
    return stateBlock(
      "Receipt not found",
      "The chain has no entry at this index. Studio-dev resets, so an entry that existed yesterday may be gone today.",
      "warn",
    );
  }

  const criteria = entry?.criteria || [];
  const challenges = receipt.challenges || [];
  const undetermined = criteria.filter((c) => c.verdict === "UNDETERMINED");
  const failed = criteria.filter((c) => c.verdict === "FAIL");

  return el(
    "div",
    { class: "receipt" },

    el(
      "header",
      { class: "receipt__head" },
      el(
        "div",
        {},
        el("p", { class: "eyebrow" }, `Receipt · programme ${receipt.program_id} · entry ${receipt.entry_index}`),
        el("h1", { class: "receipt__repo" }, receipt.repo || "—"),
        el("p", { class: "receipt__commit mono" }, receipt.commit || "—"),
      ),
      el(
        "div",
        { class: "receipt__status" },
        badge(receipt.status, receipt.status === "STANDING" ? "ok" : "muted", statusMeaning(receipt.status)),
        el("span", {}, statusMeaning(receipt.status)),
      ),
    ),

    // ---- the evidence -----------------------------------------------------
    el(
      "section",
      { class: "card" },
      el("p", { class: "eyebrow" }, "Evidence, as read at freeze"),
      el(
        "div",
        { class: "stats" },
        stat("Committer date", isoDate(receipt.committer_date), "open"),
        stat("Files seen", String(entry?.file_count ?? 0)),
        stat("README", entry?.readme_present === "yes" ? "present" : entry?.readme_present === "no" ? "absent" : "unknown"),
        stat("Tree digest", digest(receipt.tree_digest, 10, 8)),
      ),
      el(
        "p",
        { class: "card__note card__note--strong" },
        "The committer date is GitHub's signed field, not the chain's clock. ",
        "This contract cannot read a block clock — the runner exposes none — so the deadline is proven by comparing that signed date against the absolute second the organiser fixed. ",
        "It proves when the work existed, which is the claim being made; it does not claim when the transaction arrived.",
      ),
      entry?.manifest_summary
        ? el(
            "details",
            { class: "disclosure" },
            el("summary", {}, `Frozen manifest · ${entry.file_count ?? 0} files`),
            el("pre", { class: "manifest mono" }, entry.manifest_summary),
            entry.manifest_paths_omitted
              ? el(
                  "p",
                  { class: "card__note" },
                  `${entry.manifest_paths_omitted} paths beyond the stored cap were counted but not kept. The omission is reported rather than hidden.`,
                )
              : null,
          )
        : null,
    ),

    // ---- the verdicts -----------------------------------------------------
    el(
      "section",
      { class: "card" },
      el("p", { class: "eyebrow" }, `Criteria · ${criteria.length}`),
      criteria.length === 0
        ? stateBlock("No criteria recorded", "This entry has not been frozen yet.", "muted")
        : el(
            "ul",
            { class: "criteria" },
            ...criteria.map((criterion) => criterionRow(criterion)),
          ),
      criteria.length > 0
        ? el(
            "p",
            { class: "card__note" },
            undetermined.length > 0
              ? `${undetermined.length} criterion could not be settled. That is recorded as UNDETERMINED and does not disqualify the entry — ` +
                "the absence of evidence is not evidence of absence."
              : failed.length > 0
                ? `${failed.length} criterion failed, which disqualifies the entry. Each failure above names the observation that produced it.`
                : "Every criterion passed on evidence read from the source.",
          )
        : null,
    ),

    // ---- the disputes -----------------------------------------------------
    el(
      "section",
      { class: "card" },
      el("p", { class: "eyebrow" }, `Challenge log · ${challenges.length}`),
      el(
        "p",
        { class: "card__note" },
        "One challenge per entry, staked, against one named criterion, re-derived deterministically on chain. ",
        "The original verdict is never overwritten — the outcome is recorded beside it, which is why this log lives inside the receipt rather than in a separate view.",
      ),
      challenges.length === 0
        ? stateBlock("Never challenged", "Nothing was filed against this entry.", "muted")
        : el(
            "ol",
            { class: "challenges" },
            ...challenges.map((challenge) => challengeRow(challenge)),
          ),
    ),

    // ---- the digest -------------------------------------------------------
    el(
      "section",
      { class: "card card--digest" },
      el("p", { class: "eyebrow" }, "Tamper-evident digest"),
      el(
        "p",
        { class: "card__note" },
        "A SHA-256 over the programme's whole audit record, canonical JSON with sorted keys. ",
        "Re-ordering the record cannot change it. Changing the record must. This is what lets an organiser prove months later that the record they published is the record the chain holds.",
      ),
      copyable(digestValue || "—", { what: "receipt digest" }),
      receipt.finalized_at
        ? el("p", { class: "card__note" }, `Finalized: ${receipt.finalized_at}`)
        : el(
            "p",
            { class: "card__note" },
            "Not finalized yet. Value only moves after finalization is observed, so the payout is scheduled but not transferable.",
          ),
    ),

    el(
      "nav",
      { class: "receipt__nav" },
      el(
        "button",
        {
          class: "btn btn--small",
          type: "button",
          onClick: () => onRoute({ name: "programme", programId: receipt.program_id }),
        },
        "Back to the programme",
      ),
      programme
        ? el(
            "p",
            { class: "receipt__nav-note" },
            `Programme locked ${gen(programme.locked)} · paid out ${gen(accuracy?.paid_out ?? 0)} · refunded ${gen(accuracy?.refunded ?? 0)}`,
          )
        : null,
    ),
  );
}

function criterionRow(criterion) {
  const verdict = criterion.verdict || "NOT_JUDGED";
  const tone =
    verdict === "PASS" ? "ok" : verdict === "FAIL" ? "bad" : verdict === "UNDETERMINED" ? "warn" : "muted";

  return el(
    "li",
    { class: `criterion criterion--${tone}` },
    el(
      "div",
      { class: "criterion__head" },
      el(
        "span",
        { class: "criterion__name" },
        humaniseCriterion(criterion.criterion),
        el("span", { class: "criterion__weight" }, `weight ${criterion.weight}`),
      ),
      badge(verdictLabel(verdict), tone, criterion.reason || ""),
    ),
    el("p", { class: "criterion__reason" }, humaniseReason(criterion.reason)),
  );
}

function challengeRow(challenge) {
  const tone =
    challenge.status === "UPHELD" ? "ok" : challenge.status === "DENIED" ? "warn" : "open";
  return el(
    "li",
    { class: "challenge" },
    el(
      "div",
      { class: "challenge__head" },
      el(
        "span",
        { class: "challenge__ground" },
        humaniseCriterion(challenge.ground),
        el("span", { class: "challenge__criterion" }, `contested ${humaniseCriterion(challenge.criterion)}`),
      ),
      badge(challenge.status, tone),
    ),
    el(
      "dl",
      { class: "challenge__facts" },
      el("dt", {}, "original verdict"),
      el("dd", {}, verdictLabel(challenge.original_verdict)),
      el("dt", {}, "result"),
      el("dd", {}, humaniseReason(challenge.result) || "not resolved"),
      el("dt", {}, "bond"),
      el("dd", {}, gen(challenge.bond)),
    ),
    challenge.evidence
      ? el(
          "p",
          { class: "challenge__detail" },
          "Evidence: ",
          // Rendered as text, not as a link. The field holds whatever URL the
          // challenger canonicalised, and an earlier version of this file wrapped
          // it in an anchor built from an empty base — which emitted an `href`
          // of `https://github.com//`. Chain-supplied strings are shown, never
          // turned into navigation.
          el("code", { class: "mono challenge__evidence" }, challenge.evidence),
        )
      : null,
    el(
      "p",
      { class: "challenge__detail" },
      `Filed by ${challenge.filer ? challenge.filer.slice(0, 10) + "…" : "an address"}${challenge.resolved_at ? ` · resolved ${challenge.resolved_at}` : ""}`,
    ),
  );
}