"""TabKit — roll out form-tab layouts as code.

Idempotent, reversible, migrate-safe Tab Break rollouts for Frappe/ERPNext.

Every Tab Break created by TabKit carries the ``tk_`` fieldname prefix.
That prefix is the ownership tag: TabKit will never delete a Tab Break it
did not create.
"""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

PREFIX = "tk_"


def _fieldname(label: str) -> str:
    return PREFIX + frappe.scrub(label) + "_tab"


def _existing_fieldnames(doctype: str) -> set:
    meta = frappe.get_meta(doctype)
    return {df.fieldname for df in meta.fields if df.fieldname}


def apply_tabs(doctype: str, tabs: list, dry_run: bool = False) -> list:
    """Create Tab Break custom fields on *doctype*.

    Each entry in *tabs* is a dict::

        {"label": "Accounting", "insert_after": "payment_terms"}

    ``insert_after=None`` places the tab at the top of the form.
    Already-applied tabs (same generated fieldname) are skipped, which makes
    repeated runs safe. Raises if ``insert_after`` names a field that does
    not exist — half-applied layouts are worse than loud failures.

    Returns the list of fieldnames actually created.
    """
    if not frappe.db.exists("DocType", doctype):
        frappe.throw(_("DocType {0} does not exist").format(doctype))

    existing = _existing_fieldnames(doctype)
    created = []
    fields = []

    for tab in tabs:
        label = tab["label"]
        fieldname = _fieldname(label)
        if fieldname in existing:
            continue  # idempotency: already rolled out

        insert_after = tab.get("insert_after")
        if insert_after and insert_after not in existing:
            frappe.throw(
                _("{0}: insert_after field {1} not found").format(doctype, insert_after)
            )

        fields.append(
            {
                "fieldname": fieldname,
                "label": label,
                "fieldtype": "Tab Break",
                "insert_after": insert_after,
            }
        )
        created.append(fieldname)

    if fields and not dry_run:
        create_custom_fields({doctype: fields}, ignore_validate=False)
        frappe.clear_cache(doctype=doctype)

    return created


def apply_spec(spec: dict, dry_run: bool = False) -> dict:
    """Apply a multi-DocType rollout: ``{doctype: [tab, ...], ...}``.

    Designed to be called from a patch's ``execute()`` so the rollout ships
    with ``bench migrate``. Returns ``{doctype: [created fieldnames]}``.
    """
    results = {}
    for doctype, tabs in spec.items():
        results[doctype] = apply_tabs(doctype, tabs, dry_run=dry_run)
    return results


def revert_tabs(doctype: str, dry_run: bool = False) -> list:
    """Delete every TabKit-owned Tab Break on *doctype*.

    Only Custom Fields whose fieldname starts with ``tk_`` and whose
    fieldtype is ``Tab Break`` are touched. Returns deleted fieldnames.
    """
    rows = frappe.get_all(
        "Custom Field",
        filters={
            "dt": doctype,
            "fieldtype": "Tab Break",
            "fieldname": ("like", PREFIX + "%"),
        },
        pluck="name",
    )
    if not dry_run:
        for name in rows:
            frappe.delete_doc("Custom Field", name, ignore_permissions=True)
        if rows:
            frappe.clear_cache(doctype=doctype)
    return rows


def revert_spec(spec: dict, dry_run: bool = False) -> dict:
    """Revert an entire rollout previously applied with :func:`apply_spec`."""
    return {doctype: revert_tabs(doctype, dry_run=dry_run) for doctype in spec}


def audit(doctype: str) -> list:
    """Print and return the effective tab layout of *doctype*.

    TabKit-owned tabs are marked ``(tabkit)`` so a reviewer can see at a
    glance what the rollout added versus what shipped with the DocType.
    """
    meta = frappe.get_meta(doctype)
    layout = []
    print(doctype)
    for df in meta.fields:
        if df.fieldtype == "Tab Break":
            owned = " (tabkit)" if (df.fieldname or "").startswith(PREFIX) else ""
            line = "  [TAB] {0}{1}".format(df.label or df.fieldname, owned)
            layout.append(line)
            print(line)
    return layout
