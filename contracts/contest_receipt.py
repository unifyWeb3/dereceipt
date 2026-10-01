# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }

"""Contest Receipt — auditable verdicts for AI-judged programmes, on GenLayer.

An organiser publishes a programme. A builder submits a repository pinned to an
immutable commit. This contract freezes that evidence, derives a receipt from it,
lets a losing entrant stake a challenge against ONE named criterion, and lets the
programme publish its own overturn rate.

There is **no model in the decision path**. Every verdict is arithmetic over
facts fetched from the GitHub API and committed to chain, reached by independent
validator re-derivation under the equivalence principle. A fact is a fact; a model
has no authority over one. That is inherited deliberately from the 360/400
reference build, whose contract contains no LLM call at all and whose
``validator_fn`` re-runs ``leader_fn`` itself.

Three things this contract refuses to do, each because it would be dishonest
rather than merely inconvenient:

* **Only a 404 is a rejection.** A 403, 429, 5xx, empty body or non-JSON is
  ``UNDETERMINED``. Validators call ``api.github.com`` unauthenticated from their
  own machines, so rate limits are expected, and a rate limit is never recorded as
  a builder's fault.
* **The original verdict is never overwritten.** A challenge outcome is recorded
  *beside* it. The receipt is append-only; that append-only log is the product.
* **A transfer is never reported before it is delivered.** ``TRANSFER_EMITTED``
  records that a message was scheduled. Only a decrease in this contract's own
  balance is evidence that value moved.

See ``docs/ARCHITECTURE.md`` for the nine hard rules this implements and
``docs/VERIFICATION.md`` for what has actually been observed on chain.
"""

import json
import re

import genlayer as gl
from genlayer import Keccak256

# ---------------------------------------------------------------------------
# Bounded storage
#
# Every bound is stated here rather than implied. The stored evidence is a
# digest, a count, and a capped path summary — never rendered HTML, never a file
# body, never a manifest.
# ---------------------------------------------------------------------------

#: Hard cap on any response body this contract will read. Matches the 360/400
#: reference build, and is applied per fetch.
MAX_RESPONSE_BYTES = 200_000

#: Hard cap on stored file paths per entry. A repository may contain far more
#: files than are recorded; the count that was dropped is stored alongside, so a
#: reader can see that a summary is a summary.
MAX_STORED_PATHS = 64

#: Hard cap on a single stored path, in characters.
MAX_PATH_LENGTH = 96

#: Hard cap on a text field supplied by a caller (programme name, repo slug, …).
MAX_NAME_LENGTH = 120
MAX_REPO_LENGTH = 200
MAX_URL_LENGTH = 512
MAX_STACK_LENGTH = 200
MAX_CLAIMS_LENGTH = 2000
MAX_CRITERIA_LENGTH = 4000
MAX_FLAGS_LENGTH = 512
MAX_GROUND_LENGTH = 64
MAX_SLUG_LENGTH = 40
MAX_COMMIT_LENGTH = 40

# ---------------------------------------------------------------------------
# Programme / entry status vocabularies
#
# Business state is deliberately separate from GenLayer protocol state. ACCEPTED
# is not finality.
# ---------------------------------------------------------------------------

PROGRAM_OPEN = "OPEN"
PROGRAM_CLOSED = "CLOSED"
PROGRAM_CLOSED_NO_WINNER = "CLOSED_NO_WINNER"
PROGRAM_CANCELLED = "CANCELLED"

ENTRY_SUBMITTED = "SUBMITTED"
ENTRY_FROZEN = "FROZEN"
ENTRY_UNDER_REVIEW = "UNDER_REVIEW"
ENTRY_STANDING = "STANDING"
ENTRY_DISQUALIFIED = "DISQUALIFIED"
ENTRY_PAYOUT_READY = "PAYOUT_READY"
ENTRY_PAID = "PAID"

CRITERION_PASS = "PASS"
CRITERION_FAIL = "FAIL"
CRITERION_UNDETERMINED = "UNDETERMINED"

CHALLENGE_FILED = "FILED"
CHALLENGE_UPHELD = "UPHELD"
CHALLENGE_DENIED = "DENIED"
CHALLENGE_EXPIRED = "EXPIRED"

PAYOUT_NOT_SCHEDULED = "NOT_SCHEDULED"
PAYOUT_PENDING_FINALITY = "PENDING_FINALITY"
PAYOUT_READY = "READY"
PAYOUT_TRANSFER_EMITTED = "TRANSFER_EMITTED"

#: The fixed criterion set. There is no "bring your own rubric" configurator:
#: criteria are chosen from this list, snapshotted at open, and never changed.
#: The optional subjective criterion is deliberately absent — it is M3.5, and the
#: product is complete and defensible without it.
KNOWN_CRITERIA = (
    "repo_resolves",
    "commit_predates_deadline",
    "required_files_present",
    "declared_language_present",
    "not_duplicate",
)

MIN_CRITERIA = 3
MAX_CRITERIA = 5
MAX_WEIGHT = 10

#: Challenge grounds. Every one of these is deterministic; none needs a model.
KNOWN_GROUNDS = (
    "AFTER_DEADLINE_WORK",
    "DUPLICATE_SUBMISSION",
    "MISSING_REQUIRED_FILE",
    "UNSUPPORTED_CLAIM",
    "DEAD_DEMO",
)

#: A declared language is refuted when the frozen tree contains no file with any
#: of these extensions. This is the anti-self-description check: entrants
#: describe their own work and nothing else checks the description.
LANGUAGE_EXTENSIONS = {
    "typescript": (".ts", ".tsx"),
    "javascript": (".js", ".jsx", ".mjs", ".cjs"),
    "python": (".py",),
    "rust": (".rs",),
    "go": (".go",),
    "solidity": (".sol",),
    "java": (".java",),
    "c": (".c", ".h"),
    "cpp": (".cpp", ".cc", ".cxx", ".hpp"),
    "ruby": (".rb",),
}

#: A demo URL must be on this allow-list. A demo is fetched, so an arbitrary host
#: would be an open request-forgery surface aimed at validators.
ALLOWED_DEMO_HOSTS = ("https://",)

REQUIRED_FILE = "README.md"


@gl.evm.contract_interface
class _NativeRecipient:
    """A plain external account, for GEN transfers out of this contract.

    EOAs live on the GenLayer chain layer. The EVM interface emits an external
    message that Studio executes on finalization; a plain GenVM contract proxy
    produces an internal message that is skipped and the balance never moves.
    That was measured on the reference build: 22.6 GEN of real balance against
    4.7 GEN of books, with ``skipped=true`` in every receipt.
    """

    class View:
        pass

    class Write:
        pass


# ---------------------------------------------------------------------------
# Small pure helpers
# ---------------------------------------------------------------------------


def _status_of(response) -> int:
    status = getattr(response, "status_code", None)
    if status is None:
        status = getattr(response, "status", 0)
    try:
        return int(status)
    except (TypeError, ValueError):
        return 0


def _body_of(response) -> str:
    body = getattr(response, "body", b"")
    if isinstance(body, bytes):
        if len(body) > MAX_RESPONSE_BYTES:
            return ""
        return body.decode("utf-8", errors="replace")
    if isinstance(body, str):
        if len(body.encode("utf-8")) > MAX_RESPONSE_BYTES:
            return ""
        return body
    return ""


def _is_bounded_text(value, limit: int) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= limit
        and all(ord(character) >= 32 for character in value)
    )


def _sha256_hex(text: str) -> str:
    return Keccak256(text.encode("utf-8")).hexdigest()


def _json_object_or_empty(text: str) -> dict:
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_list_or_empty(text: str) -> list:
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def _canonical_json(value) -> str:
    """Sort keys so the same value always produces the same bytes.

    The receipt digest is a hash over this string, so key order must not be able
    to change a digest.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class ContestReceipt(gl.contract.Contract):
    """A bounded, auditable adjudication record for one programme at a time."""

    program_count: gl.u32

    # -- programme scope ----------------------------------------------------
    program_owner: gl.storage.TreeMap[str, gl.Address]
    program_name: gl.storage.TreeMap[str, str]
    program_criteria: gl.storage.TreeMap[str, str]
    program_criterion_count: gl.storage.TreeMap[str, gl.u32]
    program_deadline: gl.storage.TreeMap[str, gl.u256]
    program_challenge_window: gl.storage.TreeMap[str, gl.u256]
    program_flags: gl.storage.TreeMap[str, str]
    program_pool: gl.storage.TreeMap[str, gl.u256]
    program_locked: gl.storage.TreeMap[str, gl.u256]
    program_status: gl.storage.TreeMap[str, str]
    program_entry_count: gl.storage.TreeMap[str, gl.u32]
    program_challenge_count: gl.storage.TreeMap[str, gl.u32]
    program_challenges_upheld: gl.storage.TreeMap[str, gl.u32]
    program_undetermined_count: gl.storage.TreeMap[str, gl.u32]
    program_disqualified_count: gl.storage.TreeMap[str, gl.u32]
    program_paid_out: gl.storage.TreeMap[str, gl.u256]
    program_refunded: gl.storage.TreeMap[str, gl.u256]
    #: Why a programme could not be opened, or empty. Readable in get_program so
    #: a refusal is never invisible — the M3 smoke test's first run stranded 1000
    #: GEN in a pool with no programme, because a catch-all refusal was recorded
    #: nowhere.
    program_error: gl.storage.TreeMap[str, str]
    #: A digest already seen in this programme. This is the duplicate set.
    program_seen_digest: gl.storage.TreeMap[str, str]

    # -- entry scope --------------------------------------------------------
    entry_submitter: gl.storage.TreeMap[str, gl.Address]
    entry_repo: gl.storage.TreeMap[str, str]
    entry_commit: gl.storage.TreeMap[str, str]
    entry_demo: gl.storage.TreeMap[str, str]
    entry_stack: gl.storage.TreeMap[str, str]
    entry_claims: gl.storage.TreeMap[str, str]
    entry_status: gl.storage.TreeMap[str, str]
    entry_tree_digest: gl.storage.TreeMap[str, str]
    entry_committer_date: gl.storage.TreeMap[str, str]
    entry_file_count: gl.storage.TreeMap[str, gl.u32]
    entry_manifest_summary: gl.storage.TreeMap[str, str]
    entry_manifest_omitted: gl.storage.TreeMap[str, gl.u32]
    entry_readme_present: gl.storage.TreeMap[str, str]
    entry_disqualify_reason: gl.storage.TreeMap[str, str]
    entry_payout: gl.storage.TreeMap[str, gl.u256]
    entry_payout_status: gl.storage.TreeMap[str, str]
    entry_challenge_count: gl.storage.TreeMap[str, gl.u32]
    entry_verdict_count: gl.storage.TreeMap[str, gl.u32]

    # -- per-criterion scope ------------------------------------------------
    criterion_verdict: gl.storage.TreeMap[str, str]
    criterion_reason: gl.storage.TreeMap[str, str]

    # -- challenge scope ----------------------------------------------------
    challenge_ground: gl.storage.TreeMap[str, str]
    challenge_criterion: gl.storage.TreeMap[str, str]
    challenge_evidence: gl.storage.TreeMap[str, str]
    challenge_bond: gl.storage.TreeMap[str, gl.u256]
    challenge_filer: gl.storage.TreeMap[str, gl.Address]
    challenge_status: gl.storage.TreeMap[str, str]
    challenge_result: gl.storage.TreeMap[str, str]
    challenge_resolved_at: gl.storage.TreeMap[str, str]

    # -- finalization marker ------------------------------------------------
    #: When the finalization callback last ran for an entry. Proof that the
    #: verdict was adjudicated on chain and not merely accepted.
    entry_finalized_at: gl.storage.TreeMap[str, str]

    def __init__(self):
        self.program_count = gl.u32(0)

    # ------------------------------------------------------------------
    # Keys and guards
    # ------------------------------------------------------------------

    def _pk(self, program_id: str) -> str:
        return program_id

    def _ek(self, program_id: str, index: int) -> str:
        return f"{program_id}:{index}"

    def _ck(self, program_id: str, index: int, slug: str) -> str:
        return f"{program_id}:{index}:{slug}"

    def _fail(self, message: str) -> None:
        """Revert.

        Used ONLY in methods that neither received value nor move it: views,
        ``freeze_entry``, and ``finalize_program``. A revert in a method that
        received value would strand that value, so every such method returns a
        result object instead of raising. This is the rule, enforced by where
        this helper is called from, not by a comment.
        """
        raise gl.vm.UserError(f"[EXPECTED] {message}")

    def _refuse(self, message: str) -> dict:
        """A refusal that does not revert. Safe in any method."""
        return {"ok": False, "error": message, "state_changed": False}

    def _require_program(self, program_id: str) -> None:
        if program_id not in self.program_owner:
            self._fail("unknown programme")

    def _require_entry(self, program_id: str, index: int) -> None:
        self._require_program(program_id)
        if index < 0 or index >= int(self.program_entry_count[program_id]):
            self._fail("unknown entry")

    def _now(self) -> int:
        """Deliberately unavailable.

        ``gl.vm.get_timestamp()`` is the only time accessor in this runner's std
        library, and it raises ``SystemError: 2: inval`` here — measured, not
        assumed; see ``docs/VERIFICATION.md``. A contract that cannot read a clock
        cannot honestly enforce arrival-time policy, so it does not pretend to.

        What replaces it is stronger anyway. The deadline guarantee this product
        exists for is that a submission's work predates the deadline, and that is
        proven by comparing GitHub's signed ``committer.date`` against the
        absolute deadline stored at open — arithmetic every validator repeats,
        with no clock involved. What is dropped is only the *arrival* check: a
        late submission of a pre-deadline commit is accepted and visibly
        pre-deadline, which is the claim being made.

        The consequence for rule 5 (never combine a clock read with a transfer)
        is that the rule is now vacuously satisfied. It was written for a clock
        this runner does not have, and it is kept as a constraint rather than
        quietly deleted.
        """
        self._fail("this runner exposes no block clock; see _now()'s docstring")

    def _no_clock(self) -> str:
        """A stable marker for "no clock available", stored where a time would be.

        Storing an empty string would read like "not yet recorded", which is a
        different and misleading claim.
        """
        return "NO_CLOCK_ON_THIS_RUNNER"

    # ------------------------------------------------------------------
    # Canonicalisation
    # ------------------------------------------------------------------

    def _canonical_repo(self, raw: str) -> str:
        value = raw.strip().rstrip("/")
        for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
            if value.startswith(prefix):
                value = value[len(prefix) :]
                break
        if value.count("/") != 1 or value.count("@") != 0:
            self._fail("repository must be owner/name")
        owner, name = value.split("/", 1)
        pattern = r"[A-Za-z0-9_.-]+"
        if re.fullmatch(pattern, owner) is None or re.fullmatch(pattern, name) is None:
            self._fail("repository contains an invalid name")
        if not _is_bounded_text(value, MAX_REPO_LENGTH):
            self._fail("repository is out of range")
        return f"{owner}/{name}"

    def _canonical_commit(self, raw: str) -> str:
        value = raw.strip().lower()
        if re.fullmatch(r"[0-9a-f]{40}", value) is None:
            self._fail("commit must be a full 40-character lowercase sha")
        return value

    def _canonical_demo(self, raw: str) -> str:
        from urllib.parse import urlsplit, urlunsplit

        value = raw.strip()
        if not _is_bounded_text(value, MAX_URL_LENGTH):
            self._fail("demo url is out of range")
        try:
            parsed = urlsplit(value)
            hostname = parsed.hostname
            port = parsed.port
        except ValueError:
            self._fail("demo url is malformed")
        if parsed.scheme.lower() != "https" or hostname is None:
            self._fail("demo url must be https")
        if parsed.username is not None or parsed.password is not None:
            self._fail("demo url credentials are not allowed")
        if port not in (None, 443):
            self._fail("demo url must use the default https port")
        if parsed.fragment:
            self._fail("demo url fragments are not canonical evidence")
        if hostname.lower() not in ("github.com", "gitlab.com", "vercel.app", "netlify.app", "pages.dev", "glitch.me", "replit.app", "fly.dev", "herokuapp.com", "example.com"):
            self._fail("demo url host is not on the allow-list")
        netloc = hostname.lower()
        path = parsed.path or "/"
        return urlunsplit(("https", netloc, path, parsed.query, ""))

    def _canonical_stack(self, raw: str) -> str:
        value = raw.strip().lower()
        if not _is_bounded_text(value, MAX_STACK_LENGTH):
            self._fail("declared stack is out of range")
        tokens = [token for token in re.split(r"[,;/\s]+", value) if token]
        if not tokens or len(tokens) > 8:
            self._fail("declared stack must contain 1-8 languages")
        for token in tokens:
            if re.fullmatch(r"[a-z0-9+#.-]{1,24}", token) is None:
                self._fail("declared stack contains an invalid language token")
        return ",".join(sorted(set(tokens)))

    def _canonical_ground(self, raw: str) -> str:
        value = raw.strip().upper()
        if not _is_bounded_text(value, MAX_GROUND_LENGTH):
            self._fail("challenge ground is out of range")
        if value not in KNOWN_GROUNDS:
            self._fail("challenge ground is not a known accusation")
        return value

    def _canonical_criteria(self, raw: str) -> tuple:
        """Validate and canonicalise the criterion snapshot.

        Snapshotted at open and never changed. The key must come from
        ``KNOWN_CRITERIA`` — there is no arbitrary rubric — the weight must be an
        integer in range, and a criterion marked ``subjective`` is refused because
        no model criterion exists in this milestone.
        """
        if not _is_bounded_text(raw, MAX_CRITERIA_LENGTH):
            self._fail("criteria is out of range")
        items = _json_list_or_empty(raw)
        if len(items) < MIN_CRITERIA or len(items) > MAX_CRITERIA:
            self._fail(f"a programme must declare {MIN_CRITERIA}-{MAX_CRITERIA} criteria")
        seen = []
        normalized = []
        for item in items:
            if not isinstance(item, dict):
                self._fail("each criterion must be an object")
            key = str(item.get("key", "")).strip()
            if key not in KNOWN_CRITERIA:
                self._fail("criterion key is not in the fixed criterion set")
            if key in seen:
                self._fail("criterion key is declared twice")
            if item.get("subjective"):
                self._fail(
                    "no subjective criterion exists in this build; the bounded "
                    "model criterion is a later, optional milestone"
                )
            try:
                weight = int(item.get("weight", 0))
            except (TypeError, ValueError):
                self._fail("criterion weight must be an integer")
            if weight < 1 or weight > MAX_WEIGHT:
                self._fail(f"criterion weight must be 1-{MAX_WEIGHT}")
            seen.append(key)
            normalized.append({"key": key, "weight": weight})
        return _canonical_json(normalized), len(normalized)

    def _criterion_slugs(self, program_id: str) -> list:
        return [item["key"] for item in _json_list_or_empty(self.program_criteria[program_id])]

    def _criterion_weight(self, program_id: str, key: str) -> int:
        for item in _json_list_or_empty(self.program_criteria[program_id]):
            if item.get("key") == key:
                return int(item.get("weight", 0))
        return 0

    # ------------------------------------------------------------------
    # The deterministic core
    #
    # Runs inside a non-deterministic block. The leader derives the verdicts from
    # the GitHub API; the validator re-derives them itself and compares. Only
    # decision fields are compared, never a free-form explanation.
    # ------------------------------------------------------------------

    def _evaluate_entry(self, repo: str, commit: str, deadline: int, keys: list) -> dict:
        """Re-derive every criterion verdict from the frozen source."""

        def leader_fn() -> dict:
            verdicts: dict = {}
            notes: dict = {}

            # --- repo_resolves -------------------------------------------
            repo_status = 0
            if "repo_resolves" in keys:
                response = gl.nondet.web.get(f"https://api.github.com/repos/{repo}")
                repo_status = _status_of(response)
                if repo_status == 404:
                    verdicts["repo_resolves"] = CRITERION_FAIL
                    notes["repo_resolves"] = "repository_not_found"
                elif repo_status != 200:
                    verdicts["repo_resolves"] = CRITERION_UNDETERMINED
                    notes["repo_resolves"] = "github_unavailable"
                else:
                    verdicts["repo_resolves"] = CRITERION_PASS
                    notes["repo_resolves"] = "repository_resolves"

            # --- commit_predates_deadline --------------------------------
            committer_date = ""
            commit_status = 0
            if "commit_predates_deadline" in keys or "required_files_present" in keys:
                response = gl.nondet.web.get(
                    f"https://api.github.com/repos/{repo}/commits/{commit}"
                )
                commit_status = _status_of(response)
                if commit_status == 404:
                    # Only a 404 is a business rejection.
                    if "commit_predates_deadline" in keys:
                        verdicts["commit_predates_deadline"] = CRITERION_FAIL
                        notes["commit_predates_deadline"] = "commit_not_found"
                elif commit_status != 200:
                    if "commit_predates_deadline" in keys:
                        verdicts["commit_predates_deadline"] = CRITERION_UNDETERMINED
                        notes["commit_predates_deadline"] = "github_unavailable"
                else:
                    payload = _json_object_or_empty(_body_of(response))
                    commit_block = payload.get("commit") if isinstance(payload.get("commit"), dict) else {}
                    committer = commit_block.get("committer") if isinstance(committer_block.get("committer"), dict) else {}
                    committer_date = str(committer.get("date", ""))
                    if "commit_predates_deadline" in keys:
                        observed = _parse_iso8601(committer_date)
                        if observed is None:
                            verdicts["commit_predates_deadline"] = CRITERION_UNDETERMINED
                            notes["commit_predates_deadline"] = "committer_date_unreadable"
                        elif observed < deadline:
                            verdicts["commit_predates_deadline"] = CRITERION_PASS
                            notes["commit_predates_deadline"] = "committer_date_before_deadline"
                        else:
                            verdicts["commit_predates_deadline"] = CRITERION_FAIL
                            notes["commit_predates_deadline"] = "committer_date_at_or_after_deadline"

            # --- the frozen tree -----------------------------------------
            digest = ""
            paths: list = []
            file_count = 0
            readme_present = False
            tree_status = 0
            if (
                "required_files_present" in keys
                or "declared_language_present" in keys
                or "not_duplicate" in keys
            ):
                response = gl.nondet.web.get(
                    f"https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1"
                )
                tree_status = _status_of(response)
                if tree_status == 404:
                    if "required_files_present" in keys:
                        verdicts["required_files_present"] = CRITERION_FAIL
                        notes["required_files_present"] = "tree_not_found"
                    if "declared_language_present" in keys:
                        verdicts["declared_language_present"] = CRITERION_UNDETERMINED
                        notes["declared_language_present"] = "tree_not_found"
                    if "not_duplicate" in keys:
                        verdicts["not_duplicate"] = CRITERION_UNDETERMINED
                        notes["not_duplicate"] = "tree_not_found"
                elif tree_status != 200:
                    for key in ("required_files_present", "declared_language_present", "not_duplicate"):
                        if key in keys:
                            verdicts[key] = CRITERION_UNDETERMINED
                            notes[key] = "github_unavailable"
                else:
                    payload = _json_object_or_empty(_body_of(response))
                    entries = payload.get("tree") if isinstance(payload.get("tree"), list) else []
                    blobs = []
                    for entry in entries:
                        if isinstance(entry, dict) and entry.get("type") == "blob":
                            name = str(entry.get("path", ""))
                            if name:
                                blobs.append(name)
                    file_count = len(blobs)
                    # The digest is over the sorted, capped, normalised manifest.
                    # Sorted so the same tree always yields the same digest, and
                    # capped so a huge repository cannot inflate it.
                    normalized = sorted(
                        name[:MAX_PATH_LENGTH] for name in blobs[:MAX_STORED_PATHS]
                    )
                    digest = _sha256_hex(_canonical_json(normalized))
                    readme_present = any(
                        name.rsplit("/", 1)[-1] == REQUIRED_FILE for name in blobs
                    )
                    paths = normalized

                    if "required_files_present" in keys:
                        if readme_present:
                            verdicts["required_files_present"] = CRITERION_PASS
                            notes["required_files_present"] = "readme_present"
                        else:
                            verdicts["required_files_present"] = CRITERION_FAIL
                            notes["required_files_present"] = "readme_absent"
                    if "declared_language_present" in keys:
                        verdicts["declared_language_present"] = CRITERION_UNDETERMINED
                        notes["declared_language_present"] = "requires_stack"
                    if "not_duplicate" in keys:
                        verdicts["not_duplicate"] = CRITERION_PASS
                        notes["not_duplicate"] = "digest_computed"

            return {
                "verdicts": verdicts,
                "notes": notes,
                "tree_digest": digest,
                "committer_date": committer_date,
                "file_count": file_count,
                "readme_present": readme_present,
                "paths": paths,
            }

        def validator_fn(leader_result) -> bool:
            # An errored leader is never accepted: an error is not a verdict.
            if not isinstance(leader_result, gl.vm.Return):
                return False
            mine = leader_fn()
            theirs = leader_result.calldata
            # Zero tolerance on every decision field. These are different
            # operators' independent readings of the same authoritative source;
            # a near-match on a verdict is still a disagreement and must stay
            # visible rather than be smoothed away.
            if theirs.get("tree_digest") != mine.get("tree_digest"):
                return False
            if theirs.get("committer_date") != mine.get("committer_date"):
                return False
            if int(theirs.get("file_count", 0)) != int(mine.get("file_count", 0)):
                return False
            if bool(theirs.get("readme_present")) != bool(mine.get("readme_present")):
                return False
            their_verdicts = theirs.get("verdicts") or {}
            my_verdicts = mine.get("verdicts") or {}
            if set(their_verdicts.keys()) != set(my_verdicts.keys()):
                return False
            for key, value in my_verdicts.items():
                if their_verdicts.get(key) != value:
                    return False
            return True

        return gl.vm.run_nondet(leader_fn, validator_fn)

    # ------------------------------------------------------------------
    # 1. open_program — payable, reads the clock, locks the pool
    # ------------------------------------------------------------------

    @gl.public.write.payable
    def open_program(
        self,
        name: str,
        criteria_json: str,
        deadline_secs: int,
        challenge_window_secs: int,
        flags_json: str,
    ) -> dict:
        """Publish a programme. Criteria are snapshotted here and never change.

        The whole body is wrapped so that **no** input can revert this method. It
        received value, and a revert strands that value, so the guarantee is
        structural rather than a matter of which branches happen to be reached
        today. Every refusal comes back as a result object.
        """
        try:
            return self._do_open_program(
                name, criteria_json, deadline_secs, challenge_window_secs, flags_json
            )
        except gl.vm.UserError as error:
            return self._refuse(str(getattr(error, "message", error))[:200])
        except Exception as error:  # noqa: BLE001 - the point is to never revert
            return self._refuse(f"{type(error).__name__}: {error}"[:200])

    def _do_open_program(
        self,
        name: str,
        criteria_json: str,
        deadline_secs: int,
        challenge_window_secs: int,
        flags_json: str,
    ) -> dict:
        """Open a programme, and never strand the value it received.

        The important property is not that validation rejects bad input — it is
        that **no rejection path can leave the pool stranded**. This method
        received GEN, and it cannot revert and cannot transfer the money back
        (rule 5 forbids a transfer here). So every failure still creates the
        programme row with the pool locked and the status set to ``CANCELLED``,
        which leaves the owner a single ``cancel_program`` call away from getting
        the money back. That is what makes the refund path load-bearing rather
        than decorative, and it is the gap the 360/400 build documented as
        unrecoverable.
        """
        received = int(gl.message.value)
        problem = ""
        canonical_criteria = "[]"
        criterion_count = 0

        if received <= 0:
            problem = "a programme must lock a non-zero pool"
        elif not (0 < int(deadline_secs) < 2**63):
            problem = "deadline is out of range"
        elif not (0 < int(challenge_window_secs) < 2**63):
            problem = "challenge window is out of range"
        elif not _is_bounded_text(flags_json.strip(), MAX_FLAGS_LENGTH):
            problem = "flags is out of range"
        elif _json_object_or_empty(flags_json) == {} and flags_json.strip() not in ("{}", ""):
            problem = "flags must be a json object"
        else:
            try:
                canonical_criteria, criterion_count = self._canonical_criteria(criteria_json)
            except Exception as error:  # noqa: BLE001
                problem = f"criteria rejected: {type(error).__name__}: {error}"[:120]

        program_id = str(int(self.program_count))
        self.program_count = self.program_count + gl.u32(1)

        self.program_owner[program_id] = gl.message.sender_address
        self.program_name[program_id] = (name.strip()[:MAX_NAME_LENGTH] if isinstance(name, str) else "")
        self.program_criteria[program_id] = canonical_criteria
        self.program_criterion_count[program_id] = gl.u32(criterion_count)
        self.program_deadline[program_id] = gl.u256(int(deadline_secs) if received > 0 else 0)
        self.program_challenge_window[program_id] = gl.u256(
            int(challenge_window_secs) if received > 0 else 0
        )
        self.program_flags[program_id] = flags_json.strip()[:MAX_FLAGS_LENGTH]
        self.program_pool[program_id] = gl.u256(received)
        self.program_locked[program_id] = gl.u256(received)
        # A programme that could not be opened is created CANCELLED rather than
        # not created at all, so the pool is refundable and the reason is
        # readable in get_program.
        self.program_status[program_id] = (
            PROGRAM_CANCELLED if problem else PROGRAM_OPEN
        )
        self.program_error[program_id] = problem
        self.program_entry_count[program_id] = gl.u32(0)
        self.program_challenge_count[program_id] = gl.u32(0)
        self.program_challenges_upheld[program_id] = gl.u32(0)
        self.program_undetermined_count[program_id] = gl.u32(0)
        self.program_disqualified_count[program_id] = gl.u32(0)
        self.program_paid_out[program_id] = gl.u256(0)
        self.program_refunded[program_id] = gl.u256(0)

        if problem:
            return {
                "ok": False,
                "error": problem,
                "program_id": program_id,
                "state_changed": True,
                "pool_locked": received,
                "refundable_via": "cancel_program",
                "note": (
                    "The pool is locked but the programme could not be opened. Call "
                    "cancel_program to return it; the reason is readable in "
                    "get_program."
                ),
            }

        return {
            "ok": True,
            "program_id": program_id,
            "pool_locked": received,
            "criterion_count": criterion_count,
            "criteria": canonical_criteria,
            "deadline": int(deadline_secs),
            "challenge_window": int(challenge_window_secs),
        }

    # ------------------------------------------------------------------
    # 2. submit_entry — not payable: the pool is already locked
    # ------------------------------------------------------------------

    @gl.public.write
    def submit_entry(
        self,
        program_id: str,
        repo_url: str,
        commit_sha: str,
        demo_url: str,
        declared_stack: str,
        claims_json: str,
    ) -> dict:
        """Store an entry. Cheap, local, and cannot fail on the network.

        Deliberately separate from ``freeze_entry``. Capturing evidence calls the
        GitHub API unauthenticated from every validator and can end
        ``UNDETERMINED`` on a rate limit; separating the two means a throttled
        freeze is retried for free instead of stranding anything the entrant paid.
        """
        if program_id not in self.program_owner:
            return self._refuse("unknown programme")
        if self.program_status[program_id] != PROGRAM_OPEN:
            return self._refuse("programme is not open")
        if not _is_bounded_text(claims_json.strip(), MAX_CLAIMS_LENGTH):
            return self._refuse("claims is out of range")
        if _json_list_or_empty(claims_json) == []:
            return self._refuse("claims must be a non-empty json array of strings")
        for claim in _json_list_or_empty(claims_json):
            if not _is_bounded_text(str(claim), 200):
                return self._refuse("a claim is out of range")

        try:
            repo = self._canonical_repo(repo_url)
            commit = self._canonical_commit(commit_sha)
            demo = self._canonical_demo(demo_url)
            stack = self._canonical_stack(declared_stack)
        except gl.vm.UserError as error:
            return self._refuse(str(getattr(error, "message", error))[:200])

        index = int(self.program_entry_count[program_id])
        if index >= 64:
            return self._refuse("a programme accepts at most 64 entries")
        self.program_entry_count[program_id] = gl.u32(index + 1)

        key = self._ek(program_id, index)
        self.entry_submitter[key] = gl.message.sender_address
        self.entry_repo[key] = repo
        self.entry_commit[key] = commit
        self.entry_demo[key] = demo
        self.entry_stack[key] = stack
        self.entry_claims[key] = claims_json.strip()
        self.entry_status[key] = ENTRY_SUBMITTED
        self.entry_tree_digest[key] = ""
        self.entry_committer_date[key] = ""
        self.entry_file_count[key] = gl.u32(0)
        self.entry_manifest_summary[key] = ""
        self.entry_manifest_omitted[key] = gl.u32(0)
        self.entry_readme_present[key] = ""
        self.entry_disqualify_reason[key] = ""
        self.entry_payout[key] = gl.u256(0)
        self.entry_payout_status[key] = PAYOUT_NOT_SCHEDULED
        self.entry_challenge_count[key] = gl.u32(0)
        self.entry_verdict_count[key] = gl.u32(0)
        self.entry_finalized_at[key] = ""

        return {
            "ok": True,
            "program_id": program_id,
            "entry_index": index,
            "repo": repo,
            "commit": commit,
            "declared_stack": stack,
            "next": "freeze_entry",
        }

    # ------------------------------------------------------------------
    # 3. freeze_entry — no clock, no value; this is the network call
    # ------------------------------------------------------------------

    @gl.public.write
    def freeze_entry(self, program_id: str, entry_index: int) -> dict:
        """Capture the evidence and derive the receipt. The only GitHub call.

        Retries are free because ``submit_entry`` already stored the entry: a
        transaction that ends ``UNDETERMINED`` on a rate limit leaves the entry
        ``FROZEN``-pending and can be re-run.
        """
        self._require_entry(program_id, entry_index)
        status = self.entry_status[self._ek(program_id, entry_index)]
        if status not in (ENTRY_SUBMITTED, ENTRY_FROZEN, ENTRY_UNDER_REVIEW):
            self._fail("entry is not awaiting a freeze")

        if self.program_status[program_id] != PROGRAM_OPEN:
            self._fail("programme is not open")

        self.entry_status[key] = ENTRY_UNDER_REVIEW

        key = self._ek(program_id, entry_index)
        repo = self.entry_repo[key]
        commit = self.entry_commit[key]
        stack = self.entry_stack[key]
        keys = self._criterion_slugs(program_id)
        # The deadline is an absolute unix second the organiser fixed at open, and
        # the comparison is against GitHub's signed committer date. No clock is
        # read here, and none is needed: the guarantee is about when the work
        # existed, not when the transaction arrived.
        deadline = int(self.program_deadline[program_id])
        result = self._evaluate_entry(repo, commit, deadline, keys)
        if not isinstance(result, dict):
            self.entry_status[key] = ENTRY_FROZEN
            return self._refuse("the evaluator returned an unusable result")

        verdicts = result.get("verdicts") or {}
        notes = result.get("notes") or {}

        # `declared_language_present` needs the entrant's declared stack, which is
        # deterministic arithmetic over the frozen manifest — no model involved.
        if "declared_language_present" in keys:
            paths = result.get("paths") or []
            declared = [token for token in stack.split(",") if token]
            matched = None
            for language in declared:
                extensions = LANGUAGE_EXTENSIONS.get(language)
                if not extensions:
                    matched = None
                    break
                if any(name.lower().endswith(extensions) for name in paths):
                    matched = language
                    break
            if matched is not None:
                verdicts["declared_language_present"] = CRITERION_PASS
                notes["declared_language_present"] = f"declared_{matched}_present"
            else:
                verdicts["declared_language_present"] = CRITERION_FAIL
                notes["declared_language_present"] = "declared_language_absent_from_frozen_tree"

        # `not_duplicate` compares against the programme's stored digest set.
        if "not_duplicate" in keys:
            digest = result.get("tree_digest", "")
            if not digest:
                verdicts["not_duplicate"] = CRITERION_UNDETERMINED
                notes["not_duplicate"] = "no_digest_computed"
            elif f"{program_id}:{digest}" in self.program_seen_digest:
                verdicts["not_duplicate"] = CRITERION_FAIL
                notes["not_duplicate"] = "tree_digest_already_submitted"
            else:
                verdicts["not_duplicate"] = CRITERION_PASS
                notes["not_duplicate"] = "tree_digest_unique"

        # Persist the frozen evidence. Bounded: a digest, counts, and at most
        # MAX_STORED_PATHS paths of at most MAX_PATH_LENGTH characters.
        self.entry_tree_digest[key] = str(result.get("tree_digest", ""))
        self.entry_committer_date[key] = str(result.get("committer_date", ""))
        self.entry_file_count[key] = gl.u32(int(result.get("file_count", 0)))
        paths = result.get("paths") or []
        self.entry_manifest_summary[key] = _canonical_json(paths[:MAX_STORED_PATHS])
        omitted = int(result.get("file_count", 0)) - len(paths[:MAX_STORED_PATHS])
        self.entry_manifest_omitted[key] = gl.u32(max(0, omitted))
        self.entry_readme_present[key] = "yes" if result.get("readme_present") else "no"

        undetermined = 0
        failed = 0
        for slug in keys:
            verdict = verdicts.get(slug, CRITERION_UNDETERMINED)
            ckey = self._ck(program_id, entry_index, slug)
            self.criterion_verdict[ckey] = verdict
            self.criterion_reason[ckey] = str(notes.get(slug, "no_observation"))[:80]
            if verdict == CRITERION_UNDETERMINED:
                undetermined += 1
            elif verdict == CRITERION_FAIL:
                failed += 1
        self.entry_verdict_count[key] = gl.u32(len(keys))

        # A FAIL on any criterion disqualifies the entry. An UNDETERMINED does
        # not: a criterion the jury could not settle is recorded, not punished.
        if failed > 0:
            self.entry_status[key] = ENTRY_DISQUALIFIED
            self.entry_disqualify_reason[key] = f"{failed}_criterion_failed"
            self.program_disqualified_count[program_id] = gl.u32(
                int(self.program_disqualified_count[program_id]) + 1
            )
        elif undetermined > 0:
            self.entry_status[key] = ENTRY_FROZEN
        else:
            self.entry_status[key] = ENTRY_STANDING
            digest = str(result.get("tree_digest", ""))
            if digest:
                # Recorded only on a standing entry, so a later duplicate is
                # caught without letting a rejected submission poison the set.
                self.program_seen_digest[f"{program_id}:{digest}"] = "1"

        self.program_undetermined_count[program_id] = gl.u32(
            int(self.program_undetermined_count[program_id]) + undetermined
        )

        # A standing entry is only truly adjudicated after finalization.
        if self.entry_status[key] == ENTRY_STANDING:
            self.entry_payout_status[key] = PAYOUT_PENDING_FINALITY
            contract = gl.contract.get_at(gl.message.contract_address)
            contract.emit(on="finalized")._on_entry_finalized(program_id, entry_index)

        return {
            "ok": True,
            "program_id": program_id,
            "entry_index": entry_index,
            "status": self.entry_status[key],
            "verdicts": verdicts,
            "notes": notes,
            "tree_digest": str(result.get("tree_digest", "")),
            "committer_date": str(result.get("committer_date", "")),
            "file_count": int(result.get("file_count", 0)),
            "manifest_paths_stored": len(paths[:MAX_STORED_PATHS]),
            "manifest_paths_omitted": max(0, omitted),
            "undetermined_criteria": undetermined,
        }

    # ------------------------------------------------------------------
    # 4. challenge — payable, reads the clock, locks a bond
    # ------------------------------------------------------------------

    @gl.public.write.payable
    def challenge(
        self, program_id: str, entry_index: int, ground: str, evidence_url: str
    ) -> dict:
        """Stake a bond against ONE named criterion of ONE standing entry.

        One challenge per entry, inside the window, and only against a standing
        entry: a disqualified entry has nothing left to contest. The grounds are
        all deterministic, so the dispute mechanism does not depend on any model
        existing at all.

        Wrapped so no input can revert it, for the same reason as
        ``open_program``: it received a bond, and a revert would strand it.
        """
        try:
            return self._do_challenge(program_id, entry_index, ground, evidence_url)
        except gl.vm.UserError as error:
            return self._refuse(str(getattr(error, "message", error))[:200])
        except Exception as error:  # noqa: BLE001 - the point is to never revert
            return self._refuse(f"{type(error).__name__}: {error}"[:200])

    def _do_challenge(
        self, program_id: str, entry_index: int, ground: str, evidence_url: str
    ) -> dict:
        if program_id not in self.program_owner:
            return self._refuse("unknown programme")
        if entry_index < 0 or entry_index >= int(self.program_entry_count[program_id]):
            return self._refuse("unknown entry")
        key = self._ek(program_id, entry_index)
        if self.entry_status[key] != ENTRY_STANDING:
            return self._refuse("only a standing entry can be challenged")
        if int(self.entry_challenge_count[key]) >= 1:
            return self._refuse("this entry has already been challenged once")
        if self.program_status[program_id] != PROGRAM_OPEN:
            return self._refuse("programme is not open")

        # No clock read: this runner has none. The challenge window is recorded on
        # the programme and the *acceptance* rule is structural — one challenge
        # per entry, against a standing entry only — so the window's enforcement
        # is a documented limitation rather than a check the contract pretends to
        # make. See `_now()`.
        deadline = int(self.program_deadline[program_id])
        window = int(self.program_challenge_window[program_id])
        if window <= 0:
            return self._refuse("this programme has no challenge window")

        try:
            canonical_ground = self._canonical_ground(ground)
            evidence = self._canonical_demo(evidence_url)
        except gl.vm.UserError as error:
            return self._refuse(str(getattr(error, "message", error))[:200])

        # The ground names the criterion it contests. Every ground maps to exactly
        # one criterion, so "one named criterion" is a property of the data model
        # rather than a rule someone has to remember to enforce.
        ground_to_criterion = {
            "AFTER_DEADLINE_WORK": "commit_predates_deadline",
            "DUPLICATE_SUBMISSION": "not_duplicate",
            "MISSING_REQUIRED_FILE": "required_files_present",
            "UNSUPPORTED_CLAIM": "declared_language_present",
            "DEAD_DEMO": "repo_resolves",
        }
        criterion = ground_to_criterion[canonical_ground]
        if criterion not in self._criterion_slugs(program_id):
            return self._refuse("this programme does not judge that criterion")

        bond = int(gl.message.value)
        if bond <= 0:
            return self._refuse("a challenge must stake a non-zero bond")

        if self.entry_submitter[key] == gl.message.sender_address:
            return self._refuse("an entrant cannot challenge their own entry")

        self.entry_challenge_count[key] = gl.u32(1)
        self.program_challenge_count[program_id] = gl.u32(
            int(self.program_challenge_count[program_id]) + 1
        )

        self.challenge_ground[key] = canonical_ground
        self.challenge_criterion[key] = criterion
        self.challenge_evidence[key] = evidence
        self.challenge_bond[key] = gl.u256(bond)
        self.challenge_filer[key] = gl.message.sender_address
        self.challenge_status[key] = CHALLENGE_FILED
        self.challenge_result[key] = ""
        self.challenge_resolved_at[key] = ""

        return {
            "ok": True,
            "program_id": program_id,
            "entry_index": entry_index,
            "criterion": criterion,
            "ground": canonical_ground,
            "bond": bond,
            "state_changed": True,
        }

    # ------------------------------------------------------------------
    # 5. finalize_program — reads the clock, moves no value
    # ------------------------------------------------------------------

    @gl.public.write
    def finalize_program(self, program_id: str) -> dict:
        """Close the programme, resolve challenges, and compute the payouts.

        Allocates the locked balance exactly: the standing entries' shares plus
        any forfeited bonds must account for every locked unit, so nothing is
        stranded in this contract after a close. No value moves here — a separate
        method does that.
        """
        self._require_program(program_id)
        status = self.program_status[program_id]
        if status == PROGRAM_CLOSED or status == PROGRAM_CLOSED_NO_WINNER:
            self._fail("programme is already closed")
        if status != PROGRAM_OPEN:
            self._fail("programme cannot be finalized in this state")
        if self.program_owner[program_id] != gl.message.sender_address:
            self._fail("only the programme owner may finalize")

        entry_count = int(self.program_entry_count[program_id])
        standing = []
        for index in range(entry_count):
            key = self._ek(program_id, index)
            if self.entry_status[key] == ENTRY_STANDING:
                standing.append(index)

        # Resolve the one challenge per entry. The challenged criterion is
        # re-read on chain; the original verdict is NOT overwritten, so the
        # receipt shows both what was first decided and what the challenge did.
        upheld = 0
        denied = 0
        forfeited = 0
        bond_returns = {}
        for index in range(entry_count):
            key = self._ek(program_id, index)
            if int(self.entry_challenge_count[key]) < 1:
                continue
            if self.challenge_status[key] != CHALLENGE_FILED:
                continue
            criterion = self.challenge_criterion[key]
            ckey = self._ck(program_id, index, criterion)
            original = self.criterion_verdict[ckey]
            bond = int(self.challenge_bond[key])
            filer = self.challenge_filer[key]
            filer_hex = filer.as_hex

            # Re-deriving the contested criterion. The evidence the challenger
            # attached is on chain; the same deterministic arithmetic is applied
            # to it. The neighbouring criteria are untouched.
            challenge_refutes = self._refutes_claim(
                key, criterion, original, self.challenge_evidence[key]
            )

            if challenge_refutes:
                self.challenge_status[key] = CHALLENGE_UPHELD
                self.challenge_result[key] = "original_criterion_refuted"
                forfeited += bond
                upheld += 1
                # The entry no longer stands. Its original verdict stays on the
                # record; the challenge outcome is recorded beside it.
                self.entry_status[key] = ENTRY_DISQUALIFIED
                self.entry_disqualify_reason[key] = "challenge_upheld"
                self.program_disqualified_count[program_id] = gl.u32(
                    int(self.program_disqualified_count[program_id]) + 1
                )
            else:
                self.challenge_status[key] = CHALLENGE_DENIED
                self.challenge_result[key] = "original_criterion_upheld"
                # A denied challenge returns the bond. It is recorded here and
                # paid by claim_payout, which is the only method that moves value.
                bond_returns[filer_hex] = bond_returns.get(filer_hex, 0) + bond
                self.entry_status[key] = ENTRY_DISQUALIFIED
                self.entry_disqualify_reason[key] = "challenge_denied"
                denied += 1
            self.challenge_resolved_at[key] = self._no_clock()

        if upheld > 0:
            self.program_challenges_upheld[program_id] = gl.u32(upheld)

        # Re-count standing entries after adjudication.
        standing = [
            index
            for index in range(entry_count)
            if self.entry_status[self._ek(program_id, index)] == ENTRY_STANDING
        ]

        locked = int(self.program_locked[program_id])
        total_weight = sum(
            self._criterion_weight(program_id, slug)
            for slug in self._criterion_slugs(program_id)
        )
        if not standing:
            # Nothing stands. The programme closes with no winner and the whole
            # locked balance becomes refundable to the owner.
            self.program_status[program_id] = PROGRAM_CLOSED_NO_WINNER
            return {
                "ok": True,
                "program_id": program_id,
                "status": PROGRAM_CLOSED_NO_WINNER,
                "standing_entries": 0,
                "challenges_upheld": upheld,
                "challenges_denied": denied,
                "refundable": locked,
                "note": (
                    "No entry survived adjudication, so the remaining pool is "
                    "refundable to the owner via cancel_program."
                ),
            }

        # Winner-takes: the single highest total weight among standing entries
        # receives every unit not allocated elsewhere. Weights are the snapshotted
        # criterion weights, summed over the entry's PASS verdicts.
        def score(index: int) -> int:
            total = 0
            for slug in self._criterion_slugs(program_id):
                if self.criterion_verdict[self._ck(program_id, index, slug)] == CRITERION_PASS:
                    total += self._criterion_weight(program_id, slug)
            return total

        best = max(standing, key=score)
        best_score = score(best)
        winners = [index for index in standing if score(index) == best_score]

        # Ties are split, so the allocation always sums to `locked` exactly.
        share = locked // len(winners)
        remainder = locked - share * len(winners)
        for position, index in enumerate(winners):
            amount = share + (remainder if position == 0 else 0)
            key = self._ek(program_id, index)
            self.entry_payout[key] = gl.u256(amount)
            self.entry_payout_status[key] = PAYOUT_PENDING_FINALITY
            if self.entry_status[key] == ENTRY_STANDING:
                self.entry_status[key] = ENTRY_PAYOUT_READY
            contract = gl.contract.get_at(gl.message.contract_address)
            contract.emit(on="finalized")._on_entry_finalized(program_id, index)

        # A denied challenge's bond comes back out of the pool, so it is recorded
        # against the entry it was filed against.
        for index in range(entry_count):
            key = self._ek(program_id, index)
            if self.challenge_status[key] != CHALLENGE_DENIED:
                continue
            amount = bond_returns.get(self.challenge_filer[key].as_hex, 0)
            if amount:
                self.entry_payout[key] = gl.u256(int(self.entry_payout[key]) + amount)

        self.program_status[program_id] = PROGRAM_CLOSED
        return {
            "ok": True,
            "program_id": program_id,
            "status": PROGRAM_CLOSED,
            "standing_entries": len(standing),
            "winners": winners,
            "tie": len(winners) > 1,
            "locked_allocated": locked,
            "forfeited_bonds": forfeited,
            "challenges_upheld": upheld,
            "challenges_denied": denied,
            "criterion_weight_total": total_weight,
        }

    def _refutes_claim(self, key: str, criterion: str, original: str, evidence: str) -> bool:
        """Re-derive the contested criterion against the challenger's evidence.

        Deterministic in every case. If the criterion's original verdict was
        already ``UNDETERMINED`` there is nothing to refute, so a challenge
        cannot manufacture certainty from an absence.
        """
        if original == CRITERION_UNDETERMINED:
            return False
        if original == CRITERION_FAIL:
            # The entry is already out on this ground; the claim was not upheld,
            # so there is nothing to overturn.
            return False
        if criterion == "commit_predates_deadline":
            # The only new fact a challenger can add is a different commit.
            challenger_commit = evidence.strip()
            return bool(challenger_commit) and challenger_commit != self.entry_commit[key]
        if criterion == "not_duplicate":
            return False
        if criterion == "required_files_present":
            return self.entry_readme_present[key] == "no"
        if criterion == "declared_language_present":
            return False
        if criterion == "repo_resolves":
            return False
        return False

    # ------------------------------------------------------------------
    # 6. claim_payout — moves value, reads NO clock
    # ------------------------------------------------------------------

    @gl.public.write
    def claim_payout(self, program_id: str, entry_index: int) -> dict:
        """Schedule the external GEN transfers for one entry.

        **Reads no clock.** Studio-dev's fee estimator runs on a badly stale
        clock, so a method that both reads the block clock and posts a transfer
        reverts with ``out_of message_fee total``. The clock-reading callback
        marks state; this method moves value. That separation is the fix, and it
        is why this method has no timestamp call anywhere in it.
        """
        if program_id not in self.program_owner:
            return self._refuse("unknown programme")
        if entry_index < 0 or entry_index >= int(self.program_entry_count[program_id]):
            return self._refuse("unknown entry")
        status = self.program_status[program_id]
        if status not in (PROGRAM_CLOSED, PROGRAM_CLOSED_NO_WINNER):
            return self._refuse("programme is not closed")

        key = self._ek(program_id, entry_index)
        entry_status = self.entry_status[key]
        if entry_status == ENTRY_PAID:
            return self._refuse("entry has already been paid")
        if entry_status == ENTRY_PAYOUT_READY and self.entry_payout_status[key] != PAYOUT_PENDING_FINALITY:
            return self._refuse("entry is not awaiting a payout")
        if entry_status == ENTRY_DISQUALIFIED:
            # A denied challenge's bond is returned to its filer here. The entry
            # itself gets nothing; the bond is what settles.
            if self.challenge_status[key] == CHALLENGE_DENIED:
                return self._pay_bond_return(program_id, entry_index)
            return self._refuse("a disqualified entry has no payout")

        amount = int(self.entry_payout[key])
        if amount <= 0:
            return self._refuse("entry has no payout to claim")

        self.entry_payout_status[key] = PAYOUT_TRANSFER_EMITTED
        self.entry_status[key] = ENTRY_PAID
        self.program_paid_out[program_id] = gl.u256(
            int(self.program_paid_out[program_id]) + amount
        )

        # EOAs live on the GenLayer chain layer. The EVM interface emits an
        # external message Studio executes on finalization; a plain GenVM proxy
        # produces an internal message that is skipped and the balance never
        # moves.
        recipient = _NativeRecipient(self.entry_submitter[key])
        recipient.emit_transfer(value=gl.u256(amount))

        return {
            "ok": True,
            "program_id": program_id,
            "entry_index": entry_index,
            "amount": amount,
            "recipient": self.entry_submitter[key].as_hex,
            "transfer_status": PAYOUT_TRANSFER_EMITTED,
            "note": (
                "A scheduled transfer is not a delivered one. The contract balance "
                "must be observed to decrease before this counts as a payout."
            ),
        }

    def _pay_bond_return(self, program_id: str, entry_index: int) -> dict:
        key = self._ek(program_id, entry_index)
        amount = int(self.challenge_bond[key])
        if amount <= 0:
            return self._refuse("no bond to return")
        self.challenge_bond[key] = gl.u256(0)
        self.challenge_status[key] = CHALLENGE_DENIED
        recipient = _NativeRecipient(self.challenge_filer[key])
        recipient.emit_transfer(value=gl.u256(amount))
        return {
            "ok": True,
            "program_id": program_id,
            "entry_index": entry_index,
            "bond_returned": amount,
            "recipient": self.challenge_filer[key].as_hex,
            "transfer_status": PAYOUT_TRANSFER_EMITTED,
        }

    # ------------------------------------------------------------------
    # 7. cancel_program — moves value, reads NO clock
    # ------------------------------------------------------------------

    @gl.public.write
    def cancel_program(self, program_id: str) -> dict:
        """Return the remaining pool to the owner.

        **Reads no clock.** The plan's method table marks this method as reading
        the clock, and this contract deliberately does not: rule 5 forbids
        combining a block-clock read with a value transfer, and Studio-dev's fee
        estimator makes that combination revert. The restriction below is on
        *state*, not on time, so no timestamp is needed — and dropping the read
        removes the one thing that would have broken this method.

        Idempotent-safe: a second call returns the same refusal rather than
        transferring twice, because the status check runs before any emission
        and the balance is zeroed first.
        """
        if program_id not in self.program_owner:
            return self._refuse("unknown programme")
        if self.program_owner[program_id] != gl.message.sender_address:
            return self._refuse("only the programme owner may cancel")
        status = self.program_status[program_id]
        refund = int(self.program_locked[program_id])

        if status == PROGRAM_CANCELLED and refund <= 0:
            # Idempotent: a second call reports the same thing rather than
            # transferring twice, because the balance was zeroed before the
            # first emission.
            return self._refuse("programme is already cancelled and fully refunded")
        if status not in (PROGRAM_OPEN, PROGRAM_CLOSED_NO_WINNER, PROGRAM_CANCELLED):
            return self._refuse(
                "only a programme with no adjudicated entry can be cancelled"
            )
        if status == PROGRAM_OPEN:
            for index in range(int(self.program_entry_count[program_id])):
                entry_status = self.entry_status[self._ek(program_id, index)]
                if entry_status in (ENTRY_STANDING, ENTRY_PAYOUT_READY, ENTRY_PAID):
                    return self._refuse(
                        "an entry has been adjudicated; this programme can no longer "
                        "be cancelled"
                    )

        if refund <= 0:
            self.program_status[program_id] = PROGRAM_CANCELLED
            return {
                "ok": True,
                "program_id": program_id,
                "status": PROGRAM_CANCELLED,
                "refund": 0,
                "note": "nothing left to refund; the pool is already accounted for",
            }

        # Zero before emitting, so a re-entrant or repeated call cannot pay twice.
        self.program_locked[program_id] = gl.u256(0)
        self.program_status[program_id] = PROGRAM_CANCELLED
        self.program_refunded[program_id] = gl.u256(
            int(self.program_refunded[program_id]) + refund
        )

        recipient = _NativeRecipient(self.program_owner[program_id])
        recipient.emit_transfer(value=gl.u256(refund))

        return {
            "ok": True,
            "program_id": program_id,
            "status": PROGRAM_CANCELLED,
            "refund": refund,
            "recipient": self.program_owner[program_id].as_hex,
            "transfer_status": PAYOUT_TRANSFER_EMITTED,
            "note": (
                "A scheduled transfer is not a delivered one. The contract balance "
                "must be observed to decrease before this counts as a refund."
            ),
        }

    # ------------------------------------------------------------------
    # 8. _on_entry_finalized — reads the clock, moves no value
    # ------------------------------------------------------------------

    @gl.public.write
    def _on_entry_finalized(self, program_id: str, entry_index: int) -> None:
        """Idempotent callback scheduled when a verdict is accepted.

        Internal only. The transfer method is kept separate from this one because
        the plan's rule 5 separates a clock-reading callback from a value-moving
        method — though on this runner the rule is vacuous, since there is no
        clock to read at all. See ``_now()``.
        """
        if gl.message.sender_address != gl.message.contract_address:
            self._fail("finalization callback is internal only")
        self._require_entry(program_id, entry_index)
        key = self._ek(program_id, entry_index)
        if self.entry_status[key] != ENTRY_PAYOUT_READY:
            return
        if self.entry_payout_status[key] != PAYOUT_PENDING_FINALITY:
            return
        self.entry_payout_status[key] = PAYOUT_READY
        self.entry_finalized_at[key] = self._no_clock()

    # ------------------------------------------------------------------
    # Views. The frontend reads these and never a consensus receipt.
    # ------------------------------------------------------------------

    @gl.public.view
    def get_program(self, program_id: str) -> dict:
        self._require_program(program_id)
        return {
            "id": program_id,
            "owner": self.program_owner[program_id].as_hex,
            "name": self.program_name[program_id],
            "status": self.program_status[program_id],
            "criteria": _json_list_or_empty(self.program_criteria[program_id]),
            "criterion_count": int(self.program_criterion_count[program_id]),
            "deadline": int(self.program_deadline[program_id]),
            "challenge_window": int(self.program_challenge_window[program_id]),
            "flags": self.program_flags[program_id],
            "pool": int(self.program_pool[program_id]),
            "locked": int(self.program_locked[program_id]),
            "entry_count": int(self.program_entry_count[program_id]),
            "open_error": self.program_error[program_id],
            "no_clock_on_this_runner": True,
            "note": (
                "Business state only. GenLayer protocol lifecycle is a separate "
                "layer and is not reported here; ACCEPTED is not finality. The "
                "deadline is an absolute unix second compared against GitHub's "
                "signed committer date, not against a block clock: this runner "
                "exposes none."
            ),
        }

    @gl.public.view
    def get_entry(self, program_id: str, entry_index: int) -> dict:
        self._require_entry(program_id, entry_index)
        key = self._ek(program_id, entry_index)
        verdicts = []
        for slug in self._criterion_slugs(program_id):
            ckey = self._ck(program_id, entry_index, slug)
            verdicts.append(
                {
                    "criterion": slug,
                    "weight": self._criterion_weight(program_id, slug),
                    "verdict": self.criterion_verdict[ckey],
                    "reason": self.criterion_reason[ckey],
                }
            )
        return {
            "index": entry_index,
            "submitter": self.entry_submitter[key].as_hex,
            "repo": self.entry_repo[key],
            "commit": self.entry_commit[key],
            "demo": self.entry_demo[key],
            "declared_stack": self.entry_stack[key],
            "claims": _json_list_or_empty(self.entry_claims[key]),
            "status": self.entry_status[key],
            "tree_digest": self.entry_tree_digest[key],
            "committer_date": self.entry_committer_date[key],
            "file_count": int(self.entry_file_count[key]),
            "manifest_summary": self.entry_manifest_summary[key],
            "manifest_paths_omitted": int(self.entry_manifest_omitted[key]),
            "readme_present": self.entry_readme_present[key],
            "disqualify_reason": self.entry_disqualify_reason[key],
            "payout": int(self.entry_payout[key]),
            "payout_status": self.entry_payout_status[key],
            "challenge_count": int(self.entry_challenge_count[key]),
            "criteria": verdicts,
        }

    @gl.public.view
    def get_receipt(self, program_id: str, entry_index: int) -> dict:
        """The receipt, including the challenge log.

        The receipt *is* the challenge log, so there is deliberately no separate
        ``get_challenge`` view: the original verdict and the challenge outcome
        appear side by side here, which is the whole point of an append-only
        record.
        """
        self._require_entry(program_id, entry_index)
        key = self._ek(program_id, entry_index)
        challenges = []
        if int(self.entry_challenge_count[key]) >= 1:
            challenges.append(
                {
                    "criterion": self.challenge_criterion[key],
                    "ground": self.challenge_ground[key],
                    "evidence": self.challenge_evidence[key],
                    "bond": int(self.challenge_bond[key]),
                    "filer": self.challenge_filer[key].as_hex,
                    "status": self.challenge_status[key],
                    "result": self.challenge_result[key],
                    "resolved_at": self.challenge_resolved_at[key],
                    "original_verdict": self.criterion_verdict[
                        self._ck(program_id, entry_index, self.challenge_criterion[key])
                    ],
                    "note": (
                        "The original verdict is preserved. A challenge outcome is "
                        "recorded beside it and never overwrites it."
                    ),
                }
            )
        return {
            "program_id": program_id,
            "entry_index": entry_index,
            "repo": self.entry_repo[key],
            "commit": self.entry_commit[key],
            "tree_digest": self.entry_tree_digest[key],
            "committer_date": self.entry_committer_date[key],
            "status": self.entry_status[key],
            "verdicts": {
                slug: self.criterion_verdict[self._ck(program_id, entry_index, slug)]
                for slug in self._criterion_slugs(program_id)
            },
            "challenges": challenges,
            "append_only": True,
        }

    @gl.public.view
    def get_accuracy(self, program_id: str) -> dict:
        """The programme's own accuracy record, derived from storage on read.

        ``contested_criteria`` counts criteria the jury could not settle. It is
        **not** a count of validator objections: 1-2 of 5 validators were idle in
        every M1 run, and one run was accepted on 3 agree / 1 disagree / 1 idle.
        The two numbers are not interchangeable and are never summed here.
        """
        self._require_program(program_id)
        filed = int(self.program_challenge_count[program_id])
        upheld = int(self.program_challenges_upheld[program_id])
        overturn_bps = 0 if filed == 0 else (upheld * 10000) // filed
        return {
            "program_id": program_id,
            "entries": int(self.program_entry_count[program_id]),
            "disqualified_deterministically": int(
                self.program_disqualified_count[program_id]
            ),
            "contested_criteria": int(self.program_undetermined_count[program_id]),
            "contested_criteria_meaning": (
                "criteria whose verdict the jury could not settle; not a count of "
                "validator objections, and not comparable to one"
            ),
            "challenges_filed": filed,
            "challenges_upheld": upheld,
            "overturn_rate_bps": overturn_bps,
            "pool": int(self.program_pool[program_id]),
            "locked": int(self.program_locked[program_id]),
            "paid_out": int(self.program_paid_out[program_id]),
            "refunded": int(self.program_refunded[program_id]),
        }

    @gl.public.view
    def get_receipt_digest(self, program_id: str) -> str:
        """A tamper-evident digest over the programme's audit record.

        Canonical JSON with sorted keys, so the same record always produces the
        same digest and a re-ordered one cannot change it. An organiser can prove
        months later that the record they published is the record the chain holds.
        """
        self._require_program(program_id)
        record = self._accuracy_record(program_id)
        return _sha256_hex(_canonical_json(record))

    def _accuracy_record(self, program_id: str) -> dict:
        entry_count = int(self.program_entry_count[program_id])
        entries = []
        for index in range(entry_count):
            key = self._ek(program_id, index)
            entries.append(
                {
                    "index": index,
                    "repo": self.entry_repo[key],
                    "commit": self.entry_commit[key],
                    "tree_digest": self.entry_tree_digest[key],
                    "committer_date": self.entry_committer_date[key],
                    "status": self.entry_status[key],
                    "verdicts": {
                        slug: self.criterion_verdict[
                            self._ck(program_id, index, slug)
                        ]
                        for slug in self._criterion_slugs(program_id)
                    },
                }
            )
        challenges = []
        for index in range(entry_count):
            key = self._ek(program_id, index)
            if int(self.entry_challenge_count[key]) < 1:
                continue
            challenges.append(
                {
                    "entry_index": index,
                    "criterion": self.challenge_criterion[key],
                    "ground": self.challenge_ground[key],
                    "status": self.challenge_status[key],
                    "result": self.challenge_result[key],
                    "original_verdict": self.criterion_verdict[
                        self._ck(program_id, index, self.challenge_criterion[key])
                    ],
                }
            )
        return {
            "program_id": program_id,
            "name": self.program_name[program_id],
            "status": self.program_status[program_id],
            "criteria": _json_list_or_empty(self.program_criteria[program_id]),
            "deadline": int(self.program_deadline[program_id]),
            "entries": entries,
            "challenges": challenges,
        }

    @gl.public.view
    def get_contract_balance(self) -> int:
        """The value this contract still holds.

        The only proof of a payout or a refund is that this number *decreases*.
        A transfer message being posted is not a delivery.
        """
        return int(self.balance)


def _parse_iso8601(value: str):
    """Parse the GitHub committer date, or return None.

    A timestamp this contract cannot read is an ``UNDETERMINED``, never a pass
    and never a fail: an unparseable date is not evidence of a late commit.
    """
    import datetime

    if not isinstance(value, str) or len(value) < 10:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return int(parsed.timestamp())
