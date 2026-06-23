from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import secrets


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
    group_id = db.Column(
        db.Integer, db.ForeignKey("groups.id"), nullable=False, default=1, index=True
    )
    ics_token = db.Column(db.String(64), unique=True, nullable=True)

    shifts = db.relationship("Shift", backref="user", lazy=True, cascade="all, delete-orphan", foreign_keys="Shift.user_id")
    on_calls = db.relationship("OnCall", backref="user", lazy=True, cascade="all, delete-orphan", foreign_keys="OnCall.user_id")
    leaves = db.relationship("Leave", backref="user", lazy=True, cascade="all, delete-orphan", foreign_keys="Leave.user_id")

    def set_password(self, password):
        """Définir le mot de passe (hashé)."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Vérifier le mot de passe."""
        return check_password_hash(self.password_hash, password)

    def generate_ics_token(self):
        """Génère un token unique pour l'export ICS."""
        self.ics_token = secrets.token_urlsafe(32)
        return self.ics_token

    def get_ics_export_url(self, export_type="shifts", scope="all"):
        """Retourne l'URL d'export ICS avec le token.
        
        Args:
            export_type: "shifts", "oncall" ou "leaves" (par défaut: "shifts")
            scope: "all" ou "my" (par défaut: "all")
        """
        if not self.ics_token:
            return None
        return f"/export/{export_type}?scope={scope}&token={self.ics_token}"


    @property
    def total_shifts(self):
        """Nombre total de shifts pour cet utilisateur."""
        return Shift.query.filter_by(user_id=self.id).count()

    @property
    def total_oncalls(self):
        """Nombre total d'astreintes pour cet utilisateur."""
        return OnCall.query.filter_by(user_id=self.id).count()

    @property
    def total_leaves(self):
        """Nombre total de congés pour cet utilisateur."""
        return Leave.query.filter_by(user_id=self.id).count()

    @property
    def next_shift(self):
        """Prochain shift de l'utilisateur."""
        from datetime import datetime
        return Shift.query.filter(
            Shift.user_id == self.id,
            Shift.start_time > datetime.now()
        ).order_by(Shift.start_time).first()

    @property
    def current_oncall(self):
        """Astreinte actuelle de l'utilisateur."""
        from datetime import datetime
        return OnCall.query.filter(
            OnCall.user_id == self.id,
            OnCall.start_time <= datetime.now(),
            OnCall.end_time >= datetime.now()
        ).first()

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
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    
    # Index composite pour les requêtes fréquentes
    __table_args__ = (
        db.Index('idx_shift_user_date', 'user_id', 'date'),
        db.Index('idx_shift_date_start', 'date', 'start_time'),
    )


class OnCall(db.Model):
    __tablename__ = "on_call"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)
    
    # Index composite pour les requêtes fréquentes de chevauchement
    __table_args__ = (
        db.Index('idx_oncall_user_start_end', 'user_id', 'start_time', 'end_time'),
    )


class Leave(db.Model):
    __tablename__ = "leave"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    
    # Index composite pour les requêtes fréquentes de chevauchement
    __table_args__ = (
        db.Index('idx_leave_user_date_range', 'user_id', 'start_date', 'end_date'),
    )
