# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }

"""M1 consensus spike — throwaway. Not the product.

Purpose: measure whether validators converge on one subjective criterion over
three real repositories, so ``IMPLEMENTATION-PLAN.md`` §5 M1 can decide between
a 2-bucket and a 3-bucket comparison mode before M3 writes any real contract.

The single question asked per repository:

    Does this repository's own README describe a working product that is
    consistent with the repository at the pinned commit?

The answer is one of three buckets:

    CONSISTENT     the README describes something the repo actually contains
    INCONSISTENT   the README claims something the repo does not contain
    INCONCLUSIVE   the README could not be read, so there is nothing to judge

The spike records, per run: whether consensus held, how long it took, which
bucket the network accepted, and the per-validator vote split when the record
exposes it. It does **not** move value, read a clock, or implement any
workflow. It exists to answer one question with a number.

Deliberate design choices that matter for the decision this feeds:

* The bucket is the only consensus-critical field. It is compared with zero
  tolerance. Free-form reasoning is stored but never compared, because a fuzzy
  band on prose would hide exactly the disagreement the product exists to keep.
* ``INCONCLUSIVE`` is a real answer, not an error. A missing or unreadable
  README produces it, and it is not a verdict. Silence is never evidence.
* The validator re-derives the bucket itself rather than judging the leader's
  prose, following the equivalence principle's default pattern. A validator
  that only checked the leader's JSON shape would not be performing consensus.
* Failures are returned as values, not raised. The spike is a measurement
  instrument; a revert would destroy the observation it exists to produce.
"""

import json

import genlayer as gl

MAX_README_BYTES = 200_000

BUCKET_CONSISTENT = "CONSISTENT"
BUCKET_INCONSISTENT = "INCONSISTENT"
BUCKET_INCONCLUSIVE = "INCONCLUSIVE"
BUCKETS = (BUCKET_CONSISTENT, BUCKET_INCONSISTENT, BUCKET_INCONCLUSIVE)

#: The repository's own README at the pinned commit. The commit SHA is part of
#: the URL, so this is a point-in-time read of that exact tree: an entrant
#: cannot polish a README into existence after the deadline, because the URL
#: would then point at a different commit.
README_HOST = "raw.githubusercontent.com"

PANEL_PROMPT = """You are checking one narrow claim about a software repository.

The repository's own README file, taken at a pinned commit, is below.

QUESTION: Does this README describe a working product that is consistent with
what the repository actually contains?

Answer with exactly one verdict:
- CONSISTENT: the README describes something a reader would find in this repo.
- INCONSISTENT: the README makes a specific claim about this repo that the
  repository does not support.

Rules:
- Judge only what the README states and what the repository plausibly contains.
  Do not penalise a README for being brief, for marketing language, or for
  omitting features.
- If the README is empty, unreadable, or contains no substantive description,
  answer INCONCLUSIVE.
- Return JSON only, no prose, no code fences:
  {{"bucket": "CONSISTENT" | "INCONSISTENT" | "INCONCLUSIVE", "confidence": <1-10>}}

README:
---
{readme}
---
"""


def _readme_url(repo_url: str, commit_sha: str) -> str:
    return f"https://{README_HOST}/{repo_url}/{commit_sha}/README.md"


def _response_status(response) -> int:
    status = getattr(response, "status_code", None)
    if status is None:
        status = getattr(response, "status", 0)
    try:
        return int(status)
    except (TypeError, ValueError):
        return 0


def _response_text(response) -> str:
    body = getattr(response, "body", b"")
    if isinstance(body, bytes):
        if len(body) > MAX_README_BYTES:
            return ""
        return body.decode("utf-8", errors="replace")
    if isinstance(body, str):
        if len(body.encode("utf-8")) > MAX_README_BYTES:
            return ""
        return body
    return ""


def _normalize_bucket(value) -> str:
    """Coerce a model answer to a known bucket, or to INCONCLUSIVE.

    An unrecognised answer is never coerced into a verdict. An answer the model
    could not form is not evidence, and treating it as one would put a number in
    the receipt that no validator actually agreed to.
    """
    if not isinstance(value, str):
        return BUCKET_INCONCLUSIVE
    candidate = value.strip().upper()
    for bucket in BUCKETS:
        if candidate == bucket:
            return bucket
    return BUCKET_INCONCLUSIVE


def _normalize_confidence(value) -> int:
    try:
        confidence = int(value)
    except (TypeError, ValueError):
        return 0
    if confidence < 1:
        return 1
    if confidence > 10:
        return 10
    return confidence


def _undecided(reason: str) -> dict:
    """A result that records why there is no verdict. Never a bucket."""
    return {
        "bucket": BUCKET_INCONCLUSIVE,
        "confidence": 0,
        "reason": reason,
        "readme_bytes": 0,
    }


class M1PanelSpike(gl.contract.Contract):
    """One subjective criterion, run over real repositories, measured."""

    run_count: gl.u32
    last_repo: gl.storage.TreeMap[str, str]
    last_commit: gl.storage.TreeMap[str, str]
    last_bucket: gl.storage.TreeMap[str, str]
    last_confidence: gl.storage.TreeMap[str, gl.u32]
    last_reason: gl.storage.TreeMap[str, str]
    last_readme_bytes: gl.storage.TreeMap[str, gl.u32]

    def __init__(self):
        self.run_count = gl.u32(0)

    def _answer(self, repo_url: str, commit_sha: str) -> dict:
        """Re-derive the bucket from the repository's own README.

        Called by the leader and, independently, by every validator. Only the
        bucket is consensus-critical; ``confidence`` and ``reason`` are recorded
        for the log and are not compared.
        """

        def leader_fn() -> dict:
            readme_url = _readme_url(repo_url, commit_sha)
            response = gl.nondet.web.get(readme_url)
            status = _response_status(response)
            # Only 404 means the README is not there. A 403, 429 or 5xx means
            # this node could not ask the question, which is not the same as
            # the answer being "inconsistent".
            if status == 404:
                return _undecided("readme_missing")
            if status != 200:
                return _undecided("readme_source_unavailable")

            readme = _response_text(response)
            if not readme.strip():
                return _undecided("readme_empty")

            prompt = PANEL_PROMPT.replace("{readme}", readme)
            raw = gl.nondet.exec_prompt(prompt)
            try:
                payload = json.loads(raw)
            except (TypeError, ValueError):
                return _undecided("model_answer_not_json")
            if not isinstance(payload, dict):
                return _undecided("model_answer_shape_invalid")

            return {
                "bucket": _normalize_bucket(payload.get("bucket")),
                "confidence": _normalize_confidence(payload.get("confidence")),
                "reason": "model_bucket_normalized",
                "readme_bytes": len(readme),
            }

        def validator_fn(leader_result) -> bool:
            # An error is not a bucket, so an errored leader is never accepted.
            if not isinstance(leader_result, gl.vm.Return):
                return False
            mine = leader_fn()
            # Zero tolerance on the bucket. The two answer sets are different
            # models' readings of the same document, so a near-match is still a
            # disagreement and must be visible rather than smoothed.
            return leader_result.calldata.get("bucket") == mine.get("bucket")

        return gl.vm.run_nondet(leader_fn, validator_fn)

    @gl.public.write
    def run_panel(self, repo_url: str, commit_sha: str) -> dict:
        """Run the criterion once and record what the network accepted.

        The accepted result is written to storage as well as returned, so the
        bucket is readable on chain through ``get_last_run`` rather than only
        inferable by decoding a consensus receipt. The milestone's deliverable
        is a number a reviewer can check, and a receipt that has to be
        hand-decoded is a weaker deliverable than a stored value.

        A caller that gets ``INCONCLUSIVE`` has learned that the jury did not
        agree, which is the finding the milestone exists to produce.
        """
        result = self._answer(repo_url, commit_sha)
        if not isinstance(result, dict):
            result = _undecided("evaluator_result_invalid")

        key = str(int(self.run_count))
        self.run_count = self.run_count + gl.u32(1)
        self.last_repo[key] = repo_url
        self.last_commit[key] = commit_sha
        self.last_bucket[key] = str(result.get("bucket", BUCKET_INCONCLUSIVE))
        self.last_confidence[key] = gl.u32(int(result.get("confidence", 0)))
        self.last_reason[key] = str(result.get("reason", "unknown"))
        self.last_readme_bytes[key] = gl.u32(int(result.get("readme_bytes", 0)))
        return result

    @gl.public.view
    def get_last_run(self) -> dict:
        """The most recent accepted result, read back from storage."""
        count = int(self.run_count)
        if count == 0:
            return {"runs": 0, "bucket": BUCKET_INCONCLUSIVE, "reason": "no_run_yet"}
        key = str(count - 1)
        return {
            "runs": count,
            "index": count - 1,
            "repo": self.last_repo[key],
            "commit": self.last_commit[key],
            "bucket": self.last_bucket[key],
            "confidence": int(self.last_confidence[key]),
            "reason": self.last_reason[key],
            "readme_bytes": int(self.last_readme_bytes[key]),
        }
