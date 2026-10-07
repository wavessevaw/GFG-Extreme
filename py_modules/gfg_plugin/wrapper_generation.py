"""Pure generation of GFG Extreme's managed game-launch wrapper.

The wrapper is disposable generated cache. Canonical profile and sidecar data
enter through explicit arguments, and this module returns shell text without
reading or writing user files. Compatibility migrations remain in the service
that owns those persisted inputs.
"""

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re
import shlex
from typing import Any, Callable, Dict, Optional

from shared_config import (
    FG_BACKEND_GFG,
    FG_BACKEND_OPTISCALER,
    OPTISCALER_PROXY_AUTO,
    OPTISCALER_PROXY_AUTODETECT_ORDER,
    EXTERNAL_VULKAN_LAYER_VKBASALT,
)
from .config_schema import ConfigurationManager, DEFAULT_PROFILE_NAME, ProfileData
from .config_schema_generated import (
    ConfigurationData,
    get_script_generation_logic,
)
from .constants import (
    COMPETING_LSFG_DISABLE_ENVS,
    DXVK_HDR_ENV,
    EXTERNAL_VULKAN_LAYER_ENV,
    EXTERNAL_VULKAN_LAYER_MANGOHUD,
    EXTERNAL_VULKAN_LAYER_VKBASALT,
    GAMESCOPE_WSI_DISABLE_ENV,
    GAMESCOPE_WSI_ENABLE_ENV,
    GAMESCOPE_WSI_LAYER_NAME_64,
    GAMESCOPE_WAYLAND_DISPLAY_ENV,
    HDR_EXPOSURE_DISABLE_ENV,
    MAKO_CONFIG_ENV,
    MAKO_LAYER_DISABLE_ENV,
    MAKO_LAYER_ENABLE_ENV,
    MAKO_LAYER_NAME,
    MAKO_PROFILE_ENV,
    MAKO_PROFILE_FALLBACK_ENV,
    MAKO_SPLIT_LAYER_CHAIN_COMBINED_PIPELINE,
    MAKO_SPLIT_LAYER_CHAIN_ENV,
    MANGOHUD_LAYER_NAME_64,
    PRESENT_ACQUIRE_TIMEOUT_ENV,
    PRESENT_ACQUIRE_TIMEOUT_MS,
    PRESENT_DIAGNOSTICS_ENV,
    PRESENT_DIAGNOSTICS_FALLBACK_LOG,
    PRESENT_DIAGNOSTICS_LOG_ENV,
    PRESENT_DIAGNOSTICS_LOG_FILENAME,
    PRESENT_DIAGNOSTICS_RETAINED_SESSION_COUNT,
    SPATIAL_SCALING_LAYER_DISABLE_ENV,
    SPATIAL_SCALING_LAYER_ENABLE_ENV,
    SPATIAL_SCALING_LAYER_NAME,
    STEAM_APP_ID_ENV_KEYS,
    VK_ADD_IMPLICIT_LAYER_PATH_ENV,
    VK_IMPLICIT_LAYER_PATH_ENV,
    VK_INSTANCE_LAYERS_ENV,
    VKBASALT_CONFIG_FILE_ENV,
    VKBASALT_CONFIG_RELOAD_ENV,
    VKBASALT_LAYER_DISABLE_ENV,
    VKBASALT_LAYER_ENABLE_ENV,
    VKBASALT_LAYER_NAME_64,
    WAYLAND_DISPLAY_ENV,
)
from .governor_overlay import overlay_path as governor_overlay_path
from .profile_storage import (
    ProfileMetadata,
    WrapperProfileSettings,
    config_for_profile,
    metadata_steam_app_id,
    processes_for_config,
    vkbasalt_config_path,
)


WRAPPER_FORMAT_VERSION = 81
WRAPPER_FORMAT_MARKER = f"# mako-wrapper-format: {WRAPPER_FORMAT_VERSION}"
HOST_COMPATIBILITY_MARKER = "# mako-host-compatibility: aarch64-passthrough-v1"
DIAGNOSTICS_DEFAULT_MARKER = (
    "# governor diagnostics: enabled only by runtime marker"
)
LEGACY_EXTREME_PFG_LAYER_NAME = "VK_LAYER_MAKO_EXTREME_predictive"
FRAME_OS_LAYER_NAME = "VK_LAYER_GFG_pacer"
FRAME_OS_MANIFEST_FILENAME = "VkLayer_gfg_pacer.json"

REQUIRED_WRAPPER_EXPORTS = (
    f"export {PRESENT_ACQUIRE_TIMEOUT_ENV}=",
    f"export {PRESENT_DIAGNOSTICS_ENV}=",
    f"export {MAKO_LAYER_ENABLE_ENV}=1",
    "mako_renderer_required=",
    "mako_renderer_enabled=",
    f"unset {MAKO_SPLIT_LAYER_CHAIN_ENV}",
    f"export {MAKO_SPLIT_LAYER_CHAIN_ENV}={MAKO_SPLIT_LAYER_CHAIN_COMBINED_PIPELINE}",
    *(f"export {variable}=1" for variable in COMPETING_LSFG_DISABLE_ENVS),
    f"export {GAMESCOPE_WSI_DISABLE_ENV}=1",
    f"unset {GAMESCOPE_WSI_ENABLE_ENV}",
    "mako_gamescope_wsi_required=",
    "mako_gamescope_wsi_session=",
    "mako_gamescope_wsi_skip_log=",
    f"export {SPATIAL_SCALING_LAYER_DISABLE_ENV}=1",
    f"unset {SPATIAL_SCALING_LAYER_ENABLE_ENV}",
    f"export {VKBASALT_LAYER_DISABLE_ENV}=1",
    f"unset {VKBASALT_LAYER_ENABLE_ENV}",
    f"unset {VKBASALT_CONFIG_RELOAD_ENV}",
    "mako_spatial_scaling_required=",
    f"export {EXTERNAL_VULKAN_LAYER_ENV}=",
    "mako_vkbasalt_config=",
    "mako_vkbasalt_enabled=",
    "mako_managed_instance_layers=",
    f"export {VK_INSTANCE_LAYERS_ENV}=",
    f"export {VK_IMPLICIT_LAYER_PATH_ENV}=",
    f"unset {VK_ADD_IMPLICIT_LAYER_PATH_ENV}",
    "mako_steam_overlay_layers=",
    f"export {MAKO_PROFILE_FALLBACK_ENV}=",
    "mako_diagnostics_default=",
    "mako_governor_overlay_active=",
)
def is_current_wrapper(
        content: str,
        wrapper_format_marker: str = WRAPPER_FORMAT_MARKER,
        host_compatibility_marker: str = HOST_COMPATIBILITY_MARKER,
        diagnostics_default_marker: str = DIAGNOSTICS_DEFAULT_MARKER,
        required_exports: tuple[str, ...] = REQUIRED_WRAPPER_EXPORTS,
) -> bool:
    """Return whether generated cache satisfies every current safety marker."""
    return (
        wrapper_format_marker in content
        and host_compatibility_marker in content
        and diagnostics_default_marker in content
        and all(export in content for export in required_exports)
    )


@dataclass(frozen=True)
class WrapperGenerationContext:
    """Paths and compatibility inputs embedded in one generated wrapper."""

    wrapper_format_marker: str
    host_compatibility_marker: str
    diagnostics_default_marker: str
    config_dir: Path
    config_file_path: Path
    runtime_state_dir: Path
    local_share_dir: Path
    renderer_bin_dir: Path
    user_vulkan_layer_dir: Path
    spatial_scaling_layer_dir: Path
    gamescope_wsi_compatibility_dir: Path
    mangohud_layer_dir: Path
    vkbasalt_layer_dir: Path
    vkbasalt_global_config_path: Path
    vkbasalt_profile_config_dir: Path
    flatpak_implicit_layer_dir: str
    gamescope_wsi_manifest_filename_64: str
    spatial_scaling_manifest_filename_64: str
    mangohud_manifest_filename_64: str
    mangohud_manifest_filename_32: str
    vkbasalt_manifest_filename_64: str
    vkbasalt_manifest_filename_32: str
    armada_device_env: Path
    armada_game_launch: Path
    frame_os_layer_dir: Optional[Path] = None


def has_active_in(config: ConfigurationData) -> bool:
    """Return whether an engine profile can select itself by process name."""
    active_in = config.get("active_in", "")
    if isinstance(active_in, (list, tuple)):
        return bool(active_in)
    return bool(str(active_in).strip())


def profile_selection_lines(
        profile_name: str,
        config: ConfigurationData,
        automatic_matching_enabled: Optional[bool] = None,
        active_predicate: Callable[
            [ConfigurationData], bool
        ] = has_active_in,
) -> list[str]:
    """Keep the renderer active while allowing automatic live matching."""
    if automatic_matching_enabled is None:
        automatic_matching_enabled = active_predicate(config)

    matching_comment = (
        "# GFG Engine prefers active_in matches and uses this profile only as a fallback."
        if automatic_matching_enabled
        else "# Keep the default renderer context active so a newly captured profile can take over live."
    )
    return [
        matching_comment,
        f"# A caller-provided {MAKO_PROFILE_ENV} remains an explicit hard override.",
        f'if [ -z "${{{MAKO_PROFILE_ENV}:-}}" ]; then',
        f"    export {MAKO_PROFILE_FALLBACK_ENV}={shlex.quote(profile_name)}",
        "fi",
    ]


def hdr_activation_lines(config: Dict[str, Any]) -> list[str]:
    """Keep the packaged Decky launcher on its proven SDR contract."""
    del config
    return [
        f"export {HDR_EXPOSURE_DISABLE_ENV}=1",
        f"unset {DXVK_HDR_ENV}",
    ]


def effective_runtime_config(config: ConfigurationData) -> ConfigurationData:
    """Resolve runtime ownership while keeping the saved profile untouched."""
    return ConfigurationManager.get_effective_runtime_config(config)



def _manifest_key(profile_name: str) -> str:
    return hashlib.sha256(profile_name.encode("utf-8")).hexdigest()[:16]


def governor_overlay_lines(profile_name: str, runtime_state_dir: Path) -> list[str]:
    """Name this profile's Governor overlay; selection happens at env export.

    The overlay lives next to the Saved config (``<config_dir>/governor-overlay``)
    so any sandbox that can read the Saved config can read the overlay too.
    """
    path = governor_overlay_path(Path(runtime_state_dir).parent, profile_name)
    return [f"mako_governor_overlay={shlex.quote(str(path))}"]


def governor_hud_lines(config_file_path: Path) -> list[str]:
    """Enable the GFG in-game HUD through the managed MangoHud layer.

    Only while the Governor service has published an active HUD config
    (``<config_dir>/hud/active.conf``).  With no external layer chosen the HUD
    becomes the external layer; next to vkBasalt (shader effects) it is stacked
    after vkBasalt by ``governor_hud_stack_lines`` so the text is not filtered.
    A user-chosen MangoHud keeps its own config.
    """
    active = shlex.quote(str(Path(config_file_path).parent / "hud" / "active.conf"))
    return [
        "mako_governor_hud=0",
        f"if [ -r {active} ]; then",
        '    if [ -z "$mako_external_vulkan_layer" ]; then',
        f"        mako_external_vulkan_layer={EXTERNAL_VULKAN_LAYER_MANGOHUD}",
        f"        export MANGOHUD_CONFIGFILE={active}",
        f'    elif [ "$mako_external_vulkan_layer" = {EXTERNAL_VULKAN_LAYER_VKBASALT} ]; then',
        "        mako_governor_hud=1",
        f"        export MANGOHUD_CONFIGFILE={active}",
        "    fi",
        "fi",
    ]


def governor_hud_stack_lines(mangohud_manifest: str, mangohud_manifest32: str) -> list[str]:
    """Add the GFG HUD (MangoHud) after an already selected vkBasalt layer."""
    return [
        'if [ "$mako_governor_hud" = 1 ] && [ "$mako_flatpak_runtime" != 1 ] && '
        f"{{ [ -r {mangohud_manifest} ] || [ -r {mangohud_manifest32} ]; }}; then",
        "    unset DISABLE_MANGOHUD",
        "    export MANGOHUD=1",
        "    export NODEVICE_SELECT=1",
        "    export DISABLE_LAYER_MESA_ANTI_LAG=1",
        '    mako_implicit_layer_path="$mako_implicit_layer_path:$mako_mangohud_layer_dir"',
        f"    if [ -r {mangohud_manifest} ]; then",
        '        mako_managed_external_layer="${mako_managed_external_layer:+$mako_managed_external_layer:}'
        f'{MANGOHUD_LAYER_NAME_64}"',
        "    fi",
        'elif [ "$mako_governor_hud" = 1 ]; then',
        "    unset MANGOHUD_CONFIGFILE",
        "fi",
        "unset mako_governor_hud",
    ]


def governor_overlay_selection_lines() -> list[str]:
    """Pick the overlay only while its owner lease is alive; else use Saved."""
    return [
        'mako_governor_overlay_active=""',
        'if [ -n "${mako_governor_overlay:-}" ] && [ -r "$mako_governor_overlay" ]; then',
        "    mako_governor_launch=\"$(sed -n 's/^# gfg-governor-launch: //p' \"$mako_governor_overlay\" 2>/dev/null | head -n 1)\"",
        '    mako_governor_owner="${mako_governor_launch##*owner=}"',
        '    mako_governor_owner="${mako_governor_owner%% *}"',
        '    case "$mako_governor_owner" in \'\'|*[!0-9]*) mako_governor_owner=0 ;; esac',
        '    if [ "$mako_governor_owner" -gt 0 ] && [ -d "/proc/$mako_governor_owner" ]; then',
        f'        export {MAKO_CONFIG_ENV}="$mako_governor_overlay"',
        '        mako_governor_overlay_active="$mako_governor_overlay"',
        "    fi",
        "fi",
        "unset mako_governor_overlay mako_governor_launch mako_governor_owner",
    ]


def launch_manifest_profile_lines(
        profile_name: str,
        config: ConfigurationData,
        runtime_state_dir: Path,
) -> list[str]:
    """Publish static saved/effective intent for the selected profile."""
    effective = effective_runtime_config(config)
    path = runtime_state_dir / "launches" / f"{_manifest_key(profile_name)}.json"
    renderer_required = bool(
        effective.get("frame_generation_provisioned", False)
        or effective.get("scaling_enabled", False)
        or config.get("external_vulkan_layer") == EXTERNAL_VULKAN_LAYER_VKBASALT
    )
    return [
        f"gfg_manifest_path={shlex.quote(str(path))}",
        f"gfg_manifest_saved_backend={shlex.quote(str(config.get('fg_backend', FG_BACKEND_GFG)))}",
        f"gfg_manifest_saved_fg={'true' if config.get('frame_generation_enabled', False) else 'false'}",
        f"gfg_manifest_saved_dock={'true' if config.get('automatic_dock_mode', False) else 'false'}",
        f"gfg_manifest_effective_fg={'true' if effective.get('frame_generation_enabled', False) else 'false'}",
        f"gfg_manifest_effective_dock={'true' if effective.get('automatic_dock_mode', False) else 'false'}",
        f"gfg_manifest_scaling={'true' if effective.get('scaling_enabled', False) else 'false'}",
        f"gfg_manifest_shaders={'true' if config.get('external_vulkan_layer') == EXTERNAL_VULKAN_LAYER_VKBASALT else 'false'}",
        f"gfg_manifest_renderer_required={'true' if renderer_required else 'false'}",
        f"gfg_manifest_proxy={shlex.quote(str(config.get('optiscaler_proxy', OPTISCALER_PROXY_AUTO)))}",
        f"gfg_manifest_target_fps={int(effective.get('target_fps', 0) or 0)}",
    ]


def launch_manifest_write_lines() -> list[str]:
    """Atomically record launch identity just before exec preserves the PID."""
    app_id_fallback = ""
    for environment_name in reversed(STEAM_APP_ID_ENV_KEYS):
        app_id_fallback = f"${{{environment_name}:-{app_id_fallback}}}"
    json_format = (
        '{"schema":1,"timestamp":%s,"pid":%s,"starttime":%s,'
        '"app_id":"%s","profile":"%s","wrapper":"%s","command":"%s",'
        '"saved":{"fg_backend":"%s","frame_generation_enabled":%s,"automatic_dock_mode":%s},'
        '"effective":{"frame_generation_enabled":%s,"automatic_dock_mode":%s,'
        '"scaling_enabled":%s,"shaders_enabled":%s,"renderer_required":%s,"target_fps":%s},'
        '"optiscaler_proxy":"%s","governor_launch":"%s"}\\n'
    )
    printf_line = (
        "    printf " + shlex.quote(json_format) +
        ' "$gfg_launch_timestamp" "$$" "$gfg_launch_starttime" "$gfg_launch_app_id" '
        '"$gfg_launch_profile" "$gfg_launch_wrapper" "$gfg_launch_command" '
        '"$gfg_manifest_saved_backend" "$gfg_manifest_saved_fg" "$gfg_manifest_saved_dock" '
        '"$gfg_manifest_effective_fg" "$gfg_manifest_effective_dock" "$gfg_manifest_scaling" '
        '"$gfg_manifest_shaders" "$gfg_manifest_renderer_required" "$gfg_manifest_target_fps" '
        '"$gfg_manifest_proxy" "$gfg_launch_governor" > "$gfg_launch_tmp" 2>/dev/null && '
        'mv -f "$gfg_launch_tmp" "$gfg_manifest_path" || rm -f "$gfg_launch_tmp"'
    )
    return [
        'if [ -n "${gfg_manifest_path:-}" ]; then',
        '    mkdir -p "$(dirname -- "$gfg_manifest_path")" 2>/dev/null || :',
        '    gfg_json_escape() {',
        '        local gfg_value="$1"',
        r'        gfg_value="${gfg_value//\\/\\\\}"',
        r'        gfg_value="${gfg_value//\"/\\\"}"',
        '        printf "%s" "$gfg_value"',
        '    }',
        f'    gfg_launch_app_id="{app_id_fallback}"',
        '    case "$gfg_launch_app_id" in *[!0-9]*) gfg_launch_app_id="" ;; esac',
        "    gfg_launch_starttime=\"$(awk '{print $22}' \"/proc/$$/stat\" 2>/dev/null || printf 0)\"",
        '    case "$gfg_launch_starttime" in *[!0-9]*|"") gfg_launch_starttime=0 ;; esac',
        '    gfg_launch_timestamp="$(date +%s 2>/dev/null || printf 0)"',
        '    gfg_launch_profile="$(gfg_json_escape "${mako_wrapper_profile:-mako}")"',
        '    gfg_launch_wrapper="$(gfg_json_escape "$0")"',
        '    gfg_launch_command="$(gfg_json_escape "${1:-}")"',
        '    gfg_launch_governor=""',
        '    if [ -n "${mako_governor_overlay_active:-}" ]; then',
        "        gfg_launch_governor=\"$(sed -n 's/^# gfg-governor-launch: //p' \"$mako_governor_overlay_active\" 2>/dev/null | head -n 1)\"",
        '        gfg_launch_governor="$(gfg_json_escape "$gfg_launch_governor")"',
        '    fi',
        '    gfg_launch_tmp="${gfg_manifest_path}.tmp.$$"',
        printf_line,
        # One line per launch in the user-action journal: what the game got.
        '    gfg_activity_log="$(dirname -- "$(dirname -- "$gfg_manifest_path")")/activity.jsonl"',
        '    gfg_launch_overlay=inactive',
        '    [ -n "${mako_governor_overlay_active:-}" ] && gfg_launch_overlay=active',
        "    printf " + shlex.quote(
            '{"ts":%s,"source":"wrapper","kind":"game-launch","pid":%s,"app_id":"%s","profile":"%s",'
            '"command":"%s","diagnostics":"%s","diagnostics_log":"%s","governor_overlay":"%s",'
            '"vk_instance_layers":"%s"}\\n'
        ) + ' "$gfg_launch_timestamp" "$$" "$gfg_launch_app_id" "$gfg_launch_profile" '
        '"$gfg_launch_command" "${mako_diagnostics_state:-off}" '
        '"$(gfg_json_escape "${mako_diagnostics_log:-}")" "$gfg_launch_overlay" '
        '"$(gfg_json_escape "${VK_INSTANCE_LAYERS:-}")" >> "$gfg_activity_log" 2>/dev/null || :',
        '    unset gfg_activity_log gfg_launch_overlay',
        '    unset -f gfg_json_escape',
        'fi',
        'unset mako_diagnostics_state mako_diagnostics_log',
    ]


def _case_insensitive_dll_glob(name: str) -> str:
    """Return a shell glob matching ``<name>.dll`` in any letter case."""
    letters = "".join(
        f"[{char.lower()}{char.upper()}]" if char.isalpha() else char
        for char in name
    )
    return f"{letters}.[dD][lL][lL]"


def fg_backend_lines(config: ConfigurationData, status_dir: Optional[Path] = None) -> list[str]:
    """Configure external FG ownership and optional OptiScaler proxy injection.

    Proxy discovery runs once at launch and never copies or downloads a DLL.
    It looks where OptiScaler actually lives, not only in the launch working
    directory: Steam starts the wrapper in the game's install root while the
    proxy sits beside the game executable (for example ``Binaries/Win64``).

    Discovery tiers, first match wins:
      1. a candidate directory holding ``OptiScaler.ini`` next to a proxy DLL;
      2. a bounded search for ``OptiScaler.ini`` below STEAM_COMPAT_INSTALL_PATH;
      3. the first proxy DLL (by name order) in any candidate directory.
    Candidate directories are the folders of ``*.exe`` launch arguments, then
    the working directory. Names match case-insensitively. An explicitly chosen
    proxy is always applied (native-then-builtin is harmless when absent) and
    reported as ``proxy-not-found`` when no DLL could be verified. Existing
    same-proxy ``WINEDLLOVERRIDES`` entries win and are reported as a conflict.
    """
    backend = config.get("fg_backend", FG_BACKEND_GFG)
    if backend != FG_BACKEND_OPTISCALER:
        return []
    requested = config.get("optiscaler_proxy", OPTISCALER_PROXY_AUTO)
    manual = requested != OPTISCALER_PROXY_AUTO
    names = (requested,) if manual else tuple(OPTISCALER_PROXY_AUTODETECT_ORDER)
    table = " ".join(
        shlex.quote(f"{name}:{_case_insensitive_dll_glob(name)}") for name in names
    )
    ini_glob = "[oO][pP][tT][iI][sS][cC][aA][lL][eE][rR].[iI][nN][iI]"
    lines = [
        f"gfg_optiscaler_requested={shlex.quote(requested)}",
        'gfg_optiscaler_proxy=""',
        'gfg_optiscaler_dir=""',
        'gfg_optiscaler_found=0',
        'gfg_optiscaler_how=""',
        f"gfg_optiscaler_table=( {table} )",
        'gfg_optiscaler_probe_dir() {',
        '    local gfg_dir="$1" gfg_entry gfg_glob gfg_file',
        '    [ -d "$gfg_dir" ] || return 1',
        '    for gfg_entry in "${gfg_optiscaler_table[@]}"; do',
        '        gfg_glob="${gfg_entry#*:}"',
        '        for gfg_file in "$gfg_dir"/$gfg_glob; do',
        '            if [ -f "$gfg_file" ]; then',
        '                gfg_optiscaler_proxy="${gfg_entry%%:*}"',
        '                gfg_optiscaler_dir="$gfg_dir"',
        '                gfg_optiscaler_found=1',
        '                return 0',
        '            fi',
        '        done',
        '    done',
        '    return 1',
        '}',
        'gfg_optiscaler_has_ini() {',
        '    local gfg_file',
        f'    for gfg_file in "$1"/{ini_glob}; do',
        '        [ -f "$gfg_file" ] && return 0',
        '    done',
        '    return 1',
        '}',
        'gfg_optiscaler_ini_dir() {',
        '    local gfg_ini=""',
        '    [ -d "$1" ] || return 1',
        '    if command -v timeout >/dev/null 2>&1; then',
        '        gfg_ini=$(timeout 3 find "$1" -maxdepth 6 -type f -iname '"'"'OptiScaler.ini'"'"' -print -quit 2>/dev/null)',
        '    else',
        '        gfg_ini=$(find "$1" -maxdepth 6 -type f -iname '"'"'OptiScaler.ini'"'"' -print -quit 2>/dev/null)',
        '    fi',
        '    [ -n "$gfg_ini" ] || return 1',
        '    printf "%s\\n" "${gfg_ini%/*}"',
        '}',
        'gfg_optiscaler_dirs=()',
        'for gfg_optiscaler_arg in "$@"; do',
        '    case "$gfg_optiscaler_arg" in',
        '        */*.[eE][xX][eE]) gfg_optiscaler_dirs+=("${gfg_optiscaler_arg%/*}") ;;',
        '    esac',
        'done',
        'gfg_optiscaler_dirs+=("$PWD")',
        'unset gfg_optiscaler_arg',
        'for gfg_optiscaler_candidate in "${gfg_optiscaler_dirs[@]}"; do',
        '    if gfg_optiscaler_has_ini "$gfg_optiscaler_candidate" && gfg_optiscaler_probe_dir "$gfg_optiscaler_candidate"; then',
        '        gfg_optiscaler_how="ini"',
        '        break',
        '    fi',
        'done',
        'if [ "$gfg_optiscaler_found" = 0 ] && [ -n "${STEAM_COMPAT_INSTALL_PATH:-}" ]; then',
        '    gfg_optiscaler_candidate="$(gfg_optiscaler_ini_dir "$STEAM_COMPAT_INSTALL_PATH")" \\',
        '        && gfg_optiscaler_probe_dir "$gfg_optiscaler_candidate" \\',
        '        && gfg_optiscaler_how="search"',
        'fi',
        'if [ "$gfg_optiscaler_found" = 0 ]; then',
        '    for gfg_optiscaler_candidate in "${gfg_optiscaler_dirs[@]}"; do',
        '        if gfg_optiscaler_probe_dir "$gfg_optiscaler_candidate"; then',
        '            gfg_optiscaler_how="name"',
        '            break',
        '        fi',
        '    done',
        'fi',
        'unset gfg_optiscaler_candidate gfg_optiscaler_dirs gfg_optiscaler_table',
        'unset -f gfg_optiscaler_probe_dir gfg_optiscaler_has_ini gfg_optiscaler_ini_dir',
    ]
    if manual:
        lines.append(f'gfg_optiscaler_proxy={shlex.quote(requested)}')
    ready_lines = (
        ['            gfg_optiscaler_status="ready"']
        if manual
        else [
            '            if [ "$gfg_optiscaler_how" = "name" ]; then',
            '                gfg_optiscaler_status="unverified"',
            '            else',
            '                gfg_optiscaler_status="ready"',
            '            fi',
        ]
    )
    lines.extend([
        'gfg_optiscaler_conflict=0',
        'gfg_optiscaler_override=""',
        'gfg_optiscaler_status="proxy-not-found"',
        # Wine DLL names and grouped override lists are case-insensitive.
        # Preserve the user's original override string.
        'gfg_optiscaler_overrides_lower="${WINEDLLOVERRIDES,,}"',
        'gfg_optiscaler_override_conflicts() {',
        '    local gfg_target="$1" gfg_entry gfg_lhs gfg_name',
        '    local -a gfg_names=()',
        '    local IFS=";"',
        '    for gfg_entry in $gfg_optiscaler_overrides_lower; do',
        '        gfg_lhs="${gfg_entry%%=*}"',
        '        IFS="," read -r -a gfg_names <<< "$gfg_lhs"',
        '        for gfg_name in "${gfg_names[@]}"; do',
        '            [ "$gfg_name" = "$gfg_target" ] && return 0',
        '        done',
        '    done',
        '    return 1',
        '}',
        'if [ -n "$gfg_optiscaler_proxy" ]; then',
        '    if gfg_optiscaler_override_conflicts "$gfg_optiscaler_proxy"; then',
        '        gfg_optiscaler_conflict=1',
        '        gfg_optiscaler_override="external:${gfg_optiscaler_proxy}"',
        '        gfg_optiscaler_status="external-override"',
        '    else',
        '        export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:+$WINEDLLOVERRIDES;}${gfg_optiscaler_proxy}=n,b"',
        '        gfg_optiscaler_override="${gfg_optiscaler_proxy}=n,b"',
        '        if [ "$gfg_optiscaler_found" = 1 ]; then',
        *ready_lines,
        '        fi',
        '    fi',
        'fi',
        'unset gfg_optiscaler_overrides_lower',
        'unset -f gfg_optiscaler_override_conflicts',
    ])
    if status_dir is not None:
        status_path = shlex.quote(str(status_dir / "gfg-extreme-optiscaler.status"))
        lines.extend([
            f'gfg_optiscaler_status_path={status_path}',
            'mkdir -p "$(dirname -- "$gfg_optiscaler_status_path")" 2>/dev/null || :',
            'gfg_optiscaler_tmp="${gfg_optiscaler_status_path}.tmp.$$"',
            '{',
            '    printf "backend=optiscaler\\n"',
            '    printf "profile=%s\\n" "${mako_wrapper_profile:-mako}"',
            '    printf "requested=%s\\n" "$gfg_optiscaler_requested"',
            '    printf "detected=%s\\n" "$gfg_optiscaler_proxy"',
            '    printf "status=%s\\n" "$gfg_optiscaler_status"',
            '    printf "conflict=%s\\n" "$gfg_optiscaler_conflict"',
            '    printf "override=%s\\n" "$gfg_optiscaler_override"',
            '    printf "dir=%s\\n" "$gfg_optiscaler_dir"',
            '    printf "how=%s\\n" "$gfg_optiscaler_how"',
            '} > "$gfg_optiscaler_tmp" 2>/dev/null && mv -f "$gfg_optiscaler_tmp" "$gfg_optiscaler_status_path" || rm -f "$gfg_optiscaler_tmp"',
        ])
    return lines


def script_configuration_lines(
        config: ConfigurationData,
        hdr_lines: Callable[
            [Dict[str, Any]], list[str]
        ] = hdr_activation_lines,
        status_dir: Optional[Path] = None,
) -> list[str]:
    """Generate wrapper settings without repeating forced compatibility exports."""
    effective = effective_runtime_config(config)
    lines = get_script_generation_logic()(config)
    if config.get("fg_backend", FG_BACKEND_GFG) != FG_BACKEND_GFG:
        # Renderer v4 already supports these environment overrides. They are the
        # non-destructive runtime projection of the saved GFG Engine settings.
        lines.extend([
            "export MAKO_FRAME_GENERATION_PROVISIONED=0",
            "export MAKO_FRAME_GENERATION_ENABLED=0",
        ])
    # WSI is an independent, restart-only compatibility choice. Without it,
    # the combined Renderer owns scaling and Frame Generation. Only an
    # explicitly selected WSI path needs the lower spatial role for scaling.
    lines.append(
        "mako_gamescope_wsi_required="
        f"{1 if config.get('gamescope_wsi_compatibility', False) else 0}"
    )
    lines.append(
        "mako_renderer_required="
        f"{1 if (effective.get('frame_generation_provisioned', True) or effective.get('scaling_enabled', False) or config.get('external_vulkan_layer') == EXTERNAL_VULKAN_LAYER_VKBASALT) else 0}"
    )
    lines.append(
        "mako_spatial_scaling_required="
        f"{1 if (effective.get('scaling_enabled', False) and effective.get('gamescope_wsi_compatibility', False)) else 0}"
    )
    lines.extend(fg_backend_lines(config, status_dir))
    for line in hdr_lines(config):
        if line not in lines:
            lines.append(line)
    return lines


def vkbasalt_profile_environment_lines(
        profile_name: str,
        config: ConfigurationData,
        global_config_path: Path,
        profile_config_dir: Path,
        steam_app_id: Optional[str] = None,
) -> list[str]:
    """Select the automatic global or saved-profile vkBasalt config."""
    config_path = ""
    if config.get("external_vulkan_layer") == EXTERNAL_VULKAN_LAYER_VKBASALT:
        config_path = str(
            vkbasalt_config_path(
                profile_name,
                global_config_path,
                profile_config_dir,
                steam_app_id,
            )
        )
    return [f"mako_vkbasalt_config={shlex.quote(config_path)}"]


def unsupported_host_passthrough_lines(
        armada_device_env: Path,
        armada_game_launch: Path,
        indent: str = "",
) -> list[str]:
    """Disable MAKO and preserve Armada's launcher exactly once."""
    device_env = armada_device_env.as_posix()
    game_launch = armada_game_launch.as_posix()
    return [
        f"{indent}unset {MAKO_LAYER_ENABLE_ENV}",
        f"{indent}export {MAKO_LAYER_DISABLE_ENV}=1",
        f'{indent}armada_game_launch="{game_launch}"',
        f'{indent}if [ -f "{device_env}" ] && [ -x "$armada_game_launch" ]; then',
        f'{indent}    for argument in "$@"; do',
        f'{indent}        if [ "$argument" = "$armada_game_launch" ]; then',
        f'{indent}            exec "$@"',
        f"{indent}        fi",
        f"{indent}    done",
        f'{indent}    exec "$armada_game_launch" "$@"',
        f"{indent}fi",
        f'{indent}exec "$@"',
    ]


def host_compatibility_guard_lines(
        armada_device_env: Path,
        armada_game_launch: Path,
        compatibility_marker: str = HOST_COMPATIBILITY_MARKER,
        passthrough_lines: Optional[list[str]] = None,
) -> list[str]:
    """Bypass MAKO before any exports on unsupported AArch64 hosts."""
    device_env = armada_device_env.as_posix()
    return [
        compatibility_marker,
        'mako_native_arch="$(uname -m 2>/dev/null || true)"',
        f'if [ -f "{device_env}" ] || [ "$mako_native_arch" = "aarch64" ] || [ "$mako_native_arch" = "arm64" ]; then',
        "    # This release has no validated native AArch64 Renderer.",
        *(
            passthrough_lines
            if passthrough_lines is not None
            else unsupported_host_passthrough_lines(
                armada_device_env,
                armada_game_launch,
                "    ",
            )
        ),
        "fi",
    ]


def layer_environment_lines(context: WrapperGenerationContext) -> list[str]:
    """Activate MAKO through its deterministic Vulkan discovery boundary."""
    if PRESENT_DIAGNOSTICS_RETAINED_SESSION_COUNT < 1:
        raise ValueError("managed diagnostics must retain at least one session")
    diagnostics_log_path = context.config_dir / PRESENT_DIAGNOSTICS_LOG_FILENAME
    diagnostics_history_paths = " ".join(
        '"$mako_diagnostics_log' + (f".{index}" if index else "") + '"'
        for index in range(PRESENT_DIAGNOSTICS_RETAINED_SESSION_COUNT)
    )
    diagnostics_rotation_lines: list[str] = []
    for retained_index in range(
            PRESENT_DIAGNOSTICS_RETAINED_SESSION_COUNT - 1,
            0,
            -1,
    ):
        source_suffix = "" if retained_index == 1 else f".{retained_index - 1}"
        target_suffix = f".{retained_index}"
        diagnostics_rotation_lines.extend([
            (
                '        if [ "$mako_diagnostics_rotation_ready" = 1 ] && '
                f'[ -f "$mako_diagnostics_log{source_suffix}" ] && ! mv -fT -- '
                f'"$mako_diagnostics_log{source_suffix}" '
                f'"$mako_diagnostics_log{target_suffix}" 2>/dev/null; then'
            ),
            "            mako_diagnostics_rotation_ready=0",
            "        fi",
        ])
    gamescope_wsi_manifest = shlex.quote(str(
        context.gamescope_wsi_compatibility_dir /
        context.gamescope_wsi_manifest_filename_64
    ))
    gamescope_wsi_layer_dir = shlex.quote(str(
        context.gamescope_wsi_compatibility_dir
    ))
    spatial_scaling_manifest = shlex.quote(str(
        context.spatial_scaling_layer_dir /
        context.spatial_scaling_manifest_filename_64
    ))
    spatial_scaling_layer_dir = shlex.quote(str(
        context.spatial_scaling_layer_dir
    ))
    mangohud_manifest = shlex.quote(str(
        context.mangohud_layer_dir / context.mangohud_manifest_filename_64
    ))
    mangohud_manifest32 = shlex.quote(str(
        context.mangohud_layer_dir / context.mangohud_manifest_filename_32
    ))
    mangohud_layer_dir = shlex.quote(str(context.mangohud_layer_dir))
    vkbasalt_manifest = shlex.quote(str(
        context.vkbasalt_layer_dir / context.vkbasalt_manifest_filename_64
    ))
    vkbasalt_manifest32 = shlex.quote(str(
        context.vkbasalt_layer_dir / context.vkbasalt_manifest_filename_32
    ))
    vkbasalt_layer_dir = shlex.quote(str(context.vkbasalt_layer_dir))
    steam_overlay_manifest64 = shlex.quote(str(
        context.user_vulkan_layer_dir / "steamoverlay_x86_64.json"
    ))
    steam_overlay_manifest32 = shlex.quote(str(
        context.user_vulkan_layer_dir / "steamoverlay_i386.json"
    ))
    user_vulkan_layer_dir = shlex.quote(str(context.user_vulkan_layer_dir))
    frame_os_layer_dir = context.frame_os_layer_dir or context.local_share_dir.parent / "gfg-frame-os"
    inherited_managed_layer_removal_lines: list[str] = []
    for layer_name in (
        MAKO_LAYER_NAME,
        SPATIAL_SCALING_LAYER_NAME,
        GAMESCOPE_WSI_LAYER_NAME_64,
        VKBASALT_LAYER_NAME_64,
        LEGACY_EXTREME_PFG_LAYER_NAME,
        FRAME_OS_LAYER_NAME,
    ):
        inherited_managed_layer_removal_lines.extend((
            (
                'while [[ "$mako_existing_instance_layers" == *":'
                f'{layer_name}:"* ]]; do'
            ),
            (
                '    mako_existing_instance_layers="'
                '${mako_existing_instance_layers/:'
                f'{layer_name}:/:}}"'
            ),
            "done",
        ))
    return [
        f'export {PRESENT_ACQUIRE_TIMEOUT_ENV}="${{{PRESENT_ACQUIRE_TIMEOUT_ENV}:-{PRESENT_ACQUIRE_TIMEOUT_MS}}}"',
        # Governor owns the marker and keeps it while installed: diagnostics are
        # read once at game start, so every managed launch carries them and the
        # Governor can be turned on in a game that is already running.
        f'mako_governor_diagnostics_marker={shlex.quote(str(context.runtime_state_dir / "governor-diagnostics.enabled"))}',
        f'if [ -f "$mako_governor_diagnostics_marker" ]; then export {PRESENT_DIAGNOSTICS_ENV}="${{{PRESENT_DIAGNOSTICS_ENV}:-1}}"; else export {PRESENT_DIAGNOSTICS_ENV}="${{{PRESENT_DIAGNOSTICS_ENV}:-0}}"; fi',
        'unset mako_governor_diagnostics_marker',
        # GFG Frame OS (development): the gfg-pacer layer loads only when the Governor left this
        # marker and the layer is installed; the layer itself stays pass-through until the
        # control file it is pointed at says otherwise. It never joins through its implicit
        # gate: implicit order follows directory listing order, so the layer is named first in
        # the explicit list below (above the renderer) or not at all.
        f'gfg_frame_os_marker={shlex.quote(str(context.runtime_state_dir / "frame-os.enabled"))}',
        "gfg_frame_os=0",
        'if [ -f "$gfg_frame_os_marker" ] && [ -r '
        f'{shlex.quote(str(frame_os_layer_dir / FRAME_OS_MANIFEST_FILENAME))} ]; then',
        "    gfg_frame_os=1",
        '    export GFG_FRAME_OS_SHM="${GFG_FRAME_OS_SHM:-/dev/shm/gfg-frame-os}"',
        "fi",
        "unset GFG_FRAME_OS",
        "export DISABLE_GFG_FRAME_OS=1",
        'unset gfg_frame_os_marker',
        "mako_renderer_enabled=0",
        'if [ "${mako_renderer_required:-0}" = 1 ] && '
        f'[ "${{{MAKO_LAYER_DISABLE_ENV}:-0}}" != 1 ]; then',
        f"    unset {MAKO_LAYER_DISABLE_ENV}",
        f"    export {MAKO_LAYER_ENABLE_ENV}=1",
        "    mako_renderer_enabled=1",
        "else",
        f"    unset {MAKO_LAYER_ENABLE_ENV}",
        f"    export {MAKO_LAYER_DISABLE_ENV}=1",
        "fi",
        f"unset {MAKO_SPLIT_LAYER_CHAIN_ENV}",
        *(f"export {variable}=1" for variable in COMPETING_LSFG_DISABLE_ENVS),
        f"export {GAMESCOPE_WSI_DISABLE_ENV}=1",
        f"unset {GAMESCOPE_WSI_ENABLE_ENV}",
        f"export {SPATIAL_SCALING_LAYER_DISABLE_ENV}=1",
        f"unset {SPATIAL_SCALING_LAYER_ENABLE_ENV}",
        f'mako_existing_instance_layers=":${{{VK_INSTANCE_LAYERS_ENV}:-}}:"',
        *inherited_managed_layer_removal_lines,
        'mako_existing_instance_layers="${mako_existing_instance_layers#:}"',
        'mako_existing_instance_layers="${mako_existing_instance_layers%:}"',
        'if [ -n "$mako_existing_instance_layers" ]; then',
        f'    export {VK_INSTANCE_LAYERS_ENV}="$mako_existing_instance_layers"',
        "else",
        f"    unset {VK_INSTANCE_LAYERS_ENV}",
        "fi",
        "mako_managed_instance_layers=",
        "mako_managed_external_layer=",
        "mako_steam_overlay_layers=",
        "mako_gamescope_wsi_session=0",
        "mako_gamescope_wsi_skip_log=",
        f'if [ -n "${{{GAMESCOPE_WAYLAND_DISPLAY_ENV}:-}}" ] && '
        f'{{ [ -z "${{{WAYLAND_DISPLAY_ENV}:-}}" ] || '
        f'[ "${{{WAYLAND_DISPLAY_ENV}}}" = "${{{GAMESCOPE_WAYLAND_DISPLAY_ENV}}}" ]; }}; then',
        "    mako_gamescope_wsi_session=1",
        "fi",
        f'mako_external_vulkan_layer="${{{EXTERNAL_VULKAN_LAYER_ENV}:-}}"',
        f"unset {EXTERNAL_VULKAN_LAYER_ENV}",
        f"mako_gamescope_wsi_layer_dir={gamescope_wsi_layer_dir}",
        f"mako_spatial_scaling_layer_dir={spatial_scaling_layer_dir}",
        f"mako_mangohud_layer_dir={mangohud_layer_dir}",
        f"mako_vkbasalt_layer_dir={vkbasalt_layer_dir}",
        "mako_vkbasalt_enabled=0",
        "mako_flatpak_runtime=0",
        "mako_flatpak_launch=0",
        'if [ "${1##*/}" = flatpak ] && [ "${2:-}" = run ]; then',
        "    mako_flatpak_launch=1",
        "fi",
        "unset MANGOHUD",
        f"unset {VKBASALT_CONFIG_FILE_ENV}",
        f"unset {VKBASALT_CONFIG_RELOAD_ENV}",
        f"export {VKBASALT_LAYER_DISABLE_ENV}=1",
        f"unset {VKBASALT_LAYER_ENABLE_ENV}",
        f"if [ -d {shlex.quote(context.flatpak_implicit_layer_dir)} ] || "
        '[ "$mako_flatpak_launch" = 1 ]; then',
        f"    mako_implicit_layer_path={shlex.quote(context.flatpak_implicit_layer_dir)}",
        "    mako_flatpak_runtime=1",
        "    mako_spatial_scaling_manifest=\"$mako_implicit_layer_path/"
        f"{context.spatial_scaling_manifest_filename_64}\"",
        "    mako_vkbasalt_manifest=\"$mako_implicit_layer_path/"
        f"{context.vkbasalt_manifest_filename_64}\"",
        "    mako_vkbasalt_manifest32=\"$mako_implicit_layer_path/"
        f"{context.vkbasalt_manifest_filename_32}\"",
        '    mako_vkbasalt_layer_dir="$mako_implicit_layer_path"',
        "else",
        f"    mako_implicit_layer_path={shlex.quote(str(context.local_share_dir))}",
        f"    mako_spatial_scaling_manifest={spatial_scaling_manifest}",
        f"    mako_vkbasalt_manifest={vkbasalt_manifest}",
        f"    mako_vkbasalt_manifest32={vkbasalt_manifest32}",
        "fi",
        # Preserve the established Renderer -> Gamescope WSI -> spatial order.
        # Flatpak preparation stages the host's own WSI binary beside its
        # guarded manifest, so Heroic and EmuDeck use this same chain without
        # exposing or searching the host's global Vulkan layer directory.
        'if [ "$mako_renderer_enabled" = 1 ] && '
        '[ "${mako_gamescope_wsi_required:-0}" = 1 ] && '
        '[ "$mako_gamescope_wsi_session" = 1 ] && [ -r '
        f"{gamescope_wsi_manifest} ] && "
        '( [ "${mako_spatial_scaling_required:-0}" != 1 ] || '
        '[ -r "$mako_spatial_scaling_manifest" ] || '
        '[ "$mako_flatpak_launch" = 1 ] ) && '
        f'[ "${{{MAKO_LAYER_DISABLE_ENV}:-0}}" != 1 ]; then',
        '    if [ "${mako_spatial_scaling_required:-0}" = 1 ]; then',
        f"        export {MAKO_SPLIT_LAYER_CHAIN_ENV}={MAKO_SPLIT_LAYER_CHAIN_COMBINED_PIPELINE}",
        "    fi",
        f"    unset {GAMESCOPE_WSI_DISABLE_ENV}",
        f"    export {GAMESCOPE_WSI_ENABLE_ENV}=1",
        "    export NODEVICE_SELECT=1",
        "    export DISABLE_LAYER_MESA_ANTI_LAG=1",
        f"    mako_managed_instance_layers={MAKO_LAYER_NAME}:{GAMESCOPE_WSI_LAYER_NAME_64}",
        '    mako_implicit_layer_path="$mako_implicit_layer_path:$mako_gamescope_wsi_layer_dir"',
        '    if [ "${mako_spatial_scaling_required:-0}" = 1 ]; then',
        f"        unset {SPATIAL_SCALING_LAYER_DISABLE_ENV}",
        f"        export {SPATIAL_SCALING_LAYER_ENABLE_ENV}=1",
        f'        mako_managed_instance_layers="$mako_managed_instance_layers:{SPATIAL_SCALING_LAYER_NAME}"',
        '        if [ "$mako_flatpak_runtime" != 1 ]; then',
        '            mako_implicit_layer_path="$mako_implicit_layer_path:$mako_spatial_scaling_layer_dir"',
        "        fi",
        "    fi",
        'elif [ "$mako_renderer_enabled" = 1 ] && '
        '[ "${mako_gamescope_wsi_required:-0}" = 1 ] && '
        '[ "$mako_gamescope_wsi_session" != 1 ]; then',
        '    mako_gamescope_wsi_skip_log="GFG Extreme: Gamescope WSI skipped: no active Gamescope session; continuing with the managed WSI and spatial chain disabled."',
        "fi",
        *governor_hud_lines(context.config_file_path),
        'case "$mako_external_vulkan_layer" in',
        f"        {EXTERNAL_VULKAN_LAYER_MANGOHUD})",
        '            if [ "$mako_flatpak_runtime" != 1 ] && '
        f"{{ [ -r {mangohud_manifest} ] || [ -r {mangohud_manifest32} ]; }}; then",
        "                unset DISABLE_MANGOHUD",
        "                export MANGOHUD=1",
        "                export NODEVICE_SELECT=1",
        "                export DISABLE_LAYER_MESA_ANTI_LAG=1",
        '                mako_implicit_layer_path="$mako_implicit_layer_path:$mako_mangohud_layer_dir"',
        f"                if [ -r {mangohud_manifest} ]; then",
        f"                    mako_managed_external_layer={MANGOHUD_LAYER_NAME_64}",
        "                fi",
        "            fi",
        "            ;;",
        f"        {EXTERNAL_VULKAN_LAYER_VKBASALT})",
        "            if { [ -z \"$mako_vkbasalt_config\" ] || "
        "[ -r \"$mako_vkbasalt_config\" ]; } && "
        "{ [ -r \"$mako_vkbasalt_manifest\" ] || "
        "[ -r \"$mako_vkbasalt_manifest32\" ] || "
        "[ \"$mako_flatpak_launch\" = 1 ]; }; then",
        '                if [ -n "$mako_vkbasalt_config" ]; then',
        f'                    export {VKBASALT_CONFIG_FILE_ENV}="$mako_vkbasalt_config"',
        f"                    export {VKBASALT_CONFIG_RELOAD_ENV}=1",
        "                fi",
        f"                unset {VKBASALT_LAYER_DISABLE_ENV}",
        f"                export {VKBASALT_LAYER_ENABLE_ENV}=1",
        "                mako_vkbasalt_enabled=1",
        "                export NODEVICE_SELECT=1",
        "                export DISABLE_LAYER_MESA_ANTI_LAG=1",
        '                if [ "$mako_flatpak_runtime" != 1 ]; then',
        '                    mako_implicit_layer_path="$mako_implicit_layer_path:$mako_vkbasalt_layer_dir"',
        "                fi",
        '                if [ -r "$mako_vkbasalt_manifest" ] || '
        '[ "$mako_flatpak_launch" = 1 ]; then',
        f"                    mako_managed_external_layer={VKBASALT_LAYER_NAME_64}",
        "                fi",
        "            fi",
        "            ;;",
        "esac",
        *governor_hud_stack_lines(mangohud_manifest, mangohud_manifest32),
        # Steam installs its architecture-specific overlay manifests in the
        # standard per-user implicit directory. MAKO keeps that directory out
        # of implicit discovery, but Desktop Mode can safely expose it only as
        # an explicit-layer source and place the overlay after MAKO. This keeps
        # Steam's FPS counter without admitting Fossilize or arbitrary implicit
        # layers. Gaming Mode retains its compositor-owned performance path.
        f'if [ "${{ENABLE_VK_LAYER_VALVE_steam_overlay_1:-0}}" = 1 ] && '
        '[ "$mako_gamescope_wsi_session" != 1 ] && '
        '[ "$mako_flatpak_runtime" != 1 ] && '
        f'{{ [ -r {steam_overlay_manifest64} ] || '
        f'[ -r {steam_overlay_manifest32} ]; }}; then',
        f"    if [ -r {steam_overlay_manifest64} ]; then",
        "        mako_steam_overlay_layers=VK_LAYER_VALVE_steam_overlay_64",
        "    fi",
        f"    if [ -r {steam_overlay_manifest32} ]; then",
        '        mako_steam_overlay_layers="${mako_steam_overlay_layers:+$mako_steam_overlay_layers:}VK_LAYER_VALVE_steam_overlay_32"',
        "    fi",
        f"    mako_steam_overlay_layer_dir={user_vulkan_layer_dir}",
        '    export VK_LAYER_PATH="$mako_steam_overlay_layer_dir${VK_LAYER_PATH:+:$VK_LAYER_PATH}"',
        "    for mako_steam_overlay_layer in VK_LAYER_VALVE_steam_overlay_64 VK_LAYER_VALVE_steam_overlay_32; do",
        '        mako_existing_instance_layers=":$mako_existing_instance_layers:"',
        '        while [[ "$mako_existing_instance_layers" == *":$mako_steam_overlay_layer:"* ]]; do',
        '            mako_existing_instance_layers="${mako_existing_instance_layers/:$mako_steam_overlay_layer:/:}"',
        "        done",
        '        mako_existing_instance_layers="${mako_existing_instance_layers#:}"',
        '        mako_existing_instance_layers="${mako_existing_instance_layers%:}"',
        "    done",
        '    if [ "$mako_renderer_enabled" = 1 ] && [ -z "$mako_managed_instance_layers" ]; then',
        f"        mako_managed_instance_layers={MAKO_LAYER_NAME}",
        "    fi",
        "fi",
        # Frame OS: the pacer must see the game's real frames, so it goes above the renderer.
        # The renderer then also needs the explicit list (its implicit gate is cleared below).
        # Flatpak sandboxes do not get the layer until it is staged there.
        'if [ "$gfg_frame_os" = 1 ] && [ "$mako_flatpak_runtime" != 1 ]; then',
        '    if [ "$mako_renderer_enabled" = 1 ] && [ -z "$mako_managed_instance_layers" ]; then',
        f"        mako_managed_instance_layers={MAKO_LAYER_NAME}",
        "    fi",
        f'    mako_managed_instance_layers="{FRAME_OS_LAYER_NAME}${{mako_managed_instance_layers:+:$mako_managed_instance_layers}}"',
        f'    mako_implicit_layer_path="$mako_implicit_layer_path:"{shlex.quote(str(frame_os_layer_dir))}',
        "fi",
        "unset gfg_frame_os",
        # Clear retired PFG environment from old launch-option experiments.
        "unset MAKO_EXTREME_PFG",
        "unset DISABLE_MAKO_EXTREME_PFG",
        'if [ -n "$mako_managed_instance_layers" ]; then',
        '    if [ -n "$mako_managed_external_layer" ]; then',
        '        mako_managed_instance_layers="$mako_managed_instance_layers:$mako_managed_external_layer"',
        "    fi",
        '    if [ -n "$mako_steam_overlay_layers" ]; then',
        '        mako_managed_instance_layers="$mako_managed_instance_layers:$mako_steam_overlay_layers"',
        "    fi",
        '    if [ -n "$mako_existing_instance_layers" ]; then',
        f'        export {VK_INSTANCE_LAYERS_ENV}="$mako_managed_instance_layers:$mako_existing_instance_layers"',
        "    else",
        f'        export {VK_INSTANCE_LAYERS_ENV}="$mako_managed_instance_layers"',
        "    fi",
        # Prevent the same manifests from joining first through their implicit
        # activation gates. The explicit list above is the only owner of the
        # managed WSI/scaling order on this supported 64-bit path.
        f"    unset {MAKO_LAYER_ENABLE_ENV}",
        f"    unset {GAMESCOPE_WSI_ENABLE_ENV}",
        f"    unset {SPATIAL_SCALING_LAYER_ENABLE_ENV}",
        '    case ":$mako_managed_external_layer:" in',
        f'        *":{MANGOHUD_LAYER_NAME_64}:"*) unset MANGOHUD ;;',
        "    esac",
        '    case ":$mako_managed_external_layer:" in',
        f'        *":{VKBASALT_LAYER_NAME_64}:"*) unset {VKBASALT_LAYER_ENABLE_ENV} ;;',
        "    esac",
        'elif [ -n "$mako_steam_overlay_layers" ]; then',
        '    if [ -n "$mako_existing_instance_layers" ]; then',
        f'        export {VK_INSTANCE_LAYERS_ENV}="$mako_steam_overlay_layers:$mako_existing_instance_layers"',
        "    else",
        f'        export {VK_INSTANCE_LAYERS_ENV}="$mako_steam_overlay_layers"',
        "    fi",
        "fi",
        "unset mako_gamescope_wsi_required",
        "unset mako_gamescope_wsi_session",
        "unset mako_spatial_scaling_required",
        "unset mako_external_vulkan_layer",
        "unset mako_gamescope_wsi_layer_dir",
        "unset mako_spatial_scaling_layer_dir",
        "unset mako_mangohud_layer_dir",
        "unset mako_vkbasalt_layer_dir",
        "unset mako_steam_overlay_layer_dir",
        "unset mako_steam_overlay_layer",
        "unset mako_steam_overlay_layers",
        "unset mako_existing_instance_layers",
        "unset mako_managed_instance_layers",
        "unset mako_managed_external_layer",
        "unset mako_spatial_scaling_manifest",
        "unset mako_vkbasalt_manifest",
        "unset mako_vkbasalt_manifest32",
        f'export {VK_IMPLICIT_LAYER_PATH_ENV}="$mako_implicit_layer_path"',
        f"unset {VK_ADD_IMPLICIT_LAYER_PATH_ENV}",
        f"export {MAKO_CONFIG_ENV}={shlex.quote(str(context.config_file_path))}",
        *governor_overlay_selection_lines(),
        # A direct EmuDeck/Flatpak shortcut executes this wrapper on the host.
        # Per-launch Flatpak options must override its persisted app-wide
        # preparation so the explicit managed chain and the selected bundled
        # vkBasalt profile survive into the sandbox.
        'if [ "${1##*/}" = flatpak ] && [ "${2:-}" = run ]; then',
        '    mako_flatpak_command="$1"',
        "    shift",
        '    mako_flatpak_subcommand="$1"',
        "    shift",
        '    set -- "$mako_flatpak_command" "$mako_flatpak_subcommand" '
        f'--env={VK_IMPLICIT_LAYER_PATH_ENV}="${{{VK_IMPLICIT_LAYER_PATH_ENV}}}" '
        f'--env={MAKO_CONFIG_ENV}="${{{MAKO_CONFIG_ENV}}}" '
        f'--unset-env={VK_ADD_IMPLICIT_LAYER_PATH_ENV} '
        '"$@"',
        '    if [ "$mako_renderer_enabled" = 1 ] && '
        f'[ -z "${{{VK_INSTANCE_LAYERS_ENV}:-}}" ]; then',
        '        set -- "$mako_flatpak_command" "$mako_flatpak_subcommand" '
        f'--env={MAKO_LAYER_ENABLE_ENV}=1 '
        f'--unset-env={MAKO_LAYER_DISABLE_ENV} '
        '"${@:3}"',
        '    elif [ "$mako_renderer_enabled" != 1 ]; then',
        '        set -- "$mako_flatpak_command" "$mako_flatpak_subcommand" '
        f'--unset-env={MAKO_LAYER_ENABLE_ENV} '
        f'--env={MAKO_LAYER_DISABLE_ENV}=1 '
        '"${@:3}"',
        "    fi",
        f'    if [ -n "${{{VK_INSTANCE_LAYERS_ENV}:-}}" ]; then',
        '        set -- "$mako_flatpak_command" "$mako_flatpak_subcommand" '
        f'--env={VK_INSTANCE_LAYERS_ENV}="${{{VK_INSTANCE_LAYERS_ENV}}}" '
        f'--unset-env={MAKO_LAYER_ENABLE_ENV} '
        f'--unset-env={MAKO_LAYER_DISABLE_ENV} '
        f'--unset-env={GAMESCOPE_WSI_ENABLE_ENV} '
        f'--unset-env={GAMESCOPE_WSI_DISABLE_ENV} '
        f'--unset-env={SPATIAL_SCALING_LAYER_ENABLE_ENV} '
        f'--unset-env={SPATIAL_SCALING_LAYER_DISABLE_ENV} '
        '"${@:3}"',
        "    fi",
        f'    if [ -n "${{{MAKO_SPLIT_LAYER_CHAIN_ENV}:-}}" ]; then',
        '        set -- "$mako_flatpak_command" "$mako_flatpak_subcommand" '
        f'--env={MAKO_SPLIT_LAYER_CHAIN_ENV}="${{{MAKO_SPLIT_LAYER_CHAIN_ENV}}}" '
        '"${@:3}"',
        "    fi",
        '    if [ "$mako_vkbasalt_enabled" = 1 ]; then',
        '        set -- "$mako_flatpak_command" "$mako_flatpak_subcommand" '
        f'--unset-env={VKBASALT_LAYER_DISABLE_ENV} '
        '"${@:3}"',
        f'        if [ "${{{VKBASALT_LAYER_ENABLE_ENV}:-0}}" = 1 ]; then',
        '            set -- "$mako_flatpak_command" "$mako_flatpak_subcommand" '
        f'--env={VKBASALT_LAYER_ENABLE_ENV}=1 "${{@:3}}"',
        "        fi",
        f'        if [ -n "${{{VKBASALT_CONFIG_FILE_ENV}:-}}" ]; then',
        '            set -- "$mako_flatpak_command" "$mako_flatpak_subcommand" '
        f'--env={VKBASALT_CONFIG_FILE_ENV}="${{{VKBASALT_CONFIG_FILE_ENV}}}" '
        f'--env={VKBASALT_CONFIG_RELOAD_ENV}=1 '
        '"${@:3}"',
        "        fi",
        "    fi",
        "    unset mako_flatpak_command",
        "    unset mako_flatpak_subcommand",
        "fi",
        "unset mako_vkbasalt_config",
        "unset mako_vkbasalt_enabled",
        "unset mako_renderer_required",
        "unset mako_renderer_enabled",
        "unset mako_flatpak_runtime",
        "unset mako_flatpak_launch",
        "# Heroic can discard a game's stderr. Capture opt-in engine diagnostics here instead.",
        f"mako_diagnostics_default={shlex.quote(str(diagnostics_log_path))}",
        "mako_diagnostics_state=off",
        f'if [ "${{{PRESENT_DIAGNOSTICS_ENV}:-0}}" != "0" ]; then',
        "    mako_diagnostics_state=unavailable",
        f'    mako_diagnostics_log="${{{PRESENT_DIAGNOSTICS_LOG_ENV}:-$mako_diagnostics_default}}"',
        "    mako_diagnostics_rotation_ready=1",
        f"    for mako_diagnostics_entry in {diagnostics_history_paths}; do",
        '        if [ -L "$mako_diagnostics_entry" ] || { [ -e "$mako_diagnostics_entry" ] && { [ ! -f "$mako_diagnostics_entry" ] || [ ! -O "$mako_diagnostics_entry" ]; }; }; then',
        "            mako_diagnostics_rotation_ready=0",
        "            break",
        "        fi",
        "    done",
        "    # A stale log or rotation owned by another user (or a symlink) used to disable",
        "    # diagnostics silently. The default log lives in our own config dir: drop them.",
        '    if [ "$mako_diagnostics_rotation_ready" = 0 ] && [ "$mako_diagnostics_log" = "$mako_diagnostics_default" ]; then',
        "        mako_diagnostics_rotation_ready=1",
        f"        for mako_diagnostics_entry in {diagnostics_history_paths}; do",
        '            if [ -L "$mako_diagnostics_entry" ] || { [ -f "$mako_diagnostics_entry" ] && [ ! -O "$mako_diagnostics_entry" ]; }; then',
        '                rm -f -- "$mako_diagnostics_entry" 2>/dev/null || mako_diagnostics_rotation_ready=0',
        '            elif [ -e "$mako_diagnostics_entry" ] && [ ! -f "$mako_diagnostics_entry" ]; then',
        "                mako_diagnostics_rotation_ready=0",
        "            fi",
        "        done",
        "    fi",
        '    if [ "$mako_diagnostics_rotation_ready" = 1 ] && [ -f "$mako_diagnostics_log" ]; then',
        *diagnostics_rotation_lines,
        "    fi",
        (
            '    if [ "$mako_diagnostics_rotation_ready" = 1 ] && '
            '(set -C; : > "$mako_diagnostics_log") 2>/dev/null; then'
        ),
        '        exec 2>> "$mako_diagnostics_log"',
        "        mako_diagnostics_state=log",
        "    else",
        "        # Last resort: the Governor also reads this RAM log (newest wins).",
        f"        mako_diagnostics_log={shlex.quote(PRESENT_DIAGNOSTICS_FALLBACK_LOG)}",
        '        if { [ ! -e "$mako_diagnostics_log" ] && [ ! -L "$mako_diagnostics_log" ] && (set -C; : > "$mako_diagnostics_log") 2>/dev/null; } || '
        '{ [ ! -L "$mako_diagnostics_log" ] && [ -f "$mako_diagnostics_log" ] && [ -O "$mako_diagnostics_log" ] && : > "$mako_diagnostics_log"; }; then',
        '            exec 2>> "$mako_diagnostics_log"',
        "            mako_diagnostics_state=fallback",
        "        fi",
        "    fi",
        "fi",
        "unset mako_diagnostics_entry",
        'if [ -n "${mako_gamescope_wsi_skip_log:-}" ]; then',
        '    printf "%s\\n" "$mako_gamescope_wsi_skip_log" >&2',
        "fi",
        "unset mako_gamescope_wsi_skip_log",
    ]


def wrapper_profile_configuration_lines(
        profile_data: ProfileData,
        profile_settings: WrapperProfileSettings,
        metadata: ProfileMetadata,
        vkbasalt_global_config_path: Optional[Path] = None,
        vkbasalt_profile_config_dir: Optional[Path] = None,
        profile_config: Callable[
            [ProfileData, str, WrapperProfileSettings], ConfigurationData
        ] = config_for_profile,
        config_lines: Callable[
            [ConfigurationData], list[str]
        ] = script_configuration_lines,
        runtime_state_dir: Optional[Path] = None,
) -> list[str]:
    """Select launcher-only settings by explicit profile or Steam app ID."""
    global_config_path = (
        vkbasalt_global_config_path
        if vkbasalt_global_config_path is not None
        else Path("/nonexistent/vkBasalt.conf")
    )
    profile_config_dir = (
        vkbasalt_profile_config_dir
        if vkbasalt_profile_config_dir is not None
        else Path("/nonexistent/mako-vkbasalt")
    )
    current_profile = profile_data["current_profile"]
    app_id_fallback = ""
    for environment_name in reversed(STEAM_APP_ID_ENV_KEYS):
        app_id_fallback = f"${{{environment_name}:-{app_id_fallback}}}"
    app_profiles = [
        (entry.get("steam_app_id"), profile_name)
        for profile_name, entry in metadata.items()
        if re.fullmatch(r"\d+", str(entry.get("steam_app_id") or ""))
    ]
    process_profiles = [
        (profile_name, processes_for_config(config))
        for profile_name, config in profile_data["profiles"].items()
        if profile_name != DEFAULT_PROFILE_NAME
        and processes_for_config(config)
    ]

    lines = [
        f'mako_wrapper_profile="${{{MAKO_PROFILE_ENV}:-}}"',
        "mako_wrapper_profile_from_identity=0",
        f'mako_wrapper_app_id="{app_id_fallback}"',
        'if [ -z "$mako_wrapper_profile" ]; then',
        '    if [ -n "$mako_wrapper_app_id" ]; then',
        '        case "$mako_wrapper_app_id" in',
    ]
    for app_id, profile_name in app_profiles:
        lines.extend([
            f"            {app_id})",
            f"                mako_wrapper_profile={shlex.quote(profile_name)}",
            "                mako_wrapper_profile_from_identity=1",
            "                ;;",
        ])
    lines.extend([
        "            *)",
        f"                mako_wrapper_profile={shlex.quote(DEFAULT_PROFILE_NAME if DEFAULT_PROFILE_NAME in profile_data['profiles'] else current_profile)}",
        "                ;;",
        "        esac",
        "    else",
        '        case " $* " in',
    ])
    for profile_name, processes in process_profiles:
        patterns = "|".join(
            f"*{shlex.quote(process_name)}*" for process_name in processes
        )
        lines.extend([
            f"            {patterns})",
            f"                mako_wrapper_profile={shlex.quote(profile_name)}",
            "                mako_wrapper_profile_from_identity=1",
            "                ;;",
        ])
    lines.extend([
        "            *)",
        f"                mako_wrapper_profile={shlex.quote(current_profile)}",
        "                ;;",
        "        esac",
        "    fi",
        "fi",
        'case "$mako_wrapper_profile" in',
    ])

    for profile_name in profile_data["profiles"]:
        config = profile_config(
            profile_data,
            profile_name,
            profile_settings,
        )
        lines.append(f"    {shlex.quote(profile_name)})")
        lines.extend(
            f"        {line}" for line in config_lines(config)
        )
        if runtime_state_dir is not None:
            lines.extend(
                f"        {line}" for line in launch_manifest_profile_lines(
                    profile_name, config, runtime_state_dir
                )
            )
            lines.extend(
                f"        {line}" for line in governor_overlay_lines(
                    profile_name, runtime_state_dir
                )
            )
        lines.extend(
            f"        {line}" for line in vkbasalt_profile_environment_lines(
                profile_name,
                config,
                global_config_path,
                profile_config_dir,
                metadata_steam_app_id(metadata, profile_name),
            )
        )
        lines.append("        ;;")

    fallback_config = profile_config(
        profile_data,
        current_profile,
        profile_settings,
    )
    lines.append("    *)")
    lines.extend(
        f"        {line}"
        for line in config_lines(fallback_config)
    )
    if runtime_state_dir is not None:
        lines.extend(
            f"        {line}" for line in launch_manifest_profile_lines(
                current_profile, fallback_config, runtime_state_dir
            )
        )
        lines.extend(
            f"        {line}" for line in governor_overlay_lines(
                current_profile, runtime_state_dir
            )
        )
    lines.extend(
        f"        {line}" for line in vkbasalt_profile_environment_lines(
            current_profile,
            fallback_config,
            global_config_path,
            profile_config_dir,
            metadata_steam_app_id(metadata, current_profile),
        )
    )
    lines.extend([
        "        ;;",
        "esac",
        'if [ "$mako_wrapper_profile_from_identity" = "1" ]; then',
        f'    export {MAKO_PROFILE_ENV}="$mako_wrapper_profile"',
        "fi",
    ])
    return lines


def assemble_script_content(
        context: WrapperGenerationContext,
        host_guard_lines: list[str],
        configuration_lines: list[str],
        layer_lines: list[str],
        selection_lines: list[str],
) -> str:
    """Assemble a single-profile wrapper from explicit generated sections."""
    lines = [
        "#!/bin/bash",
        context.wrapper_format_marker,
        context.diagnostics_default_marker,
        "# mako launch script generated by GFG Extreme",
        "# This script sets up the environment for mako to work with the plugin configuration",
    ]
    lines.extend(host_guard_lines)
    lines.extend(configuration_lines)
    lines.extend(layer_lines)
    lines.extend(selection_lines)
    lines.extend(launch_manifest_write_lines())
    lines.extend(vrr_lease_lines(context))
    lines.append('exec "$@"')
    return "\n".join(lines) + "\n"


def assemble_profile_script_content(
        current_profile: str,
        context: WrapperGenerationContext,
        host_guard_lines: list[str],
        profile_configuration_lines: list[str],
        layer_lines: list[str],
        selection_lines: list[str],
) -> str:
    """Assemble a multi-profile wrapper from explicit generated sections."""
    lines = [
        "#!/bin/bash",
        context.wrapper_format_marker,
        context.diagnostics_default_marker,
        f"# Current profile: {current_profile}",
    ]
    lines.extend(host_guard_lines)
    lines.extend(profile_configuration_lines)
    lines.extend(layer_lines)
    lines.extend(selection_lines)
    lines.extend(launch_manifest_write_lines())
    lines.extend(vrr_lease_lines(context))
    lines.append('exec "$@"')
    return "\n".join(lines) + "\n"


def vrr_lease_lines(context: WrapperGenerationContext) -> list[str]:
    """Attach a detached live Gamescope lease without changing exec semantics."""
    helper = shlex.quote(str(context.renderer_bin_dir / "mako-vrr-lease"))
    return [
        f'if [ -n "${{{GAMESCOPE_WAYLAND_DISPLAY_ENV}:-}}" ] && '
        f'{{ [ -z "${{{WAYLAND_DISPLAY_ENV}:-}}" ] || '
        f'[ "${{{WAYLAND_DISPLAY_ENV}}}" = "${{{GAMESCOPE_WAYLAND_DISPLAY_ENV}}}" ]; }} && '
        f'[ -x {helper} ]; then',
        '    export MAKO_VRR_LEASE_TOKEN="$$-$RANDOM-$RANDOM"',
        f'    {helper} --start "$$" "$MAKO_VRR_LEASE_TOKEN" || :',
        'fi',
    ]


def generate_script_content(
        config: ConfigurationData,
        context: WrapperGenerationContext,
) -> str:
    """Generate the isolated single-profile launch script."""
    return assemble_script_content(
        context,
        host_compatibility_guard_lines(
            context.armada_device_env,
            context.armada_game_launch,
            context.host_compatibility_marker,
        ),
        [
            *script_configuration_lines(config, status_dir=context.runtime_state_dir),
            *vkbasalt_profile_environment_lines(
                DEFAULT_PROFILE_NAME,
                config,
                context.vkbasalt_global_config_path,
                context.vkbasalt_profile_config_dir,
            ),
        ],
        layer_environment_lines(context),
        profile_selection_lines(DEFAULT_PROFILE_NAME, config),
    )


def generate_profile_script_content(
        profile_data: ProfileData,
        profile_settings: WrapperProfileSettings,
        metadata: ProfileMetadata,
        context: WrapperGenerationContext,
) -> str:
    """Generate the isolated multi-profile launch script."""
    current_profile = profile_data["current_profile"]
    fallback_profile = (
        DEFAULT_PROFILE_NAME
        if DEFAULT_PROFILE_NAME in profile_data["profiles"]
        else current_profile
    )
    fallback_config = config_for_profile(
        profile_data,
        fallback_profile,
        profile_settings,
    )
    automatic_matching_enabled = any(
        has_active_in(profile_config)
        for profile_config in profile_data["profiles"].values()
    )
    return assemble_profile_script_content(
        current_profile,
        context,
        host_compatibility_guard_lines(
            context.armada_device_env,
            context.armada_game_launch,
            context.host_compatibility_marker,
        ),
        wrapper_profile_configuration_lines(
            profile_data,
            profile_settings,
            metadata,
            context.vkbasalt_global_config_path,
            context.vkbasalt_profile_config_dir,
            config_lines=lambda cfg: script_configuration_lines(
                cfg, status_dir=context.runtime_state_dir
            ),
        ),
        layer_environment_lines(context),
        profile_selection_lines(
            fallback_profile,
            fallback_config,
            automatic_matching_enabled,
        ),
    )
