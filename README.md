# Frappe TabKit

**Roll out form-tab layouts across many DocTypes as code — idempotent, reversible, migrate-safe.**

Reorganizing large Frappe/ERPNext deployments into tabbed forms usually means
hand-clicking *Customize Form* on every DocType — unrepeatable, unreviewable,
and impossible to roll back. TabKit turns the whole rollout into a patch:

- **Idempotent** — run it twice, nothing breaks. Already-applied tabs are skipped.
- **Reversible** — every Tab Break it creates is tagged, so `revert()` removes
  exactly what TabKit added and nothing else.
- **Migrate-safe** — pure Custom Fields (`Tab Break`), no DocType JSON edits,
  no core changes. `bench update --reset` stays clean.
- **Auditable** — `audit()` prints the effective tab layout of any DocType.

This pattern was battle-tested on a production ERP where **128 DocTypes** were
re-organized into tabbed layouts in a single reviewable, reversible patch.

## Install

```bash
bench get-app https://github.com/Saleh-E/frappe-tabkit
bench --site yoursite.local install-app tabkit
```

TabKit ships no DocTypes and no fixtures — it is a pure utility app.

## Usage

### One DocType

```python
from tabkit.api import apply_tabs

apply_tabs("Customer", [
    {"label": "Overview",   "insert_after": None},            # first tab
    {"label": "Contacts",   "insert_after": "customer_group"},
    {"label": "Accounting", "insert_after": "payment_terms"},
])
```

### A whole rollout (inside a patch)

```python
# yourapp/patches/v1_0/rollout_tabs.py
from tabkit.api import apply_spec

SPEC = {
    "Customer": [
        {"label": "Overview",   "insert_after": None},
        {"label": "Accounting", "insert_after": "payment_terms"},
    ],
    "Supplier": [
        {"label": "Overview",   "insert_after": None},
        {"label": "Banking",    "insert_after": "default_currency"},
    ],
}

def execute():
    apply_spec(SPEC)
```

Add the patch to `patches.txt` and `bench migrate` does the rest — on every
site, every environment, identically.

### Roll back

```python
from tabkit.api import revert_tabs, revert_spec

revert_tabs("Customer")   # remove TabKit tabs from one DocType
revert_spec(SPEC)         # remove an entire rollout
```

### Audit a layout

```python
from tabkit.api import audit
audit("Customer")
# Customer
#   [TAB] Overview            (tabkit)
#   ...fields...
#   [TAB] Accounting          (tabkit)
```

## How it works

Each tab is a `Custom Field` with `fieldtype="Tab Break"` whose `fieldname`
carries the `tk_` prefix — that prefix is TabKit's ownership tag. Creation
goes through Frappe's official `create_custom_fields` helper (so property
setters, cache and migrations behave normally), and reverts delete only
`tk_`-prefixed Tab Breaks.

Rules TabKit enforces for you:

1. Never touch DocType JSON — customizations only.
2. Never delete a Tab Break it didn't create.
3. Skip silently when the tab already exists (idempotency).
4. Fail loudly when `insert_after` doesn't exist (no half-applied layouts).

## Why not just Customize Form?

Hand customization works for one DocType on one site. It does not work for
128 DocTypes across dev → staging → production, reviewed in a pull request,
applied by `bench migrate`, and reverted in one line when the design changes.
Layout is code. Treat it like code.

## License

MIT — © Saleh Amin ([linkedin.com/in/salehamin-hassan](https://www.linkedin.com/in/salehamin-hassan/))

Built while shipping [ehgzli.com](https://ehgzli.com) (multi-tenant healthcare
SaaS on Frappe) and a complete maritime-operations platform — both of which
follow one golden rule: *the custom app extends; core stays pristine.*
