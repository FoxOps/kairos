"""
Resource blueprints for the public API (flask-smorest Blueprint +
MethodView pairs, one module per resource). app/api/__init__.py wires
each one up (auth before_request, JSON error handlers, registration on
the Api object) by iterating `all_blueprints`.
"""

all_blueprints: list = []

# Each import below appends that module's blueprint to all_blueprints
# (see the `all_blueprints.append(blp)` line at the bottom of each
# resource module) - the imports themselves are the registration
# mechanism, order doesn't matter.
from app.api.resources import (  # noqa: E402,F401
    leave,
    oncall,
    shift_types,
    shifts,
    users,
)
