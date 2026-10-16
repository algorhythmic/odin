# OptChat cache-fix inspection

Inspected 2026-10-15 through GitHub's public Gist API. This is source review
and a small arithmetic check, not an Odin runtime or provider-cache test.

## Source identity

- Before: [revision f51fe5c](https://gist.github.com/VictorTaelin/91837951a5ce5b38f341ec1ba1df6449/f51fe5c910427fd6f384d22823140b1693c76207),
  2026-10-04, `optchat.md`, SHA-256
  `8f6997e8944d85e4df53b5704bf7c4e393e4da361071181e9cc2f7d9d1b6e430`.
- Corrected: [revision 3c190e0](https://gist.github.com/VictorTaelin/91837951a5ce5b38f341ec1ba1df6449/3c190e06f34aba0c69f49042c526093269604935),
  2026-10-08 01:58:24 UTC, `optchat.md`, SHA-256
  `12f300f760af82bc07bc5201051d1267824ded09c9def8186e4f8144368038d8`.
  GitHub's corresponding raw-file URL uses content revision
  `4c09901baa3685852bf252cdb70ace81d01d6be5`; it is distinct from the
  Gist history revision above. Current content matched the corrected file.
- The author's [comment 6413482](https://gist.github.com/VictorTaelin/91837951a5ce5b38f341ec1ba1df6449?permalink_comment_id=6413482#gistcomment-6413482),
  2026-10-08 01:59:25 UTC, confirms multiple fixes including cache damage.
  It does not attribute all damage to a single changed line. The revision
  is a broad rewrite, not a standalone implementation patch.

## Changes relevant to caching

Comparing the two recipes identifies these changes:

| Concern | Earlier recipe | Corrected recipe |
|---|---|---|
| Merge priority | Age measured from a sibling pair's first message | Measure from its last message |
| Merge timing | Fit whenever the fixed view budget is exceeded | Grow past 128,000 bytes, then shrink toward 64,000 in a batch |
| Restart | Reconstruct view membership by replaying the log | Persist and restore the selected view |
| Cache layout | Character-offset breakpoints | Four-line blocks and request-end marking; coordinate concurrent prefix writes |
| Compaction | Separate prompt and large context view | Shared turn prompt/tools and a smaller, persistent compaction context view |

The revised recipe's 98.6% turn and 96.2% compaction cache-read figures are
results from a cache-model replay, not independently measured Odin traffic.

## Deterministic counterexample

Let `T` be the message count, `s = 2^l` the child span, and `i` the even
index of the left sibling. The pair ends at `last = (i + 2) * s - 1`.

```text
old priority       = (T - i*s) / (4*s)
corrected priority = (T - last) / s
equivalent ranking = (T + 1) / s - i
```

The last expression exceeds the corrected priority by a constant 2, so
their order agrees. Removing the old denominator's factor 4 alone cannot
fix the ranking: that scales every candidate equally.

At `T=10`, consider view `0+4, 4+4, 8+1, 9+1`, with both parents built:

| Candidate merge | Old priority | Corrected priority |
|---|---|---|
| Messages 0–7 | 5/8 | 3/4 |
| Messages 8–9 | 1/2 | 1 |

The old rule changes the beginning of the view; the corrected rule keeps
its first two lines and merges the newest pair. An isolated Python check
using exact fractions reproduced this choice and verified the constant-2
identity for every complete sibling pair through `T=200`. This establishes
the arithmetic, not the gist's broader performance claims.

## Application to Odin

Odin's contract already specifies batching, persisted view selection and
ready-node queues. Make the corrected priority explicit so implementation
cannot accidentally follow the older formula. Preserve selected node ids,
order and in-progress batch state transactionally; regenerating `view.json`
must render that state rather than choose a new view from the log. Planned
I2 checks should cover the counterexample, unchanged old prefixes between
batches, a missing parent and an identical restart rendering. Redaction or
corruption repair is an intentional invalidation, not a cache-preservation
promise.

Odin deliberately keeps its compactor separate from the planning harness.
Do not add planner tools or copy the planner's entire prefix just to imitate
the recipe's cache sharing. Any reuse between compactor requests needs its
own stable prefix, adapter support and measured usage; planner-side cache
layout remains the harness's responsibility.

One fidelity gap remains: the contract does not specify how much preceding
context a tool-less compactor receives to resolve references in a raw
message. Independence from the planner's cache does not imply context-free
summarization. Track this as X-10 before I2; compare bounded preceding
context with input-only summarization under ADR-005's budget and fidelity
checks. No new context size or shared-cache architecture is approved here.

Source inspection is complete. Implementation regression checks, live
cache measurement and the existing third-party reuse/attribution question
remain open. No upstream source text or code is vendored by this review.
