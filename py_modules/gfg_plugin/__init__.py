"""GFG Extreme 3.0 backend package. ``Plugin`` is imported lazily: it needs Decky's runtime."""


def __getattr__(name):
    if name == "Plugin":
        from .plugin import Plugin
        return Plugin
    raise AttributeError(name)
