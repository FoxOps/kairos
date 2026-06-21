from app import app, db
import logging
import os

# Importer les modèles pour enregistrer les tables avec SQLAlchemy
from app.models import Group, User, ShiftType, Shift, OnCall, Leave

# Importer les routes pour qu'elles soient enregistrées
from app.routes import main, admin, export, auth

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('leviia_schedule.log'),
        logging.StreamHandler()
    ]
)

# Configurer les loggers spécifiques
logging.getLogger('app.config.automation_rules').setLevel(logging.INFO)
logging.getLogger('app.config.migration').setLevel(logging.INFO)

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
    
    # Vérifier que la table user a le champ is_part_of_oncall
    if inspector.has_table("user"):
        columns = [col["name"] for col in inspector.get_columns("user")]
        if "is_part_of_oncall" not in columns:
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


def migrate_user_is_part_of_oncall():
    """Migration pour ajouter le champ is_part_of_oncall à la table user."""
    from sqlalchemy import inspect
    
    inspector = inspect(db.engine)
    print("🔧 Migration: ajout du champ is_part_of_oncall à la table user...")
    
    # Vérifier si la colonne existe déjà
    if inspector.has_table("user"):
        columns = [col["name"] for col in inspector.get_columns("user")]
        if "is_part_of_oncall" not in columns:
            print("💾 Ajout du champ is_part_of_oncall...")
            
            try:
                # Sauvegarder les données existantes
                existing_users = db.session.execute(
                    db.text("SELECT id, name, email, password_hash, is_admin, group_id FROM user")
                ).fetchall()
                
                print(f"💾 Sauvegarde de {len(existing_users)} utilisateurs existants...")
                
                # Supprimer la table user
                db.session.execute(db.text("DROP TABLE IF EXISTS user"))
                db.session.commit()
                
                # Recréer la table avec la nouvelle structure
                db.create_all()
                
                # Restaurer les données
                for user_data in existing_users:
                    new_user = User(
                        id=user_data.id,
                        name=user_data.name,
                        email=user_data.email,
                        password_hash=user_data.password_hash,
                        is_admin=user_data.is_admin,
                        group_id=user_data.group_id,
                        is_part_of_oncall=False  # Valeur par défaut
                    )
                    db.session.add(new_user)
                
                db.session.commit()
                print(f"✅ {len(existing_users)} utilisateurs migrés avec succès.")
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erreur lors de la migration des utilisateurs: {e}")
                raise


def migrate_legacy_database():
    """Migration de l'ancienne structure de base de données (si nécessaire).
    
    Cette fonction est appelée UNIQUEMENT si la base existe mais a l'ancienne structure.
    """
    from sqlalchemy import inspect
    
    inspector = inspect(db.engine)
    print("🔧 Migration de l'ancienne structure de base de données...")
    
    # Vérifier si la table user a besoin du champ is_part_of_oncall
    if inspector.has_table("user"):
        columns = [col["name"] for col in inspector.get_columns("user")]
        if "is_part_of_oncall" not in columns:
            migrate_user_is_part_of_oncall()
            return
    
    # Vérifier si la table shift existe avec l'ancienne colonne shift_type
    if inspector.has_table("shift"):
        columns = [col["name"] for col in inspector.get_columns("shift")]
        if "shift_type" in columns and "shift_type_id" not in columns:
            print("💾 Migration des shifts existants avec l'ancienne colonne 'shift_type'...")
            
            try:
                # Sauvegarder les données existantes
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
                
                # Créer les types de shifts par défaut si ce n'est pas déjà fait
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


def setup_database():
    """Configure la base de données : initialisation ou migration si nécessaire.
    
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
    
    # Cas 3 : Migration nécessaire (ancienne structure détectée)
    migrate_legacy_database()


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

    app.run(debug=True)
