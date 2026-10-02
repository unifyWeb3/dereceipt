/**
 * DOM helpers. Enough structure to keep the views readable, and nothing that
 * looks like a framework.
 *
 * The rule this file follows: a view is a function that returns an HTMLElement.
 * No string templates spliced with innerHTML, because an entrant's repository
 * name and a challenge's evidence URL are attacker-influenced strings, and
 * `innerHTML` is how a demo ends up executing somebody else's markup.
 */

import { copyText } from "./format.js";

/**
 * Create an element.
 *
 *   el("div", { class: "panel" }, "text", el("span", {}, "child"))
 *
 * Props starting with `on` become listeners; `class`, `id`, `href`, `title`,
 * `data-*` and `aria-*` become attributes. Everything else that is a plain value
 * becomes a property, so `el("input", { value: 3 })` works.
 */
export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);

  for (const [key, value] of Object.entries(props || {})) {
    if (value === null || value === undefined || value === false) continue;

    if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === "class") {
      node.className = value;
    } else if (key === "dataset" && typeof value === "object") {
      Object.assign(node.dataset, value);
    } else if (key === "style" && typeof value === "object") {
      Object.assign(node.style, value);
    } else if (
      key === "href" ||
      key === "id" ||
      key === "title" ||
      key === "type" ||
      key === "placeholder" ||
      key === "rel" ||
      key === "target" ||
      key === "disabled" ||
      key === "value" ||
      key === "name" ||
      key === "lang"
    ) {
      node.setAttribute(key, value === true ? "" : String(value));
    } else {
      node.setAttribute(key, value === true ? "" : String(value));
    }
  }

  append(node, children);
  return node;
}

export function append(parent, children) {
  for (const child of children.flat(4)) {
    if (child === null || child === undefined || child === false) continue;
    parent.appendChild(
      child instanceof Node ? child : document.createTextNode(String(child)),
    );
  }
  return parent;
}

/** Replace a node's children in one operation. */
export function replace(parent, ...children) {
  parent.replaceChildren();
  append(parent, children);
  return parent;
}

export const frag = (...children) => append(document.createDocumentFragment(), children);

export const $ = (selector, scope = document) => scope.querySelector(selector);

/**
 * An explorer deep link.
 *
 * The Studio-dev explorer returns 503 intermittently — measured at M0, twice on
 * five probes — so a link is never awaited and never gates a render. It is a
 * plain anchor; if the explorer is down, the receipt still renders.
 */
export function explorerLink(base, kind, value, label) {
  return el(
    "a",
    {
      class: "link",
      href: `${base}/${kind}/${value}`,
      target: "_blank",
      rel: "noreferrer noopener",
      title: `Open ${kind} on the GenLayer explorer`,
    },
    label || value,
  );
}

/**
 * A state badge.
 *
 * `tone` is semantic, not decorative: `settled`, `open`, `warn`, `bad`,
 * `muted`. A badge for UNDETERMINED uses `warn`, never `bad` — a criterion the
 * jury could not settle is the product working, and rendering it as an error
 * would be a lie about what happened.
 */
export function badge(text, tone = "muted", title = "") {
  return el("span", { class: `badge badge--${tone}`, title }, text);
}

/** A labelled figure. The workhorse of the receipt. */
export function stat(label, value, tone) {
  return el(
    "div",
    { class: `stat${tone ? ` stat--${tone}` : ""}` },
    el("p", { class: "stat__label" }, label),
    el("p", { class: "stat__value" }, value),
  );
}

/** A copyable monospace value — a digest, an address, a transaction id. */
export function copyable(value, { label = "Copy", what = "value" } = {}) {
  if (!value) return el("code", { class: "mono" }, "—");
  const button = el(
    "button",
    {
      class: "copy",
      type: "button",
      "aria-label": `Copy the ${what}`,
      onClick: async (event) => {
        event.stopPropagation();
        const ok = await copyText(String(value));
        button.textContent = ok ? "Copied" : "Press ⌘C";
        button.classList.toggle("copy--ok", ok);
        setTimeout(() => {
          button.textContent = label;
          button.classList.remove("copy--ok");
        }, 1600);
      },
    },
    label,
  );
  return el("span", { class: "copyable" }, el("code", { class: "mono" }, value), button);
}

/** A full-width state block: loading, empty, or an honest explanation. */
export function stateBlock(title, detail, tone = "muted") {
  return el(
    "div",
    { class: `state state--${tone}` },
    el("p", { class: "state__title" }, title),
    detail ? el("p", { class: "state__detail" }, detail) : null,
  );
}

/** An error a person can act on, with the technical text kept but secondary. */
export function errorBlock(title, error) {
  const message = error?.message || String(error);
  return el(
    "div",
    { class: "state state--bad", role: "alert" },
    el("p", { class: "state__title" }, title),
    el("p", { class: "state__detail" }, message),
  );
}