from icalendar import Calendar, Event
from datetime import datetime, timedelta
from app.models import Shift, OnCall, Leave
import pytz


def generate_ics_standard(events, calendar_name="Leviia Schedule"):
    """
    Génère un fichier ICS standard à partir d'une liste d'événements.
    Supporte Shift, OnCall, et Leave.

    Args:
        events: Liste d'objets (Shift, OnCall ou Leave) avec les attributs nécessaires.
        calendar_name: Nom du calendrier (par défaut: "Leviia Schedule").

    Returns:
        str: Contenu du fichier ICS.
    """
    tz = pytz.timezone('Europe/Paris')

    cal = Calendar()
    cal.add('prodid', '-//Leviia Schedule//fr')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('name', calendar_name)
    cal.add('x-wr-timezone', 'Europe/Paris')

    for event_obj in events:
        event = Event()

        # Définir l'UID (identifiant unique)
        event.add('uid', f"{event_obj.__class__.__name__}-{event_obj.id}@mtg-schedule")

        # Gestion des titres, descriptions et dates selon le type d'événement
        if isinstance(event_obj, Shift):
            shift_type_label = event_obj.shift_type.label if event_obj.shift_type else event_obj.shift_type
            title = f"Shift {shift_type_label} - {event_obj.user.name}"
            description = f"Type: {shift_type_label}\nUtilisateur: {event_obj.user.name}"
            start_time = event_obj.start_time
            end_time = event_obj.end_time
        elif isinstance(event_obj, OnCall):
            title = f"Astreinte - {event_obj.user.name}"
            description = f"Utilisateur: {event_obj.user.name}"
            start_time = event_obj.start_time
            end_time = event_obj.end_time
        elif isinstance(event_obj, Leave):
            title = f"Conge - {event_obj.user.name}"
            description = f"Raison: {event_obj.reason or 'Non specifie'}\nUtilisateur: {event_obj.user.name}"
            # Pour les congés, créer des événements toute la journée
            start_time = datetime.combine(event_obj.start_date, datetime.min.time())
            end_time = datetime.combine(event_obj.end_date + timedelta(days=1), datetime.min.time())
        else:
            continue  # Ignorer les objets non supportés

        # Appliquer le timezone aux dates
        if start_time.tzinfo is None:
            start_time = tz.localize(start_time)
        if end_time.tzinfo is None:
            end_time = tz.localize(end_time)

        # Définir les dates de début et de fin avec timezone
        event.add('summary', title)
        event.add('description', description)
        event.add('dtstart', start_time)
        event.add('dtend', end_time)

        # Ajouter l'événement au calendrier
        cal.add_component(event)

    return cal.to_ical().decode('utf-8')


def generate_ics_shifts(shifts):
    """Génère un fichier ICS pour les shifts."""
    return generate_ics_standard(shifts, "Leviia Schedule - Shifts")


def generate_ics_oncall(on_calls):
    """Génère un fichier ICS pour les astreintes."""
    return generate_ics_standard(on_calls, "Leviia Schedule - Astreintes")


def generate_ics_leaves(leaves):
    """Génère un fichier ICS pour les congés."""
    return generate_ics_standard(leaves, "Leviia Schedule - Conge")
