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
    
    try:
        # Vérifier que toutes les tables existent
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        required_tables = ['user', 'group', 'shift_type', 'shift', 'oncall', 'leave']
        
        for table in required_tables:
            if table not in tables:
                return False
        
        return True
    except Exception:
        return False


def setup_database():
    """Configure la base de données."""
    with app.app_context():
        # Créer les tables si elles n'existent pas
        db.create_all()
        
        # Vérifier l'intégrité de la base de données
        if not check_database_integrity():
            # Si les tables n'existent pas, les recréer
            db.drop_all()
            db.create_all()


def create_default_data():
    """Crée les données par défaut si elles n'existent pas."""
    import os
    from werkzeug.security import generate_password_hash
    
    with app.app_context():
        # Créer le groupe par défaut
        default_group_name = os.environ.get("DEFAULT_GROUP_NAME") or "Defaut"
        default_group = Group.query.filter_by(name=default_group_name).first()
        if not default_group:
            default_group = Group(name=default_group_name)
            db.session.add(default_group)
            db.session.commit()
        
        # Créer l'utilisateur admin par défaut
        default_admin_email = os.environ.get("DEFAULT_ADMIN_EMAIL") or "admin@leviia.local"
        default_admin_password = os.environ.get("DEFAULT_ADMIN_PASSWORD") or "admin123"
        
        admin_user = User.query.filter_by(email=default_admin_email).first()
        if not admin_user:
            # ✅ CORRIGÉ: Le modèle User n'a pas de champ 'username', utiliser 'name' à la place
            admin_user = User(
                email=default_admin_email,
                name="Administrateur",  # Utiliser 'name' au lieu de 'username'
                password_hash=generate_password_hash(default_admin_password),
                is_admin=True,
                group_id=default_group.id
            )
            db.session.add(admin_user)
            db.session.commit()
            print(f"✅ Utilisateur admin créé: {default_admin_email}")
        else:
            print(f"✅ Utilisateur admin existe déjà: {default_admin_email}")
        
        # Créer les types de shifts par défaut
        for shift_type_data in DEFAULT_SHIFT_TYPES:
            shift_type = ShiftType.query.filter_by(name=shift_type_data["name"]).first()
            if not shift_type:
                shift_type = ShiftType(
                    name=shift_type_data["name"],
                    label=shift_type_data["label"],
                    start_hour=shift_type_data["start_hour"],
                    end_hour=shift_type_data["end_hour"]
                )
                db.session.add(shift_type)
        db.session.commit()


if __name__ == "__main__":
    import os
    
    with app.app_context():
        # Configurer la base de données (une seule fois)
        setup_database()
        
        # Créer les données par défaut
        create_default_data()

    # ✅ Écouter sur 0.0.0.0:5000 pour permettre les connexions externes
    host = os.environ.get("FLASK_HOST") or "0.0.0.0"
    port = int(os.environ.get("FLASK_PORT") or 5000)
    
    # Désactiver le reloader pour éviter les problèmes de "database is locked" avec SQLite
    # Le reloader crée un nouveau processus qui peut verrouiller la base de données
    app.run(host=host, port=port, debug=True, use_reloader=False)
