/**
 * Configuration et interactions du calendrier FullCalendar (page d'accueil).
 *
 * Externalisé depuis un <script> inline de index.html en Phase 6, pour
 * permettre une CSP script-src 'self' stricte (un <script> inline aurait
 * besoin de 'unsafe-inline' ou d'un nonce). Les données injectées par le
 * serveur (isAdmin, events) transitent désormais par des attributs
 * data-* et une balise <script type="application/json"> plutôt que par
 * de l'interpolation Jinja directement dans du JS.
 */

import {
    announceToScreenReader,
    confirmActionAccessible,
    focusElement,
    setupKeyboardNavigation,
} from '../utils/accessibility.js';

document.addEventListener('DOMContentLoaded', function () {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) {
        console.error("Élément #calendar introuvable !");
        return;
    }

    const isAdmin = calendarEl.dataset.isAdmin === 'true';
    const eventsDataEl = document.getElementById('calendar-events-data');
    const events = eventsDataEl ? JSON.parse(eventsDataEl.textContent) : [];
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

    // Lire l'état du mode édition depuis l'URL
    const urlParams = new URLSearchParams(window.location.search);
    let editModeEnabled = urlParams.get('edit') === 'true';
    let tipsVisible = false;

    // Gestion des boutons de toggle
    const toggleEditModeBtn = document.getElementById('toggle-edit-mode');
    const toggleTipsBtn = document.getElementById('toggle-tips');
    const editModeStatusTag = document.getElementById('edit-mode-status-tag');
    const tipsContainer = document.getElementById('tips-container');

    // Fonction pour mettre à jour l'URL et l'état du mode édition
    function updateEditModeState(enabled) {
        editModeEnabled = enabled;

        // Mettre à jour l'URL sans recharger la page
        const url = new URL(window.location);
        if (enabled) {
            url.searchParams.set('edit', 'true');
        } else {
            url.searchParams.delete('edit');
        }
        window.history.pushState({}, '', url);

        // Mettre à jour l'UI
        if (editModeStatusTag) {
            if (enabled) {
                editModeStatusTag.innerHTML = '<i class="fas fa-edit" aria-hidden="true"></i>&nbsp; Mode édition activé';
                editModeStatusTag.classList.remove('is-danger');
                editModeStatusTag.classList.add('is-success');
                editModeStatusTag.setAttribute('aria-label', 'Mode édition activé');
            } else {
                editModeStatusTag.innerHTML = '<i class="fas fa-edit" aria-hidden="true"></i>&nbsp; Mode édition désactivé';
                editModeStatusTag.classList.remove('is-success');
                editModeStatusTag.classList.add('is-danger');
                editModeStatusTag.setAttribute('aria-label', 'Mode édition désactivé');
            }
        }

        if (toggleEditModeBtn) {
            if (enabled) {
                toggleEditModeBtn.innerHTML = '<i class="fas fa-toggle-off" aria-hidden="true"></i>&nbsp; Désactiver l\'édition';
                toggleEditModeBtn.classList.remove('is-success');
                toggleEditModeBtn.classList.add('is-danger');
                toggleEditModeBtn.setAttribute('aria-label', 'Désactiver le mode édition');
            } else {
                toggleEditModeBtn.innerHTML = '<i class="fas fa-toggle-on" aria-hidden="true"></i>&nbsp; Activer l\'édition';
                toggleEditModeBtn.classList.remove('is-danger');
                toggleEditModeBtn.classList.add('is-success');
                toggleEditModeBtn.setAttribute('aria-label', 'Activer le mode édition');
            }
        }

        // Mettre à jour les propriétés du calendrier
        if (window.calendar) {
            window.calendar.setOption('editable', enabled && isAdmin);
            window.calendar.setOption('selectable', enabled && isAdmin);
            window.calendar.setOption('droppable', enabled && isAdmin);
        }
    }

    if (toggleEditModeBtn && editModeStatusTag) {
        toggleEditModeBtn.addEventListener('click', function () {
            updateEditModeState(!editModeEnabled);
        });
    }

    if (toggleTipsBtn && tipsContainer) {
        toggleTipsBtn.addEventListener('click', function () {
            tipsVisible = !tipsVisible;

            if (tipsVisible) {
                tipsContainer.style.display = 'block';
                toggleTipsBtn.innerHTML = '<i class="fas fa-eye-slash" aria-hidden="true"></i>&nbsp; Cacher conseils';
                toggleTipsBtn.classList.remove('is-info');
                toggleTipsBtn.classList.add('is-warning');
                toggleTipsBtn.setAttribute('aria-label', 'Cacher les conseils');
            } else {
                tipsContainer.style.display = 'none';
                toggleTipsBtn.innerHTML = '<i class="fas fa-eye" aria-hidden="true"></i>&nbsp; Afficher conseils';
                toggleTipsBtn.classList.remove('is-warning');
                toggleTipsBtn.classList.add('is-info');
                toggleTipsBtn.setAttribute('aria-label', 'Afficher les conseils');
            }
        });
    }

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        events: events,
        locale: 'fr',
        firstDay: 1,
        eventTimeFormat: {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        },
        height: 'auto',

        // Activation du Drag & Drop pour les administrateurs
        editable: editModeEnabled && isAdmin,
        selectable: editModeEnabled && isAdmin,
        droppable: editModeEnabled && isAdmin,

        // Configuration du drag & drop
        eventDrop: function (info) {
            // Appelé quand un événement est déplacé
            const event = info.event;
            const eventId = event.id;
            const newStart = event.start;
            const newEnd = event.end;

            if (!eventId || eventId === undefined) {
                // C'est un nouvel événement créé par drop externe
                return;
            }

            // Déterminer le type d'événement et l'ID de la ressource
            const extendedProps = event.extendedProps || {};
            const type = extendedProps.type;
            const resourceId = extendedProps.resourceId;

            let endpoint = '';

            if (type === 'shift') {
                endpoint = `/api/shifts/${resourceId}`;
            } else if (type === 'oncall') {
                endpoint = `/api/oncall/${resourceId}`;
            } else if (type === 'leave') {
                endpoint = `/api/leave/${resourceId}`;
            } else {
                info.revert();
                return;
            }

            // Envoyer la mise à jour au serveur
            fetch(endpoint, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    start: newStart.toISOString(),
                    end: newEnd.toISOString()
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('Événement mis à jour:', data.message);
                        // Recharge uniquement les événements du calendrier
                        // (requête AJAX FullCalendar) au lieu de la page
                        // entière, pour ne pas perdre le contexte de
                        // l'utilisateur (filtres, scroll, vue courante).
                        calendar.refetchEvents();
                        if (data.rebalance_warning) {
                            announceToScreenReader(
                                'Événement mis à jour, mais le rééquilibrage automatique des shifts a échoué.',
                                'assertive'
                            );
                        }
                    } else {
                        // Revert le changement en cas d'erreur
                        info.revert();
                        announceToScreenReader('Erreur: ' + data.error, 'assertive');
                    }
                })
                .catch(error => {
                    info.revert();
                    console.error('Erreur:', error);
                    announceToScreenReader('Une erreur est survenue lors de la mise à jour.', 'assertive');
                });
        },

        eventResize: function (info) {
            // Appelé quand un événement est redimensionné
            const event = info.event;
            const eventId = event.id;
            const newStart = event.start;
            const newEnd = event.end;

            if (!eventId || eventId === undefined) {
                return;
            }

            // Déterminer le type d'événement et l'ID de la ressource
            const extendedProps = event.extendedProps || {};
            const type = extendedProps.type;
            const resourceId = extendedProps.resourceId;

            let endpoint = '';

            if (type === 'shift') {
                endpoint = `/api/shifts/${resourceId}`;
            } else if (type === 'oncall') {
                endpoint = `/api/oncall/${resourceId}`;
            } else if (type === 'leave') {
                endpoint = `/api/leave/${resourceId}`;
            } else {
                info.revert();
                return;
            }

            // Envoyer la mise à jour au serveur
            fetch(endpoint, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    start: newStart.toISOString(),
                    end: newEnd.toISOString()
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('Événement redimensionné:', data.message);
                        // Recharge uniquement les événements du calendrier,
                        // pas la page entière (cf. eventDrop ci-dessus).
                        calendar.refetchEvents();
                        if (data.rebalance_warning) {
                            announceToScreenReader(
                                'Événement mis à jour, mais le rééquilibrage automatique des shifts a échoué.',
                                'assertive'
                            );
                        }
                    } else {
                        info.revert();
                        announceToScreenReader('Erreur: ' + data.error, 'assertive');
                    }
                })
                .catch(error => {
                    info.revert();
                    console.error('Erreur:', error);
                    announceToScreenReader('Une erreur est survenue lors du redimensionnement.', 'assertive');
                });
        },

        select: function (info) {
            // Appelé quand une plage horaire est sélectionnée (pour créer un nouveau shift)
            // Uniquement en mode édition
            if (!isAdmin || !editModeEnabled) {
                calendar.unselect();
                return;
            }

            const start = info.start;
            const end = info.end || start;

            // Ouvrir un modal pour sélectionner l'utilisateur et le type de shift
            openShiftCreationModal(start, end);

            calendar.unselect();
        },

        eventClick: function (info) {
            // Appelé quand un événement est cliqué
            const event = info.event;
            const eventId = event.id;

            if (!eventId || eventId === undefined) {
                return;
            }

            // En mode édition, cliquer sur un événement permet de le supprimer avec confirmation
            // Hors mode édition, cliquer ne fait rien
            if (editModeEnabled && isAdmin) {
                // Déterminer le type d'événement et l'ID de la ressource
                const extendedProps = event.extendedProps || {};
                const type = extendedProps.type;
                const resourceId = extendedProps.resourceId;

                let endpoint = '';
                let message = '';

                if (type === 'shift') {
                    endpoint = `/api/shifts/${resourceId}`;
                    message = 'Voulez-vous supprimer ce shift ?';
                } else if (type === 'oncall') {
                    endpoint = `/api/oncall/${resourceId}`;
                    message = 'Voulez-vous supprimer cette astreinte ?';
                } else if (type === 'leave') {
                    endpoint = `/api/leave/${resourceId}`;
                    message = 'Voulez-vous supprimer ce congé ?';
                } else {
                    return;
                }

                confirmActionAccessible(message,
                    () => {
                        fetch(endpoint, {
                            method: 'DELETE',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-Requested-With': 'XMLHttpRequest',
                                'X-CSRFToken': csrfToken
                            },
                            credentials: 'same-origin'
                        })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    event.remove();
                                    console.log('Événement supprimé:', data.message);
                                    announceToScreenReader('Événement supprimé avec succès.', 'polite');
                                    // Recharger la page pour synchroniser avec le backend
                                    location.reload();
                                } else {
                                    announceToScreenReader('Erreur: ' + data.error, 'assertive');
                                }
                            })
                            .catch(error => {
                                console.error('Erreur:', error);
                                announceToScreenReader('Une erreur est survenue lors de la suppression.', 'assertive');
                            });
                    },
                    () => {
                        announceToScreenReader('Suppression annulée.', 'polite');
                    }
                );
            }
        },

        eventDidMount: function (info) {
            // Ajouter des données personnalisées à l'événement
            const event = info.event;
            if (event.extendedProps && event.extendedProps.userId) {
                event.setExtendedProp('userId', event.extendedProps.userId);
            }
        },

        // Désactiver le drag & drop pour les week-ends
        dateClick: function (info) {
            const date = info.date;
            if (date.getDay() === 0 || date.getDay() === 6) { // Dimanche (0) ou Samedi (6)
                announceToScreenReader('Les shifts ne peuvent pas être créés ou déplacés vers les week-ends (samedi/dimanche).', 'assertive');
                return false;
            }
        }
    });

    calendar.render();

    // Rendre le calendrier accessible globalement
    window.calendar = calendar;

    // Initialiser l'UI et le calendrier selon l'état du mode édition
    updateEditModeState(editModeEnabled);

    // Fonction pour ouvrir le modal de création de shift
    function openShiftCreationModal(start, end) {
        // Charger les utilisateurs et types de shifts
        Promise.all([
            fetch('/api/users').then(r => r.json()),
            fetch('/api/shift-types').then(r => r.json())
        ]).then(([users, shiftTypes]) => {
            // Créer le modal
            const modalId = 'create-shift-modal';
            let modal = document.getElementById(modalId);

            if (!modal) {
                modal = document.createElement('div');
                modal.id = modalId;
                modal.className = 'modal';
                modal.setAttribute('role', 'dialog');
                modal.setAttribute('aria-modal', 'true');
                modal.setAttribute('aria-labelledby', 'create-shift-title');
                modal.innerHTML = `
                    <div class="modal-background" role="button" tabindex="0" aria-label="Fermer"></div>
                    <div class="modal-card">
                        <header class="modal-card-head">
                            <h2 id="create-shift-title" class="modal-card-title">
                                <i class="fas fa-plus" aria-hidden="true"></i> Créer un nouveau shift
                            </h2>
                            <button class="delete close-modal" aria-label="Fermer" role="button"></button>
                        </header>
                        <section class="modal-card-body">
                            <form id="shift-creation-form" aria-labelledby="create-shift-title">
                                <div class="field">
                                    <label class="label" for="shift-start">Date et heure de début</label>
                                    <div class="control">
                                        <input type="datetime-local" id="shift-start" class="input" value="${formatDateForInput(start)}" required aria-required="true">
                                    </div>
                                </div>
                                <div class="field">
                                    <label class="label" for="shift-end">Date et heure de fin</label>
                                    <div class="control">
                                        <input type="datetime-local" id="shift-end" class="input" value="${formatDateForInput(end)}" required aria-required="true">
                                    </div>
                                </div>
                                <div class="field">
                                    <label class="label" for="shift-user">Utilisateur</label>
                                    <div class="control">
                                        <div class="select is-fullwidth">
                                            <select id="shift-user" required aria-required="true">
                                                <option value="">Sélectionnez un utilisateur</option>
                                                ${users.map(u => `<option value="${u.id}">${u.name} (${u.email})</option>`).join('')}
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                <div class="field">
                                    <label class="label" for="shift-type">Type de shift</label>
                                    <div class="control">
                                        <div class="select is-fullwidth">
                                            <select id="shift-type" required aria-required="true">
                                                <option value="">Sélectionnez un type de shift</option>
                                                ${shiftTypes.map(st => `<option value="${st.id}">${st.label} (${st.start_hour}:00 - ${st.end_hour}:00)</option>`).join('')}
                                            </select>
                                        </div>
                                    </div>
                                </div>
                            </form>
                        </section>
                        <footer class="modal-card-foot">
                            <button class="button is-primary create-shift-btn" aria-label="Créer le shift">
                                <i class="fas fa-check" aria-hidden="true"></i> Créer
                            </button>
                            <button class="button close-modal" aria-label="Annuler">
                                <i class="fas fa-times" aria-hidden="true"></i> Annuler
                            </button>
                        </footer>
                    </div>
                `;
                document.body.appendChild(modal);
            } else {
                // Mettre à jour les valeurs
                modal.querySelector('#shift-start').value = formatDateForInput(start);
                modal.querySelector('#shift-end').value = formatDateForInput(end);
            }

            // Ouvrir le modal
            modal.classList.add('is-active');

            // Piège de focus dans la modale
            setupKeyboardNavigation(modal, '[tabindex], button, [href], input, select, textarea');

            // Mettre le focus sur le premier champ du formulaire
            const firstInput = modal.querySelector('#shift-start');
            if (firstInput) {
                focusElement(firstInput);
            }

            // Gérer les boutons
            modal.querySelectorAll('.close-modal').forEach(btn => {
                btn.onclick = () => {
                    modal.classList.remove('is-active');
                    announceToScreenReader('Création de shift annulée.', 'polite');
                };
            });

            modal.querySelector('.create-shift-btn').onclick = () => {
                const userId = modal.querySelector('#shift-user').value;
                const shiftTypeId = modal.querySelector('#shift-type').value;
                const startInput = modal.querySelector('#shift-start').value;
                const endInput = modal.querySelector('#shift-end').value;

                if (!userId || !shiftTypeId || !startInput || !endInput) {
                    announceToScreenReader('Veuillez remplir tous les champs obligatoires.', 'assertive');
                    return;
                }

                // Créer le shift via API
                fetch('/api/shifts', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        userId: userId,
                        shiftTypeId: shiftTypeId,
                        start: new Date(startInput).toISOString(),
                        end: new Date(endInput).toISOString()
                    })
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            modal.classList.remove('is-active');
                            console.log('Shift créé:', data.message);
                            announceToScreenReader('Shift créé avec succès.', 'polite');
                            // Recharger la page pour synchroniser avec le backend
                            location.reload();
                        } else {
                            announceToScreenReader('Erreur: ' + data.error, 'assertive');
                        }
                    })
                    .catch(error => {
                        console.error('Erreur:', error);
                        announceToScreenReader('Une erreur est survenue lors de la création du shift.', 'assertive');
                    });
            };
        }).catch(error => {
            console.error('Erreur lors du chargement des données:', error);
            announceToScreenReader('Une erreur est survenue lors du chargement des données.', 'assertive');
        });
    }

    // Fonction pour formater une date pour l'input datetime-local
    function formatDateForInput(date) {
        const pad = (num) => num.toString().padStart(2, '0');
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
    }

    // Gérer la touche Suppr pour supprimer un événement (uniquement en mode édition)
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Delete' || e.key === 'Suppr') {
            const selectedEvent = window.selectedEvent;
            if (selectedEvent && isAdmin && editModeEnabled) {
                // Déterminer le type d'événement et l'ID de la ressource
                const extendedProps = selectedEvent.extendedProps || {};
                const type = extendedProps.type;
                const resourceId = extendedProps.resourceId;

                let endpoint = '';
                let message = '';

                if (type === 'shift') {
                    endpoint = `/api/shifts/${resourceId}`;
                    message = 'Voulez-vous supprimer ce shift ?';
                } else if (type === 'oncall') {
                    endpoint = `/api/oncall/${resourceId}`;
                    message = 'Voulez-vous supprimer cette astreinte ?';
                } else if (type === 'leave') {
                    endpoint = `/api/leave/${resourceId}`;
                    message = 'Voulez-vous supprimer ce congé ?';
                } else {
                    return;
                }

                confirmActionAccessible(message,
                    () => {
                        fetch(endpoint, {
                            method: 'DELETE',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-Requested-With': 'XMLHttpRequest',
                                'X-CSRFToken': csrfToken
                            },
                            credentials: 'same-origin'
                        })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    selectedEvent.remove();
                                    console.log('Événement supprimé:', data.message);
                                    announceToScreenReader('Événement supprimé avec succès.', 'polite');
                                    // Recharger la page pour synchroniser avec le backend
                                    location.reload();
                                } else {
                                    announceToScreenReader('Erreur: ' + data.error, 'assertive');
                                }
                            })
                            .catch(error => {
                                console.error('Erreur:', error);
                                announceToScreenReader('Une erreur est survenue lors de la suppression.', 'assertive');
                            });
                    },
                    () => {
                        announceToScreenReader('Suppression annulée.', 'polite');
                    }
                );
            }
        }
    });

    // Stocker l'événement sélectionné
    calendar.on('eventClick', function (info) {
        window.selectedEvent = info.event;
    });
});
