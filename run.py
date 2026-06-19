from app import app, db
from app.models import Group, User, ShiftType, Shift

# Importer les routes pour qu'elles soient enregistrées
# Cela fonctionne car app existe déjà dans app/__init__.py
from app.routes import main, admin, export, auth

# Types de shifts par défaut
DEFAULT_SHIFT_TYPES = [
    {"name": "morning", "label": "07h-15h", "start_hour": 7, "end_hour": 15},
    {"name": "afternoon", "label": "09h-17h", "start_hour": 9, "end_hour": 17},
    {"name": "evening", "label": "13h-21h", "start_hour": 13, "end_hour": 21},
]


def migrate_database():
    """Migration de la base de données vers la nouvelle structure avec shift_type_id."""
    from sqlalchemy import inspect

    inspector = inspect(db.engine)

    # Vérifier si la colonne shift_type_id existe déjà
    if inspector.has_table("shift"):
        columns = [col["name"] for col in inspector.get_columns("shift")]
        if "shift_type_id" in columns:
            print("✅ La colonne shift_type_id existe déjà. Migration déjà effectuée.")
            return

    print("🔧 Migration de la base de données nécessaire...")

    # Vérifier si la table shift_types existe
    if not inspector.has_table("shift_types"):
        print("❌ La table shift_types n'existe pas. Création...")
        db.create_all()
        print("✅ Table shift_types créée.")

    # Créer les types de shifts par défaut
    for shift_type_data in DEFAULT_SHIFT_TYPES:
        if not ShiftType.query.filter_by(name=shift_type_data["name"]).first():
            shift_type = ShiftType(
                name=shift_type_data["name"],
                label=shift_type_data["label"],
                start_hour=shift_type_data["start_hour"],
                end_hour=shift_type_data["end_hour"],
            )
            db.session.add(shift_type)
    db.session.commit()
    print("✅ Types de shifts par défaut créés.")

    # Si la table shift existe avec l'ancienne structure, migrer les données
    if inspector.has_table("shift") and "shift_type" in [
        col["name"] for col in inspector.get_columns("shift")
    ]:
        print("💾 Migration des shifts existants...")

        # Sauvegarder les données existantes
        try:
            existing_shifts = db.session.execute(
                db.text(
                    "SELECT id, user_id, shift_type, start_time, end_time, date FROM shift"
                )
            ).fetchall()

            print(f"💾 Sauvegarde de {len(existing_shifts)} shifts existants...")

            # Supprimer la table shift
            db.session.execute(db.text("DROP TABLE IF EXISTS shift"))
            db.session.commit()

            # Recréer la table avec la nouvelle structure
            db.create_all()

            # Restaurer les données avec la nouvelle structure
            shift_type_map = {st.name: st.id for st in ShiftType.query.all()}

            for shift_data in existing_shifts:
                shift_type_id = shift_type_map.get(shift_data.shift_type)
                if shift_type_id:
                    new_shift = Shift(
                        id=shift_data.id,
                        user_id=shift_data.user_id,
                        shift_type_id=shift_type_id,
                        start_time=shift_data.start_time,
                        end_time=shift_data.end_time,
                        date=shift_data.date,
                    )
                    db.session.add(new_shift)

            db.session.commit()
            print(
                f"✅ {len(existing_shifts)} shifts migrés avec succès vers la nouvelle structure."
            )

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la migration des shifts: {e}")
            raise


if __name__ == "__main__":
    with app.app_context():
        # Exécuter la migration si nécessaire
        migrate_database()

        # Créer le groupe par défaut s'il n'existe pas
        if not Group.query.first():
            default_group = Group(
                name="Défaut",
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
                name="Admin",
                email="admin@leviia.local",
                is_admin=True,
                group_id=default_group.id if default_group else 1,
            )
            admin_user.set_password("admin123")  # Mot de passe par défaut
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Utilisateur admin créé avec succès !")
            print(f"   Email: admin@leviia.local")
            print(f"   Mot de passe: admin123")
            print("   Pensez à changer le mot de passe après la première connexion.")

    app.run(debug=True)
