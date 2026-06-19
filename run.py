from app import app, db
from app.models import Group, User, ShiftType

# Importer les routes pour qu'elles soient enregistrées
# Cela fonctionne car app existe déjà dans app/__init__.py
from app.routes import main, admin, export, auth

# Types de shifts par défaut
DEFAULT_SHIFT_TYPES = [
    {'name': 'morning', 'label': '07h-15h', 'start_hour': 7, 'end_hour': 15},
    {'name': 'afternoon', 'label': '09h-17h', 'start_hour': 9, 'end_hour': 17},
    {'name': 'evening', 'label': '13h-21h', 'start_hour': 13, 'end_hour': 21},
]

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Créer les types de shifts par défaut s'ils n'existent pas
        if not ShiftType.query.first():
            for shift_type_data in DEFAULT_SHIFT_TYPES:
                shift_type = ShiftType(
                    name=shift_type_data['name'],
                    label=shift_type_data['label'],
                    start_hour=shift_type_data['start_hour'],
                    end_hour=shift_type_data['end_hour'],
                )
                db.session.add(shift_type)
            db.session.commit()
            print("✅ Types de shifts par défaut créés avec succès !")
        
        # Créer le groupe par défaut s'il n'existe pas
        if not Group.query.first():
            default_group = Group(
                name='Défaut',
                is_part_of_schedule=True,
                is_part_of_oncall=True,
            )
            db.session.add(default_group)
            db.session.commit()
        
        # Créer un utilisateur admin par défaut s'il n'existe pas
        # (seulement si aucun utilisateur n'existe)
        if not User.query.first():
            default_group = Group.query.first()
            admin_user = User(
                name='Admin',
                email='admin@leviia.local',
                is_admin=True,
                group_id=default_group.id if default_group else 1
            )
            admin_user.set_password('admin123')  # Mot de passe par défaut
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Utilisateur admin créé avec succès !")
            print(f"   Email: admin@leviia.local")
            print(f"   Mot de passe: admin123")
            print("   Pensez à changer le mot de passe après la première connexion.")

    app.run(debug=True)
