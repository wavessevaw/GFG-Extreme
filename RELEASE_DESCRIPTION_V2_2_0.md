# GFG Extreme 2.2.0 — SteamOS appearance preview

Built-in black/red Steam Gaming Mode appearance. No CSS Loader dependency.

- Settings → GFG theme → GFG SteamOS; explicit restore action.
- Styles for eight Steam surfaces, native actions and navigation retained.
- Automatic reconnect after UI reload; expiring styles restore Steam after a lost backend connection.
- Separate persisted appearance preference; off by default during preview.

This candidate has synthetic browser coverage. It has not been verified on physical Steam Deck hardware or against a specific Steam Stable/Beta build. The approved concept's custom layouts are not reproduced exactly; this implementation styles Steam's existing interface.

See docs/GFG_STEAMOS_SHELL.md for installation, recovery and validation limits. Stable 2.1.1 remains the recommended release until device verification.
