"""
Unit tests for UserRepository.list_paginated() (app/repositories/
user_repository.py) - the one genuinely new repository method added to
back GET /api/v1/users/'s pagination + group_id filter
(app/api/resources/users.py).
"""

from app import db
from app.models import Group, User
from app.repositories.user_repository import UserRepository


class TestListPaginated:
    def test_paginates_all_users(self, test_app, test_user):
        pagination = UserRepository.list_paginated(1, 10)
        assert pagination.total == 1
        assert pagination.items[0].id == test_user.id

    def test_filters_by_group_id(self, test_app, test_user, test_group):
        other_group = Group(
            name="Other", is_part_of_schedule=True, is_part_of_oncall=True
        )
        db.session.add(other_group)
        db.session.commit()
        other_user = User(
            name="Other",
            email="other@test.com",
            password_hash="x",
            group_id=other_group.id,
        )
        db.session.add(other_user)
        db.session.commit()

        pagination = UserRepository.list_paginated(1, 10, group_id=test_group.id)
        assert pagination.total == 1
        assert pagination.items[0].id == test_user.id

    def test_unmatched_group_id_returns_empty(self, test_app, test_user):
        pagination = UserRepository.list_paginated(1, 10, group_id=999999)
        assert pagination.total == 0
