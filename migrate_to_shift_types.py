#!/usr/bin/env python3
"""
Script de migration pour ajouter le support des types de shifts dynamiques.

Ce script doit être exécuté une fois pour migrer la base de données existante
vers la nouvelle structure avec les types de shifts dans une table séparée.
"""

from app import app, db
from app.models import Shift, ShiftType

def migrate():
    with app.app_context():
        print("🔍 Vérification de la structure de la base de données...")
        
        # Vérifier si la colonne shift_type_id existe déjà
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('shift')]
        
        if 'shift_type_id' in columns:
            print("✅ La colonne shift_type_id existe déjà. Migration déjà effectuée.")
            return
        
        print("📋 Migration nécessaire...")
        
        # Vérifier si la table shift_types existe
        if inspector.has_table('shift_types'):
            print("✅ La table shift_types existe déjà.")
        else:
            print("❌ La table shift_types n'existe pas. Création...")
            db.create_all()
            print("✅ Table shift_types créée.")
        
        # Créer les types de shifts par défaut
        default_shift_types = [
            {'name': 'morning', 'label': '07h-15h', 'start_hour': 7, 'end_hour': 15},
            {'name': 'afternoon', 'label': '09h-17h', 'start_hour': 9, 'end_hour': 17},
            {'name': 'evening', 'label': '13h-21h', 'start_hour': 13, 'end_hour': 21},
        ]
        
        for shift_type_data in default_shift_types:
            if not ShiftType.query.filter_by(name=shift_type_data['name']).first():
                shift_type = ShiftType(
                    name=shift_type_data['name'],
                    label=shift_type_data['label'],
                    start_hour=shift_type_data['start_hour'],
                    end_hour=shift_type_data['end_hour'],
                )
                db.session.add(shift_type)
        db.session.commit()
        print("✅ Types de shifts par défaut créés.")
        
        # Ajouter la colonne shift_type_id à la table shift
        print("🔧 Ajout de la colonne shift_type_id...")
        try:
            # Pour SQLite, nous devons recréer la table
            # Sauvegarder les données existantes
            existing_shifts = db.session.query(
                Shift.id, 
                Shift.user_id, 
                Shift.shift_type, 
                Shift.start_time, 
                Shift.end_time, 
                Shift.date
            ).all()
            
            print(f"💾 Sauvegarde de {len(existing_shifts)} shifts existants...")
            
            # Supprimer la table shift
            db.session.execute(db.text("DROP TABLE IF EXISTS shift"))
            db.session.commit()
            
            # Recréer la table avec la nouvelle structure
            db.create_all()
            
            # Restaurer les données avec la nouvelle structure
            shift_type_map = {st.name: st.id for st in ShiftType.query.all()}
            
            for shift_data in existing_shifts:
                shift_type_id = shift_type_map.get(shift_data.shift_type)
                if shift_type_id:
                    new_shift = Shift(
                        id=shift_data.id,
                        user_id=shift_data.user_id,
                        shift_type_id=shift_type_id,
                        start_time=shift_data.start_time,
                        end_time=shift_data.end_time,
                        date=shift_data.date,
                    )
                    db.session.add(new_shift)
            
            db.session.commit()
            print(f"✅ {len(existing_shifts)} shifts restaurés avec la nouvelle structure.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la migration: {e}")
            raise
        
        print("✅ Migration terminée avec succès!")

if __name__ == '__main__':
    migrate()
