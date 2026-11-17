"""
Documentation-only schemas for the public API's error envelope (see
app/api/errors.py::json_error_handler for the actual runtime shape).
Used with @blp.alt_response(...) to document non-2xx responses in the
generated OpenAPI spec - never used to actually serialize a response,
same "doc-only" role flask-smorest's own ErrorSchema plays.
"""

from marshmallow import Schema, fields


class ErrorDetailSchema(Schema):
    code = fields.Str(
        metadata={
            "description": (
                "Stable machine-readable error code. One of: bad_request, "
                "unauthorized, forbidden, not_found, method_not_allowed, "
                "validation_error, rate_limited, internal_error, "
                "service_unavailable."
            ),
            "example": "not_found",
        }
    )
    message = fields.Str(
        metadata={
            "description": "Human-readable error message.",
            "example": "Shift not found.",
        }
    )
    details = fields.Raw(
        allow_none=True,
        metadata={
            "description": (
                "Additional structured detail, e.g. per-field validation "
                "errors for validation_error. null when there is none."
            )
        },
    )


class PublicApiErrorSchema(Schema):
    """Named to avoid colliding with flask_smorest's own internal
    ErrorSchema (flask_smorest.error_handler.ErrorSchema, used for its
    default 422 doc) - apispec resolves schemas by class name, and two
    different classes both named "ErrorSchema" get silently renamed/
    de-duplicated in a confusing way otherwise (confirmed: without this
    rename, apispec emits "Multiple schemas resolved to the name Error"
    and mangles one of them)."""

    error = fields.Nested(ErrorDetailSchema, required=True)
