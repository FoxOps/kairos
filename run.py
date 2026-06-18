from app import app, db

if __name__ == '__main__':
    # Créer les tables de la base de données
    with app.app_context():
        db.create_all()
    
    # Lancer l'application Flask
    app.run(debug=True)