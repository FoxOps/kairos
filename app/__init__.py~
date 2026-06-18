from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# Initialisation de la base de données (sans lier à une app pour l'instant)
db = SQLAlchemy()

# Configuration CSRF
csrf = CSRFProtect()


def create_app():
    """Factory pour créer une instance de l'application Flask."""
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Initialiser les extensions
    db.init_app(app)
    csrf.init_app(app)
    
    # Importer les modèles pour les enregistrer avec SQLAlchemy
    from app import models
    
    # Importer et enregistrer les blueprints
    from app.routes import main, admin, export
    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(export)
    
    return app


# Créer une instance par défaut pour le développement
app = create_app()
=======
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Initialisation de la base de données (sans lier à une app pour l'instant)
db = SQLAlchemy()


def create_app():
    """Factory pour créer une instance de l'application Flask."""
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Initialiser les extensions
    db.init_app(app)
    
    # Configuration CSRF (désactivée par défaut pour éviter les erreurs si Flask-WTF n'est pas installé)
    try:
        from flask_wtf.csrf import CSRFProtect
        csrf = CSRFProtect(app)
        app.config['WTF_CSRF_ENABLED'] = True
    except ImportError:
        app.config['WTF_CSRF_ENABLED'] = False
    
    # Importer les modèles pour les enregistrer avec SQLAlchemy
    from app import models
    
    # Importer et enregistrer les blueprints
    from app.routes import main, admin, export
    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(export)
    
    return app


# Créer une instance par défaut pour le développement
app = create_app()
=======
# ========== FICHIER: app/__init__.py ==========
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Initialisation de la base de données (sans lier à une app pour l'instant)
db = SQLAlchemy()


def create_app():
    """Factory pour créer une instance de l'application Flask."""
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Initialiser les extensions
    db.init_app(app)
    
    # Importer les modèles pour les enregistrer avec SQLAlchemy
    from app import models
    
    # Importer et enregistrer les blueprints
    from app.routes import main, admin, export
    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(export)
    
    return app


# Créer une instance par défaut pour le développement
app = create_app()==========
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Initialisation de la base de données (sans lier à une app pour l'instant)
db = SQLAlchemy()


def create_app():
    """Factory pour créer une instance de l'application Flask."""
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Initialiser les extensions
    db.init_app(app)
    
    # Configuration CSRF (désactivée par défaut pour éviter les erreurs si Flask-WTF n'est pas installé)
    try:
        from flask_wtf.csrf import CSRFProtect
        csrf = CSRFProtect(app)
        app.config['WTF_CSRF_ENABLED'] = True
    except ImportError:
        app.config['WTF_CSRF_ENABLED'] = False
    
    # Importer les modèles pour les enregistrer avec SQLAlchemy
    from app import models
    
    # Importer et enregistrer les blueprints
    from app.routes import main, admin, export
    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(export)
    
    return app


# Créer une instance par défaut pour le développement
app = create_app()==========
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# Initialisation de la base de données (sans lier à une app pour l'instant)
db = SQLAlchemy()

# Configuration CSRF
csrf = CSRFProtect()


def create_app():
    """Factory pour créer une instance de l'application Flask."""
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Initialiser les extensions
    db.init_app(app)
    csrf.init_app(app)
    
    # Importer les modèles pour les enregistrer avec SQLAlchemy
    from app import models
    
    # Importer et enregistrer les blueprints
    from app.routes import main, admin, export
    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(export)
    
    return app


# Créer une instance par défaut pour le développement
app = create_app()
