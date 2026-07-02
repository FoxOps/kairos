#!/usr/bin/env python3
"""
Script pour corriger les appels url_for dans les fichiers de tests et templates.

Ce script remplace les anciens noms d'endpoints par les nouveaux noms avec préfixe de blueprint.
"""

import os
import re
from pathlib import Path

# Mapping des endpoints anciens -> nouveaux
ENDPOINT_MAPPING = {
    # Main blueprint
    "'index'": "'main.index'",
    '"index"': '"main.index"',
    "'schedule'": "'main.schedule'",
    '"schedule"': '"main.schedule"',
    "'user_dashboard'": "'main.user_dashboard'",
    '"user_dashboard"': '"main.user_dashboard"',
    "'leave'": "'main.leave'",
    '"leave"': '"main.leave"',
    "'oncall'": "'main.oncall'",
    '"oncall"': '"main.oncall"',
    "'add_shift'": "'main.add_shift'",
    '"add_shift"': '"main.add_shift"',
    "'add_leave'": "'main.add_leave'",
    '"add_leave"': '"main.add_leave"',
    "'add_oncall'": "'main.add_oncall'",
    '"add_oncall"': '"main.add_oncall"',
    "'delete_shift'": "'main.delete_shift'",
    '"delete_shift"': '"main.delete_shift"',
    "'delete_leave'": "'main.delete_leave'",
    '"delete_leave"': '"main.delete_leave"',
    "'delete_oncall'": "'main.delete_oncall'",
    '"delete_oncall"': '"main.delete_oncall"',
    "'api_get_shifts'": "'main.api_get_shifts'",
    '"api_get_shifts"': '"main.api_get_shifts"',
    "'api_get_shift_types'": "'main.api_get_shift_types'",
    '"api_get_shift_types"': '"main.api_get_shift_types"',
    "'api_get_users'": "'main.api_get_users'",
    '"api_get_users"': '"main.api_get_users"',
    "'api_create_shift'": "'main.api_create_shift'",
    '"api_create_shift"': '"main.api_create_shift"',
    "'api_update_shift'": "'main.api_update_shift'",
    '"api_update_shift"': '"main.api_update_shift"',
    "'api_delete_shift'": "'main.api_delete_shift'",
    '"api_delete_shift"': '"main.api_delete_shift"',
    "'delete_all_shifts'": "'main.delete_all_shifts'",
    '"delete_all_shifts"': '"main.delete_all_shifts"',
    "'delete_all_shifts_for_day'": "'main.delete_all_shifts_for_day'",
    '"delete_all_shifts_for_day"': '"main.delete_all_shifts_for_day"',
    "'delete_all_shifts_for_user'": "'main.delete_all_shifts_for_user'",
    '"delete_all_shifts_for_user"': '"main.delete_all_shifts_for_user"',
    "'delete_all_shifts_for_week'": "'main.delete_all_shifts_for_week'",
    '"delete_all_shifts_for_week"': '"main.delete_all_shifts_for_week"',
    "'accessibility_statement'": "'main.accessibility_statement'",
    '"accessibility_statement"': '"main.accessibility_statement"',
    
    # Auth blueprint
    "'login'": "'auth.login'",
    '"login"': '"auth.login"',
    "'logout'": "'auth.logout'",
    '"logout"': '"auth.logout"',
    "'profile'": "'auth.profile'",
    '"profile"': '"auth.profile"',
    "'update_profile'": "'auth.update_profile'",
    '"update_profile"': '"auth.update_profile"',
    "'oidc_login'": "'auth.oidc_login'",
    '"oidc_login"': '"auth.oidc_login"',
    "'generate_ics_token'": "'auth.generate_ics_token'",
    '"generate_ics_token"': '"auth.generate_ics_token"',
    
    # Admin blueprint
    "'admin_dashboard'": "'admin.admin_dashboard'",
    '"admin_dashboard"': '"admin.admin_dashboard"',
    "'list_users'": "'admin.list_users'",
    '"list_users"': '"admin.list_users"',
    "'add_user'": "'admin.add_user'",
    '"add_user"': '"admin.add_user"',
    "'edit_user'": "'admin.edit_user'",
    '"edit_user"': '"admin.edit_user"',
    "'delete_user'": "'admin.delete_user'",
    '"delete_user"': '"admin.delete_user"',
    "'list_groups'": "'admin.list_groups'",
    '"list_groups"': '"admin.list_groups"',
    "'add_group'": "'admin.add_group'",
    '"add_group"': '"admin.add_group"',
    "'edit_group'": "'admin.edit_group'",
    '"edit_group"': '"admin.edit_group"',
    "'delete_group'": "'admin.delete_group'",
    '"delete_group"': '"admin.delete_group"',
    "'list_shift_types'": "'admin.list_shift_types'",
    '"list_shift_types"': '"admin.list_shift_types"',
    "'add_shift_type'": "'admin.add_shift_type'",
    '"add_shift_type"': '"admin.add_shift_type"',
    "'edit_shift_type'": "'admin.edit_shift_type'",
    '"edit_shift_type"': '"admin.edit_shift_type"',
    "'delete_shift_type'": "'admin.delete_shift_type'",
    '"delete_shift_type"': '"admin.delete_shift_type"',
    "'automation_dashboard'": "'admin.automation_dashboard'",
    '"automation_dashboard"': '"admin.automation_dashboard"',
    "'automation_shifts'": "'admin.automation_shifts'",
    '"automation_shifts"': '"admin.automation_shifts"',
    "'automation_full'": "'admin.automation_full'",
    '"automation_full"': '"admin.automation_full"',
    "'refresh_shifts'": "'admin.refresh_shifts'",
    '"refresh_shifts"': '"admin.refresh_shifts"',
    
    # Export blueprint
    "'export_shifts'": "'export.export_shifts'",
    '"export_shifts"': '"export.export_shifts"',
    "'export_oncall'": "'export.export_oncall'",
    '"export_oncall"': '"export.export_oncall"',
    "'export_leaves'": "'export.export_leaves'",
    '"export_leaves"': '"export.export_leaves"',
}


def fix_file(filepath):
    """Corrige les url_for dans un fichier."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Remplacer tous les mappings
    for old, new in ENDPOINT_MAPPING.items():
        content = content.replace(f"url_for({old})", f"url_for({new})")
        content = content.replace(f"url_for( {old} ", f"url_for( {new} ")
        content = content.replace(f"url_for({old},", f"url_for({new},")
        content = content.replace(f"url_for({old}) ", f"url_for({new}) ")
    
    # Si le fichier a été modifié, l'écrire
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    """Corrige tous les fichiers."""
    # Dossiers à scanner
    directories = ['tests/', 'app/templates/']
    
    modified_files = []
    
    for directory in directories:
        for filepath in Path(directory).rglob('*'):
            if filepath.is_file() and filepath.suffix in ['.py', '.html']:
                if fix_file(str(filepath)):
                    modified_files.append(str(filepath))
                    print(f"✅ Modified: {filepath}")
    
    print(f"\n📊 Summary: {len(modified_files)} files modified")
    
    if modified_files:
        print("\n📝 Modified files:")
        for f in modified_files[:10]:  # Affiche les 10 premiers
            print(f"  - {f}")
        if len(modified_files) > 10:
            print(f"  ... and {len(modified_files) - 10} more")


if __name__ == '__main__':
    main()
