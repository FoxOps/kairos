from app import app, db
from app.models import Group

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
