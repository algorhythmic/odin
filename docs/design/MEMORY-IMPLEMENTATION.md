# Local memory implementation evidence

`python/odin/memory.py` implements a PLAN-03 fixture-only memory slice in the
service-owned `odin_history` SQLite database. It uses additive `memory_*`
tables and a separate `memory_migrations` table; it does not change the Store
database's `user_version`. Each mutation uses the Store transaction and
appends a content-free event to its history. Source and statement shapes are
closed JSON schemas, with shared valid/invalid examples in
`fixtures/memory-contracts.json`.

Sources are immutable numbered revisions with verified content digests.
Retrieval metadata is separate, so re-reading cached text cannot renew its
observation time. The service stamps when it learned each source, statement
and relation; a historical query cannot use the source's claimed date to
move knowledge backward. Statements are attributed, typed, status-labelled and
bound to exact source revisions. An accepted decision statement must match
the choice in a canonical Commitment decision at the referenced revision;
the statement alone supplies no authority. Retrieval checks the current
reader list even for historical queries. Revisions, relations and redactions
invalidate affected statements on read. Redaction scrubs local source text
and transitively derived statement text while retaining per-destination
pending or confirmed receipts. Per-producer processing advances only across
captured, explicitly processed sequences; holes are bounded intervals.
Snapshots apply current access on every read and have item and byte limits.
Local redaction initially leaves a `local_storage` receipt pending. After the
enclosing transaction commits, `purge_local_storage()` uses SQLite secure
deletion configured at initialization, checkpoints and truncates the WAL,
vacuums, and checkpoints again.
A blocked reader leaves the receipt pending for retry. A synthetic test checks
that the redacted text disappears from the active database and WAL files.
This does not promise erasure from filesystem media remnants or independent
backups; those destinations retain separate pending receipts.

Prepared decision wording is stored in a removable continuity projection;
canonical HumanRequest history uses generic prompts and stable choice handles.
Fresh resume views revalidate the projection's evidence. A source redaction
conservatively scrubs all prepared questions bound to that project's memory,
cancels their requests and retains their underlying commitments. Legacy
history containing full question text leaves a `legacy_history` destination
pending and prevents local purge confirmation; this work does not rewrite
append-only history or implement real-history migration.

The local regression suite covers PLAN-C02–C06, canonical decision binding
and restart persistence. This is synthetic local evidence. There is no model
extractor, live provider retrieval, external deletion executor, summary tree
or portfolio cache in this slice. The caller must supply trusted reader
identity and deterministic statement content; these APIs are not directly
model-callable. Pending redaction destinations require an external executor
to confirm them. Production data policy and live Saga/harness gates remain
open under the governing design documents.
