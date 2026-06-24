#!/bin/bash
# =============================================================================
# Leviia Schedule - Entrypoint Script
# =============================================================================
#
# Ce script est exécuté au démarrage du conteneur Docker.
# Il gère:
# - L'initialisation de la base de données
# - La création des données par défaut
# - Le démarrage de l'application
#
# =============================================================================

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher un message avec une couleur
log_message() {
    local color="$1"
    local message="$2"
    echo -e "${color}[Leviia Schedule]${NC} ${message}"
}

# Fonction pour vérifier si une commande existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Vérifier si nous sommes dans un conteneur
if [ -f /.dockerenv ]; then
    log_message "$BLUE" "Démarrage dans un conteneur Docker..."
fi

# Attendre que la base de données soit disponible (si PostgreSQL/MySQL)
wait_for_database() {
    local db_url="${DATABASE_URL:-sqlite:///app.db}"
    
    # Si c'est SQLite, pas besoin d'attendre
    if [[ "$db_url" == sqlite://* ]]; then
        log_message "$GREEN" "Base de données SQLite détectée - pas d'attente nécessaire"
        return 0
    fi
    
    # Extraire l'hôte et le port de l'URL de la base de données
    local db_host
    local db_port
    
    if [[ "$db_url" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/ ]]; then
        db_host="${BASH_REMATCH[3]}"
        db_port="${BASH_REMATCH[4]}"
    elif [[ "$db_url" =~ mysql://([^:]+):([^@]+)@([^:]+):([0-9]+)/ ]]; then
        db_host="${BASH_REMATCH[3]}"
        db_port="${BASH_REMATCH[4]}"
    elif [[ "$db_url" =~ mariadb://([^:]+):([^@]+)@([^:]+):([0-9]+)/ ]]; then
        db_host="${BASH_REMATCH[3]}"
        db_port="${BASH_REMATCH[4]}"
    elif [[ "$db_url" =~ postgresql://([^@]+)@([^:]+):([0-9]+)/ ]]; then
        db_host="${BASH_REMATCH[2]}"
        db_port="${BASH_REMATCH[3]}"
    elif [[ "$db_url" =~ mysql://([^@]+)@([^:]+):([0-9]+)/ ]]; then
        db_host="${BASH_REMATCH[2]}"
        db_port="${BASH_REMATCH[3]}"
    elif [[ "$db_url" =~ mariadb://([^@]+)@([^:]+):([0-9]+)/ ]]; then
        db_host="${BASH_REMATCH[2]}"
        db_port="${BASH_REMATCH[3]}"
    else
        # Essayer de détecter l'hôte et le port par défaut
        db_host="db"
        db_port="5432"
    fi
    
    log_message "$YELLOW" "Attente de la disponibilité de la base de données (${db_host}:${db_port})..."
    
    local max_attempts=30
    local attempt=0
    local connected=false
    
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        
        # Vérifier si l'hôte est accessible
        if nc -z "$db_host" "$db_port" 2>/dev/null; then
            log_message "$GREEN" "Connexion à la base de données établie après $attempt tentative(s)"
            connected=true
            break
        fi
        
        if [ $attempt -eq 1 ]; then
            log_message "$YELLOW" "Tentative $attempt/$max_attempts..."
        elif [ $((attempt % 5)) -eq 0 ]; then
            log_message "$YELLOW" "Tentative $attempt/$max_attempts..."
        fi
        
        sleep 2
    done
    
    if [ "$connected" = false ]; then
        log_message "$RED" "Échec de la connexion à la base de données après $max_attempts tentatives"
        log_message "$RED" "Vérifiez que:"
        log_message "$RED" "  1. Le service de base de données est démarré"
        log_message "$RED" "  2. L'URL de la base de données est correcte: $db_url"
        log_message "$RED" "  3. Le réseau Docker est correctement configuré"
        exit 1
    fi
}

# Initialiser la base de données
initialize_database() {
    log_message "$BLUE" "Initialisation de la base de données..."
    
    # Exécuter le script d'initialisation via Python
    python -c "
from app import app, db
from app.models import Group, User, ShiftType, Shift, OnCall, Leave
from app.routes import main, admin, export, auth
import os

# Charger la configuration
app.config.from_object('config.Config')

# Override avec les variables d'environnement
if os.environ.get('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
if os.environ.get('SECRET_KEY'):
    app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

with app.app_context():
    # Vérifier et initialiser la base de données
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    
    # Si aucune table n'existe, créer toutes les tables
    if not inspector.get_table_names():
        db.create_all()
        print('✅ Tables créées')
    else:
        # Vérifier l'intégrité de la base
        required_tables = ['groups', 'user', 'shift_types', 'shift', 'on_call', 'leave']
        missing_tables = [t for t in required_tables if not inspector.has_table(t)]
        if missing_tables:
            print(f'⚠️  Tables manquantes: {missing_tables}. Recréation...')
            db.drop_all()
            db.create_all()
            print('✅ Tables recréées')
        else:
            print('✅ Base de données existante avec toutes les tables')
    
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
    db.session.commit()
    print('✅ Types de shifts par défaut vérifiés/créés')
    
    # Créer le groupe par défaut
    if not Group.query.first():
        default_group = Group(
            name=os.environ.get('DEFAULT_GROUP_NAME', 'Défaut'),
            is_part_of_schedule=os.environ.get('DEFAULT_GROUP_IN_SCHEDULE', 'true').lower() == 'true',
            is_part_of_oncall=os.environ.get('DEFAULT_GROUP_IN_ONCALL', 'true').lower() == 'true',
        )
        db.session.add(default_group)
        db.session.commit()
        print('✅ Groupe par défaut créé')
    
    # Créer l'utilisateur admin par défaut
    if not User.query.first():
        default_group = Group.query.first()
        admin_email = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@leviia.local')
        admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
        
        admin_user = User(
            name='Admin',
            email=admin_email,
            is_admin=True,
            group_id=default_group.id if default_group else 1,
        )
        admin_user.set_password(admin_password)
        admin_user.generate_ics_token()
        db.session.add(admin_user)
        db.session.commit()
        print('✅ Utilisateur admin créé')
        print(f'   Email: {admin_email}')
        print(f'   Mot de passe: {admin_password}')
        print('   ⚠️  Pensez à changer le mot de passe après la première connexion!')
"
}

# Fonction pour démarrer l'application avec Gunicorn
start_gunicorn() {
    local bind="${GUNICORN_BIND:-0.0.0.0:5000}"
    local workers="${GUNICORN_WORKERS:-4}"
    local threads="${GUNICORN_THREADS:-2}"
    local timeout="${GUNICORN_TIMEOUT:-120}"
    local log_level="${GUNICORN_LOG_LEVEL:-info}"
    
    log_message "$BLUE" "Démarrage de Gunicorn..."
    log_message "$BLUE" "  Bind: $bind"
    log_message "$BLUE" "  Workers: $workers"
    log_message "$BLUE" "  Threads: $threads"
    log_message "$BLUE" "  Timeout: $timeout"
    log_message "$BLUE" "  Log Level: $log_level"
    
    # Vérifier si Gunicorn est installé
    if ! command_exists gunicorn; then
        log_message "$RED" "Gunicorn n'est pas installé. Installation..."
        pip install gunicorn
    fi
    
    exec gunicorn \
        --bind "$bind" \
        --workers "$workers" \
        --threads "$threads" \
        --timeout "$timeout" \
        --log-level "$log_level" \
        --access-logfile - \
        --error-logfile - \
        run:app
}

# Fonction pour démarrer l'application avec le serveur Flask intégré
start_flask() {
    local host="${FLASK_HOST:-0.0.0.0}"
    local port="${FLASK_PORT:-5000}"
    local debug="${FLASK_DEBUG:-false}"
    
    log_message "$BLUE" "Démarrage du serveur Flask..."
    log_message "$BLUE" "  Host: $host"
    log_message "$BLUE" "  Port: $port"
    log_message "$BLUE" "  Debug: $debug"
    
    # Désactiver le reloader pour éviter les problèmes avec SQLite
    export FLASK_APP=run.py
    export FLASK_ENV="${FLASK_ENV:-production}"
    
    if [ "$debug" = "true" ]; then
        exec python run.py
    else
        exec python run.py
    fi
}

# Fonction pour démarrer l'application avec uWSGI
start_uwsgi() {
    log_message "$BLUE" "Démarrage de uWSGI..."
    
    if ! command_exists uwsgi; then
        log_message "$RED" "uWSGI n'est pas installé. Installation..."
        pip install uwsgi
    fi
    
    exec uwsgi \
        --http :5000 \
        --module run:app \
        --workers 4 \
        --threads 2 \
        --master \
        --die-on-term
}

# =============================================================================
# Point d'entrée principal
# =============================================================================

log_message "$GREEN" "=========================================="
log_message "$GREEN" "  Leviia Schedule - Démarrage"
log_message "$GREEN" "=========================================="

# Afficher la version de Python
log_message "$BLUE" "Python version: $(python --version 2>&1)"

# Afficher l'URL de la base de données (masquée pour la sécurité)
if [ -n "$DATABASE_URL" ]; then
    if [[ "$DATABASE_URL" == *://* ]]; then
        protocol="${DATABASE_URL%%://*}"
        rest="${DATABASE_URL#*://}"
        if [[ "$rest" == *@* ]]; then
            user_pass="${rest%%@*}"
            host_port="${rest#*@}"
            log_message "$BLUE" "Database: ${protocol}://***@${host_port}"
        else
            log_message "$BLUE" "Database: ${protocol}://${rest}"
        fi
    else
        log_message "$BLUE" "Database: $DATABASE_URL"
    fi
else
    log_message "$BLUE" "Database: sqlite:///app.db (par défaut)"
fi

# Attendre la base de données
wait_for_database

# Initialiser la base de données
initialize_database

log_message "$GREEN" "=========================================="
log_message "$GREEN" "  Initialisation terminée"
log_message "$GREEN" "=========================================="

# Choisir le serveur en fonction de la variable d'environnement
server="${SERVER:-gunicorn}"

case "$server" in
    gunicorn)
        start_gunicorn
        ;;
    flask)
        start_flask
        ;;
    uwsgi)
        start_uwsgi
        ;;
    *)
        log_message "$YELLOW" "Serveur non reconnu: $server. Utilisation de Gunicorn par défaut."
        start_gunicorn
        ;;
esac
