"""EU4 monthly autosave mod builder.

Generates and installs a minimal EU4 mod that forces an autosave on every
in-game month via a hidden ``country_event`` triggered by ``on_monthly_pulse``.
"""


from .mod_builder import ModBuilder, ModInstallResult, ModInstallStatus

__all__ = ["ModBuilder", "ModInstallResult", "ModInstallStatus"]
