from app import app, db

# Importer les modèles pour enregistrer les tables avec SQLAlchemy
from app.models import Group, User, ShiftType, Shift, OnCall, Leave

# Importer les routes pour qu'elles soient enregistrées
from app.routes import main, admin, export, auth

# Types de shifts par défaut
DEFAULT_SHIFT_TYPES = [
    {"name": "morning", "label": "07h-15h", "start_hour": 7, "end_hour": 15},
    {"name": "afternoon", "label": "09h-17h", "start_hour": 9, "end_hour": 17},
    {"name": "evening", "label": "13h-21h", "start_hour": 13, "end_hour": 21},
]


def check_database_integrity():
    """Vérifie l'intégrité de la base de données et retourne True si elle est valide."""
    from sqlalchemy import inspect
    
    inspector = inspect(db.engine)
    
    # Vérifier que toutes les tables nécessaires existent
    required_tables = ["groups", "user", "shift_types", "shift", "on_call", "leave"]
    for table in required_tables:
        if not inspector.has_table(table):
            return False
    
    # Vérifier que la table shift a la bonne structure
    if inspector.has_table("shift"):
        columns = [col["name"] for col in inspector.get_columns("shift")]
        required_columns = ["id", "user_id", "shift_type_id", "start_time", "end_time", "date"]
        for col in required_columns:
            if col not in columns:
                return False
    
    return True


def initialize_database():
    """Initialise la base de données avec les tables et données par défaut."""
    print("🔧 Initialisation de la base de données...")
    
    # Créer toutes les tables
    db.create_all()
    print("✅ Tables créées.")
    
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


def setup_database():
    """Configure la base de données : initialisation si nécessaire.
    
    Cette fonction est appelée UNIQUEMENT une fois au premier démarrage.
    """
    from sqlalchemy import inspect
    
    inspector = inspect(db.engine)
    
    # Cas 1 : Aucune table n'existe -> initialisation complète
    if not inspector.get_table_names():
        initialize_database()
        return
    
    # Cas 2 : Vérifier si la base a la bonne structure
    if check_database_integrity():
        print("✅ La base de données a une structure valide.")
        return
    
    # Cas 3 : La base existe mais a une structure invalide -> recréer
    print("⚠️  La base de données a une structure invalide. Recréation des tables...")
    db.drop_all()
    initialize_database()


def create_default_data():
    """Crée les données par défaut (groupe, utilisateur admin) si elles n'existent pas."""
    # Créer le groupe par défaut s'il n'existe pas
    if not Group.query.first():
        default_group = Group(
            name="Défaut",
            is_part_of_schedule=True,
            is_part_of_oncall=True,
        )
        db.session.add(default_group)
        db.session.commit()
        print("✅ Groupe par défaut créé.")

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


if __name__ == "__main__":
    with app.app_context():
        # Configurer la base de données (une seule fois)
        setup_database()
        
        # Créer les données par défaut
        create_default_data()

    # Désactiver le reloader pour éviter les problèmes de "database is locked" avec SQLite
    # Le reloader crée un nouveau processus qui peut verrouiller la base de données
    app.run(debug=True, use_reloader=False)
