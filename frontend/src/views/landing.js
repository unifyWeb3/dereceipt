/**
 * The landing page.
 *
 * Structure, and the reason for it, comes from the competitive review in
 * `state/reviews/2026-10-02-frontend-competitive-review/FINDINGS.md`:
 *
 * * Lead with a stake, not a noun. Every one of the eight projects studied opens
 *   with something at stake ("Too small to litigate. Too big to walk away
 *   from."); none opens with a product category.
 * * Put the product doing the thing above the fold, not a description of it.
 * * Pair every claim with what checks it.
 * * Say what is deliberately absent. "Judges are AI" is the objection, so it is
 *   answered before it is asked.
 */

import { el, badge, stat, stateBlock, copyable } from "../lib/dom.js";
import { gen, statusMeaning } from "../lib/format.js";
import {
  ASSURANCES,
  CONTRACT_ADDRESS,
  CHAIN_ID,
  CHAIN_NAME,
  KNOWN_CRITERIA,
  MAX_WEIGHT,
  MIN_CRITERIA,
  PRODUCT_NAME,
  SDK_VERSION,
  TAGLINE,
} from "../config.js";
import { receiptStage } from "./stage.js";

export function landingView({ programme, entry, contractLive, onOpen, onOpenProgramme }) {
  return el(
    "div",
    { class: "landing" },

    // ---- hero -------------------------------------------------------------
    el(
      "section",
      { class: "hero" },
      el(
        "div",
        { class: "hero__copy" },
        el("p", { class: "eyebrow eyebrow--mint" }, `${CHAIN_NAME} · chain ${CHAIN_ID}`),
        el("h1", { class: "hero__title" }, "A verdict you can check."),
        el(
          "p",
          { class: "hero__lede" },
          "When an AI jury judges a hackathon entry, the losing side has no way to find out why. ",
          el("strong", {}, PRODUCT_NAME),
          " keeps the reasoning, the evidence and the disputes — and publishes the programme's own overturn rate.",
        ),
        el(
          "div",
          { class: "hero__actions" },
          el(
            "button",
            { class: "btn btn--primary", type: "button", onClick: onOpenProgramme },
            "Open a programme",
          ),
          programme
            ? el(
                "button",
                { class: "btn", type: "button", onClick: () => onOpen("programme", programme) },
                "See the live receipt",
              )
            : null,
        ),
        el(
          "ul",
          { class: "hero__truths" },
          el("li", {}, "No model in the decision path"),
          el("li", {}, "Evidence read from GitHub, not from a claim"),
          el("li", {}, "Only a 404 rejects — a rate limit never disqualifies"),
        ),
      ),
      receiptStage(programme ? { ...programme.receipt } : null, programme?.entry, programme?.program),
    ),

    // ---- the objection, answered before it is asked -----------------------
    el(
      "section",
      { class: "band" },
      el(
        "div",
        { class: "band__inner" },
        el("p", { class: "eyebrow" }, "The objection"),
        el("h2", { class: "band__title" }, "“You are letting an AI judge a hackathon.”"),
        el(
          "p",
          { class: "band__lede" },
          "Fair, and it is the right thing to be suspicious about. So the decision path contains no model at all. ",
          "Every criterion is arithmetic over facts fetched from the GitHub API and committed on chain, re-derived independently by each validator.",
          " The model is nowhere in it.",
        ),
      ),
    ),

    // ---- claim paired with what checks it ---------------------------------
    el(
      "section",
      { class: "band band--tight" },
      el(
        "div",
        { class: "band__inner" },
        el("p", { class: "eyebrow" }, "What it guarantees, and how you would know"),
        el(
          "div",
          { class: "assurances" },
          ...ASSURANCES.map((item, index) =>
            el(
              "article",
              { class: "assurance" },
              el("span", { class: "assurance__index" }, `0${index + 1}`),
              el("h3", { class: "assurance__claim" }, item.claim),
              el("p", { class: "assurance__detail" }, item.detail),
              el("p", { class: "assurance__evidence" }, item.evidence),
            ),
          ),
        ),
      ),
    ),

    // ---- the criterion set, which is fixed and non-negotiable -------------
    el(
      "section",
      { class: "band" },
      el(
        "div",
        { class: "band__inner" },
        el("p", { class: "eyebrow" }, "The rubric"),
        el("h2", { class: "band__title" }, "Five criteria. No custom rubric, and no subjectivity."),
        el(
          "p",
          { class: "band__lede" },
          `An organiser picks ${MIN_CRITERIA} to ${MAX_CRITERIA} of these and gives each a weight from 1 to ${MAX_WEIGHT}. ` +
            "The snapshot is fixed when the programme opens and never changes, so a builder knows before submitting what is being judged.",
        ),
        el(
          "div",
          { class: "criteria-grid" },
          ...KNOWN_CRITERIA.map((criterion) =>
            el(
              "article",
              { class: "criterion-card" },
              el("h3", { class: "criterion-card__key" }, criterion.label),
              el("p", { class: "criterion-card__body" }, criterion.blurb),
            ),
          ),
        ),
        el(
          "p",
          { class: "band__footnote" },
          "There is deliberately no “subjective” criterion in this build. A bounded model criterion is a later, optional milestone, " +
            "and the product is complete and defensible without it.",
        ),
      ),
    ),

    // ---- what is on chain right now ---------------------------------------
    el(
      "section",
      { class: "band band--tight" },
      el(
        "div",
        { class: "band__inner" },
        el("p", { class: "eyebrow" }, "Live on chain"),
        contractLive
          ? programme
            ? el(
                "div",
                { class: "live" },
                el(
                  "div",
                  { class: "live__stats" },
                  stat("Programme", programme.program.id, "open"),
                  stat("Locked", gen(programme.program.locked)),
                  stat("Entries", String(programme.program.entry_count ?? 0)),
                  stat("Deadline", new Date(Number(programme.program.deadline) * 1000)
                    .toISOString()
                    .slice(0, 10)),
                ),
                el(
                  "p",
                  { class: "live__status" },
                  badge(programme.program.status, "open", statusMeaning(programme.program.status)),
                  " ",
                  statusMeaning(programme.program.status),
                ),
                el("div", { class: "live__address" }, "Contract ", copyable(CONTRACT_ADDRESS, { what: "contract address" })),
                el(
                  "button",
                  { class: "btn", type: "button", onClick: () => onOpen("programme", programme.program) },
                  "Open the receipt",
                ),
              )
            : stateBlock(
                "No programme yet",
                "The contract is deployed and answering, but nothing has been opened on it yet. " +
                  "Open one and it will appear here.",
                "open",
              )
          : stateBlock(
              "This deployment has been reset",
              `${CHAIN_NAME} resets periodically. The address ${CONTRACT_ADDRESS} no longer holds a contract, ` +
                "so there is nothing to read. Redeploy with scripts/deploy_studio_dev.py and set " +
                "VITE_CONTRACT_ADDRESS to the new address.",
              "warn",
            ),
      ),
    ),

    el(
      "footer",
      { class: "footer" },
      el("p", { class: "footer__line" }, `${PRODUCT_NAME} · ${TAGLINE}`),
      el(
        "p",
        { class: "footer__line footer__line--dim" },
        `${CHAIN_NAME} chain ${CHAIN_ID} · ${SDK_VERSION} · no framework, no database, no backend`,
      ),
    ),
  );
}