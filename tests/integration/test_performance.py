"""
Tests de performance pour Leviia Schedule.

Deux angles, volontairement modestes (pas de vrai outil de profiling/
benchmark en place) :
1. Temps de réponse : seuils larges pour attraper une régression grossière
   (une route qui se met à prendre 10x plus longtemps), pas un micro-
   benchmark précis - inutile sur une machine de dev partagée.
2. Nombre de requêtes SQL : les repositories utilisent joinedload() pour
   éviter le N+1 (ex: ShiftRepository.list_paginated charge user +
   shift_type en une requête). Ces tests vérifient que le nombre de
   requêtes ne grandit pas linéairement avec le nombre d'enregistrements -
   c'est ce qui attraperait une vraie régression de performance ici,
   contrairement à un chrono qui varie trop selon la machine.
"""

import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from sqlalchemy import event

from app import compress, create_app, db
from app.models import Shift, ShiftType, SwapRequest, User


@contextmanager
def count_queries():
    """Compte les requêtes SQL exécutées dans le bloc `with`."""
    queries = []

    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    engine = db.engine
    event.listen(engine, "before_cursor_execute", _on_execute)
    try:
        yield queries
    finally:
        event.remove(engine, "before_cursor_execute", _on_execute)


def _seed_shifts(group, count, offset=0):
    shift_type = ShiftType(
        name=f"perf-{offset}-{count}", label="Perf", start_hour=7, end_hour=15
    )
    db.session.add(shift_type)
    db.session.flush()

    users = []
    for i in range(offset, offset + count):
        user = User(name=f"Perf User {i}", email=f"perf{i}@test.com", group_id=group.id)
        user.set_password("pw")
        db.session.add(user)
        users.append(user)
    db.session.flush()

    start = date.today()
    for i, user in enumerate(users):
        on_date = start + timedelta(days=i % 5)
        db.session.add(
            Shift(
                date=on_date,
                start_time=datetime.combine(on_date, datetime.min.time()),
                end_time=datetime.combine(on_date, datetime.min.time())
                + timedelta(hours=8),
                user_id=user.id,
                shift_type_id=shift_type.id,
            )
        )
    db.session.commit()


class TestResponseTime:
    """Seuils larges - attrape une régression grossière, pas un micro-benchmark."""

    def test_schedule_route_responds_quickly(
        self, test_app, test_group, logged_in_client
    ):
        with logged_in_client.application.app_context():
            _seed_shifts(test_group, 30)

        start = time.monotonic()
        resp = logged_in_client.get("/schedule?per_page=50")
        elapsed = time.monotonic() - start

        assert resp.status_code == 200
        assert elapsed < 2.0, f"/schedule a mis {elapsed:.2f}s (seuil 2s)"

    def test_dashboard_route_responds_quickly(self, test_app, logged_in_client):
        start = time.monotonic()
        resp = logged_in_client.get("/dashboard")
        elapsed = time.monotonic() - start

        assert resp.status_code == 200
        assert elapsed < 2.0, f"/dashboard a mis {elapsed:.2f}s (seuil 2s)"


class TestCompression:
    """Bug réel corrigé en Phase 6 : flask-compress était une dépendance
    déclarée (COMPRESS_REGISTER/COMPRESS_MIMETYPES dans ProductionConfig)
    mais Compress(app) n'était jamais appelé nulle part - la compression ne
    faisait donc jamais rien en pratique. Compress est maintenant initialisé
    dans create_app() (sauf en TESTING, car le client de test ne décode pas
    Content-Encoding et resp.data doit rester du texte brut pour les autres
    tests) - ces deux tests construisent donc leur propre app avec Compress
    réactivé manuellement, comme le fait déjà secure_app pour Talisman."""

    def test_response_is_gzip_compressed_when_accepted(self):
        app = create_app("app.config.TestingConfig")
        compress.init_app(app)
        with app.app_context():
            db.drop_all()
            db.create_all()
        client = app.test_client()
        resp = client.get("/login", headers={"Accept-Encoding": "gzip"})
        assert resp.status_code == 200
        assert resp.headers.get("Content-Encoding") == "gzip"
        with app.app_context():
            db.drop_all()

    def test_response_not_compressed_without_accept_encoding(self):
        app = create_app("app.config.TestingConfig")
        compress.init_app(app)
        with app.app_context():
            db.drop_all()
            db.create_all()
        client = app.test_client()
        resp = client.get("/login", headers={"Accept-Encoding": "identity"})
        assert resp.status_code == 200
        assert "Content-Encoding" not in resp.headers
        with app.app_context():
            db.drop_all()


class TestNPlusOneQueries:
    """Le nombre de requêtes SQL ne doit pas grandir linéairement avec le
    nombre d'enregistrements listés (sinon le joinedload() ne fait plus
    son travail)."""

    def test_schedule_query_count_stable_across_dataset_size(
        self, test_app, test_group, logged_in_client
    ):
        with logged_in_client.application.app_context():
            _seed_shifts(test_group, 5)
        with count_queries() as small_queries:
            resp_small = logged_in_client.get("/schedule?per_page=50")
        assert resp_small.status_code == 200

        with logged_in_client.application.app_context():
            _seed_shifts(test_group, 25, offset=100)
        with count_queries() as big_queries:
            resp_big = logged_in_client.get("/schedule?per_page=50")
        assert resp_big.status_code == 200

        # Une régression N+1 ferait croître le nombre de requêtes à peu
        # près proportionnellement au nombre de shifts affichés (30 ici).
        # Avec joinedload(), l'écart doit rester faible (marge de 5 pour
        # les requêtes de pagination/comptage annexes).
        assert len(big_queries) <= len(small_queries) + 5, (
            f"{len(small_queries)} requêtes pour 5 shifts, "
            f"{len(big_queries)} pour 25 shifts supplémentaires - "
            "suspicion de N+1 (joinedload cassé ?)"
        )

    def test_shift_repository_list_paginated_uses_eager_load(
        self, test_app, test_group
    ):
        _seed_shifts(test_group, 10)

        from app.repositories.shift_repository import ShiftRepository

        with count_queries() as queries:
            paginated = ShiftRepository.list_paginated(1, 50)
            # Accéder aux relations ne doit déclencher AUCUNE requête
            # supplémentaire si le joinedload a fonctionné.
            for shift in paginated.items:
                _ = shift.user.name
                _ = shift.shift_type.label

        assert len(queries) <= 3, (
            f"{len(queries)} requêtes pour lister 10 shifts avec leurs "
            "relations - le joinedload ne semble pas efficace"
        )

    def _seed_swap_requests(self, group, shift_type, count, offset=0):
        """Crée `count` SwapRequest, chacune avec son propre requester/
        target_user/shift - pas de partage entre lignes, pour que le
        pré-chargement bulk soit vraiment mis à l'épreuve."""
        on_date = date.today() + timedelta(days=3)
        while on_date.weekday() >= 5:
            on_date += timedelta(days=1)

        for i in range(offset, offset + count):
            requester = User(
                name=f"Swap Requester {i}",
                email=f"swap-req-{i}@test.com",
                group_id=group.id,
            )
            requester.set_password("pw")
            target = User(
                name=f"Swap Target {i}",
                email=f"swap-target-{i}@test.com",
                group_id=group.id,
            )
            target.set_password("pw")
            db.session.add_all([requester, target])
            db.session.flush()

            shift = Shift(
                date=on_date,
                start_time=datetime.combine(on_date, datetime.min.time()),
                end_time=datetime.combine(on_date, datetime.min.time())
                + timedelta(hours=8),
                user_id=requester.id,
                shift_type_id=shift_type.id,
            )
            db.session.add(shift)
            db.session.flush()

            db.session.add(
                SwapRequest(
                    requester_id=requester.id,
                    shift_id=shift.id,
                    target_user_id=target.id,
                    status=SwapRequest.PENDING,
                )
            )
        db.session.commit()

    def test_swap_request_repository_preloads_related_rows(self, test_app, test_group):
        """Régression N+1 : SwapRequest n'a pas de db.relationship() (voir
        app/models/swap_request.py) - sans le préchargement bulk de
        SwapRequestRepository._preload_related, accéder à
        requester/target_user/shift sur chaque ligne coûterait 3 requêtes
        de plus par ligne, faisant grandir le total proportionnellement au
        nombre de demandes listées."""
        shift_type = ShiftType(
            name="swap-perf", label="Perf", start_hour=7, end_hour=15
        )
        db.session.add(shift_type)
        db.session.flush()

        self._seed_swap_requests(test_group, shift_type, 3)
        with count_queries() as small_queries:
            from app.repositories.swap_request_repository import (
                SwapRequestRepository,
            )

            pending = SwapRequestRepository.list_pending()
            for sr in pending:
                _ = sr.requester.name
                _ = sr.target_user.name
                _ = sr.shift.date

        self._seed_swap_requests(test_group, shift_type, 15, offset=100)
        with count_queries() as big_queries:
            from app.repositories.swap_request_repository import (
                SwapRequestRepository,
            )

            pending = SwapRequestRepository.list_pending()
            for sr in pending:
                _ = sr.requester.name
                _ = sr.target_user.name
                _ = sr.shift.date

        # 18 demandes en plus (15 vs 3) ne devraient ajouter qu'une poignée
        # de requêtes bulk, pas ~54 requêtes individuelles (3 par ligne).
        assert len(big_queries) <= len(small_queries) + 5, (
            f"{len(small_queries)} requêtes pour 3 demandes, "
            f"{len(big_queries)} pour 18 demandes supplémentaires - "
            "suspicion de N+1 (préchargement cassé ?)"
        )

    def test_generate_oncall_schedule_query_count_stable_across_period_length(
        self, test_app, test_group, test_user, second_user
    ):
        """Régression : avant AvailabilityIndex (voir
        app/utils/automation/oncall_automation.py), find_next_available_user
        et check_oncall_constraint interrogeaient la DB à chaque candidat
        testé pour chaque semaine (jusqu'à 3 requêtes/candidat) - une
        génération de plusieurs mois grimpait à 1500+ requêtes."""
        from app.utils.automation import OnCallAutomation

        start_date = date(2024, 1, 5)  # Vendredi

        with count_queries() as short_queries:
            oncalls_short, _ = OnCallAutomation.generate_oncall_schedule(
                start_date, start_date + timedelta(days=28), dry_run=True
            )
        assert len(oncalls_short) > 0

        with count_queries() as long_queries:
            oncalls_long, _ = OnCallAutomation.generate_oncall_schedule(
                start_date, start_date + timedelta(days=180), dry_run=True
            )
        assert len(oncalls_long) > len(oncalls_short)

        # ~26 semaines de plus (180 vs 28 jours) ne devraient pas ajouter
        # de requêtes proportionnelles au nombre de semaines - juste le
        # préchargement bulk (borné au nombre d'utilisateurs éligibles).
        assert len(long_queries) <= len(short_queries) + 5, (
            f"{len(short_queries)} requêtes pour {len(oncalls_short)} astreintes, "
            f"{len(long_queries)} pour {len(oncalls_long)} astreintes - "
            "suspicion de N+1 (AvailabilityIndex cassé ?)"
        )
