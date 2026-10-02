/**
 * Wallet connection over EIP-1193.
 *
 * The app never holds a key. It asks an injected provider to sign, and refuses
 * to proceed on the wrong chain — a wallet pointed at the wrong network is the
 * most common way a demo fails, and on GenLayer it fails as an opaque
 * `code=-32000` rather than as anything a reader can act on.
 *
 * The two known injected providers are both EIP-1193, so there is no adapter
 * layer: `window.ethereum.request` is the interface.
 */

import { CHAIN_ID, CHAIN_ID_HEX, CHAIN_NAME } from "../config.js";

export function getProvider() {
  if (typeof window === "undefined") return null;
  return window.ethereum || null;
}

export function hasProvider() {
  return Boolean(getProvider());
}

/**
 * The chain-switch request shape. Declared rather than inlined so the string is
 * greppable — a typo in `wallet_switchEthereumChain` fails as "unrecognized
 * method" and gives no hint why.
 */
export const SWITCH_CHAIN = {
  method: "wallet_switchEthereumChain",
  params: [{ chainId: CHAIN_ID_HEX }],
};

/** Connect and return the account address. Throws with a sentence a human can act on. */
export async function connectWallet() {
  const provider = getProvider();
  if (!provider) {
    throw new Error(
      "No injected wallet found. This app never holds a key — it needs a browser wallet " +
        "such as MetaMask or Freighter to sign. Reading a programme needs no wallet at all.",
    );
  }

  const accounts = await provider.request({ method: "eth_requestAccounts" });
  const address = accounts?.[0];
  if (!address) throw new Error("The wallet returned no account.");

  await assertWalletChain(provider, address);
  return address;
}

/** Read the account without prompting. Returns null when there is none. */
export async function readConnectedAccount() {
  const provider = getProvider();
  if (!provider) return null;
  try {
    const accounts = await provider.request({ method: "eth_accounts" });
    return accounts?.[0] || null;
  } catch {
    return null;
  }
}

/**
 * Fail loudly on the wrong chain, offering to switch.
 *
 * `switch` is requested explicitly by the caller rather than silently, because a
 * wallet prompt the user did not ask for is its own surprise.
 */
export async function assertWalletChain(provider, address, { switchChain = false } = {}) {
  let reported;
  try {
    reported = await provider.request({ method: "eth_chainId", params: [] });
  } catch {
    return true; // A provider that will not say is given the benefit of the doubt.
  }
  if (!reported || Number.parseInt(reported, 16) === CHAIN_ID) return true;

  if (switchChain) {
    try {
      await provider.request(SWITCH_CHAIN);
      return true;
    } catch (error) {
      throw new Error(
        `Could not switch this wallet to ${CHAIN_NAME} (chain ${CHAIN_ID}). ` +
          `Change the network in your wallet and try again. ${error?.message || ""}`.trim(),
      );
    }
  }

  throw new Error(
    `This wallet is on chain ${Number.parseInt(reported, 16)}, but ${PRODUCT_LABEL} reads ` +
      `${CHAIN_NAME} (chain ${CHAIN_ID}). Switch the wallet's network to continue.`,
  );
}

const PRODUCT_LABEL = "DeReceipt";

/** Turn a 0x-prefixed address into a checksummed-ish short form for display. */
export function shortAccount(address) {
  if (typeof address !== "string") return "not connected";
  return `${address.slice(0, 6)}…${address.slice(-4)}`;
}

export function listenForAccountChange(handler) {
  const provider = getProvider();
  if (!provider?.on) return () => {};
  provider.on("accountsChanged", handler);
  return () => provider.removeListener?.("accountsChanged", handler);
}

export function listenForChainChange(handler) {
  const provider = getProvider();
  if (!provider?.on) return () => {};
  provider.on("chainChanged", handler);
  return () => provider.removeListener?.("chainChanged", handler);
}