/**
 * Open a programme. The organizer path.
 *
 * The form validates against the same constants the contract validates against,
 * so a refusal is visible before a transaction is signed rather than after.
 * That is the point: the pool is real value, and a method that received it cannot
 * revert, so a mistake becomes a locked pool the owner has to remember to cancel.
 */

import { el, badge, stateBlock } from "../lib/dom.js";
import {
  KNOWN_CRITERIA,
  MAX_CRITERIA,
  MAX_WEIGHT,
  MIN_CRITERIA,
} from "../config.js";

export function openProgrammeView({ connected, onRoute, onOpenProgramme }) {
  const selected = new Map();
  // Start with the three highest-signal criteria selected, since three is the
  // documented floor and a first-time organiser should not have to think about
  // which minimum to pick.
  ["repo_resolves", "commit_predates_deadline", "required_files_present"].forEach(
    (key) => selected.set(key, 3),
  );

  const errorSlot = el("div", { class: "form__errors" });
  const summary = el("p", { class: "form__summary" });

  const sync = () => {
    const chosen = [...selected.entries()];
    summary.textContent =
      `${chosen.length} of ${MAX_CRITERIA} criteria · ${MIN_CRITERIA} minimum · ` +
      `total weight ${chosen.reduce((sum, [, weight]) => sum + weight, 0)}`;
    return chosen;
  };

  const weightInputs = new Map();

  const rows = KNOWN_CRITERIA.map((criterion) => {
    const checkbox = el("input", {
      type: "checkbox",
      checked: selected.has(criterion.key),
      onChange: (event) => {
        if (event.target.checked) selected.set(criterion.key, 3);
        else selected.delete(criterion.key);
        sync();
      },
    });
    const weight = el("input", {
      class: "input input--weight",
      type: "number",
      min: "1",
      max: String(MAX_WEIGHT),
      value: String(selected.get(criterion.key) || 3),
      onInput: (event) => {
        const value = Number(event.target.value);
        if (selected.has(criterion.key)) selected.set(criterion.key, value);
        sync();
      },
    });
    weightInputs.set(criterion.key, weight);
    sync();

    return el(
      "label",
      { class: "criterion-option" },
      checkbox,
      el(
        "span",
        { class: "criterion-option__body" },
        el("span", { class: "criterion-option__label" }, criterion.label),
        el("span", { class: "criterion-option__blurb" }, criterion.blurb),
      ),
      el("span", { class: "criterion-option__weight" }, "weight", weight),
    );
  });

  const nameInput = el("input", {
    class: "input",
    type: "text",
    placeholder: "GenLayer Studio Preview",
    maxlength: "120",
  });
  const poolInput = el("input", {
    class: "input",
    type: "number",
    min: "1",
    value: "1000",
  });
  const deadlineInput = el("input", {
    class: "input",
    type: "number",
    min: "1",
    value: String(Math.floor(Date.now() / 1000) + 7 * 24 * 3600),
  });
  const windowInput = el("input", {
    class: "input",
    type: "number",
    min: "1",
    value: "3600",
  });

  const submit = el(
    "button",
    {
      class: "btn btn--primary",
      type: "submit",
      onClick: (event) => {
        event.preventDefault();
        const chosen = sync();
        errorSlot.replaceChildren();

        if (chosen.length < MIN_CRITERIA || chosen.length > MAX_CRITERIA) {
          errorSlot.replaceChildren(
            stateBlock(
              `Pick ${MIN_CRITERIA} to ${MAX_CRITERIA} criteria`,
              `You have ${chosen.length}. This is checked here as well as on chain, so a mistake does not become a locked pool.`,
              "bad",
            ),
          );
          return;
        }
        const badWeight = chosen.find(([, weight]) => !(weight >= 1 && weight <= MAX_WEIGHT));
        if (badWeight) {
          errorSlot.replaceChildren(
            stateBlock("Weight out of range", `Weights run from 1 to ${MAX_WEIGHT}.`, "bad"),
          );
          return;
        }

        onOpenProgramme({
          name: nameInput.value.trim() || "Untitled programme",
          criteria: chosen.map(([key, weight]) => ({ key, weight })),
          pool: Number(poolInput.value),
          deadline: Number(deadlineInput.value),
          challengeWindow: Number(windowInput.value),
        });
      },
    },
    connected ? "Open programme and lock the pool" : "Connect a wallet first",
  );

  return el(
    "div",
    { class: "form-page" },
    el(
      "header",
      { class: "form-page__head" },
      el("p", { class: "eyebrow" }, "Organizer"),
      el("h1", { class: "form-page__title" }, "Open a programme"),
      el(
        "p",
        { class: "form-page__lede" },
        "The pool is locked when the programme opens and released only by adjudication or by cancelling. ",
        "A refusal does not revert — it creates a cancelled programme you can refund — so the checks below run before anything is signed.",
      ),
    ),

    errorSlot,

    el(
      "form",
      { class: "form", onSubmit: (event) => event.preventDefault() },
      el(
        "div",
        { class: "form__grid" },
        field("Name", nameInput),
        field("Pool to lock", poolInput, "GEN"),
        field("Deadline", deadlineInput, "unix seconds"),
        field("Challenge window", windowInput, "seconds"),
      ),
      el(
        "p",
        { class: "form__note" },
        "The deadline is an absolute unix second compared against GitHub's signed committer date, not against a block clock — this runner has none. ",
        "Set it far enough ahead that a builder can make a real commit before it.",
      ),
      el("p", { class: "eyebrow" }, "Criteria"),
      el("div", { class: "criteria-options" }, ...rows),
      summary,
      el(
        "div",
        { class: "form__actions" },
        submit,
        el(
          "button",
          { class: "btn", type: "button", onClick: () => onRoute({ name: "landing" }) },
          "Cancel",
        ),
      ),
    ),
  );
}

function field(label, input, suffix) {
  return el(
    "label",
    { class: "field" },
    el("span", { class: "field__label" }, label),
    el("span", { class: "field__control" }, input, suffix ? el("span", { class: "field__suffix" }, suffix) : null),
  );
}