from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


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
    __tablename__ = "oncall"
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
