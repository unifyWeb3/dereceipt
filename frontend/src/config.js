/**
 * Every constant the product needs, in one place.
 *
 * ## Why this file exists
 *
 * The product name appears in the page title, the header, the landing hero, the
 * README and the submission notes. When it lived in several files, renaming meant
 * finding every occurrence and hoping none was missed. It is defined **once**
 * here and imported everywhere else. Renaming the product should be a one-line
 * change in this file, plus the README title.
 *
 * What is deliberately NOT renamed: `contracts/contest_receipt.py`, and every
 * reference to that path in scripts, tests and evidence. A file's name is part
 * of the record of what was measured — M0 through M4 all cite that exact path,
 * and the deployed contract's identity comes from its content, not its filename.
 * The product is DeReceipt; the artefact that implements it is a contract called
 * contest_receipt, and conflating the two would make the evidence trail lie.
 */

/** The product name. The only place it is written. */
export const PRODUCT_NAME = "DeReceipt";

/** One line, used in the header, the hero and the README. */
export const TAGLINE =
  "Auditable verdicts for AI-judged hackathons and grant rounds.";

/**
 * The claim the product actually makes, in the words a sceptic would use.
 *
 * Every clause here is backed by a test or an on-chain observation. The evidence
 * is listed beside each one on the landing page, because a claim without a
 * pointer to what checks it is decoration.
 */
export const ASSURANCES = [
  {
    claim: "A rate limit can never disqualify anyone",
    detail:
      "Only a 404 is a rejection. A 403, a 429, a 5xx, an empty body or a non-JSON body is UNDETERMINED — recorded, never punished. The absence of evidence is not evidence of absence.",
    evidence: "8 tests · tests/direct/test_contest_receipt.py group 6",
  },
  {
    claim: "A receipt is a receipt, not a score",
    detail:
      "Every criterion carries the observation that produced it. A criterion the jury could not settle reads UNDETERMINED and leaves the entry standing rather than out.",
    evidence: "92 tests · group 3 and group 5",
  },
  {
    claim: "The original verdict is never overwritten",
    detail:
      "A challenge outcome is recorded beside the verdict it contested. One challenge per entry, staked, against one named criterion, re-derived deterministically.",
    evidence: "9 tests · group 9",
  },
  {
    claim: "Every unit is accounted for",
    detail:
      "Value received is either still held, scheduled to leave, or reconciled in the accuracy block. Nothing is stranded, including a forfeited or returned challenge bond.",
    evidence: "6 tests · group 11",
  },
];

/** GenLayer Studio-dev. Chain 61997. Contracts here can be reset by the network. */
export const CHAIN_ID = 61997;
export const CHAIN_ID_HEX = "0xf22d";
export const CHAIN_NAME = "Studio-dev";

export const RPC = "https://studio-dev.genlayer.com/api";

/**
 * The Studio-dev explorer returns 503 intermittently — M0 saw it on two of five
 * probes — so every deep link is rendered as a normal anchor and never awaited.
 * A dead link must not block a render.
 */
export const EXPLORER = "https://explorer-studio-dev.genlayer.com";

/**
 * The deployed contract, as a public build variable with a working default.
 *
 * `VITE_CONTRACT_ADDRESS` overrides it. The default points at the M5 deployment,
 * which holds a real frozen receipt: programme `0`, one standing entry, evidence
 * fetched from the live GitHub API by the Studio-dev validators.
 *
 * Studio-dev resets periodically. A reset makes the address point at nothing, and
 * the UI says so plainly rather than rendering an empty dashboard — see
 * `views/landing.js`.
 */
export const CONTRACT_ADDRESS =
  import.meta.env.VITE_CONTRACT_ADDRESS || "0xAFCc7a6fCa2ceb26365708E1456735f087CF8f7D";

/**
 * The fixed criterion set, mirrored for display only.
 *
 * The contract is the source of truth — `get_program` returns the snapshotted
 * criteria. This exists so the UI can explain the shape of the product before a
 * programme is opened, and it is deliberately not used to render a live
 * programme's criteria.
 */
export const KNOWN_CRITERIA = [
  { key: "repo_resolves", label: "Repository resolves", blurb: "The repository exists at the moment of freezing." },
  { key: "commit_predates_deadline", label: "Commit predates the deadline", blurb: "GitHub's signed committer date is earlier than the deadline the organiser fixed." },
  { key: "required_files_present", label: "Required files present", blurb: "A README is in the frozen manifest." },
  { key: "declared_language_present", label: "Declared language present", blurb: "The entrant's declared stack appears in the manifest they submitted." },
  { key: "not_duplicate", label: "Not a duplicate", blurb: "No earlier entry in this programme froze the same tree." },
];

export const MIN_CRITERIA = 3;
export const MAX_CRITERIA = 5;
export const MAX_WEIGHT = 10;

/**
 * Every challenge ground, and the single criterion it contests.
 *
 * One ground names one criterion, so "one challenge against one criterion" is a
 * property of the data rather than a rule to remember.
 */
export const GROUNDS = [
  { ground: "AFTER_DEADLINE_WORK", criterion: "commit_predates_deadline", label: "After the deadline", blurb: "Names a different commit, so the contested date is re-derived against it." },
  { ground: "DUPLICATE_SUBMISSION", criterion: "not_duplicate", label: "Duplicate submission", blurb: "Claims the same tree was already submitted." },
  { ground: "MISSING_REQUIRED_FILE", criterion: "required_files_present", label: "Missing required file", blurb: "The frozen manifest contradicts the claim that a required file is present." },
  { ground: "UNSUPPORTED_CLAIM", criterion: "declared_language_present", label: "Unsupported claim", blurb: "The manifest does not evidence the declared stack." },
  { ground: "DEAD_DEMO", criterion: "repo_resolves", label: "Dead demo", blurb: "The repository does not resolve." },
];

export const SDK_VERSION = "genlayer-js 2.0.0-rc.1";