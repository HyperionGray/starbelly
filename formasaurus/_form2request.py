"""High-level API for easier integration with form2request."""

from __future__ import annotations

from lxml.html import FormElement, HtmlElement
from parsel import Selector, SelectorList

from .classifiers import extract_forms


def build_submission(
    html: bytes | str | HtmlElement | Selector | SelectorList,
    form_type: str,
    fields: dict[str, str] = None,
    *,
    min_proba: float = 0.05,
) -> tuple[FormElement, dict[str, str], HtmlElement | None]:
    """Return the form, data, and submit button to submit an HTML form.

    *html* is the source HTML response, where the form to submit will be found.

    *form_type* is one of the :ref:`supported form types <form-types>`. The
    returned form is the one of the specified type with the highest probability
    and a minimum probability of *min_proba*. If there is no match,
    :exc:`ValueError` is raised.

    .. note:: A probability is always a :class:`float` in the [0, 1] range.

    *fields* is a dictionary of key-value pairs of data to submit with the
    form, where keys are :ref:`supported field types <field-types>` instead of
    actual form field names.

    The resulting tuple contains:

    #.  The matching form.

    #.  A dictionary of data to submit with the form. It is the content of
        *fields*, with keys replaced by their corresponding form field names.
        Missing fields are silently dropped. When multiple field names matching
        a given field type are found, the field name with the highest
        probability is used.

    #.  The submit button of the form, or ``None`` if no submit button was
        found. If multiple submit buttons are found, the one with the highest
        probability is returned.

    You can use the :doc:`form2request library <form2request:index>` to turn
    the result into an HTTP request:

    >>> form, data, submit_button = build_submission(html, "search", {"search query": "foo"})  # doctest: +SKIP
    >>> request_data = form2request(form, data, click=submit_button)  # doctest: +SKIP
    """
    if isinstance(html, Selector):
        html = html.root
    elif isinstance(html, SelectorList):
        try:
            html = html[0].root
        except IndexError:
            raise ValueError("html is an empty SelectorList")
    forms = extract_forms(html, proba=True, threshold=min_proba)
    if not forms:
        raise ValueError("No form found")
    form, info = max(forms, key=lambda entry: entry[1]["form"].get(form_type, 0.0))
    proba = info["form"].get(form_type, 0.0)
    if proba < min_proba:
        raise ValueError(
            f"Best matching form probability is below {min_proba:%}: {proba:%}"
        )

    data = {}
    fields = fields or {}
    for field_type, value in fields.items():
        matching_fields = [
            (field_name, proba)
            for field_name, field_data in info["fields"].items()
            for _field_type, proba in field_data.items()
            if _field_type == field_type
        ]
        if not matching_fields:
            continue
        field_name, _ = max(matching_fields, key=lambda entry: entry[1])
        data[field_name] = value

    submit_button = None
    matching_fields = [
        (field_name, proba)
        for field_name, field_data in info["fields"].items()
        for field_type, proba in field_data.items()
        if field_type == "submit button"
    ]
    if matching_fields:
        field_name, _ = max(matching_fields, key=lambda entry: entry[1])
        submit_button = form.xpath(f".//*[@name='{field_name}']")[0]

    return form, data, submit_button
