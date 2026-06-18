from app import app, db
from app.models import Group

# Importer les routes pour qu'elles soient enregistrées
# Cela fonctionne car app existe déjà dans app/__init__.py
from app.routes import main, admin, export

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Group.query.first():
            default_group = Group(
                name='Défaut',
                is_part_of_schedule=True,
                is_part_of_oncall=True,
            )
            db.session.add(default_group)
            db.session.commit()

    app.run(debug=True)
