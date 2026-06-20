# ============================================================================
# AUTOMATISATION AVANCÉE DES SHIFTS (NOUVELLES RÈGLES MÉTIERS)
# ============================================================================

class AdvancedShiftAutomation:
    """
    Classe pour gérer l'automatisation avancée des shifts selon les nouvelles règles métiers.
    
    Règles implémentées :
    1. Créneau 13h-21h : Réservé à la personne d'astreinte SI elle fait partie d'un groupe schedule
    2. Rotation des créneaux : Si une personne était sur 13h-21h une semaine, elle doit être sur 07h-15h la semaine suivante
    3. Créneau par défaut : 09h-17h pour tous les autres cas (plusieurs personnes peuvent être sur ce créneau)
    4. Cas des congés : Si seulement 2 personnes disponibles, la personne NON d'astreinte doit être sur 07h-15h
    5. Contrainte légale : Pas 2 astreintes de suite - minimum 2 semaines sans astreinte entre deux astreintes
    """
    
    # Créneaux horaires
    SHIFT_07_15 = (7, 15)  # 07h-15h
    SHIFT_09_17 = (9, 17)  # 09h-17h
    SHIFT_13_21 = (13, 21)  # 13h-21h
    
    @staticmethod
    def get_shift_type_by_hours(start_hour: int, end_hour: int) -> 'ShiftType':
        """Récupère ou crée un type de shift basé sur les heures."""
        from app import db
        from app.models import ShiftType
        
        shift_type = ShiftType.query.filter_by(start_hour=start_hour, end_hour=end_hour).first()
        if shift_type:
            return shift_type
        
        # Créer un nouveau type de shift si nécessaire
        name = f"{start_hour:02d}-{end_hour:02d}"
        label = f"{start_hour:02d}h-{end_hour:02d}h"
        
        new_shift_type = ShiftType(
            name=name,
            label=label,
            start_hour=start_hour,
            end_hour=end_hour
        )
        db.session.add(new_shift_type)
        db.session.flush()  # Pour obtenir l'ID
        return new_shift_type
    
    @staticmethod
    def get_users_in_schedule_groups() -> list:
        """Récupère les utilisateurs qui font partie de groupes pouvant être ajoutés au schedule."""
        from app.models import User, Group
        return (
            User.query
            .join(Group)
            .filter(Group.is_part_of_schedule == True)
            .all()
        )
    
    @staticmethod
    def get_available_users_for_date(date: 'date') -> list:
        """Récupère les utilisateurs disponibles pour une date donnée (pas en congé)."""
        from datetime import datetime
        from app import db
        from app.models import Leave
        
        eligible_users = AdvancedShiftAutomation.get_users_in_schedule_groups()
        
        available_users = []
        for user in eligible_users:
            has_leave = db.session.query(
                db.exists().where(
                    Leave.user_id == user.id,
                    Leave.start_date <= date,
                    Leave.end_date >= date,
                )
            ).scalar()
            
            if not has_leave:
                available_users.append(user)
        
        return available_users
    
    @staticmethod
    def get_oncall_user_for_date(date: 'date') -> 'Optional[User]':
        """Récupère l'utilisateur d'astreinte pour une date donnée."""
        from datetime import datetime
        from app.models import OnCall
        
        oncall = OnCall.query.filter(
            OnCall.start_time <= datetime.combine(date, datetime.max.time()),
            OnCall.end_time >= datetime.combine(date, datetime.min.time())
        ).first()
        
        return oncall.user if oncall else None
    
    @staticmethod
    def check_oncall_constraint(user: 'User', date: 'date') -> bool:
        """
        Vérifie la contrainte légale : pas 2 astreintes de suite.
        Il doit y avoir au moins 2 semaines sans astreinte entre deux astreintes.
        """
        from datetime import datetime, timedelta
        from app.models import OnCall
        
        last_oncall = OnCall.query.filter_by(user_id=user.id).order_by(OnCall.start_time.desc()).first()
        
        if not last_oncall:
            return True
        
        last_end = last_oncall.end_time
        
        # Trouver le vendredi de la semaine de la date
        friday_date = date
        while friday_date.weekday() != 4:
            friday_date += timedelta(days=1)
        
        new_start = datetime.combine(friday_date, datetime.min.time()).replace(hour=21)
        
        weeks_between = (new_start - last_end).days / 7
        return weeks_between >= 2
    
    @staticmethod
    def get_previous_week_shift(user: 'User', date: 'date') -> 'Optional[Tuple[int, int]]':
        """Récupère le créneau de shift de l'utilisateur la semaine précédente."""
        from datetime import timedelta
        from app.models import Shift
        
        previous_week_date = date - timedelta(days=7)
        shift = Shift.query.filter(
            Shift.user_id == user.id,
            Shift.date == previous_week_date
        ).first()
        
        if shift and shift.shift_type:
            return (shift.shift_type.start_hour, shift.shift_type.end_hour)
        return None
    
    @staticmethod
    def determine_shift_for_user(user: 'User', date: 'date') -> 'Tuple[int, int]':
        """
        Détermine le créneau de shift pour un utilisateur à une date donnée.
        
        Règles :
        1. Si l'utilisateur était sur 13h-21h la semaine précédente -> 07h-15h
        2. Si l'utilisateur est d'astreinte ET fait partie d'un groupe schedule -> 13h-21h
        3. Sinon -> 09h-17h
        """
        # Règle 1 : Vérifier la semaine précédente
        previous_shift = AdvancedShiftAutomation.get_previous_week_shift(user, date)
        if previous_shift == AdvancedShiftAutomation.SHIFT_13_21:
            return AdvancedShiftAutomation.SHIFT_07_15
        
        # Règle 2 : Vérifier si d'astreinte
        oncall_user = AdvancedShiftAutomation.get_oncall_user_for_date(date)
        if oncall_user and oncall_user.id == user.id:
            schedule_users = AdvancedShiftAutomation.get_users_in_schedule_groups()
            if any(u.id == user.id for u in schedule_users):
                return AdvancedShiftAutomation.SHIFT_13_21
        
        # Règle 3 : Créneau par défaut
        return AdvancedShiftAutomation.SHIFT_09_17
    
    @staticmethod
    def handle_two_users_case(available_users: list, date: 'date') -> 'Dict':
        """
        Gère le cas spécial où il n'y a que 2 personnes disponibles.
        La personne NON d'astreinte doit être sur 07h-15h.
        """
        if len(available_users) != 2:
            return {}
        
        oncall_user = AdvancedShiftAutomation.get_oncall_user_for_date(date)
        assignments = {}
        
        for user in available_users:
            if oncall_user and user.id == oncall_user.id:
                schedule_users = AdvancedShiftAutomation.get_users_in_schedule_groups()
                if any(u.id == user.id for u in schedule_users):
                    assignments[user] = AdvancedShiftAutomation.SHIFT_13_21
                else:
                    assignments[user] = AdvancedShiftAutomation.SHIFT_09_17
            else:
                assignments[user] = AdvancedShiftAutomation.SHIFT_07_15
        
        return assignments
    
    @staticmethod
    def generate_daily_shifts(date: 'date', dry_run: bool = False) -> 'Tuple[list, list]':
        """Génère les shifts pour une journée selon les nouvelles règles."""
        from datetime import datetime
        from app import db
        from app.models import Shift
        
        messages = []
        generated_shifts = []
        
        if date.weekday() >= 5:
            return [], [f"⏭️ Pas de shift généré pour le {date.strftime('%d/%m/%Y')} (week-end)"]
        
        available_users = AdvancedShiftAutomation.get_available_users_for_date(date)
        
        if not available_users:
            return [], [f"⚠️ Aucun utilisateur disponible pour le {date.strftime('%d/%m/%Y')}"]
        
        # Cas spécial : seulement 2 personnes disponibles
        if len(available_users) == 2:
            assignments = AdvancedShiftAutomation.handle_two_users_case(available_users, date)
            if assignments:
                for user, (start_hour, end_hour) in assignments.items():
                    shift_type = AdvancedShiftAutomation.get_shift_type_by_hours(start_hour, end_hour)
                    start_time = datetime.combine(date, datetime.min.time()).replace(hour=start_hour)
                    end_time = datetime.combine(date, datetime.min.time()).replace(hour=end_hour)
                    
                    shift = Shift(
                        user_id=user.id,
                        shift_type_id=shift_type.id,
                        start_time=start_time,
                        end_time=end_time,
                        date=date,
                    )
                    generated_shifts.append(shift)
                    messages.append(f"✅ Shift {start_hour:02d}h-{end_hour:02d}h assigné à {user.name} le {date.strftime('%d/%m/%Y')}")
                
                if not dry_run:
                    try:
                        db.session.add_all(generated_shifts)
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        messages.append(f"❌ Erreur : {str(e)}")
                        return [], messages
                
                return generated_shifts, messages
        
        # Cas normal : 3+ utilisateurs
        schedule_users = AdvancedShiftAutomation.get_users_in_schedule_groups()
        
        for user in schedule_users:
            if user not in available_users:
                continue
            
            start_hour, end_hour = AdvancedShiftAutomation.determine_shift_for_user(user, date)
            shift_type = AdvancedShiftAutomation.get_shift_type_by_hours(start_hour, end_hour)
            start_time = datetime.combine(date, datetime.min.time()).replace(hour=start_hour)
            end_time = datetime.combine(date, datetime.min.time()).replace(hour=end_hour)
            
            shift = Shift(
                user_id=user.id,
                shift_type_id=shift_type.id,
                start_time=start_time,
                end_time=end_time,
                date=date,
            )
            generated_shifts.append(shift)
            messages.append(f"✅ Shift {start_hour:02d}h-{end_hour:02d}h assigné à {user.name} le {date.strftime('%d/%m/%Y')}")
        
        if not dry_run and generated_shifts:
            try:
                db.session.add_all(generated_shifts)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                messages.append(f"❌ Erreur : {str(e)}")
                return [], messages
        
        return generated_shifts, messages
    
    @staticmethod
    def generate_full_schedule(start_date: 'date', end_date: 'date', dry_run: bool = False) -> 'Tuple[list, list]':
        """Génère les shifts pour toute une période."""
        all_shifts = []
        all_messages = []
        from datetime import timedelta
        
        current_date = start_date
        while current_date <= end_date:
            shifts, messages = AdvancedShiftAutomation.generate_daily_shifts(current_date, dry_run=True)
            all_shifts.extend(shifts)
            all_messages.extend(messages)
            current_date += timedelta(days=1)
        
        if not dry_run and all_shifts:
            try:
                from app import db
                db.session.add_all(all_shifts)
                db.session.commit()
                all_messages.insert(0, f"🎉 {len(all_shifts)} shifts générés !")
            except Exception as e:
                db.session.rollback()
                all_messages.insert(0, f"❌ Erreur : {str(e)}")
                return [], all_messages
        
        return all_shifts, all_messages
    
    @staticmethod
    def rebalance_after_leave(leave: 'Leave', dry_run: bool = False) -> 'Tuple[list, list]':
        """
        Rééquilibre les shifts après l'ajout/modification d'un congé.
        Appelé automatiquement lors de l'ajout d'un congé.
        """
        from datetime import timedelta
        from app import db
        from app.models import Shift
        
        messages = []
        regenerated_shifts = []
        
        # Récupérer toutes les dates du congé
        leave_dates = []
        current_date = leave.start_date
        while current_date <= leave.end_date:
            leave_dates.append(current_date)
            current_date += timedelta(days=1)
        
        for date in leave_dates:
            # Supprimer les shifts existants
            existing_shifts = Shift.query.filter_by(date=date).all()
            if existing_shifts and not dry_run:
                for shift in existing_shifts:
                    db.session.delete(shift)
                db.session.commit()
                messages.append(f"🗑️ {len(existing_shifts)} shifts supprimés pour le {date.strftime('%d/%m/%Y')}")
            
            # Régénérer
            shifts, date_messages = AdvancedShiftAutomation.generate_daily_shifts(date, dry_run=dry_run)
            regenerated_shifts.extend(shifts)
            messages.extend(date_messages)
        
        return regenerated_shifts, messages
