"""Plex Cast Explorer local administrative commands."""
import getpass
import sys
from app import set_password


def main():
    if sys.argv[1:] != ['set-password']:
        print('Usage: python manage.py set-password')
        return 2
    print('Set a password for Cast Explorer LAN access. Minimum 12 characters.')
    first = getpass.getpass('New gallery password: ')
    second = getpass.getpass('Confirm password: ')
    if first != second:
        print('Passwords did not match. Nothing changed.')
        return 1
    try:
        set_password(first)
    except ValueError as exc:
        print(exc)
        return 1
    print('Password updated. Existing browser sessions are now invalid. Restart is not required.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
