/**
 * Formulaire de demande d'échange de shift (add_swap.html) : peuple
 * dynamiquement la liste des shifts à venir de l'utilisateur cible
 * choisi, via GET /api/swaps/target-shifts.
 */

function resetTargetShiftSelect(select, message) {
    select.innerHTML = '';
    const option = document.createElement('option');
    option.value = '';
    option.textContent = message;
    select.appendChild(option);
}

async function loadTargetShifts(targetUserId, select) {
    resetTargetShiftSelect(select, 'Chargement...');
    select.disabled = true;

    try {
        const response = await fetch(
            `/api/swaps/target-shifts?user_id=${encodeURIComponent(targetUserId)}`
        );
        const data = await response.json();

        resetTargetShiftSelect(select, 'Aucun (don simple)');

        if (data.success && data.shifts.length > 0) {
            for (const shift of data.shifts) {
                const option = document.createElement('option');
                option.value = shift.id;
                const date = new Date(shift.date).toLocaleDateString('fr-FR');
                option.textContent = `${date} - ${shift.shift_type}`;
                select.appendChild(option);
            }
        }
    } catch {
        resetTargetShiftSelect(select, 'Erreur de chargement');
    } finally {
        select.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const targetUserSelect = document.getElementById('target_user_id');
    const targetShiftSelect = document.getElementById('target_shift_id');

    if (!targetUserSelect || !targetShiftSelect) {
        return;
    }

    targetUserSelect.addEventListener('change', () => {
        if (targetUserSelect.value) {
            loadTargetShifts(targetUserSelect.value, targetShiftSelect);
        } else {
            resetTargetShiftSelect(targetShiftSelect, 'Aucun (don simple)');
            targetShiftSelect.disabled = true;
        }
    });
});
