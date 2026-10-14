# Windows service installation

The legacy migration-based service installer has been superseded by the [Windows Setup wizard and upgrade process](WINDOWS_INSTALLER.md).

On Windows, double-click `BUILD-INSTALLER.cmd` in the source kit to compile the setup executable. Do **not** uninstall a running service before applying the new installer; it upgrades the existing service in place and retains ProgramData.
