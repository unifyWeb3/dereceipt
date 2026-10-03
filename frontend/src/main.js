/**
 * Boot, hash routing, and the two state regions that persist across every view.
 *
 * ## Why the regions never merge
 *
 * GenLayer's transaction lifecycle and the contract's business state are
 * different layers. A transaction can reach `ACCEPTED` — a majority agreed —
 * while nothing has settled, and only `FINALIZED` moves value. A UI that merges
 * them comes to imply that acceptance was settlement. So they are two separate
 * regions, always both present, never combined into one summary.
 *
 * ## Routes
 *
 *   #/                                    landing
 *   #/open                                open a programme
 *   #/program/0                           a programme and its entries
 *   #/program/0/entry/1                   one receipt, shareable by URL
 *
 * Reading needs no wallet. Only a write does.
 */

import {
  CHAIN_ID,
  CHAIN_ID_HEX,
  CHAIN_NAME,
  CONTRACT_ADDRESS,
  PRODUCT_NAME,
  TAGLINE,
} from "./config.js";
import {
  assertPinnedChain,
  contractExists,
  readAccuracy,
  readBalance,
  readDigest,
  readEntry,
  readProgram,
  readReceipt,
  waitForFinalizedLifecycle,
  writeAndWait,
} from "./lib/contract.js";
import { buildRoute, parseRoute } from "./lib/identifiers.js";
import { assertWalletChain, connectWallet, getProvider, listenForAccountChange, listenForChainChange, readConnectedAccount, shortAccount } from "./lib/wallet.js";
import { el, errorBlock, replace, stateBlock, badge } from "./lib/dom.js";
import { gen } from "./lib/format.js";
import { landingView } from "./views/landing.js";
import { programmeView } from "./views/programme.js";
import { receiptView } from "./views/receipt.js";
import { openProgrammeView } from "./views/openProgramme.js";

/** Everything the views read. One object, replaced wholesale on every load. */
const state = {
  route: { name: "landing" },
  connected: null,
  chainVerified: null,
  chainError: null,
  contractLive: false,
  programme: null,
  entry: null,
  receipt: null,
  accuracy: null,
  digest: null,
  balance: null,
  entries: [],
  transactions: [],
  loading: false,
  loadError: null,
};

/** Transactions this browser sent, with the lifecycle that was observed. */
const transactionLog = [];

const root = document.querySelector("#app");
let statusBar = null;

// ---------------------------------------------------------------------------
// Loading
// ---------------------------------------------------------------------------

/**
 * Load everything the current route needs.
 *
 * Reads are independent, so they are issued together and a failure in one does
 * not blank the page. Each failure is recorded against its own field rather than
 * thrown, because "the accuracy block failed but the receipt loaded" is more
 * useful to a reader than an empty screen.
 */
async function load() {
  state.loading = true;
  state.loadError = null;
  render();

  const route = state.route;
  const settle = async (assign, fn) => {
    try {
      assign(await fn());
    } catch (error) {
      assign(null);
      if (!state.loadError) state.loadError = error;
    }
  };

  if (route.name === "landing" || route.name === "programme" || route.name === "receipt") {
    state.contractLive = await contractExists();
    await settle((v) => (state.balance = v), readBalance);
  }

  if (route.name === "programme" || route.name === "receipt") {
    await settle((v) => (state.programme = v), () => readProgram(route.programId));
    await settle((v) => (state.accuracy = v), () => readAccuracy(route.programId));
    await settle((v) => (state.digest = v), () => readDigest(route.programId));
    await settle((v) => (state.entries = v), loadEntries(route.programId));
  }

  if (route.name === "receipt") {
    await settle((v) => (state.entry = v), () => readEntry(route.programId, route.entryIndex));
    await settle((v) => (state.receipt = v), () => readReceipt(route.programId, route.entryIndex));
  }

  state.loading = false;
  render();
}

/** Every entry of a programme, tolerating a reset that outruns the request. */
async function loadEntries(programId) {
  const programme = state.programme;
  const count = Number(programme?.entry_count ?? 0);
  if (!count) return [];
  const reads = [];
  for (let index = 0; index < count; index += 1) {
    reads.push(readEntry(programId, index));
  }
  const settled = await Promise.allSettled(reads);
  const entries = [];
  for (const [index, result] of settled.entries()) {
    if (result.status !== "fulfilled") continue;
    entries.push({ ...result.value, program_id: programId, index });
  }
  return entries;
}

/** Landing needs the first programme's receipt so the stage has real content. */
async function loadLandingHero() {
  if (!state.contractLive) return;
  try {
    // Programme ids are strings that increment as "0", "1", … Probing a few is
    // cheaper than an index view the contract does not expose, and a miss is a
    // refusal rather than an error.
    for (const candidate of ["0", "1", "2"]) {
      const programme = await readProgram(candidate);
      if (!programme) continue;
      state.programme = programme;
      state.accuracy = await readAccuracy(candidate);
      state.digest = await readDigest(candidate);
      state.entries = await loadEntries(candidate);
      if (state.entries.length > 0) {
        const first = state.entries[0];
        state.entry = first;
        state.receipt = await readReceipt(candidate, first.index);
      }
      return;
    }
  } catch {
    // A landing page with no hero receipt is a valid state; the stage says so.
  }
}

// ---------------------------------------------------------------------------
// Writes
// ---------------------------------------------------------------------------

/**
 * Every write in the app. One helper, so the chain assertion, the lifecycle wait
 * and the two-not-success states cannot be handled inconsistently.
 */
async function send(method, args, { value, label } = {}) {
  if (!state.connected) {
    await connect();
    if (!state.connected) return;
  }
  const provider = getProvider();
  if (provider) {
    await assertWalletChain(provider, state.connected, { switchChain: true });
  }

  appendNotice(`Sending ${label || method}…`, "open");

  try {
    const result = await writeAndWait(method, args, { account: state.connected, value });
    const record = {
      method,
      label: label || method,
      hash: result.hash,
      lifecycle: result.lifecycle,
      at: new Date().toLocaleTimeString("en-GB"),
    };
    transactionLog.unshift(record);
    if (transactionLog.length > 12) transactionLog.pop();
    replaceNotice(
      el(
        "div",
        { class: "notice notice--ok" },
        el("strong", {}, `${label || method} finalized. `),
        el("code", { class: "mono" }, result.hash.slice(0, 18) + "…"),
      ),
      "ok",
    );
    await load();
    return result;
  } catch (error) {
    // Undetermined and Canceled arrive here as exceptions, by design. They are
    // outcomes to display, not failures to hide behind a toast.
    replaceNotice(
      el(
        "div",
        { class: "notice notice--warn" },
        el("strong", {}, `${label || method} did not settle. `),
        el("span", {}, error?.message || String(error)),
      ),
      "warn",
    );
    await load();
    return null;
  }
}

function appendNotice(text, tone) {
  if (!statusBar) return;
  replace(statusBar, el("div", { class: `notice notice--${tone}` }, text));
}

function replaceNotice(node, tone) {
  if (!statusBar) return;
  replace(statusBar, el("div", { class: `notice notice--${tone}` }, node));
}

// ---------------------------------------------------------------------------
// Wallet
// ---------------------------------------------------------------------------

async function connect() {
  try {
    const provider = getProvider();
    if (provider) await assertWalletChain(provider, null, { switchChain: true });
    state.connected = await connectWallet();
    render();
  } catch (error) {
    replaceNotice(
      el(
        "div",
        { class: "notice notice--bad", role: "alert" },
        el("strong", {}, "Wallet. "),
        el("span", {}, error?.message || String(error)),
      ),
      "bad",
    );
  }
}

// ---------------------------------------------------------------------------
// Routing
// ---------------------------------------------------------------------------

function go(route) {
  const path = buildRoute(route);
  if (window.location.pathname === path) {
    state.route = route;
    load();
  } else {
    // A real path, not a hash. A receipt URL is meant to be pasted into a
    // submission note, a demo script or a chat message, and `/#/program/0` in
    // that context reads as a workaround rather than a link.
    window.history.pushState({}, "", path);
    state.route = route;
    load();
  }
}

/**
 * Read the route from the URL.
 *
 * Both a real path and a legacy hash are accepted, because the first version of
 * this app shipped hash routes and a bookmarked `#/program/0` should still land
 * somewhere useful.
 */
function readRoute() {
  const { pathname, hash } = window.location;
  const source = pathname && pathname !== "/" ? pathname : hash || "/";
  try {
    return parseRoute(source);
  } catch (error) {
    // A malformed URL must not blank the app. The identifier assertion throws a
    // sentence naming which argument was wrong, which is exactly what is needed.
    return { name: "landing", routeError: error?.message || String(error) };
  }
}

function onLocationChange() {
  state.route = readRoute();
  load();
}

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------

function chrome() {
  const account = state.connected
    ? el(
        "button",
        {
          class: "pill pill--account",
          type: "button",
          onClick: () => {
            state.connected = null;
            render();
          },
          title: "Disconnect",
        },
        shortAccount(state.connected),
      )
    : el(
        "button",
        { class: "pill pill--connect", type: "button", onClick: connect },
        "Connect wallet",
      );

  const chainPill = state.chainVerified
    ? badge(`${CHAIN_NAME} · chain ${CHAIN_ID}`, "ok", `RPC reports ${state.chainVerified}`)
    : state.chainError
      ? badge("wrong chain", "bad", state.chainError)
      : badge("checking chain…", "open");

  return el(
    "header",
    { class: "topbar" },
    el(
      "a",
      { class: "topbar__brand", href: "/" },
      el("span", { class: "topbar__name" }, PRODUCT_NAME),
      el("span", { class: "topbar__tag" }, TAGLINE),
    ),
    el("div", { class: "topbar__right" }, chainPill, account),
  );
}

function render() {
  const route = state.route;

  const body = (() => {
    if (state.chainError) {
      return errorBlock("This build is pointed at the wrong network", state.chainError);
    }
    if (route.routeError) {
      return errorBlock("That address in the URL is not valid", route.routeError);
    }
    switch (route.name) {
      case "programme":
        return programmeView({
          programme: state.programme,
          entries: state.entries,
          accuracy: state.accuracy,
          digestValue: state.digest,
          transactions: transactionLog,
          onRoute: go,
          onWrite: send,
        });
      case "receipt":
        return receiptView({
          receipt: state.receipt,
          entry: state.entry,
          accuracy: state.accuracy,
          digestValue: state.digest,
          programme: state.programme,
          onRoute: go,
        });
      case "open":
        return openProgrammeView({ connected: Boolean(state.connected), onRoute: go, onOpenProgramme: openProgramme });
      case "landing":
      default:
        return landingView({
          programme:
            state.programme && state.receipt
              ? { program: state.programme, receipt: state.receipt, entry: state.entry }
              : null,
          contractLive: state.contractLive,
          onOpen: go,
          onOpenProgramme: () => go({ name: "open" }),
        });
    }
  })();

  statusBar = el("div", { class: "statusbar" });

  replace(
    root,
    chrome(),
    statusBar,
    el("main", { class: "shell" }, body),
    el(
      "footer",
      { class: "footbar" },
      el(
        "p",
        {},
        `${PRODUCT_NAME} · ${CHAIN_NAME} chain ${CHAIN_ID} · contract `,
        el("code", { class: "mono" }, CONTRACT_ADDRESS.slice(0, 10) + "…" + CONTRACT_ADDRESS.slice(-6)),
        ` · contract holds ${gen(state.balance)} GEN`,
      ),
    ),
  );
}

/** Open a programme from the form. One call, then route to what was created. */
async function openProgramme({ name, criteria, pool, deadline, challengeWindow }) {
  const result = await send(
    "open_program",
    [name, JSON.stringify(criteria), deadline, challengeWindow, "{}"],
    { value: BigInt(Math.trunc(pool)), label: "open_program" },
  );
  if (result) {
    // The contract returns the new id; route to it so the reader lands on what
    // they just made rather than back on a landing page that does not mention it.
    try {
      const raw = result.transaction?.result ?? result.transaction?.rawReturn;
      const id = typeof raw === "string" ? raw : null;
      if (id) go({ name: "programme", programId: id });
    } catch {
      go({ name: "programme", programId: "0" });
    }
  }
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

/**
 * A legacy `#/...` link fires `hashchange`, not `popstate`. Kept so an old
 * bookmark does not silently do nothing.
 */
function onHashChangeLegacy() {
  state.route = readRoute();
  load();
}


async function boot() {
  state.route = readRoute();

  // The chain assertion runs before anything is sent, so a misconfigured build
  // fails with a sentence rather than a screen of zeroes.
  try {
    state.chainVerified = await assertPinnedChain();
  } catch (error) {
    state.chainError = error?.message || String(error);
  }

  state.connected = await readConnectedAccount();

  window.addEventListener("popstate", onLocationChange);
  window.addEventListener("hashchange", onHashChangeLegacy);
  listenForAccountChange(() => {
    readConnectedAccount().then((account) => {
      state.connected = account;
      render();
    });
  });
  listenForChainChange(() => {
    assertPinnedChain().catch((error) => {
      state.chainError = error?.message || String(error);
      render();
    });
  });

  if (state.route.name === "landing") await loadLandingHero();
  await load();
}

boot().catch((error) => {
  replace(
    root,
    el(
      "div",
      { class: "shell" },
      errorBlock(
        "Could not start",
        `${error?.message || String(error)} — expected ${CHAIN_ID_HEX} on ${CHAIN_NAME}.`,
      ),
    ),
  );
});