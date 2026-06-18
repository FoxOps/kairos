from app import db

# Modèle pour les groupes
class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    is_part_of_schedule = db.Column(db.Boolean, default=False)
    is_part_of_oncall = db.Column(db.Boolean, default=False)

    # Relation avec les utilisateurs
    users = db.relationship('User', backref='group', lazy=True)

# Modèle pour les utilisateurs
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    # Clé étrangère pour le groupe (pointe vers groups.id)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False, default=1)

    # Relations existantes
    shifts = db.relationship('Shift', backref='user', lazy=True)
    on_calls = db.relationship('OnCall', backref='user', lazy=True)
    leaves = db.relationship('Leave', backref='user', lazy=True)

# Modèles pour les shifts, astreintes et congés (inchangés)
class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shift_type = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    date = db.Column(db.Date, nullable=False)

class OnCall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(200))