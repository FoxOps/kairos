#!/bin/sh
set -e

# Afficher la configuration actuelle
echo "🔍 Configuration actuelle:"
echo "  FLASK_ENV: ${FLASK_ENV:-non défini}"
echo "  DATABASE_URL: ${DATABASE_URL:-non défini}"
echo ""

# Initialiser la base de données SQLite
if [ ! -f "/app/data/app.db" ]; then
    echo "🔧 Initialisation de la base de données SQLite..."
    python -c "
from app import app, db
from app.models import Group, User, ShiftType

with app.app_context():
    db.create_all()
    
    # Types de shifts par défaut
    for st in [{'name': 'morning', 'label': '07h-15h', 'start_hour': 7, 'end_hour': 15},
                {'name': 'afternoon', 'label': '09h-17h', 'start_hour': 9, 'end_hour': 17},
                {'name': 'evening', 'label': '13h-21h', 'start_hour': 13, 'end_hour': 21}]:
        if not ShiftType.query.filter_by(name=st['name']).first():
            db.session.add(ShiftType(**st))
    
    # Groupe par défaut
    if not Group.query.first():
        db.session.add(Group(name='Défaut', is_part_of_schedule=True, is_part_of_oncall=True))
        db.session.commit()
    
    # Admin par défaut
    if not User.query.first():
        group = Group.query.first()
        admin = User(name='Admin', email='admin@leviia.local', is_admin=True, group_id=group.id)
        admin.set_password('admin123')
        admin.generate_ics_token()
        db.session.add(admin)
        db.session.commit()
        print('✅ Utilisateur admin créé')
"
    echo "✅ Base de données initialisée"
fi

# Choisir le serveur selon FLASK_ENV
# Note: Docker Compose charge les variables d'environnement, mais python-dotenv
# peut aussi les charger depuis .env. On vérifie explicitement FLASK_ENV.
if [ "$FLASK_ENV" = "production" ]; then
    echo "🎯 Mode PRODUCTION détecté - Démarrage de Gunicorn"
    exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 run:app
else
    echo "🎯 Mode DEVELOPPEMENT détecté - Démarrage de Flask"
    exec python run.py
fi
