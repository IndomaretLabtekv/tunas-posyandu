# Role-focused demo seed design

## Goal

Keep the Ibu Demo dashboard believable with exactly two children while retaining ten varied follow-up cases for the Kader Demo and Ahli Gizi Demo dashboards.

## Considered approaches

1. **Hidden community mother (selected).** Create one non-advertised mother user that owns the ten community children. This preserves existing foreign keys and role semantics while keeping quick login limited to the three public demo accounts.
2. **Nullable child ownership.** Allow community children without a mother. This requires a schema and API contract change and represents incomplete data, so it is unnecessary for demo seeding.
3. **Demo-only API filtering.** Keep every child owned by Ibu Demo but hide ten by name or flag. This adds special-case production behavior and makes ownership data misleading.

## Data shape

- Public demo accounts remain Ibu Demo, Kader Demo, and Ahli Gizi Demo.
- Ibu Demo owns two normal children with growth history.
- One hidden community mother owns ten additional children in `posyandu-demo`.
- The ten community children cover the existing case distribution: two `needs_review`, two `assigned`, two `home_visit`, two `verified_risk`, one `referred`, and one `resolved`.
- Kader and nutritionist queries remain unchanged because they already list cases by scope rather than mother ownership.

## Existing database behavior

The seed remains deterministic and idempotent. On rerun, known community children previously owned by Ibu Demo are reassigned to the hidden community mother; existing growth checks, cases, and transitions are retained instead of duplicated.

## Verification

The seed test will run the command twice and assert:

- Ibu Demo owns exactly two children.
- The scope contains twelve children total and ten cases.
- Case statuses retain the intended distribution.
- Public quick-login account names and credentials remain unchanged.
