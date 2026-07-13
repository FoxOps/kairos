"""
Fixtures pour les tests E2E navigateur réel (test_browser_flows.py).

Ce module ne doit jamais faire échouer la collecte de tests/e2e/ dans
son ensemble si playwright n'est pas installé - test_user_flows.py (E2E
client de test Flask, sans navigateur) doit continuer à tourner
normalement dans cet environnement. C'est pourquoi l'import de
playwright n'est pas fait au niveau module ici : chaque fixture qui en
a besoin fait son propre `pytest.importorskip`, ce qui ne skippe que
les tests qui la demandent (test_browser_flows.py), pas le reste du
dossier e2e/.
"""

import socket
import threading
import time

import pytest


def _free_port() -> int:
    """Trouve un port TCP libre sur localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(host: str, port: int, timeout: float = 10.0) -> None:
    """Attend qu'un port TCP accepte des connexions, ou lève TimeoutError."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"Serveur non démarré après {timeout}s sur {host}:{port}")


ADMIN_EMAIL = "e2e-admin@leviia.local"
ADMIN_PASSWORD = "e2e-password-123"  # noqa: S105 - identifiant de test synthétique, pas un vrai secret


@pytest.fixture(scope="module")
def live_server_url():
    """Lance un vrai serveur Flask (thread, port libre) avec Talisman
    réellement actif - pas TestingConfig, qui désactive Talisman et donc
    la CSP. Sans ça, les bugs CSP resteraient invisibles même avec un
    vrai navigateur (voir report/E2E Playwright - Tests navigateur
    réel.md pour le contexte : c'est exactement le point de cette suite
    de tests).
    """
    pytest.importorskip("playwright")

    from flask_talisman import Talisman

    from app import CSP_POLICY, compress, create_app, db
    from app.models import Group, User

    app = create_app("app.config.TestingConfig")
    # CSRF désactivé ici : on teste le rendu/comportement navigateur
    # (JS, CSS, CSP), pas la protection CSRF - déjà couverte par
    # tests/integration/test_security.py.
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TALISMAN_FORCE_HTTPS"] = True
    Talisman(
        app,
        force_https=False,
        strict_transport_security=False,
        content_security_policy=CSP_POLICY,
    )
    compress.init_app(app)

    with app.app_context():
        db.drop_all()
        db.create_all()

        group = Group(
            name="E2E Group", is_part_of_schedule=True, is_part_of_oncall=True
        )
        db.session.add(group)
        db.session.commit()

        admin = User(
            name="E2E Admin", email=ADMIN_EMAIL, group_id=group.id, is_admin=True
        )
        admin.set_password(ADMIN_PASSWORD)
        admin.generate_ics_token()
        db.session.add(admin)
        db.session.commit()

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    server_thread = threading.Thread(
        target=lambda: app.run(
            host="127.0.0.1", port=port, use_reloader=False, debug=False
        ),
        daemon=True,
    )
    server_thread.start()
    _wait_until_up("127.0.0.1", port)

    yield base_url

    # Thread démon : s'arrête avec le process de test, pas de teardown
    # explicite nécessaire (app.run() bloquant n'a pas de méthode
    # d'arrêt propre côté Werkzeug dev server).


@pytest.fixture
def logged_in_page(live_server_url, page):
    """Page Playwright déjà connectée en admin (formulaire réel, pas de
    cookie injecté directement - vérifie que le flux de login fonctionne
    vraiment dans le navigateur)."""
    page.goto(f"{live_server_url}/login")
    page.fill('input[name="email"]', ADMIN_EMAIL)
    page.fill('input[name="password"]', ADMIN_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    return page
