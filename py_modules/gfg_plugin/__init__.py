"""
GFG Extreme package for Decky Loader.

This package provides services for installing and managing the GFG Engine
Vulkan layer for Lossless Scaling frame generation and spatial scaling.
"""

import sys

from .package_paths import PLUGIN_ROOT


# Decky Loader exposes only ``py_modules`` on sys.path. Add the containing
# plugin directory before importing services that consume shared_config.py.
plugin_root = str(PLUGIN_ROOT)
if plugin_root not in sys.path:
    sys.path.insert(0, plugin_root)

# With Decky's ``root`` flag: keep a root helper for TDP caps only and run the
# plugin itself as the desktop user, before any service touches the home.
try:
    import decky as _decky
    from .privileged_power import start_and_drop_privileges as _drop

    _drop(getattr(_decky, "DECKY_USER_HOME", None))
except ImportError:
    pass

try:
    from .plugin import Plugin
    __all__ = ['Plugin']
except ImportError:
    __all__ = []
