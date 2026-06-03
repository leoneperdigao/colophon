# 0014. Synonym-aware entity-type scoring in the eval gate

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

The gold-set scorer ([eval/run.py](../../eval/run.py)) credits an extracted entity
as a true positive only when its `(type, value)` pair matches the gold label
exactly (after casefold). The gold set uses a **small controlled vocabulary** for
the type — `org`, `date`, `amount` — chosen by construction in
[samples/generate.py](../../samples/generate.py).

A real run surfaced the problem. Against `gpt-5.4-mini` the model extracted the
**correct values** and never hallucinated (`groundedness_rate 1.000`,
`document_type_accuracy 1.000`), yet `entity_precision` and `entity_recall`
collapsed to ~0.2 — well below the 0.80 gate. The cause was purely the **type
label**: the model returns `organization`/`vendor` where gold says `org`,
`invoice_date`/`reporting_period_end` where gold says `date`, `amount_due`/
`net_revenue` where gold says `amount`. Exact `(type, value)` matching counts each
of these as *both* a false positive and a false negative.

That is the gate measuring **vocabulary conformance**, not extraction quality. The
gold vocabulary was an internal labelling convenience; we never required a model to
reproduce those exact tokens.

## Decision

**Canonicalise the entity type on both sides before scoring.** A new pure module,
[eval/entity_types.py](../../eval/entity_types.py), maps known synonyms onto the
canonical type (`organization`/`vendor` → `org`, `invoice_date`/`period_end` →
`date`, `amount_due`/`revenue` → `amount`); `_entity_key` applies it to gold and
predicted types alike. The **value** is still compared verbatim (after casefold)
and groundedness is unchanged — a right type with a wrong value is still a miss.

The mapping is **explicit, not fuzzy**:

- A type is normalised (casefold + separators → underscore) and looked up in a
  hand-maintained synonym table. **Unknown names are not force-fit to a bucket** —
  they pass through normalised and are compared as-is.
- So a genuinely mistyped entity (`type="other"` for an org) is still a miss, and
  the gate cannot be gamed by over-broad keyword matching. This keeps the existing
  property test `test_mistyped_entities_are_not_true_positives` true.

## Consequences

- The gate now rewards **getting the value right under a reasonable type name**,
  which is what we actually care about. Type *accuracy* against the controlled
  vocabulary is no longer conflated with extraction recall.
- The synonym table is a maintenance surface: a model may coin a type name we
  haven't mapped, which scores as a miss until added. That is the deliberate,
  conservative failure mode (under-credit, never over-credit). New synonyms are a
  one-line addition with a parametrised test case.
- Scoring stays a pure, infra-free function — the harness remains CI-testable with
  an injected oracle, no model required.

## Alternatives considered

- **Score on value only, ignore type.** Simplest, but loses the ability to catch a
  right value filed under a wrong type (e.g. a date returned as an `org`); it would
  also let the existing mistyped-entity guard regress. Rejected.
- **Fuzzy/keyword or embedding-based type matching.** More tolerant of unseen
  names, but introduces false credit (e.g. substring collisions) and non-determinism
  into a gate whose value is its predictability. Rejected for the take-home scope.
- **Constrain the model's type vocabulary via the extraction schema (enum).** A
  real option — make `key_entities[].type` an enum in
  [agent.py](../../app/adapters/llm/agent.py) so the model emits canonical types
  directly. Complementary, not a substitute: it shapes future output but doesn't
  fix scoring of free-form types, and over-constraining can suppress legitimately
  finer-grained entities. Noted as a follow-up; scoring canonicalisation is the
  lower-risk change.
