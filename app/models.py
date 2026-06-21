from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.config.automation_rules import AutomationConfig
import logging

# Configuration du logger
logger = logging.getLogger(__name__)


# =============================================================================
# HOOKS DE SYNCHRONISATION AUTOMATIQUE
# =============================================================================

def setup_sync_hooks():
    """
    Configure les hooks pour la synchronisation automatique entre BDD et TOML.
    Ces hooks s'assurent que les modifications dans la base de données sont
    reflétées dans le fichier TOML, et vice versa.
    """
    from sqlalchemy import event
    
    # Hook après commit pour synchroniser BDD -> TOML
    @event.listens_for(db.session, 'after_commit')
    def after_commit_sync(session):
        """Synchronise automatiquement après chaque commit."""
        try:
            # Vérifier si des groupes, types de shifts ou utilisateurs ont été modifiés
            if any(obj.__class__.__name__ in ['Group', 'ShiftType', 'User'] 
                   for obj in session.new | session.dirty | session.deleted):
                logger.debug("Détection de modifications - synchronisation TOML...")
                AutomationConfig.sync_groups_to_toml()
                AutomationConfig.sync_shift_types_to_toml()
                AutomationConfig.reload()
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation automatique après commit: {str(e)}")
    
    # Hook après flush pour synchroniser avant commit
    @event.listens_for(db.session, 'after_flush')
    def after_flush_sync(session, context):
        """Synchronise automatiquement après chaque flush."""
        try:
            # Vérifier si des groupes ou types de shifts ont été modifiés
            if any(obj.__class__.__name__ in ['Group', 'ShiftType'] 
                   for obj in session.new | session.dirty | session.deleted):
                logger.debug("Détection de modifications - synchronisation TOML...")
                AutomationConfig.sync_groups_to_toml()
                AutomationConfig.sync_shift_types_to_toml()
                AutomationConfig.reload()
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation automatique après flush: {str(e)}")


# Appeler la configuration des hooks au démarrage
# Cela sera appelé dans app/__init__.py après l'initialisation de db


class Group(db.Model):
    __tablename__ = "groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    is_part_of_schedule = db.Column(db.Boolean, default=False)
    is_part_of_oncall = db.Column(db.Boolean, default=False)

    users = db.relationship("User", backref="group", lazy=True, cascade="all, delete-orphan")


class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    is_part_of_oncall = db.Column(db.Boolean, default=False)
    group_id = db.Column(
        db.Integer, db.ForeignKey("groups.id"), nullable=False, default=1
    )

    shifts = db.relationship("Shift", backref="user", lazy=True, cascade="all, delete-orphan", foreign_keys="Shift.user_id")
    on_calls = db.relationship("OnCall", backref="user", lazy=True, cascade="all, delete-orphan", foreign_keys="OnCall.user_id")
    leaves = db.relationship("Leave", backref="user", lazy=True, cascade="all, delete-orphan", foreign_keys="Leave.user_id")

    def set_password(self, password):
        """Définir le mot de passe (hashé)."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Vérifier le mot de passe."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.name} ({self.email})>"


class ShiftType(db.Model):
    __tablename__ = "shift_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)
    label = db.Column(db.String(20), nullable=False)
    start_hour = db.Column(db.Integer, nullable=False)
    end_hour = db.Column(db.Integer, nullable=False)

    # Relation bidirectionnelle avec Shift
    shifts = db.relationship("Shift", backref="shift_type", lazy=True, cascade="all, delete-orphan")


class Shift(db.Model):
    __tablename__ = "shift"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    shift_type_id = db.Column(
        db.Integer, db.ForeignKey("shift_types.id"), nullable=False, index=True
    )
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)


class OnCall(db.Model):
    __tablename__ = "on_call"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)


class Leave(db.Model):
    __tablename__ = "leave"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
