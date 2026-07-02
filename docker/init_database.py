#!/usr/bin/env python3
"""Script d'initialisation de la base de données SQLite pour Leviia Schedule."""

from app import app, db
from app.models import Group, User, ShiftType

# Types de shifts par défaut
DEFAULT_SHIFT_TYPES = [
    {'name': 'morning', 'label': '07h-15h', 'start_hour': 7, 'end_hour': 15},
    {'name': 'afternoon', 'label': '09h-17h', 'start_hour': 9, 'end_hour': 17},
    {'name': 'evening', 'label': '13h-21h', 'start_hour': 13, 'end_hour': 21},
]


def main():
    """Initialise la base de données avec les tables et données par défaut."""
    with app.app_context():
        db.create_all()
        
        # Types de shifts par défaut
        for st in DEFAULT_SHIFT_TYPES:
            if not ShiftType.query.filter_by(name=st['name']).first():
                db.session.add(ShiftType(**st))
        
        # Groupe par défaut
        if not Group.query.first():
            db.session.add(Group(
                name='Defaut',
                is_part_of_schedule=True,
                is_part_of_oncall=True
            ))
            db.session.commit()
        
        # Admin par défaut
        if not User.query.first():
            group = Group.query.first()
            admin = User(
                name='Admin',
                email='admin@leviia.local',
                is_admin=True,
                group_id=group.id
            )
            admin.set_password('admin123')
            admin.generate_ics_token()
            db.session.add(admin)
            db.session.commit()
            print('✅ Utilisateur admin créé')


if __name__ == '__main__':
    main()
