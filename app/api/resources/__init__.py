"""
Resource blueprints for the public API (flask-smorest Blueprint +
MethodView pairs, one module per resource). app/api/__init__.py wires
each one up (auth before_request, JSON error handlers, registration on
the Api object) by iterating `all_blueprints`.
"""

all_blueprints: list = []
