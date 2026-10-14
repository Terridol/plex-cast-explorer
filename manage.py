"""Plex Cast Explorer local-only administrative commands (never exposed via HTTP)."""
import getpass
import sys
from app import set_password, set_admin_password


def main():
    commands = {'set-password': (set_password, 'gallery password', 12),
                'set-admin-password': (set_admin_password, 'REMOTE ADMIN password', 16)}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        print('Usage: python manage.py set-password | set-admin-password')
        return 2
    setter, label, minimum = commands[sys.argv[1]]
    print(f'Set a {label} (minimum {minimum} characters).')
    first = getpass.getpass(f'New {label}: ')
    second = getpass.getpass('Confirm: ')
    if first != second:
        print('Passwords do not match. No changes were made.')
        return 1
    try:
        setter(first)
    except ValueError as exc:
        print(exc)
        return 1
    print(f'{label.capitalize()} updated; prior sessions for this role are invalid.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
