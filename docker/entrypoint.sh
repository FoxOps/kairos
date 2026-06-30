#!/bin/bash
# =============================================================================
# Script d'entrée pour Leviia Schedule
# =============================================================================
#
# Ce script choisit automatiquement le bon serveur selon l'environnement :
# - Développement : python run.py (avec reloader)
# - Production : gunicorn (avec plusieurs workers)
#

set -e

# Afficher la configuration
if [ -n "$FLASK_ENV" ]; then
    echo "🚀 Démarrage de Leviia Schedule en mode: $FLASK_ENV"
else
    echo "🚀 Démarrage de Leviia Schedule (FLASK_ENV non défini, mode par défaut: development)"
fi

# Vérifier que les dépendances sont installées
if [ ! -f "/opt/venv/bin/python" ]; then
    echo "❌ Erreur: Python virtual environment non trouvé dans /opt/venv/bin/python"
    exit 1
fi

# Attendre que la base de données soit prête (si PostgreSQL)
if [[ "$DATABASE_URL" == postgresql* ]]; then
    echo "⏳ Attente de la base de données PostgreSQL..."
    until /opt/venv/bin/python -c "import psycopg; psycopg.connect('${DATABASE_URL}')" 2>/dev/null; do
        sleep 2
    done
    echo "✅ Base de données PostgreSQL prête"
fi

# Initialiser la base de données si nécessaire
if [ "$FLASK_ENV" = "development" ] || [ -z "$FLASK_ENV" ]; then
    echo "🔧 Initialisation de la base de données..."
    /opt/venv/bin/python -c "
from app import app, db
from app.models import Group, User, ShiftType, Shift, OnCall, Leave
from sqlalchemy import inspect

with app.app_context():
    # Créer les tables
    db.create_all()
    
    # Créer les types de shifts par défaut
    DEFAULT_SHIFT_TYPES = [
        {'name': 'morning', 'label': '07h-15h', 'start_hour': 7, 'end_hour': 15},
        {'name': 'afternoon', 'label': '09h-17h', 'start_hour': 9, 'end_hour': 17},
        {'name': 'evening', 'label': '13h-21h', 'start_hour': 13, 'end_hour': 21},
    ]
    
    for shift_type_data in DEFAULT_SHIFT_TYPES:
        if not ShiftType.query.filter_by(name=shift_type_data['name']).first():
            shift_type = ShiftType(
                name=shift_type_data['name'],
                label=shift_type_data['label'],
                start_hour=shift_type_data['start_hour'],
                end_hour=shift_type_data['end_hour'],
            )
            db.session.add(shift_type)
    
    # Créer le groupe par défaut
    if not Group.query.first():
        default_group = Group(
            name='Défaut',
            is_part_of_schedule=True,
            is_part_of_oncall=True,
        )
        db.session.add(default_group)
        db.session.commit()
    
    # Créer l'utilisateur admin par défaut
    if not User.query.first():
        default_group = Group.query.first()
        admin_user = User(
            name='Admin',
            email='admin@leviia.local',
            is_admin=True,
            group_id=default_group.id if default_group else 1,
        )
        admin_user.set_password('admin123')
        admin_user.generate_ics_token()
        db.session.add(admin_user)
        db.session.commit()
        print('✅ Utilisateur admin créé: admin@leviia.local / admin123')
"
fi

# Choisir le serveur selon l'environnement
if [ "$FLASK_ENV" = "production" ]; then
    echo "🎯 Mode production: démarrage de Gunicorn"
    # Vérifier si on utilise PostgreSQL ou SQLite
    if [[ "$DATABASE_URL" == postgresql* ]]; then
        echo "📦 Base de données: PostgreSQL - Utilisation de 4 workers"
        exec /opt/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 120 --log-level info run:app
    else
        echo "📦 Base de données: SQLite - Utilisation de 1 worker"
        exec /opt/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 --log-level info run:app
    fi
else
    echo "🎯 Mode développement: démarrage de Flask avec run.py"
    exec /opt/venv/bin/python run.py
fi
