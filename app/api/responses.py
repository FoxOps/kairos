"""
Shared OpenAPI error-response documentation for public API operations
(app/api/resources/*.py). Every operation is authenticated (401) and
rate-limited (429) and scope-gated (403) - those three apply uniformly.
404/422 are added per-operation (detail views / filtered list views)
since they don't apply everywhere. All reference the same ErrorSchema
(app/api/schemas/error_schema.py), matching the one real runtime
envelope (app/api/errors.py::json_error_handler) - apispec dedupes a
repeatedly-referenced schema into one #/components/schemas/Error entry.
"""

from app.api.schemas.error_schema import PublicApiErrorSchema

_ALWAYS = {
    401: "Missing, invalid, revoked, or expired ServiceAccount token.",
    403: "The token does not have the scope required for this resource.",
    429: "Rate limit exceeded for this ServiceAccount.",
}
_NOT_FOUND = {404: "Resource not found."}
_VALIDATION = {422: "Request validation failed (invalid query parameters)."}


def document_errors(blp, *, not_found: bool = False, validation: bool = False):
    """Decorator factory applying @blp.alt_response for every error
    status this operation can realistically return."""
    codes = dict(_ALWAYS)
    if not_found:
        codes.update(_NOT_FOUND)
    if validation:
        codes.update(_VALIDATION)

    def decorator(func):
        for code, description in codes.items():
            func = blp.alt_response(
                code, schema=PublicApiErrorSchema, description=description
            )(func)
        return func

    return decorator
