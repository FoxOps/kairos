from icalendar import Calendar, Event
from datetime import datetime, timedelta
from app.models import Shift, OnCall
import pytz


def generate_ics_standard(events, calendar_name="Leviia Schedule"):
    """
    Génère un fichier ICS standard à partir d'une liste d'événements.
    
    Args:
        events: Liste d'objets (Shift ou OnCall) avec les attributs start_time et end_time.
        calendar_name: Nom du calendrier (par défaut: "Leviia Schedule").
    
    Returns:
        str: Contenu du fichier ICS.
    """
    # Timezone Europe/Paris
    tz = pytz.timezone('Europe/Paris')
    
    # Créer un nouveau calendrier
    cal = Calendar()
    cal.add('prodid', '-//Leviia Schedule//fr')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('name', calendar_name)
    cal.add('x-wr-timezone', 'Europe/Paris')
    
    # Ajouter chaque événement au calendrier
    for event_obj in events:
        event = Event()
        
        # Définir l'UID (identifiant unique)
        event.add('uid', f"{event_obj.__class__.__name__}-{event_obj.id}@mtg-schedule")
        
        # Définir le titre
        if isinstance(event_obj, Shift):
            title = f"Shift {event_obj.shift_type} - {event_obj.user.name}"
        elif isinstance(event_obj, OnCall):
            title = f"Astreinte - {event_obj.user.name}"
        else:
            title = "Événement"
        event.add('summary', title)
        
        # Définir la description
        if isinstance(event_obj, Shift):
            description = f"Type: {event_obj.shift_type}\nUtilisateur: {event_obj.user.name}"
        elif isinstance(event_obj, OnCall):
            description = f"Utilisateur: {event_obj.user.name}"
        else:
            description = ""
        event.add('description', description)
        
        # Appliquer le timezone aux dates
        start_time = event_obj.start_time
        end_time = event_obj.end_time
        
        if start_time.tzinfo is None:
            start_time = tz.localize(start_time)
        if end_time.tzinfo is None:
            end_time = tz.localize(end_time)
        
        # Définir les dates de début et de fin avec timezone
        event.add('dtstart', start_time)
        event.add('dtend', end_time)
        
        # Ajouter l'événement au calendrier
        cal.add_component(event)
    
    # Retourner le contenu du calendrier au format ICS
    return cal.to_ical().decode('utf-8')


def generate_ics_shifts(shifts):
    """
    Génère un fichier ICS pour les shifts.
    
    Args:
        shifts: Liste d'objets Shift.
    
    Returns:
        str: Contenu du fichier ICS.
    """
    return generate_ics_standard(shifts, "Leviia Schedule - Shifts")


def generate_ics_oncall(on_calls):
    """
    Génère un fichier ICS pour les astreintes.
    
    Args:
        on_calls: Liste d'objets OnCall.
    
    Returns:
        str: Contenu du fichier ICS.
    """
    return generate_ics_standard(on_calls, "Leviia Schedule - Astreintes")


def generate_ics_leaves(leaves):
    """
    Génère un fichier ICS pour les congés.
    
    Args:
        leaves: Liste d'objets Leave.
    
    Returns:
        str: Contenu du fichier ICS.
    """
    # Timezone Europe/Paris
    tz = pytz.timezone('Europe/Paris')
    
    cal = Calendar()
    cal.add('prodid', '-//Leviia Schedule//fr')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('name', "Leviia Schedule - Congés")
    cal.add('x-wr-timezone', 'Europe/Paris')
    
    for leave in leaves:
        event = Event()
        event.add('uid', f"Leave-{leave.id}@mtg-schedule")
        event.add('summary', f"Congé - {leave.user.name}")
        event.add('description', f"Raison: {leave.reason or 'Non spécifié'}\nUtilisateur: {leave.user.name}")
        
        # Appliquer le timezone aux dates (les dates sont naives, on les localise)
        start_date = tz.localize(datetime.combine(leave.start_date, datetime.min.time()))
        end_date = tz.localize(datetime.combine(leave.end_date + timedelta(days=1), datetime.min.time()))
        
        # Les congés sont des événements toute la journée
        event.add('dtstart', start_date)
        event.add('dtend', end_date)
        event.add('dtstamp', datetime.now(tz))
        
        cal.add_component(event)
    
    return cal.to_ical().decode('utf-8')