# heimdall to commitment mapping

`heimdall-to-commitment.json` maps standalone heimdall's task-core record
types onto Odin's commitment record. ODIN-ADR-007 makes the commitment
record the single task authority and retires heimdall's task,
checkpoint and decision layer by a one-time import; it requires this
mapping to be kept with the record schemas
([decision record](../../../docs/DECISIONS.md#odin-adr-007--the-commitment-record-is-the-single-task-authority);
[I/O contract Appendix A](../../../docs/design/ODIN-IO-CONTRACT.md#appendix-a--record-schemas)).
The rows follow the code inventory's §B.5
([inventory](../../../docs/research/consolidation-2026-10/inventory-go-repos.md#b5-task-core-record-types-mapped-to-odin-commitments)).

**Status: a mapping only.** The import itself is I4, after gate G-10
(I/O contract §14 step 6; proposed scenario AC-38). Nothing here reads a
heimdall database, and real data enters only through the scoped
migration, never as a fixture.

## Format

Validated by `heimdall-to-commitment.schema.json`:

- `status`: the sentence above.
- `commitment_fields`: every top-level field of
  `../records/commitment.schema.json`.
- `status_mapping`: how a heimdall task status maps to
  `Commitment.state`. Status names are per workflow template, so the
  mapping is by class (initial and other non-terminal, success, dropped).
- `rows`: one row per heimdall record type or field group, with
  `heimdall_type` (`null` for a field heimdall has no source for),
  `heimdall_fields` (`["*"]` for the record as a whole), `commitment_field`
  (an Appendix A field, optionally dotted, or `null`), `disposition`
  (`mapped`, `provenance`, `dropped`, `new_in_odin`, `saga_owned`,
  `deferred`), `gap` and `source`.

The fixture case `migration/mapping-complete` checks that every
commitment field is covered by at least one row; the coverage rule is in
[the schemas README](../README.md#48-migration-mapping-check_mapping_coverage).

## Choices recorded in the rows

- Each heimdall subtask (`Step`) becomes one `criteria` entry whose id is
  the step id prefixed `step:`, its provenance link; `met` starts false,
  because an imported claim corroborates nothing independently (D22.4).
- Owner, ownership generation, assignments and budget are new in Odin;
  budget lives in `Assignment.limits`, not on the commitment.
- `Grant` is dropped: it is a scoped credential, not a delegation. The
  commitment's `delegation` references a Saga delegation (D17).
- heimdall's `SessionBinding` is not a commitment field; workspace
  bindings are Odin's SessionBinding record, deferred to the I4 Herdr
  adapter.
- Identity-key gap: heimdall keys captured transcripts by
  `os.Hostname()`, skald by `/etc/machine-id` (inventory §0.8), so the
  same transcript gets two keys until one host-identity rule is chosen.
