/**
 * Fonctions de formatage de dates (locale fr-FR).
 */

/**
 * Formate une date pour l'affichage.
 * @param {Date|string} date - Date à formater
 * @returns {string} Date formatée
 */
export function formatDate(date) {
    if (!date) return '';
    if (typeof date === 'string') date = new Date(date);
    return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

/**
 * Formate une heure pour l'affichage.
 * @param {Date|string} date - Date à formater
 * @returns {string} Heure formatée
 */
export function formatTime(date) {
    if (!date) return '';
    if (typeof date === 'string') date = new Date(date);
    return date.toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Formate une date et heure pour l'affichage.
 * @param {Date|string} date - Date à formater
 * @returns {string} Date et heure formatées
 */
export function formatDateTime(date) {
    if (!date) return '';
    if (typeof date === 'string') date = new Date(date);
    return date.toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}
