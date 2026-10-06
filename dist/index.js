// Decky Loader will pass this api in, it's versioned to allow for backwards compatibility.
// @ts-ignore

// Prevents it from being duplicated in output.
const manifest = {"name":"GFG Extreme","author":"Eugenio Segala","flags":[],"api_version":1,"publish":{"tags":["installer","vulkan","gfg-extreme","framegen","lossless-scaling","scaling","shaders","vkbasalt","steam-machine"],"description":"GFG Extreme: streamlined frame generation, adaptive display sync, scaling, and shader controls for SteamOS."}};
const API_VERSION = 2;
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
// Initialize
if (!internalAPIConnection) {
    throw new Error('[@decky/api]: Failed to connect to the loader as as the loader API was not initialized. This is likely a bug in Decky Loader.');
}
// Version 1 throws on version mismatch so we have to account for that here.
let api;
try {
    api = internalAPIConnection.connect(API_VERSION, manifest.name);
}
catch {
    api = internalAPIConnection.connect(1, manifest.name);
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version 1. Some features may not work.`);
}
if (api._version != API_VERSION) {
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version ${api._version}. Some features may not work.`);
}
const callable = api.callable;
const toaster = api.toaster;
const definePlugin = (fn) => {
    return (...args) => {
        // TODO: Maybe wrap this
        return fn(...args);
    };
};

var DefaultContext = {
  color: undefined,
  size: undefined,
  className: undefined,
  style: undefined,
  attr: undefined
};
var IconContext = SP_REACT.createContext && /*#__PURE__*/SP_REACT.createContext(DefaultContext);

var _excluded = ["attr", "size", "title"];
function _objectWithoutProperties(source, excluded) { if (source == null) return {}; var target = _objectWithoutPropertiesLoose(source, excluded); var key, i; if (Object.getOwnPropertySymbols) { var sourceSymbolKeys = Object.getOwnPropertySymbols(source); for (i = 0; i < sourceSymbolKeys.length; i++) { key = sourceSymbolKeys[i]; if (excluded.indexOf(key) >= 0) continue; if (!Object.prototype.propertyIsEnumerable.call(source, key)) continue; target[key] = source[key]; } } return target; }
function _objectWithoutPropertiesLoose(source, excluded) { if (source == null) return {}; var target = {}; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { if (excluded.indexOf(key) >= 0) continue; target[key] = source[key]; } } return target; }
function _extends() { _extends = Object.assign ? Object.assign.bind() : function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; }; return _extends.apply(this, arguments); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), !0).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(obj, key, value) { key = _toPropertyKey(key); if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == typeof i ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != typeof t || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r || "default"); if ("object" != typeof i) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
function Tree2Element(tree) {
  return tree && tree.map((node, i) => /*#__PURE__*/SP_REACT.createElement(node.tag, _objectSpread({
    key: i
  }, node.attr), Tree2Element(node.child)));
}
function GenIcon(data) {
  return props => /*#__PURE__*/SP_REACT.createElement(IconBase, _extends({
    attr: _objectSpread({}, data.attr)
  }, props), Tree2Element(data.child));
}
function IconBase(props) {
  var elem = conf => {
    var {
        attr,
        size,
        title
      } = props,
      svgProps = _objectWithoutProperties(props, _excluded);
    var computedSize = size || conf.size || "1em";
    var className;
    if (conf.className) className = conf.className;
    if (props.className) className = (className ? className + " " : "") + props.className;
    return /*#__PURE__*/SP_REACT.createElement("svg", _extends({
      stroke: "currentColor",
      fill: "currentColor",
      strokeWidth: "0"
    }, conf.attr, attr, svgProps, {
      className: className,
      style: _objectSpread(_objectSpread({
        color: props.color || conf.color
      }, conf.style), props.style),
      height: computedSize,
      width: computedSize,
      xmlns: "http://www.w3.org/2000/svg"
    }), title && /*#__PURE__*/SP_REACT.createElement("title", null, title), props.children);
  };
  return IconContext !== undefined ? /*#__PURE__*/SP_REACT.createElement(IconContext.Consumer, null, conf => elem(conf)) : elem(DefaultContext);
}

// THIS FILE IS AUTO GENERATED
function GiSharkFin (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M349.603 42.768c-31.36-1.053-234.946 205.685-280.595 309.828 26.998-7.923 58.257-15.23 82.4-13.004 22.594 2.083 40.82 15.274 57.844 26.603 17.023 11.33 32.575 20.703 48.654 20.416 16.378-.29 32.196-11.74 49.502-24.862 17.306-13.122 36.175-27.944 60.272-27.812 6.093.033 12.397.946 18.79 2.505-56.174-100.224-21.42-289.766-36.062-293.598-.255-.04-.523-.065-.805-.074zm21.586 312.37c-24.097-.13-42.966 14.69-60.272 27.813-17.306 13.123-33.124 24.573-49.502 24.864-16.08.287-31.63-9.086-48.654-20.416-17.023-11.33-35.25-24.52-57.844-26.603-25.39-2.34-58.66 5.86-86.557 14.234-27.895 8.372-50.07 17.28-50.07 17.28l6.706 16.702s21.492-8.624 48.54-16.743c27.047-8.12 60-15.37 79.73-13.55 16.277 1.5 32.278 12.186 49.523 23.663 17.244 11.476 36 23.838 58.946 23.43 24.043-.43 42.793-15.428 60.057-28.518 17.264-13.09 32.97-24.245 49.3-24.156 17.393.094 46.024 13.347 68.952 27.23 22.928 13.882 40.662 27.745 40.662 27.745l11.09-14.176s-18.476-14.464-42.43-28.967c-23.954-14.504-52.877-29.696-78.178-29.834zm1.91 41.12c-24.097-.132-42.966 14.69-60.272 27.812-17.306 13.122-33.124 24.572-49.502 24.864-16.08.286-31.63-9.087-48.654-20.416-17.023-11.33-35.25-24.52-57.844-26.604-25.39-2.34-58.66 5.86-86.557 14.234-27.895 8.374-50.07 17.28-50.07 17.28l6.708 16.703s21.49-8.623 48.537-16.74c27.048-8.12 60.002-15.37 79.73-13.552 16.28 1.5 32.28 12.187 49.524 23.664 17.244 11.477 36 23.84 58.946 23.43 24.044-.43 42.795-15.427 60.06-28.518 17.263-13.09 32.966-24.245 49.296-24.156 17.394.095 46.025 13.348 68.953 27.23 22.928 13.883 40.662 27.748 40.662 27.748l11.092-14.177s-18.476-14.464-42.43-28.968c-23.955-14.504-52.88-29.696-78.18-29.834z"},"child":[]}]})(props);
}

// src/config/generatedConfigSchema.ts
// Stable cross-language profile contract
const DEFAULT_PROFILE_NAME = "mako";
const MAKO_WRAPPER_RELATIVE_PATH = ".local/bin/mako-run";
const PER_GAME_WRAPPER_FLATPAK_APP_IDS = [
    "com.heroicgameslauncher.hgl",
    "net.lutris.Lutris",
];
const PROFILE_KIND_DEFAULT = "default";
const PROFILE_KIND_GAME = "game";
// Ordered Flatpak runtime contract generated from shared_config.py
const SUPPORTED_FLATPAK_RUNTIMES = [
    { version: "23.08", statusField: "installed_23_08", i18nKey: "FLATPAK_RUNTIME_VERSION" },
    { version: "24.08", statusField: "installed_24_08", i18nKey: "FLATPAK_RUNTIME_VERSION" },
    { version: "25.08", statusField: "installed_25_08", i18nKey: "FLATPAK_RUNTIME_VERSION" },
];
// Shared backend validation and Decky UI limits
const BASE_FPS_CAP_MIN = 0;
const BASE_FPS_CAP_UI_MAX = 120;
const TARGET_FPS_MIN = 30;
const TARGET_FPS_MAX = 240;
const ADAPTIVE_MINIMUM_BASE_FPS = 10;
const ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_AUTO = "auto";
const ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_LOW = "low";
const ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_MEDIUM = "medium";
const ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_HIGH = "high";
const ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_VERY_HIGH = "very-high";
const DYNAMIC_CADENCE_PROBE_INTERVAL_SECONDS_VALUES = [
    0.1,
    0.2,
    0.25,
    0.5,
    0.75,
    1.0,
    1.5,
    2.0,
    3.0,
];
const FLOW_SCALE_MIN = 0.25;
const FLOW_SCALE_MAX = 1.0;
const SCALING_FACTOR_MIN = 1.0;
const SCALING_FACTOR_MAX = 2.0;
const SCALING_METHOD_NATIVE = "native";
const SCALING_METHOD_MAKO = "mako";
const SCALING_METHOD_LS1 = "ls1";
const SCALING_METHOD_LS1_PERFORMANCE = "ls1-performance";
const FG_BACKEND_GFG = "gfg";
const FG_BACKEND_OPTISCALER = "optiscaler";
const FG_BACKEND_NATIVE = "native";
const FG_BACKEND_OFF = "off";
const OPTISCALER_PROXY_AUTO = "auto";
const OPTISCALER_PROXY_VALUES = ["auto", "dxgi", "winmm", "d3d12", "version", "wininet", "winhttp", "dbghelp"];
const SCALING_SHARPNESS_MIN = 0.0;
const SCALING_SHARPNESS_MAX = 1.0;
const ULTRA_PERFORMANCE_FLOW_SCALE = 0.7;
const FRAME_GENERATION_REFRESH_THRESHOLD_MAX = 240;
const FRAME_GENERATION_REFRESH_THRESHOLD_UI_MIN = 30;
const FRAME_GENERATION_REFRESH_THRESHOLD_PRESET = 60;
// Stable persisted values for the optional post-process Vulkan layer
const EXTERNAL_VULKAN_LAYER_NONE = "";
const EXTERNAL_VULKAN_LAYER_MANGOHUD = "mangohud";
const EXTERNAL_VULKAN_LAYER_VKBASALT = "vkbasalt";
// Decky-owned vkBasalt controls
const VKBASALT_SHARPENING_NONE = "none";
const VKBASALT_SHARPENING_CAS = "cas";
const VKBASALT_SHARPENING_DLS = "dls";
const VKBASALT_ANTIALIASING_NONE = "none";
const VKBASALT_ANTIALIASING_FXAA = "fxaa";
const VKBASALT_ANTIALIASING_SMAA = "smaa";
const VKBASALT_SHADER_NONE = "none";
const VKBASALT_SHADER_VIBRANCE = "vibrance";
const VKBASALT_SHADER_CURVES = "curves";
const VKBASALT_SHADER_DEBAND = "deband";
const VKBASALT_SHADER_TECHNICOLOR = "technicolor";
const VKBASALT_SHADER_SEPIA = "sepia";
const VKBASALT_SHADER_MONOCHROME = "monochrome";
const VKBASALT_SHADER_VIGNETTE = "vignette";
const VKBASALT_SHADER_HDR_LOOK = "hdr_look";
const VKBASALT_SHADER_COLOURFULNESS = "colourfulness";
const VKBASALT_SHADER_TECHNICOLOR2 = "technicolor2";
const VKBASALT_SHADER_DPX = "dpx";
const VKBASALT_SHADER_BLEACH_BYPASS = "bleach_bypass";
const VKBASALT_SHADER_NOIR = "noir";
const VKBASALT_SHADER_FILM_GRAIN = "film_grain";
const VKBASALT_SHADER_CARTOON = "cartoon";
const VKBASALT_SHADER_NOSTALGIA = "nostalgia";
const VKBASALT_SHADER_CHROMATIC_ABERRATION = "chromatic_aberration";
const VKBASALT_SHADER_CLARITY = "clarity";
const VKBASALT_SHADER_LEVELS_PLUS = "levels_plus";
const VKBASALT_STRENGTH_MIN = 0.0;
const VKBASALT_STRENGTH_MAX = 1.0;
// Configuration field type enum - matches Python
var ConfigFieldType;
(function (ConfigFieldType) {
    ConfigFieldType["BOOLEAN"] = "boolean";
    ConfigFieldType["INTEGER"] = "integer";
    ConfigFieldType["FLOAT"] = "float";
    ConfigFieldType["STRING"] = "string";
})(ConfigFieldType || (ConfigFieldType = {}));
// Field name constants for type-safe access
const DLL = "dll";
const ALLOW_FP16 = "allow_fp16";
const SCALING_ENABLED = "scaling_enabled";
const SCALING_METHOD = "scaling_method";
const SCALING_FACTOR = "scaling_factor";
const SCALING_SUPERSAMPLING = "scaling_supersampling";
const SCALING_SHARPNESS = "scaling_sharpness";
const FRAME_GENERATION_PROVISIONED = "frame_generation_provisioned";
const FRAME_GENERATION_ENABLED = "frame_generation_enabled";
const FG_BACKEND = "fg_backend";
const OPTISCALER_PROXY = "optiscaler_proxy";
const FRAME_GENERATION_REFRESH_THRESHOLD = "frame_generation_refresh_threshold";
const TARGET_FPS = "target_fps";
const ADAPTIVE_STABLE_CADENCE = "adaptive_stable_cadence";
const GAMESCOPE_VRR_MODE = "gamescope_vrr_mode";
const DYNAMIC_CADENCE_PROBE_INTERVAL_SECONDS = "dynamic_cadence_probe_interval_seconds";
const ULTRA_PERFORMANCE = "ultra_performance";
const FLOW_SCALE = "flow_scale";
const PERFORMANCE_MODE = "performance_mode";
const ACTIVE_IN = "active_in";
const GPU = "gpu";
const DISABLE_MAKO = "disable_mako";
const GAMESCOPE_WSI_COMPATIBILITY = "gamescope_wsi_compatibility";
const SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY = "swapchain_image_count_compatibility";
const EXTERNAL_VULKAN_LAYER = "external_vulkan_layer";
const VKBASALT_SHARPENING = "vkbasalt_sharpening";
const VKBASALT_SHARPNESS = "vkbasalt_sharpness";
const VKBASALT_DLS_DENOISE = "vkbasalt_dls_denoise";
const VKBASALT_ANTIALIASING = "vkbasalt_antialiasing";
const VKBASALT_SHADER = "vkbasalt_shader";
const DISABLE_STEAMDECK_MODE = "disable_steamdeck_mode";
const ENABLE_ZINK = "enable_zink";
const FORCE_ALSA_AUDIO = "force_alsa_audio";
function getDefaults() {
    return {
        dll: "",
        allow_fp16: true,
        scaling_enabled: false,
        scaling_method: "ls1",
        scaling_factor: 1.5,
        scaling_supersampling: false,
        scaling_sharpness: 0.8,
        frame_generation_provisioned: true,
        frame_generation_enabled: true,
        automatic_dock_mode: false,
        fg_backend: "gfg",
        optiscaler_proxy: "auto",
        frame_generation_refresh_threshold: 0,
        base_fps_cap: 0,
        multiplier: 2,
        adaptive: false,
        adaptive_auto_base_fps_cap: true,
        adaptive_fractional_real_frame_priority: "auto",
        target_fps: 90,
        adaptive_max_multiplier: 3,
        adaptive_stable_cadence: true,
        gamescope_vrr_mode: "follow-steam",
        dynamic_cadence_recovery: false,
        dynamic_cadence_probe_interval_seconds: 2.0,
        ultra_performance: false,
        flow_scale: 0.8,
        performance_mode: false,
        pacing: "none",
        active_in: "",
        gpu: "",
        disable_mako: false,
        disable_hdr_exposure: true,
        gamescope_wsi_compatibility: false,
        swapchain_image_count_compatibility: false,
        external_vulkan_layer: "",
        vkbasalt_sharpening: "cas",
        vkbasalt_sharpness: 0.5,
        vkbasalt_dls_denoise: 0.2,
        vkbasalt_antialiasing: "none",
        vkbasalt_shader: "none",
        disable_steamdeck_mode: false,
        enable_zink: false,
        force_alsa_audio: false,
    };
}

// The backend RPC replaces this pre-load fallback with the actual Decky home.
const DEFAULT_MAKO_WRAPPER_PATH = `/home/deck/${MAKO_WRAPPER_RELATIVE_PATH}`;
const DEFAULT_STEAM_LAUNCH_OPTION = `${DEFAULT_MAKO_WRAPPER_PATH} %command%`;

function configFailureResult(error) {
    return { success: false, config: null, message: "", error };
}
function profilesFailureResult(error) {
    return {
        success: false,
        profiles: null,
        current_profile: null,
        profile_details: null,
        message: "",
        error,
    };
}
function profileFailureResult(error, fields = {}) {
    return { success: false, message: "", error, ...fields };
}
// API functions
const installGFG = callable("install_mako");
const uninstallGFG = callable("uninstall_mako");
const checkGFGInstalled = callable("check_mako_installed");
const checkLosslessScalingDll = callable("check_lossless_scaling_dll");
const checkScalingModel = callable("check_scaling_model");
const checkFrameGenerationModel = callable("check_frame_generation_model");
callable("get_dll_stats");
const getGFGConfig = callable("get_mako_config");
const getProfileConfig = callable("get_profile_config");
const getRuntimeStatus = callable("get_runtime_status");
const getFgBackendStatus = callable("get_fg_backend_status");
const getGovernorStatus = callable("get_governor_status");
const setGovernorEnabled = callable("set_governor_enabled");
const getPipelineInspector = callable("get_pipeline_inspector");
const getConfigJournal = callable("get_config_journal");
const restoreConfigJournalEntry = callable("restore_config_journal_entry");
callable("get_config_schema");
const getLaunchOption = callable("get_launch_option");
callable("get_config_file_content");
callable("get_launch_script_content");
const checkFgmodDirectory = callable("check_fgmod_directory");
// Flatpak management API functions
const checkFlatpakExtensionStatus = callable("check_flatpak_extension_status");
const installFlatpakExtension = callable("install_flatpak_extension");
const uninstallFlatpakExtension = callable("uninstall_flatpak_extension");
const getFlatpakApps = callable("get_flatpak_apps");
const setFlatpakAppOverride = callable("set_flatpak_app_override");
const removeFlatpakAppOverride = callable("remove_flatpak_app_override");
// Updated config function using object-based configuration (single source of truth)
const updateGFGConfig = callable("update_mako_config");
// Object-based configuration helper
const updateGFGConfigFromObject = async (config) => {
    return updateGFGConfig(config);
};
// Self-updater API functions
// Profile management API functions
const getProfiles = callable("get_profiles");
callable("create_profile");
const deleteProfile = callable("delete_profile");
const renameProfile = callable("rename_profile");
const captureGameProfile = callable("capture_game_profile");
const setCurrentProfile = callable("set_current_profile");
const syncCurrentProfile = callable("sync_current_profile");
const updateProfileConfig = callable("update_profile_config");
const updateProfileConfigFields = callable("update_profile_config_fields");

const MAKO_INSTALL_COMPLETION_DURATION_MS = 3000;
const CLIPBOARD_SUCCESS_DURATION_MS = 3000;
const RUNTIME_STATUS_POLL_INTERVAL_MS = 1500;
const MODEL_STATUS_POLL_INTERVAL_MS = 30000;
const MODEL_STATUS_DEBOUNCE_MS = 500;

function scalingInactiveReason(status, profileName) {
    if (!status.success)
        return null;
    const context = status.contexts.find((candidate) => !candidate.spatial_scaling.activation_supported &&
        candidate.requested.scaling_enabled &&
        candidate.requested.scaling_method !== "native" &&
        (!profileName ||
            candidate.requested.name === profileName ||
            candidate.applied.name === profileName));
    return context
        ? context.spatial_scaling.inactive_reason ||
            "gamescope-wsi-surface-unproven"
        : null;
}
const EMPTY_RUNTIME_SCALING_UI_STATE = {
    hasContext: false,
    phase: "inactive",
    frameGenerationActive: false,
    frameGenerationEnabled: false,
    frameGenerationMode: "off",
    frameGenerationAdaptiveStyle: null,
    frameGenerationTargetFps: null,
    frameGenerationMultiplier: null,
    frameGenerationPending: false,
    scalingActive: false,
    scalingEnabled: false,
    scalingActivationSupported: null,
    scalingPending: false,
    inactiveReason: null,
    constraintReason: null,
    requestedFactor: 1,
    nonSupersamplingFactorCeiling: null,
    sourceWidth: 0,
    sourceHeight: 0,
    presentationWidth: 0,
    presentationHeight: 0,
    gamescopeTargetWidth: 0,
    gamescopeTargetHeight: 0,
    requestedMethod: "native",
    activeMethod: "native",
    effectiveFactor: 1,
    pipeline: "inactive",
    supersamplingActive: false,
    fallbackReason: null,
};
function newestContext(contexts, predicate) {
    return contexts.find(predicate);
}
function runtimeScalingUiState(status, profileName) {
    if (!status.success) {
        return { ...EMPTY_RUNTIME_SCALING_UI_STATE };
    }
    const contexts = status.contexts.filter((candidate) => !profileName ||
        candidate.requested.name === profileName ||
        candidate.applied.name === profileName);
    const ceilings = contexts
        .map((candidate) => candidate.spatial_scaling.non_supersampling_factor_ceiling)
        .filter((value) => value !== null && value >= 1);
    const frameContext = newestContext(contexts, (candidate) => candidate.role === "frame-generation");
    const scalingRequestedContext = newestContext(contexts, (candidate) => candidate.requested.scaling_enabled);
    const spatialContext = newestContext(contexts, (candidate) => candidate.spatial_scaling.active) ??
        scalingRequestedContext ??
        newestContext(contexts, (candidate) => candidate.role === "spatial-scaling");
    const appliedFrameProfile = frameContext?.applied;
    const frameGenerationEnabled = Boolean(appliedFrameProfile?.frame_generation_enabled);
    const frameGenerationMode = !frameGenerationEnabled
        ? "off"
        : appliedFrameProfile?.adaptive
            ? "adaptive"
            : "fixed";
    return {
        hasContext: contexts.length > 0,
        phase: contexts.length > 0 ? status.phase : "inactive",
        frameGenerationActive: Boolean(frameContext?.frame_generation_active),
        frameGenerationEnabled,
        frameGenerationMode,
        frameGenerationAdaptiveStyle: appliedFrameProfile?.adaptive
            ? appliedFrameProfile.adaptive_auto_base_fps_cap
                ? "steady"
                : "fractional"
            : null,
        frameGenerationTargetFps: appliedFrameProfile?.adaptive
            ? appliedFrameProfile.target_fps
            : null,
        frameGenerationMultiplier: frameGenerationEnabled
            ? appliedFrameProfile?.adaptive
                ? appliedFrameProfile.adaptive_max_multiplier
                : (appliedFrameProfile?.multiplier ?? null)
            : null,
        frameGenerationPending: Boolean(frameContext &&
            (frameContext.pending.frame_generation_private ||
                frameContext.pending.process_restart)),
        scalingActive: Boolean(spatialContext?.spatial_scaling.active),
        scalingEnabled: Boolean(scalingRequestedContext?.requested.scaling_enabled),
        scalingActivationSupported: spatialContext
            ? spatialContext.spatial_scaling.activation_supported
            : null,
        scalingPending: Boolean(spatialContext &&
            (spatialContext.pending.spatial_private ||
                spatialContext.pending.swapchain_recreation ||
                spatialContext.pending.process_restart)),
        inactiveReason: spatialContext?.spatial_scaling.inactive_reason ??
            scalingInactiveReason(status, profileName),
        constraintReason: spatialContext?.spatial_scaling.constraint_reason ?? null,
        requestedFactor: spatialContext?.requested.scaling_factor ??
            scalingRequestedContext?.requested.scaling_factor ??
            1,
        nonSupersamplingFactorCeiling: ceilings.length > 0 ? Math.min(...ceilings) : null,
        sourceWidth: spatialContext?.spatial_scaling.source_width ?? 0,
        sourceHeight: spatialContext?.spatial_scaling.source_height ?? 0,
        presentationWidth: spatialContext?.spatial_scaling.presentation_width ?? 0,
        presentationHeight: spatialContext?.spatial_scaling.presentation_height ?? 0,
        gamescopeTargetWidth: spatialContext?.spatial_scaling.gamescope_target_width ?? 0,
        gamescopeTargetHeight: spatialContext?.spatial_scaling.gamescope_target_height ?? 0,
        requestedMethod: spatialContext?.spatial_scaling.requested_method ?? "native",
        activeMethod: spatialContext?.spatial_scaling.active_method ?? "native",
        effectiveFactor: spatialContext?.spatial_scaling.effective_factor ?? 1,
        pipeline: spatialContext?.spatial_scaling.pipeline ?? "inactive",
        supersamplingActive: Boolean(spatialContext?.spatial_scaling.supersampling_active),
        fallbackReason: spatialContext?.spatial_scaling.fallback_reason ?? null,
    };
}

var es = {
	CONFIG_VKBASALT_ADVANCED_GLOBAL_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. The Default profile uses this global file.",
	CONFIG_VKBASALT_ADVANCED_PROFILE_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. This file belongs to the selected profile and is removed when that profile is deleted.",
	CONFIG_VKBASALT_SHARPENING: "Sharpening",
	CONFIG_VKBASALT_SHARPENING_DESC: "CAS is a crisp general-purpose sharpener. DLS can preserve noisy or grainy detail better when paired with denoise.",
	CONFIG_VKBASALT_EFFECT_NONE: "Off",
	CONFIG_VKBASALT_SHARPENING_CAS: "CAS",
	CONFIG_VKBASALT_SHARPENING_DLS: "DLS",
	CONFIG_VKBASALT_SHARPNESS: "Sharpness ({value}%)",
	CONFIG_VKBASALT_SHARPNESS_DESC: "Higher values produce a stronger effect but can exaggerate grain and create halos around high-contrast edges.",
	CONFIG_VKBASALT_DLS_DENOISE: "DLS Denoise ({value}%)",
	CONFIG_VKBASALT_DLS_DENOISE_DESC: "Limits how strongly DLS sharpens film grain and fine noise.",
	CONFIG_VKBASALT_ANTIALIASING: "Anti-aliasing",
	CONFIG_VKBASALT_ANTIALIASING_DESC: "Optionally smooth jagged edges before sharpening. FXAA is lighter and softer; SMAA is more selective and may cost more GPU time.",
	CONFIG_VKBASALT_ANTIALIASING_FXAA: "FXAA",
	CONFIG_VKBASALT_ANTIALIASING_SMAA: "SMAA",
	CONFIG_VKBASALT_SHADER: "Efectos",
	CONFIG_VKBASALT_SHADER_DESC: "Effects run in selection order; uncheck and recheck to move one last. Stacking increases GPU load, especially with heavier effects such as HDR Look. Test per game and monitor GPU usage.",
	CONFIG_VKBASALT_EFFECTS_SELECTED: "Choose effects ({value} selected)",
	CONFIG_VKBASALT_EFFECTS_CLEAR: "Clear all",
	CONFIG_VKBASALT_EFFECTS_DONE: "Done",
	CONFIG_VKBASALT_EFFECTS_PREVIOUS_PAGE: "Previous effects page",
	CONFIG_VKBASALT_EFFECTS_NEXT_PAGE: "Next effects page",
	CONFIG_VKBASALT_SHADER_VIBRANCE: "Vibrance",
	CONFIG_VKBASALT_SHADER_CURVES: "Curves",
	CONFIG_VKBASALT_SHADER_DEBAND: "Deband",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR: "Technicolor",
	CONFIG_VKBASALT_SHADER_SEPIA: "Sepia",
	CONFIG_VKBASALT_SHADER_MONOCHROME: "Monochrome",
	CONFIG_VKBASALT_SHADER_VIGNETTE: "Vignette",
	CONFIG_VKBASALT_SHADER_HDR_LOOK: "HDR Look (SDR)",
	CONFIG_VKBASALT_SHADER_CLARITY: "Clarity",
	CONFIG_VKBASALT_SHADER_LEVELS_PLUS: "Levels Plus",
	CONFIG_VKBASALT_SHADER_COLOURFULNESS: "Colourfulness",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR2: "Technicolor 2",
	CONFIG_VKBASALT_SHADER_DPX: "DPX / Cineon",
	CONFIG_VKBASALT_SHADER_BLEACH_BYPASS: "Bleach Bypass",
	CONFIG_VKBASALT_SHADER_NOIR: "Noir",
	CONFIG_VKBASALT_SHADER_FILM_GRAIN: "Film Grain",
	CONFIG_VKBASALT_SHADER_CARTOON: "Cartoon",
	CONFIG_VKBASALT_SHADER_NOSTALGIA: "Nostalgia",
	CONFIG_VKBASALT_SHADER_CHROMATIC_ABERRATION: "Chromatic Aberration",
	CONTENT_HIDE_INFO: "Ocultar información",
	CONTENT_SHOW_INFO: "Mostrar información",
	DEVELOPMENT_DEPLOYMENT_TITLE: "Despliegue local de desarrollo",
	DEVELOPMENT_DETAILS: "Detalles",
	DEVELOPMENT_HIDE: "Ocultar",
	DEVELOPMENT_DEPLOYED: "desplegado",
	DEVELOPMENT_DEPLOYED_AT: "Desplegado",
	DEVELOPMENT_UNCHANGED: "sin cambios",
	DEVELOPMENT_COMMIT: "Commit",
	DEVELOPMENT_FRONTEND: "Interfaz",
	DEVELOPMENT_BACKEND: "Backend",
	DEVELOPMENT_LOCAL_EDITS: "+ cambios locales",
	DEVELOPMENT_LAYER_64: "Capa de 64 bits",
	DEVELOPMENT_LAYER_32: "Capa de 32 bits",
	DEVELOPMENT_FLATPAK_BUNDLES: "Paquetes Flatpak",
	DEVELOPMENT_UNCHANGED_BY_DEPLOYMENT: "Sin cambios en este despliegue",
	CONTENT_IMAGE_PROCESSING: "Procesamiento de imagen",
	IMAGE_PROCESSING_PERFORMANCE_INFO: "Combinar generación de cuadros, escalado y shaders puede reducir el rendimiento. Desactiva lo que no uses; prueba Ventana y Pantalla completa por juego.",
	CONTENT_TAB_FRAME_GENERATION: "Generación",
	CONTENT_TAB_SCALING: "Escalado",
	CONTENT_TAB_SHADERS: "Shaders",
	CONTENT_SCALING: "Escalado",
	CONTENT_SHADERS: "Shaders",
	SCALING_ENABLED: "Habilitar escalado (Reiniciar)",
	EXPERIMENTAL_LABEL: "Experimental",
	SCALING_ENABLED_DESC: "Actívalo antes de iniciar para usar Lossless Scaling o GFG Scaler; al apagarlo se desactiva el escalado. Algunos juegos pueden requerir el modo Ventana; Pantalla completa sin bordes también puede funcionar.",
	SCALING_RUNTIME_SURFACE_UNSUPPORTED: "This running surface does not support GFG Extreme scaling. Quality Supersampling, Scale Factor, and Sharpness are locked until a supported surface is detected. Frame Generation remains available.",
	SCALING_METHOD: "Método de escalado",
	SCALING_METHOD_DESC: "Elige el modelo de escalado. Puedes cambiarlo mientras el juego está en ejecución.",
	SCALING_LS1_ACTIVE_FALLBACK: "LS1 is unavailable for this game. GFG Scaler is active. Your LS1 selection is preserved.",
	SCALING_LS1_UNAVAILABLE: "LS1 falló la comprobación. GFG Scaler lo sustituye si no puede cargarse; tu selección queda guardada.",
	SCALING_METHOD_COMPARISON_TIP: "Cómo funciona el escalado:\n1. En Steam, establece la resolución del juego en la resolución máxima de tu pantalla (Steam Deck: 1280 × 800; Steam Machine: 3840 × 2160).\n2. En el juego, elige una resolución menor, como 480p, 720p o más.\n3. Ajusta el factor de escala para ampliar la imagen. 2x busca duplicar el ancho y alto de la entrada (640×360 → 1280×720).\n\nReducir la resolución del juego y volver a escalarla puede mejorar mucho el rendimiento, con una compensación en la calidad de imagen.",
	SCALING_METHOD_NATIVE: "Resolución nativa",
	SCALING_METHOD_MAKO: "GFG Scaler",
	SCALING_METHOD_LS1: "LS1 Quality",
	SCALING_METHOD_LS1_PERFORMANCE: "LS1 Performance",
	SCALING_FACTOR: "Factor de escala",
	SCALING_FACTOR_DESC: "2x busca duplicar el ancho y alto de la imagen renderizada por el juego (640×360 → 1280×720). Con una salida fija, GFG Extreme solicita una imagen más pequeña al juego. Si el juego define el tamaño de la ventana, baja primero su resolución dentro del juego; GFG Extreme amplía la salida, dentro de los límites de la pantalla y la GPU.",
	SCALING_FACTOR_LIMIT_SUFFIX: "límite de pantalla",
	SCALING_FACTOR_DEVICE_LIMIT: "Límite actual de pantalla: {factor}x. Se conserva el valor guardado de {saved}x; activa Supermuestreo de calidad para usarlo.",
	SCALING_FACTOR_NO_HEADROOM: "Esta entrada ya llena la pantalla de destino. Prueba el modo ventana, reduce la resolución del juego o activa el Supermuestreo de calidad.",
	SCALING_SUPERSAMPLING: "Supermuestreo de calidad",
	SCALING_SUPERSAMPLING_DESC: "Permite superar un límite de salida de Gamescope para reducir la imagen con mayor calidad, aumentando el uso de GPU y memoria. No cambia el escalado en otras superficies del escritorio.",
	SCALING_SUPERSAMPLING_WARNING: "Con el supermuestreo activado, GFG Extreme puede superar el límite de salida de Gamescope para un resultado más nítido.",
	SCALING_SHARPNESS: "Nitidez del escalado",
	SCALING_SHARPNESS_DESC: "GFG Scaler: 0–100 % de su base de nitidez 3x. LS1: una de cinco variantes de nitidez aprendidas.",
	CONTENT_FPS_MULTIPLIER: "Generación de cuadros",
	CONTENT_PERFORMANCE_SETTINGS: "Configuración de rendimiento",
	CONTENT_ADVANCED_DETAILS: "Detalles avanzados",
	CONTENT_FLATPAK_SETUP: "Configuración de Flatpak",
	CONFIG_SECTION_TITLE: "Configuración avanzada de renderizado",
	CONFIG_WORKAROUNDS_TITLE: "Configuración de compatibilidad",
	CONFIG_FLOW_SCALE: "Escala de flujo",
	CONFIG_FLOW_SCALE_DESC: "Resolución de estimación de movimiento de la generación de cuadros. Menos ahorra GPU; más prioriza calidad.",
	CONFIG_BASE_FPS_CAP: "Límite de FPS base",
	CONFIG_BASE_FPS_CAP_OFF: "Desactivado",
	CONFIG_BASE_FPS_CAP_DESC: "Limita los cuadros reales de la aplicación antes de la generación. Funciona con DirectX, OpenGL mediante Zink y Vulkan.",
	CONFIG_BASE_FPS_CAP_STEADY_RELATION: "Controlado por Límite base estable ({fps} FPS). El valor manual permanece guardado.",
	CONFIG_BASE_FPS_CAP_FRACTIONAL_PRIORITY_RELATION: "Controlado por Prioridad de cuadros reales ({fps} FPS). El valor manual permanece guardado.",
	CONFIG_BASE_FPS_CAP_RECOVERY_RELATION: "Cambiar este límite desactiva la Recuperación de cadencia dinámica.",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD: "Desactivar automáticamente la generación según la frecuencia",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD_DESC: "Pausa la generación a la frecuencia de Gamescope elegida o por debajo; la reanuda por encima. Requiere información de frecuencia.",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD: "Umbral de frecuencia de actualización",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD_DESC: "Elija la frecuencia más alta a la que la generación de cuadros debe permanecer pausada.",
	CONFIG_ULTRA_PERFORMANCE: "Rendimiento ultra (Reiniciar)",
	CONFIG_ULTRA_PERFORMANCE_DESC: "Reduce la carga de la GPU de GFG Extreme en dispositivos de bajo consumo. Usa una escala de flujo del 70 %, el modelo de FG ligero, FP16 cuando es compatible y LS1 Performance cuando el escalado está habilitado. Sacrifica calidad de imagen para mejorar el rendimiento de las funciones activas de GFG Extreme.",
	CONFIG_ULTRA_PERFORMANCE_WARNING: "Activar o desactivar Ultra Performance requiere reiniciar el juego. Los demás controles de perfil compatibles siguen disponibles después del inicio.",
	CONFIG_PERFORMANCE_MODE: "Modelo de FG ligero",
	CONFIG_PERFORMANCE_MODE_DESC: "El modelo FG ligero reduce la carga de GPU, pero aumenta las imágenes fantasma; Rendimiento ultra lo fuerza.",
	CONFIG_DISABLE_STEAMDECK_MODE: "Desactivar el modo Steam Deck (Reiniciar)",
	CONFIG_DISABLE_STEAMDECK_MODE_DESC: "Desactiva el modo Steam Deck. Desbloquea opciones ocultas en algunos juegos.",
	CONFIG_ENABLE_ZINK: "Activar Zink para juegos OpenGL (Reiniciar)",
	CONFIG_ENABLE_ZINK_DESC: "Ejecuta juegos OpenGL mediante Vulkan; puede causar bloqueos o congelaciones.",
	CONFIG_FORCE_ALSA_AUDIO: "Forzar audio ALSA (Reiniciar)",
	CONFIG_FORCE_ALSA_AUDIO_DESC: "Puede ayudar con Zink, cortes de audio o sonidos fuertes repentinos. Desactívalo para restaurar el audio normal.",
	CONFIG_EXTERNAL_TOOLS_TITLE: "Herramientas externas",
	CONFIG_ENABLE_MANGOHUD: "Activar MangoHud (Reiniciar)",
	CONFIG_ENABLE_MANGOHUD_DESC: "Usa MangoHud instalado y su configuración; consulta la guía avanzada para cambios por juego.",
	CONFIG_ENABLE_VKBASALT: "Habilitar shaders (Reiniciar)",
	CONFIG_ENABLE_VKBASALT_DESC: "Actívalo antes de iniciar para usar nitidez, antialiasing y shaders incluidos. No necesita instalación aparte. Si no ves los efectos, prueba el modo Ventana o Pantalla completa sin bordes.",
	INSTALL_INSTALLING: "Instalando GFG Engine...",
	INSTALL_UNINSTALLING: "Eliminando GFG Engine...",
	FLATPAK_MODAL_TITLE: "Extensiones de Flatpak",
	FLATPAK_RUNTIME_INSTALLER: "Instalador de extensiones de entorno",
	FLATPAK_RUNTIME_VERSION: "Entorno {version}",
	FLATPAK_INSTALLED: "Instalado",
	FLATPAK_NOT_INSTALLED: "No instalado",
	FLATPAK_UNINSTALL_TITLE: "Desinstalar extensión de entorno",
	FLATPAK_UNINSTALL_CONFIRM_PREFIX: "¿Seguro que desea desinstalar el entorno",
	FLATPAK_UNINSTALL_CONFIRM_SUFFIX: "seleccionado?",
	FLATPAK_UNINSTALL_BTN: "Desinstalar",
	FLATPAK_INSTALL_BTN: "Instalar",
	FLATPAK_UPDATE_BTN: "Actualizar",
	FLATPAK_INSTALLING_BTN: "Instalando...",
	FLATPAK_UNINSTALLING_BTN: "Desinstalando...",
	FLATPAK_UPDATING_BTN: "Actualizando...",
	FLATPAK_APPS_TITLE: "Aplicaciones Flatpak",
	FLATPAK_NO_APPS: "No se encontraron aplicaciones Flatpak",
	FLATPAK_NO_APPS_DESC: "No hay aplicaciones Flatpak instaladas actualmente",
	FLATPAK_STATUS_CONFIGURED: "Preparada",
	FLATPAK_STATUS_PARTIAL: "Parcial",
	FLATPAK_STATUS_NO_OVERRIDES: "Sin ajustes",
	FLATPAK_ERROR: "Error",
	FLATPAK_ERROR_STATUS: "No se pudo comprobar el estado de la extensión",
	FLATPAK_ERROR_APPS: "No se pudieron cargar las aplicaciones Flatpak",
	FLATPAK_STEAM_CONFIG_TITLE: "Referencia para accesos directos manuales de Steam",
	FLATPAK_STEAM_CONFIG_HEADER: "Ejemplo de destino (no configura Steam)",
	FLATPAK_STEAM_CONFIG_DESC: "Solo para accesos directos de Steam añadidos a mano cuyo destino original era /usr/bin/flatpak. Prepara la aplicación arriba; conserva Iniciar en y Opciones de lanzamiento. Heroic, Lutris y EmuDeck usan la guía de lanzadores.",
	FLATPAK_IMPORTANT_LABEL: "IMPORTANTE:",
	FLATPAK_STEAM_CONFIG_IMPORTANT: "Sustituya solo DESTINO. No pegue esto en OPCIONES DE LANZAMIENTO.",
	FLATPAK_PER_GAME_APP_DESC: "{app_id} - {status}. Active GFG Extreme por juego usando {wrapper_path}. Consulte el campo correcto en la guía de lanzadores.",
	FLATPAK_DIRECT_APP_DESC: "{app_id} - {status}. La preparación se aplica a toda esta aplicación Flatpak. Consulte la guía de lanzadores para EmuDeck y los accesos directos de Steam.",
	FLATPAK_STEP_WRAPPER_PATH: "Contenedor instalado en este dispositivo:",
	FLATPAK_STEP_FINAL: "Destino para un acceso directo que originalmente usaba \"/usr/bin/flatpak\":",
	FLATPAK_OPEN_README: "Abrir guía de lanzadores",
	FLATPAK_CLOSE: "Cerrar",
	ADVANCED_DETAILS_LOADING: "Cargando información...",
	ADVANCED_DETAILS_ERROR_PREFIX: "Error:",
	ADVANCED_DETAILS_DLL_PATH: "Ruta de la DLL",
	ADVANCED_DETAILS_LIBRARY: "Biblioteca de Lossless Scaling",
	ADVANCED_DETAILS_RENDERER: "GFG Engine",
	ADVANCED_DETAILS_INSTALLATION: "Installation",
	ADVANCED_DETAILS_INSTALLED_VERSION: "Installed version",
	ADVANCED_DETAILS_BUNDLED_VERSION: "Bundled version",
	ADVANCED_DETAILS_HOST_ARCHITECTURE: "Host architecture",
	ADVANCED_DETAILS_LAYER_PATH: "Renderer library",
	ADVANCED_DETAILS_MANIFEST_PATH: "Vulkan manifest",
	ADVANCED_DETAILS_LAUNCHER_PATH: "Launch wrapper",
	ADVANCED_DETAILS_DETECTION: "Detection",
	ADVANCED_DETAILS_DLL_NOT_DETECTED: "Lossless Scaling not detected",
	ADVANCED_DETAILS_UNSUPPORTED_HOST: "Unsupported host",
	ADVANCED_DETAILS_UPDATE_REQUIRED: "Bundled update available",
	ADVANCED_DETAILS_INCOMPLETE: "Incomplete installation",
	ADVANCED_DETAILS_NOT_AVAILABLE: "No disponible",
	ADVANCED_DETAILS_DETECTION_SOURCE: "Origen de detección",
	ADVANCED_DETAILS_CLOSE: "Cerrar",
	WELCOME_TITLE: "¡Hola desde el equipo de GFG Extreme!",
	WELCOME_TIPS_COLLAPSE: "Ocultar consejos",
	WELCOME_TIPS_EXPAND: "Mostrar consejos",
	WELCOME_LIVE_UPDATES: "Muchos ajustes se aplican en tiempo real.",
	WELCOME_RESTART_REQUIRED: "Las opciones marcadas como «Reiniciar» requieren reiniciar el juego.",
	WELCOME_PERFORMANCE_NOTE: "Los cambios en la resolución y el escalado del juego pueden afectar al rendimiento.",
	WELCOME_CLEAN_SESSION_PREFIX: "Si algo ",
	WELCOME_CLEAN_SESSION_WRONG: "no se ve o no se siente bien",
	WELCOME_CLEAN_SESSION_AFTER: " después de ",
	WELCOME_CLEAN_SESSION_CHANGES: "varios cambios",
	WELCOME_CLEAN_SESSION_RESTART_SEPARATOR: ", ",
	WELCOME_CLEAN_SESSION_RESTART: "reinicie el juego para comenzar una sesión nueva y limpia.",
	WELCOME_ENJOY: "Los ajustes dependen del juego. Prueba lo que te funcione; consulta la página de lanzamientos para ver novedades de GFG Extreme.",
	PROFILE_CAPTURE_READY: "GFG Extreme selecciona automáticamente los perfiles guardados. Si este juego es nuevo, guárdelo abajo; reinicie el juego tras cambiar opciones que requieran reinicio.",
	PROFILE_HELP: "Guarda una vez el proceso del juego para seleccionar su perfil automáticamente. Fuera del juego, el menú elige el perfil que editas.",
	PROFILE_SECTION_TITLE: "Perfiles de juego / proceso",
	PROFILE_DEFAULT: "Predeterminado",
	PROFILE_SAVED_LABEL: "Perfil guardado",
	PROFILE_GAME_SAVED: "Perfil de juego guardado",
	PROFILE_GAME_SAVE_FAILED: "No se pudo guardar el perfil del juego",
	PROFILE_SAVE_RUNNING: "Guardar perfil para {game}",
	PROFILE_DETAIL_DEFAULT: "Abra un juego para guardar su perfil",
	PROFILE_DETAIL_GAME: "Juego guardado",
	PROFILE_DETAIL_PROCESS: "Proceso guardado",
	PROFILE_STEAM_APP_ID: "ID de aplicación de Steam: {app_id}",
	PROFILE_PROCESSES: "Procesos: {processes}",
	PROFILE_PROCESSES_EMPTY: "Procesos: introduzca uno en Procesos coincidentes abajo",
	PROFILE_MANAGE_WHEN_IDLE: "Cierre el juego en ejecución para renombrar o eliminar perfiles.",
	PROFILE_NAME_LABEL: "Nombre",
	PROFILE_CANCEL_BTN: "Cancelar",
	PROFILE_RENAME_TITLE: "Renombrar perfil",
	PROFILE_RENAME_DESC_PREFIX: "Elija un nombre reconocible para este perfil de juego o proceso.",
	PROFILE_RENAME_BTN: "Renombrar",
	PROFILE_CANNOT_DELETE_TITLE: "No se puede eliminar el perfil predeterminado",
	PROFILE_CANNOT_DELETE_MSG: "El perfil predeterminado no se puede eliminar",
	PROFILE_DELETE_TITLE: "Eliminar perfil de juego / proceso",
	PROFILE_DELETE_CONFIRM: "¿Eliminar \"{profile}\" y todos sus ajustes guardados?",
	PROFILE_DELETE_BTN: "Eliminar",
	PROFILE_CANNOT_RENAME_TITLE: "No se puede renombrar el perfil predeterminado",
	PROFILE_CANNOT_RENAME_MSG: "El perfil predeterminado no se puede renombrar",
	USAGE_TITLE: "Instrucciones de uso",
	USAGE_DESC: "Añade esta opción de lanzamiento en Steam para activar Generación de cuadros, Escalado o ambos en GFG Extreme.",
	CLIPBOARD_COPIED: "Copiado al portapapeles",
	CLIPBOARD_COPYING: "Copiando...",
	CLIPBOARD_COPY_LAUNCH: "Copiar opción de lanzamiento",
	CLIPBOARD_MAKO_FGMOD: "GFG Extreme + DeckyFG",
	CONTENT_RUNNING: "en ejecución.",
	CONTENT_ENGINE_UPDATE_REQUIRED: "Se requiere actualizar GFG Engine",
	CONTENT_ENGINE_INSTALLED: "Instalado:",
	CONTENT_ENGINE_NOT_RECORDED: "no registrado",
	CONTENT_ENGINE_EXPECTS: "Este complemento espera:",
	CONTENT_ENGINE_BUNDLED_VERSION: "la versión incluida",
	CONTENT_ENGINE_PREDATES_TRACKING: "La carga instalada es anterior al seguimiento de versiones.",
	CONTENT_ENGINE_UPDATE_DESC: "Reinstala el GFG Engine incluido y actualiza las extensiones de ejecución de los Flatpaks preparados.",
	CONTENT_UPDATE_RENDERER: "Actualizar GFG Engine",
	CONTENT_UPDATING_RENDERER: "Actualizando GFG Engine...",
	ADAPTIVE_TITLE: "Generación de cuadros adaptativa",
	ADAPTIVE_DESC: "Busca los FPS de salida deseados. El Límite base estable prioriza un ritmo uniforme por defecto; el Adaptativo fraccionario conserva más cuadros reales. Prueba cada juego.",
	FRACTIONAL_ADAPTIVE_PRESET: "Adaptativo fraccionario",
	FRACTIONAL_ADAPTIVE_PRESET_DESC: "Combina proporciones de generación para alcanzar objetivos como 60 FPS reales → 90 FPS mostrados. Conserva más cuadros reales y puede reducir la latencia de entrada y las imágenes fantasma, pero puede sentirse menos fluido en algunos juegos.",
	FRACTIONAL_ADAPTIVE_PRESET_RELATION: "No se puede combinar con el Límite base estable. Cambiar esta opción también desactiva la Recuperación de cadencia dinámica.",
	ADAPTIVE_REAL_FRAME_PRIORITY: "Prioridad de cuadros reales",
	ADAPTIVE_REAL_FRAME_PRIORITY_DESC: "Los valores de FPS mostrados son estimaciones del límite de cuadros reales según los FPS objetivo, no tasas garantizadas. Una prioridad mayor permite más cuadros reales y puede reducir la latencia y las imágenes fantasma, pero el ritmo puede ser menos uniforme.",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO: "Automática",
	ADAPTIVE_REAL_FRAME_PRIORITY_LOW: "Baja",
	ADAPTIVE_REAL_FRAME_PRIORITY_MEDIUM: "Media",
	ADAPTIVE_REAL_FRAME_PRIORITY_HIGH: "Alta",
	ADAPTIVE_REAL_FRAME_PRIORITY_VERY_HIGH: "Muy alta",
	ADAPTIVE_REAL_FRAME_PRIORITY_OPTION: "{priority} — hasta {cap} FPS reales ({percent}% del objetivo)",
	ADAPTIVE_REAL_FRAME_PRIORITY_ACTIVE_RELATION: "Con objetivo de {target} FPS: unos {cap} reales / {generated_fps} generados ({real}:{generated}) si se alcanza. La tasa puede variar; sustituye al Límite de FPS base.",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO_RELATION: "Automática mantiene el comportamiento actual de Adaptativo fraccionario. El Límite de FPS base sigue disponible.",
	ADAPTIVE_TARGET_FPS: "FPS objetivo",
	ADAPTIVE_TARGET_FPS_DESC: "FPS de salida. El Adaptativo fraccionario mezcla relaciones; el Límite base estable parte de la mitad y puede usar un entero inferior validado.",
	ADAPTIVE_AUTO_BASE_FPS_CAP: "Límite base estable",
	ADAPTIVE_AUTO_BASE_FPS_CAP_DESC: "Modo adaptativo predeterminado: empieza a mitad del objetivo; la Cadencia suave puede alinear relaciones 3x–5x validadas. Suele ser más fluido, con menos cuadros reales y posible retraso o ghosting adicional.",
	ADAPTIVE_AUTO_BASE_FPS_CAP_RELATION: "Sustituye al Límite de FPS base. No se puede combinar con Adaptativo fraccionario ni con Recuperación de cadencia dinámica.",
	ADAPTIVE_MAX_MULTIPLIER: "Multiplicador adaptativo máximo",
	ADAPTIVE_MAX_MULTIPLIER_DESC: "Usa 0x para pausar o reanudar la generación de cuadros en vivo sin descargar sus recursos. En los demás valores, este es el límite de interpolación, no una relación fija; Adaptativo puede usar multiplicadores inferiores o fraccionarios. Ajústalo solo lo necesario para alcanzar los FPS objetivo. Prueba 2x–5x en cada juego.",
	ADAPTIVE_SMOOTH_CADENCE: "Cadencia suave",
	ADAPTIVE_SMOOTH_CADENCE_DESC: "Usa la presentación ordenada validada de Gamescope para un ritmo más estable. El Adaptativo fraccional mantiene los cuadros reales; el modo Fijo y el Límite base estable pueden priorizar una salida uniforme. Puede reducir los FPS reales y la respuesta. Está activada de forma predeterminada; desactívela por juego si lo prefiere.",
	GAMESCOPE_VRR_MODE: "VRR de Gamescope",
	GAMESCOPE_VRR_MODE_DESC: "Desactivar VRR permite que GFG Extreme controle el ritmo de los fotogramas. Esto puede mejorar la generación de fotogramas en algunos juegos, pero no en otros; pruébalo en cada juego. Si tu dispositivo o pantalla no admite VRR, esta opción no tendrá efecto.",
	GAMESCOPE_VRR_FOLLOW_STEAM: "Seguir Steam",
	GAMESCOPE_VRR_ON: "Activado",
	GAMESCOPE_VRR_OFF: "Desactivado",
	DYNAMIC_CADENCE_RECOVERY: "Recuperación de cadencia dinámica",
	DYNAMIC_CADENCE_RECOVERY_DESC: "Ayuda a juegos y emuladores que cambian entre frecuencias nativas, como 30 FPS durante el juego y 60 FPS en los menús. Comprueba periódicamente los cambios y recupera la cadencia correcta, pero cada comprobación puede afectar brevemente al ritmo. Actívela solo en los juegos afectados.",
	DYNAMIC_CADENCE_RECOVERY_RELATION: "Recuperación desactiva el Límite base estable y el Límite de FPS base y reinicia la Prioridad de cuadros reales a Automática. Cambiar un límite o la prioridad la desactiva.",
	DYNAMIC_CADENCE_PROBE_INTERVAL: "Intervalo de sondeo de cadencia",
	DYNAMIC_CADENCE_PROBE_INTERVAL_DESC: "Intervalo de revisión: 0,1 s puede causar tirones frecuentes; 2 s es el valor predeterminado; 3 s revisa menos. Prueba cada juego.",
	ADAPTIVE_VALUE: "Adaptativo",
	CONFIG_DLL_PATH: "Ruta de Lossless.dll (Reiniciar)",
	CONFIG_DLL_PATH_DESC: "Ruta completa opcional a Lossless.dll. Déjela vacía para usar la detección automática de GFG Engine. Reinicie el juego después de cambiarla.",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH: "Desactivar GFG Engine en el próximo inicio",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH_DESC: "Para diagnóstico: omite GFG Engine en el próximo inicio. Usa Generación de cuadros arriba para activar o desactivar la generación.",
	CONFIG_DISABLE_HDR_EXPOSURE: "Desactivar HDR",
	CONFIG_DISABLE_HDR_EXPOSURE_DESC: "HDR no está disponible en esta versión. Este ajuste obligatorio mantiene activa la ruta SDR estable.",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY: "Gamescope WSI (Reiniciar)",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_DESC: "Puede reducir artefactos de movimiento coloreados o pixelados mediante la presentación de Gamescope. Opcional con Escalado y Generación de cuadros; actívalo solo si hace falta.",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_WARNING: "Solo en lanzamientos de host de 64 bits compatibles. Déjalo apagado salvo que haga falta; puede reducir el rendimiento.",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY: "Imágenes de intercambio del juego (Reiniciar)",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_DESC: "Puede corregir fallos de inicio con Generación de cuadros al conservar el mínimo de imágenes de swapchain pedido por el juego. Úsalo solo en juegos afectados.",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_WARNING: "Los cuadros generados pueden omitirse cuando el compositor no tiene una imagen libre, lo que puede reducir la fluidez o el rendimiento bajo presión.",
	FRAME_GENERATION_PROVISIONED: "Habilitar Frame-gen (Reiniciar)",
	FRAME_GENERATION_PROVISIONED_DESC: "Actívalo antes de iniciar para cargar Generación de cuadros; desactívalo si solo usas Escalado o Shaders.",
	FIXED_MULTIPLIER: "Multiplicador fijo",
	FIXED_MULTIPLIER_DESC: "2x–5x fija una relación de salida; 5x cuesta más y sirve para pantallas de alta frecuencia. 0x pausa la generación sin descargar recursos.",
	CONFIG_ALLOW_FP16: "Permitir FP16 (Reiniciar)",
	CONFIG_ALLOW_FP16_DESC: "Ajuste global del renderizador: se aplica a todos los perfiles y no puede cambiarse por juego. Mejora el rendimiento en AMD; desactívelo para GPU NVIDIA antiguas. Reinicie el juego después de cambiarlo.",
	CONFIG_GPU: "GPU (Reiniciar)",
	CONFIG_GPU_DESC: "Nombre de GPU, ID proveedor:dispositivo o ID de bus PCI opcional. Reinicie el juego después de cambiarlo.",
	CONFIG_ACTIVE_IN: "Procesos coincidentes",
	CONFIG_ACTIVE_IN_DESC: "Nombres de procesos separados por comas. La captura del juego los rellena; edítalos solo para añadir un alias de lanzador o emulador.",
	CONFIG_MANUAL_OVERRIDES_TITLE: "Ajustes manuales",
	INSTALL_REMOVE_RENDERER: "Eliminar GFG Engine",
	INSTALL_RENDERER: "Instalar GFG Engine",
	FLATPAK_EXTENSION_UPDATED: "Extensión Flatpak actualizada",
	FLATPAK_EXTENSION_FAILED: "Falló la extensión Flatpak",
	FLATPAK_EXTENSION_ACTION_FAILED: "No se pudo",
	FLATPAK_RUNTIME_EXTENSION_UPDATED: "extensión de entorno actualizada",
	FLATPAK_RUNTIME_EXTENSION: "extensión de entorno",
	FLATPAK_APPLICATION_UPDATED: "Aplicación Flatpak actualizada",
	FLATPAK_UPDATED: "actualizada",
	FLATPAK_PREPARE_APPLICATION: "Preparar una aplicación",
	FLATPAK_PREPARE_APPLICATION_DESC: "Instala la extensión correspondiente y prepara la aplicación. Heroic/Lutris necesitan un wrapper por juego; los emuladores se preparan para toda la aplicación. Consulta la guía de lanzadores.",
	FLATPAK_INSTALL_ACTION: "instalar",
	FLATPAK_UNINSTALL_ACTION: "desinstalar",
	FLATPAK_APPLICATION_ACTION_FAILED: "No se pudo actualizar",
	PROFILE_UNKNOWN_ERROR: "Error desconocido",
	PROFILE_LOAD_FAILED: "No se pudieron cargar los perfiles",
	PROFILE_LOAD_ERROR: "Error al cargar los perfiles",
	PROFILE_SWITCHED: "Perfil cambiado",
	PROFILE_SWITCHED_DESC: "Perfil cambiado a:",
	PROFILE_SWITCH_FAILED: "No se pudo cambiar de perfil",
	PROFILE_SWITCH_ERROR: "Error al cambiar de perfil",
	PROFILE_DELETED: "Perfil eliminado",
	PROFILE_DELETED_DESC: "Perfil eliminado:",
	PROFILE_DELETE_FAILED: "No se pudo eliminar el perfil",
	PROFILE_DELETE_ERROR: "Error al eliminar el perfil",
	PROFILE_RENAMED: "Perfil renombrado",
	PROFILE_RENAMED_DESC: "Perfil renombrado a:",
	PROFILE_RENAME_FAILED: "No se pudo renombrar el perfil",
	PROFILE_RENAME_ERROR: "Error al renombrar el perfil",
	PROFILE_UPDATE_CONFIG_FAILED: "No se pudo actualizar la configuración del perfil",
	PROFILE_UPDATE_CONFIG_ERROR: "Error al actualizar la configuración del perfil",
	USAGE_MAKO_CONFIG_NOTE: "Este comando aplica GFG Extreme solo al juego que inicie con él.",
	USAGE_ISOLATION_NOTE: "No combine GFG Extreme con otra herramienta de generación de cuadros o escalado para el mismo juego.",
	ADVANCED_DETAILS_FAILED_LOAD_DATA: "No se pudieron cargar los datos",
	STATUS_ENGINE_INSTALLED: "GFG Engine instalado",
	STATUS_ENGINE_NOT_INSTALLED: "GFG Engine no instalado",
	STATUS_ENGINE_INSTALLING: "Instalando GFG Engine...",
	STATUS_ENGINE_UPDATING: "Actualizando GFG Engine...",
	STATUS_ENGINE_REMOVING: "Eliminando GFG Engine...",
	STATUS_ENGINE_REMOVED: "¡GFG Engine se eliminó correctamente!",
	STATUS_INSTALL_FAILED: "Error de instalación:",
	STATUS_UNINSTALL_FAILED: "Error de desinstalación:",
	STATUS_LOSSLESS_INSTALLED: "Lossless Scaling instalado",
	STATUS_LOSSLESS_NOT_INSTALLED: "Lossless Scaling no está instalado — es necesario para la generación de fotogramas y LS1; GFG Scaler sigue disponible",
	TOAST_INSTALL_COMPLETE: "Instalación completada",
	TOAST_INSTALL_COMPLETE_DESC: "Se recomienda reiniciar el dispositivo.",
	TOAST_INSTALL_FAILED: "Error de instalación",
	TOAST_UNKNOWN_ERROR: "Se produjo un error desconocido",
	TOAST_UNINSTALL_COMPLETE: "GFG Engine eliminado",
	TOAST_UNINSTALL_COMPLETE_DESC: "Se eliminaron los archivos de GFG Engine",
	TOAST_UNINSTALL_FAILED: "Error de desinstalación",
	TOAST_CONFIG_UPDATE_FAILED: "Error de actualización",
	TOAST_CONFIG_UPDATE_FAILED_DESC: "No se pudo actualizar la configuración",
	TOAST_CLIPBOARD_SUCCESS: "¡Copiado al portapapeles!",
	TOAST_CLIPBOARD_SUCCESS_DESC: "Opción de lanzamiento lista para pegar",
	TOAST_CLIPBOARD_FAILED: "Error al copiar",
	TOAST_CLIPBOARD_FAILED_DESC: "No se pudo copiar al portapapeles",
	FEATURE_UPSCALING_TAB: "Upscaling",
	LIVE_STATUS_TITLE: "Live Status",
	LIVE_STATUS_CONNECTED: "GFG Extreme is active",
	LIVE_STATUS_WAITING: "Waiting for GFG Extreme",
	LIVE_STATUS_WAITING_DESC: "Sin métricas en vivo; GFG Extreme puede seguir activo. Algunos juegos no las informan. Comprueba la generación o el escalado manualmente.",
	LIVE_STATUS_FG_INACTIVE: "On in settings, but not currently generating frames.",
	LIVE_STATUS_FG_MENU_SUSPENDED: "Frame Generation is disabled while a Steam or Decky menu is open.",
	LIVE_STATUS_OFF: "Off",
	LIVE_STATUS_SCALING_INACTIVE: "On in settings, but the game image is not being upscaled.",
	LIVE_STATUS_SCALING_MEMORY_LIMIT: "The requested render resolution exceeds this GPU's memory safety limit. Lower the in-game resolution.",
	LIVE_STATUS_SCALING_MEMORY_CONSTRAINED: "Requested {requested}×; limited to {effective}× by this GPU's memory safety limit.",
	LIVE_STATUS_SCALING_NO_HEADROOM: "Esta entrada ya llena la pantalla de destino. Prueba el modo ventana, reduce la resolución del juego o activa el Supermuestreo de calidad.",
	LIVE_STATUS_PENDING: "A saved change is still applying or needs a restart.",
	LIVE_STATUS_SUPERSAMPLING: "Quality Supersampling active.",
	LIVE_STATUS_SCALING_FALLBACK: "You selected {requested}; GFG Extreme is using {active} instead.",
	LIVE_STATUS_MODE: "Mode",
	LIVE_STATUS_FIXED_VALUE: "Fixed",
	LIVE_STATUS_ADAPTIVE_STYLE: "Style",
	LIVE_STATUS_STEADY_VALUE: "Steady",
	LIVE_STATUS_FRACTIONAL_VALUE: "Fractional",
	LIVE_STATUS_TARGET: "Target",
	LIVE_STATUS_MAX_MULTIPLIER: "Max factor",
	LIVE_STATUS_MULTIPLIER: "Factor",
	LIVE_STATUS_MODEL: "Model",
	LIVE_STATUS_NATIVE: "Native",
	LIVE_STATUS_LS1_PERFORMANCE: "LS1 Perf",
	LIVE_STATUS_ORIGINAL_RESOLUTION: "Input",
	LIVE_STATUS_RENDER_RESOLUTION: "Render",
	LIVE_STATUS_DISPLAY_RESOLUTION: "Display",
	LIVE_STATUS_SCALED_RESOLUTION: "Output",
	LIVE_STATUS_SCALING_UNAVAILABLE: "Unavailable for this running surface.",
	MODEL_WARNING_TITLE: "Advertencia sobre los modelos de Lossless Scaling",
	MODEL_WARNING_DESCRIPTION: "Algunas funciones de Lossless Scaling podrían no estar disponibles:",
	MODEL_WARNING_LS1: "LS1 no ha superado la comprobación de disponibilidad. GFG Scaler se usa automáticamente si LS1 no puede cargarse.",
	MODEL_WARNING_LSFG: "Ha fallado una comprobación de modelos LSFG. La generación de fotogramas podría no estar disponible con la precisión seleccionada.",
	MODEL_WARNING_UPDATE: "Aplica las actualizaciones disponibles de GFG Extreme y Renderer y reinicia. Si persiste, verifica los archivos de Lossless Scaling y recopila diagnósticos.",
	MODEL_WARNING_CHECK_UPDATES: "Abrir versiones del motor"
};
var ja = {
	CONFIG_VKBASALT_ADVANCED_GLOBAL_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. The Default profile uses this global file.",
	CONFIG_VKBASALT_ADVANCED_PROFILE_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. This file belongs to the selected profile and is removed when that profile is deleted.",
	CONFIG_VKBASALT_SHARPENING: "Sharpening",
	CONFIG_VKBASALT_SHARPENING_DESC: "CAS is a crisp general-purpose sharpener. DLS can preserve noisy or grainy detail better when paired with denoise.",
	CONFIG_VKBASALT_EFFECT_NONE: "Off",
	CONFIG_VKBASALT_SHARPENING_CAS: "CAS",
	CONFIG_VKBASALT_SHARPENING_DLS: "DLS",
	CONFIG_VKBASALT_SHARPNESS: "Sharpness ({value}%)",
	CONFIG_VKBASALT_SHARPNESS_DESC: "Higher values produce a stronger effect but can exaggerate grain and create halos around high-contrast edges.",
	CONFIG_VKBASALT_DLS_DENOISE: "DLS Denoise ({value}%)",
	CONFIG_VKBASALT_DLS_DENOISE_DESC: "Limits how strongly DLS sharpens film grain and fine noise.",
	CONFIG_VKBASALT_ANTIALIASING: "Anti-aliasing",
	CONFIG_VKBASALT_ANTIALIASING_DESC: "Optionally smooth jagged edges before sharpening. FXAA is lighter and softer; SMAA is more selective and may cost more GPU time.",
	CONFIG_VKBASALT_ANTIALIASING_FXAA: "FXAA",
	CONFIG_VKBASALT_ANTIALIASING_SMAA: "SMAA",
	CONFIG_VKBASALT_SHADER: "エフェクト",
	CONFIG_VKBASALT_SHADER_DESC: "Effects run in selection order; uncheck and recheck to move one last. Stacking increases GPU load, especially with heavier effects such as HDR Look. Test per game and monitor GPU usage.",
	CONFIG_VKBASALT_EFFECTS_SELECTED: "Choose effects ({value} selected)",
	CONFIG_VKBASALT_EFFECTS_CLEAR: "Clear all",
	CONFIG_VKBASALT_EFFECTS_DONE: "Done",
	CONFIG_VKBASALT_EFFECTS_PREVIOUS_PAGE: "Previous effects page",
	CONFIG_VKBASALT_EFFECTS_NEXT_PAGE: "Next effects page",
	CONFIG_VKBASALT_SHADER_VIBRANCE: "Vibrance",
	CONFIG_VKBASALT_SHADER_CURVES: "Curves",
	CONFIG_VKBASALT_SHADER_DEBAND: "Deband",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR: "Technicolor",
	CONFIG_VKBASALT_SHADER_SEPIA: "Sepia",
	CONFIG_VKBASALT_SHADER_MONOCHROME: "Monochrome",
	CONFIG_VKBASALT_SHADER_VIGNETTE: "Vignette",
	CONFIG_VKBASALT_SHADER_HDR_LOOK: "HDR Look (SDR)",
	CONFIG_VKBASALT_SHADER_CLARITY: "Clarity",
	CONFIG_VKBASALT_SHADER_LEVELS_PLUS: "Levels Plus",
	CONFIG_VKBASALT_SHADER_COLOURFULNESS: "Colourfulness",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR2: "Technicolor 2",
	CONFIG_VKBASALT_SHADER_DPX: "DPX / Cineon",
	CONFIG_VKBASALT_SHADER_BLEACH_BYPASS: "Bleach Bypass",
	CONFIG_VKBASALT_SHADER_NOIR: "Noir",
	CONFIG_VKBASALT_SHADER_FILM_GRAIN: "Film Grain",
	CONFIG_VKBASALT_SHADER_CARTOON: "Cartoon",
	CONFIG_VKBASALT_SHADER_NOSTALGIA: "Nostalgia",
	CONFIG_VKBASALT_SHADER_CHROMATIC_ABERRATION: "Chromatic Aberration",
	CONTENT_HIDE_INFO: "情報を隠す",
	CONTENT_SHOW_INFO: "情報を表示",
	DEVELOPMENT_DEPLOYMENT_TITLE: "ローカル開発版のデプロイ",
	DEVELOPMENT_DETAILS: "詳細",
	DEVELOPMENT_HIDE: "隠す",
	DEVELOPMENT_DEPLOYED: "デプロイ済み",
	DEVELOPMENT_DEPLOYED_AT: "デプロイ済み",
	DEVELOPMENT_UNCHANGED: "変更なし",
	DEVELOPMENT_COMMIT: "コミット",
	DEVELOPMENT_FRONTEND: "フロントエンド",
	DEVELOPMENT_BACKEND: "バックエンド",
	DEVELOPMENT_LOCAL_EDITS: "+ ローカルの変更",
	DEVELOPMENT_LAYER_64: "64 ビットレイヤー",
	DEVELOPMENT_LAYER_32: "32 ビットレイヤー",
	DEVELOPMENT_FLATPAK_BUNDLES: "Flatpak バンドル",
	DEVELOPMENT_UNCHANGED_BY_DEPLOYMENT: "今回のデプロイでは変更なし",
	CONTENT_IMAGE_PROCESSING: "画像処理",
	IMAGE_PROCESSING_PERFORMANCE_INFO: "フレーム生成、スケーリング、シェーダーの併用は性能を下げる場合があります。不要な機能を切り、ゲームごとにウィンドウと全画面を試してください。",
	CONTENT_TAB_FRAME_GENERATION: "フレーム生成",
	CONTENT_TAB_SCALING: "スケーリング",
	CONTENT_TAB_SHADERS: "シェーダー",
	CONTENT_SCALING: "スケーリング",
	CONTENT_SHADERS: "シェーダー",
	SCALING_ENABLED: "スケーリングを有効化（再起動）",
	EXPERIMENTAL_LABEL: "実験的",
	SCALING_ENABLED_DESC: "起動前に有効にすると Lossless Scaling または GFG Scaler を使えます。オフにするとスケーリングは無効です。ゲームによってはウィンドウモードが必要です。ボーダーレス全画面でも動作する場合があります。",
	SCALING_RUNTIME_SURFACE_UNSUPPORTED: "この実行サーフェスは GFG Extreme スケーリングに対応していません。対応するサーフェスが検出されるまで、クオリティスーパーサンプリング、スケール倍率、シャープネスはロックされます。フレーム生成は引き続き利用できます。",
	SCALING_METHOD: "スケーリング方式",
	SCALING_METHOD_DESC: "スケーリングモデルを選択します。ゲームの実行中でも変更できます。",
	SCALING_LS1_ACTIVE_FALLBACK: "このゲームでは LS1 を利用できません。GFG Scaler が有効になっています。LS1 の選択は保持されます。",
	SCALING_LS1_UNAVAILABLE: "LS1 の利用確認に失敗しました。読み込めない場合は GFG Scaler に切り替わりますが、LS1 の選択は保持されます。",
	SCALING_METHOD_COMPARISON_TIP: "スケーリングの仕組み:\n1. Steam でゲーム解像度をディスプレイの最大解像度に設定します（Steam Deck: 1280 × 800、Steam Machine: 3840 × 2160）。\n2. ゲーム内では 480p、720p、またはそれ以上の低い解像度を選びます。\n3. スケール倍率で画像を拡大します。2x は入力の幅と高さをそれぞれ 2 倍にする目標値です（640×360 → 1280×720）。\n\nゲームの描画解像度を下げて再び拡大すると、画質とのトレードオフはありますが、パフォーマンスを大きく改善できます。",
	SCALING_METHOD_NATIVE: "ネイティブ解像度",
	SCALING_METHOD_MAKO: "GFG Scaler",
	SCALING_METHOD_LS1: "LS1 Quality",
	SCALING_METHOD_LS1_PERFORMANCE: "LS1 Performance",
	SCALING_FACTOR: "スケール倍率",
	SCALING_FACTOR_DESC: "2x はゲーム描画の幅と高さをそれぞれ 2 倍にする目標値です（640×360 → 1280×720）。出力サイズが固定なら、GFG Extreme はゲームに小さい画像を要求します。ゲームがウィンドウサイズを決める場合は、先にゲーム内解像度を下げてください。GFG Extreme は出力を拡大しますが、画面と GPU の制限を受けます。",
	SCALING_FACTOR_LIMIT_SUFFIX: "ディスプレイ上限",
	SCALING_FACTOR_DEVICE_LIMIT: "現在のディスプレイ上限: {factor}x。保存済みの {saved}x は維持されます。使用するにはクオリティスーパーサンプリングを有効にしてください。",
	SCALING_FACTOR_NO_HEADROOM: "この入力はすでに表示先全体を満たしています。ウィンドウモードを試すか、ゲーム内解像度を下げるか、クオリティスーパーサンプリングを有効にしてください。",
	SCALING_SUPERSAMPLING: "クオリティスーパーサンプリング",
	SCALING_SUPERSAMPLING_DESC: "Gamescope の出力上限を超えて高品質なダウンサンプリングを行えるようにします。GPU とメモリの使用量が増加します。他のデスクトップサーフェスでのスケーリングには影響しません。",
	SCALING_SUPERSAMPLING_WARNING: "スーパーサンプリング中は、GFG Extreme が Gamescope の出力上限を超えて、より鮮明にダウンサンプリングする場合があります。",
	SCALING_SHARPNESS: "スケーリングのシャープネス",
	SCALING_SHARPNESS_DESC: "GFG Scaler: 3x シャープニング基準の 0～100%。LS1: 学習済みの 5 段階から選択します。",
	CONTENT_FPS_MULTIPLIER: "フレーム生成",
	CONTENT_PERFORMANCE_SETTINGS: "パフォーマンス設定",
	CONTENT_ADVANCED_DETAILS: "詳細情報",
	CONTENT_FLATPAK_SETUP: "Flatpak設定",
	CONFIG_SECTION_TITLE: "高度なレンダリング設定",
	CONFIG_WORKAROUNDS_TITLE: "互換性設定",
	CONFIG_FLOW_SCALE: "フロースケール",
	CONFIG_FLOW_SCALE_DESC: "フレーム生成のモーション推定解像度です。低い値は GPU 負荷を減らし、高い値は画質を優先します。",
	CONFIG_BASE_FPS_CAP: "ベース FPS 制限",
	CONFIG_BASE_FPS_CAP_OFF: "オフ",
	CONFIG_BASE_FPS_CAP_DESC: "フレーム生成前の実フレームレートを制限します。DirectX、Zink 経由の OpenGL、Vulkan に対応します。",
	CONFIG_BASE_FPS_CAP_STEADY_RELATION: "安定ベース FPS 制限（{fps} FPS）によって制御されています。手動値は保存されたままです。",
	CONFIG_BASE_FPS_CAP_FRACTIONAL_PRIORITY_RELATION: "実フレーム優先度（{fps} FPS）によって制御されています。手動値は保存されたままです。",
	CONFIG_BASE_FPS_CAP_RECOVERY_RELATION: "この制限を変更すると、動的ケイデンス回復がオフになります。",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD: "リフレッシュレートに応じてフレーム生成を自動無効化",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD_DESC: "Gamescope の選択したリフレッシュレート以下でフレーム生成を一時停止し、超えると再開します。リフレッシュ情報が必要です。",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD: "リフレッシュレートしきい値",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD_DESC: "フレーム生成を一時停止する最大リフレッシュレートを選択します。",
	CONFIG_ULTRA_PERFORMANCE: "ウルトラパフォーマンス（再起動）",
	CONFIG_ULTRA_PERFORMANCE_DESC: "低消費電力デバイスで GFG Extreme の GPU 負荷を軽減します。フロースケール 70%、軽量 FG モデル、対応環境では FP16、スケーリング有効時は LS1 Performance を使用します。有効な GFG Extreme 機能全体で、画質と引き換えにパフォーマンスを高めます。",
	CONFIG_ULTRA_PERFORMANCE_WARNING: "Ultra Performance のオン／オフ切り替えにはゲームの再起動が必要です。その他の互換性のあるプロファイル設定は起動後も利用できます。",
	CONFIG_PERFORMANCE_MODE: "軽量 FG モデル",
	CONFIG_PERFORMANCE_MODE_DESC: "軽量 FG モデルは GPU 負荷を下げますが残像が増えます。ウルトラパフォーマンスでは強制的にオンです。",
	CONFIG_DISABLE_STEAMDECK_MODE: "Steam Deckモードを無効化（再起動）",
	CONFIG_DISABLE_STEAMDECK_MODE_DESC: "Steam Deck モードを無効化します。一部ゲームの隠し設定を解放します。",
	CONFIG_ENABLE_ZINK: "OpenGLゲーム用Zinkを有効化（再起動）",
	CONFIG_ENABLE_ZINK_DESC: "OpenGL ゲームを Vulkan 経由で実行します。一部でクラッシュやフリーズの可能性があります。",
	CONFIG_FORCE_ALSA_AUDIO: "ALSA オーディオを強制（再起動）",
	CONFIG_FORCE_ALSA_AUDIO_DESC: "Zink との互換性、音の途切れ、突然の大音量に役立つ場合があります。オフにすると通常の音声設定に戻ります。",
	CONFIG_EXTERNAL_TOOLS_TITLE: "外部ツール",
	CONFIG_ENABLE_MANGOHUD: "MangoHud を有効化（再起動）",
	CONFIG_ENABLE_MANGOHUD_DESC: "インストール済み MangoHud とその設定を使います。ゲーム別の変更はエキスパートガイドを参照してください。",
	CONFIG_ENABLE_VKBASALT: "シェーダーを有効化（再起動）",
	CONFIG_ENABLE_VKBASALT_DESC: "起動前に有効にすると、同梱のシャープ化、アンチエイリアス、シェーダーを使えます。別途インストールは不要です。効果が見えない場合は、ウィンドウモードまたはボーダーレス全画面を試してください。",
	INSTALL_INSTALLING: "GFG Engine をインストール中...",
	INSTALL_UNINSTALLING: "GFG Engine を削除中...",
	FLATPAK_MODAL_TITLE: "Flatpak拡張",
	FLATPAK_RUNTIME_INSTALLER: "ランタイム拡張インストーラー",
	FLATPAK_RUNTIME_VERSION: "ランタイム {version}",
	FLATPAK_INSTALLED: "インストール済み",
	FLATPAK_NOT_INSTALLED: "未インストール",
	FLATPAK_UNINSTALL_TITLE: "ランタイム拡張をアンインストール",
	FLATPAK_UNINSTALL_CONFIRM_PREFIX: "本当に",
	FLATPAK_UNINSTALL_CONFIRM_SUFFIX: "ランタイム拡張をアンインストールしますか？",
	FLATPAK_UNINSTALL_BTN: "アンインストール",
	FLATPAK_INSTALL_BTN: "インストール",
	FLATPAK_UPDATE_BTN: "更新",
	FLATPAK_INSTALLING_BTN: "インストール中...",
	FLATPAK_UNINSTALLING_BTN: "アンインストール中...",
	FLATPAK_UPDATING_BTN: "更新中...",
	FLATPAK_APPS_TITLE: "Flatpakアプリケーション",
	FLATPAK_NO_APPS: "Flatpakアプリなし",
	FLATPAK_NO_APPS_DESC: "現在インストールされているFlatpakアプリケーションはありません",
	FLATPAK_STATUS_CONFIGURED: "準備済み",
	FLATPAK_STATUS_PARTIAL: "部分設定",
	FLATPAK_STATUS_NO_OVERRIDES: "オーバーライドなし",
	FLATPAK_ERROR: "エラー",
	FLATPAK_ERROR_STATUS: "拡張ステータスの確認に失敗しました",
	FLATPAK_ERROR_APPS: "Flatpakアプリケーションの読み込みに失敗しました",
	FLATPAK_STEAM_CONFIG_TITLE: "手動 Steam ショートカットの参照",
	FLATPAK_STEAM_CONFIG_HEADER: "ターゲット例（Steam は自動設定されません）",
	FLATPAK_STEAM_CONFIG_DESC: "元のターゲットが /usr/bin/flatpak の手動追加 Steam ショートカット専用です。先に上でアプリを準備し、作業フォルダーと起動オプションは維持してください。Heroic、Lutris、EmuDeck はランチャー設定ガイドを参照してください。",
	FLATPAK_IMPORTANT_LABEL: "重要:",
	FLATPAK_STEAM_CONFIG_IMPORTANT: "TARGET のみを置き換えてください。Launch Options には貼り付けないでください。",
	FLATPAK_PER_GAME_APP_DESC: "{app_id} - {status}。{wrapper_path} を使ってゲームごとに GFG Extreme を有効にします。入力欄はランチャー設定ガイドで確認してください。",
	FLATPAK_DIRECT_APP_DESC: "{app_id} - {status}。準備はこの Flatpak アプリ全体に適用されます。EmuDeck と Steam ショートカットの手順はランチャー設定ガイドをご覧ください。",
	FLATPAK_STEP_WRAPPER_PATH: "このデバイスにインストールされたラッパー:",
	FLATPAK_STEP_FINAL: "元のターゲットが \"/usr/bin/flatpak\" のショートカット用ターゲット:",
	FLATPAK_OPEN_README: "ランチャー設定ガイドを開く",
	FLATPAK_CLOSE: "閉じる",
	ADVANCED_DETAILS_LOADING: "情報を読み込み中...",
	ADVANCED_DETAILS_ERROR_PREFIX: "エラー:",
	ADVANCED_DETAILS_DLL_PATH: "DLLパス",
	ADVANCED_DETAILS_LIBRARY: "Lossless Scaling ライブラリ",
	ADVANCED_DETAILS_RENDERER: "GFG Engine",
	ADVANCED_DETAILS_INSTALLATION: "Installation",
	ADVANCED_DETAILS_INSTALLED_VERSION: "Installed version",
	ADVANCED_DETAILS_BUNDLED_VERSION: "Bundled version",
	ADVANCED_DETAILS_HOST_ARCHITECTURE: "Host architecture",
	ADVANCED_DETAILS_LAYER_PATH: "Renderer library",
	ADVANCED_DETAILS_MANIFEST_PATH: "Vulkan manifest",
	ADVANCED_DETAILS_LAUNCHER_PATH: "Launch wrapper",
	ADVANCED_DETAILS_DETECTION: "Detection",
	ADVANCED_DETAILS_DLL_NOT_DETECTED: "Lossless Scaling not detected",
	ADVANCED_DETAILS_UNSUPPORTED_HOST: "Unsupported host",
	ADVANCED_DETAILS_UPDATE_REQUIRED: "Bundled update available",
	ADVANCED_DETAILS_INCOMPLETE: "Incomplete installation",
	ADVANCED_DETAILS_NOT_AVAILABLE: "利用不可",
	ADVANCED_DETAILS_DETECTION_SOURCE: "検出ソース",
	ADVANCED_DETAILS_CLOSE: "閉じる",
	WELCOME_TITLE: "GFG Extreme チームからこんにちは！",
	WELCOME_TIPS_COLLAPSE: "ヒントを隠す",
	WELCOME_TIPS_EXPAND: "ヒントを表示",
	WELCOME_LIVE_UPDATES: "多くの設定はリアルタイムで反映されます。",
	WELCOME_RESTART_REQUIRED: "「再起動」と表示された項目はゲームの再起動が必要です。",
	WELCOME_PERFORMANCE_NOTE: "ゲームの解像度やスケーリングの変更はパフォーマンスに影響する場合があります。",
	WELCOME_CLEAN_SESSION_PREFIX: "もし",
	WELCOME_CLEAN_SESSION_WRONG: "表示や操作感に違和感がある",
	WELCOME_CLEAN_SESSION_AFTER: "場合は、",
	WELCOME_CLEAN_SESSION_CHANGES: "何度か変更した後",
	WELCOME_CLEAN_SESSION_RESTART_SEPARATOR: "、",
	WELCOME_CLEAN_SESSION_RESTART: "ゲームを再起動して新しいクリーンなセッションでお試しください。",
	WELCOME_ENJOY: "最適な設定はゲームごとに異なります。試して選び、GFG Extreme の更新はリリースページでご確認ください。",
	PROFILE_CAPTURE_READY: "保存済みプロファイルは GFG Extreme が自動的に選択します。新しいゲームの場合は下で保存してください。再起動が必要な設定を変更した後はゲームを再起動してください。",
	PROFILE_HELP: "ゲームのプロセスを一度保存するとプロファイルが自動選択されます。ゲーム外ではドロップダウンで編集するプロファイルを選びます。",
	PROFILE_SECTION_TITLE: "ゲーム / プロセス プロファイル",
	PROFILE_DEFAULT: "デフォルト",
	PROFILE_SAVED_LABEL: "保存済みプロファイル",
	PROFILE_GAME_SAVED: "ゲームプロファイルを保存しました",
	PROFILE_GAME_SAVE_FAILED: "ゲームプロファイルを保存できませんでした",
	PROFILE_SAVE_RUNNING: "{game} のプロファイルを保存",
	PROFILE_DETAIL_DEFAULT: "ゲームを開いてプロフィールを保存してください",
	PROFILE_DETAIL_GAME: "保存済みゲーム",
	PROFILE_DETAIL_PROCESS: "保存済みプロセス",
	PROFILE_STEAM_APP_ID: "Steam アプリ ID: {app_id}",
	PROFILE_PROCESSES: "プロセス: {processes}",
	PROFILE_PROCESSES_EMPTY: "プロセス: 下の「一致するプロセス」に入力してください",
	PROFILE_MANAGE_WHEN_IDLE: "実行中のゲームを終了すると、プロファイルの名前変更や削除ができます。",
	PROFILE_NAME_LABEL: "名前",
	PROFILE_CANCEL_BTN: "キャンセル",
	PROFILE_RENAME_TITLE: "プロファイルの名前を変更",
	PROFILE_RENAME_DESC_PREFIX: "このゲームまたはプロセスプロファイルの分かりやすい名前を選択してください。",
	PROFILE_RENAME_BTN: "名前変更",
	PROFILE_CANNOT_DELETE_TITLE: "デフォルトプロファイルは削除できません",
	PROFILE_CANNOT_DELETE_MSG: "デフォルトプロファイルは削除できません",
	PROFILE_DELETE_TITLE: "ゲーム / プロセス プロファイルを削除",
	PROFILE_DELETE_CONFIRM: "「{profile}」と保存済み設定をすべて削除しますか？",
	PROFILE_DELETE_BTN: "削除",
	PROFILE_CANNOT_RENAME_TITLE: "デフォルトプロファイルの名前は変更できません",
	PROFILE_CANNOT_RENAME_MSG: "デフォルトプロファイルの名前は変更できません",
	USAGE_TITLE: "使用方法",
	USAGE_DESC: "この起動オプションを Steam のゲームに追加すると、GFG Extreme のフレーム生成、スケーリング、または両方を使えます。",
	CLIPBOARD_COPIED: "クリップボードにコピーしました",
	CLIPBOARD_COPYING: "コピー中...",
	CLIPBOARD_COPY_LAUNCH: "起動オプションをコピー",
	CLIPBOARD_MAKO_FGMOD: "GFG Extreme + DeckyFG",
	CONTENT_RUNNING: "実行中。",
	CONTENT_ENGINE_UPDATE_REQUIRED: "GFG Engine の更新が必要です",
	CONTENT_ENGINE_INSTALLED: "インストール済み:",
	CONTENT_ENGINE_NOT_RECORDED: "記録なし",
	CONTENT_ENGINE_EXPECTS: "このプラグインが必要とするバージョン:",
	CONTENT_ENGINE_BUNDLED_VERSION: "同梱バージョン",
	CONTENT_ENGINE_PREDATES_TRACKING: "インストール済みのペイロードはバージョン追跡より前のものです。",
	CONTENT_ENGINE_UPDATE_DESC: "同梱版の GFG Engine を再インストールし、準備済み Flatpak のランタイム拡張も更新してください。",
	CONTENT_UPDATE_RENDERER: "GFG Engine を更新",
	CONTENT_UPDATING_RENDERER: "GFG Engine を更新中...",
	ADAPTIVE_TITLE: "アダプティブ フレーム生成",
	ADAPTIVE_DESC: "目標出力 FPS に合わせます。既定の安定ベース FPS 制限は滑らかさを優先し、分数倍率 アダプティブは実フレームを多く残します。ゲームごとに試してください。",
	FRACTIONAL_ADAPTIVE_PRESET: "分数倍率 アダプティブ",
	FRACTIONAL_ADAPTIVE_PRESET_DESC: "生成倍率を組み合わせ、実 FPS 60 → 表示 FPS 90 のような目標を目指します。実フレームを多く保ち、入力遅延とゴーストを減らせる場合がありますが、一部のゲームでは滑らかさが落ちることがあります。",
	FRACTIONAL_ADAPTIVE_PRESET_RELATION: "安定ベース FPS 制限とは同時に使用できません。この設定を変更すると、動的ケイデンス回復もオフになります。",
	ADAPTIVE_REAL_FRAME_PRIORITY: "実フレーム優先度",
	ADAPTIVE_REAL_FRAME_PRIORITY_DESC: "表示される FPS は目標 FPS に基づく実フレーム上限の推定値であり、ゲームでの実際の FPS を保証するものではありません。優先度を高くすると実フレームが増え、遅延やゴーストを減らせる場合がありますが、均一さが低下することがあります。",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO: "自動",
	ADAPTIVE_REAL_FRAME_PRIORITY_LOW: "低",
	ADAPTIVE_REAL_FRAME_PRIORITY_MEDIUM: "中",
	ADAPTIVE_REAL_FRAME_PRIORITY_HIGH: "高",
	ADAPTIVE_REAL_FRAME_PRIORITY_VERY_HIGH: "最高",
	ADAPTIVE_REAL_FRAME_PRIORITY_OPTION: "{priority} — 最大 {cap} 実 FPS (目標の {percent}%)",
	ADAPTIVE_REAL_FRAME_PRIORITY_ACTIVE_RELATION: "目標 {target} FPS に達した場合、実 {cap} / 生成 {generated_fps} FPS（約 {real}:{generated}）です。実際の値は変動し、ベース FPS 制限より優先します。",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO_RELATION: "自動では分数倍率 アダプティブの現在の動作を維持します。ベース FPS 制限は引き続き使用できます。",
	ADAPTIVE_TARGET_FPS: "目標FPS",
	ADAPTIVE_TARGET_FPS_DESC: "希望する出力 FPS。分数倍率は倍率を混ぜ、安定ベース FPS 制限は目標の半分から始め、検証済みの低い整数倍率に合わせる場合があります。",
	ADAPTIVE_AUTO_BASE_FPS_CAP: "安定ベース FPS 制限",
	ADAPTIVE_AUTO_BASE_FPS_CAP_DESC: "既定のアダプティブモード。目標の半分から始め、スムーズ ケイデンスで検証済みの 3x～5x 倍率に合わせられます。通常は滑らかですが、実フレームが減り、遅延や残像が増える場合があります。",
	ADAPTIVE_AUTO_BASE_FPS_CAP_RELATION: "ベース FPS 制限を上書きします。分数倍率 アダプティブまたは動的ケイデンス回復とは同時に使用できません。",
	ADAPTIVE_MAX_MULTIPLIER: "アダプティブ最大倍率",
	ADAPTIVE_MAX_MULTIPLIER_DESC: "0x を使うと、リソースを解放せずにフレーム生成をライブで一時停止または再開できます。それ以外は固定比率ではなく補間の上限で、アダプティブはより低い倍率や分数倍率を使用する場合があります。目標 FPS に届く範囲で、必要以上に高く設定しないでください。ゲームごとに 2x～5x を確認してください。",
	ADAPTIVE_SMOOTH_CADENCE: "スムーズ ケイデンス",
	ADAPTIVE_SMOOTH_CADENCE_DESC: "検証済みの順序付き Gamescope 表示でペーシングを安定させます。フラクショナル適応では実フレームを維持し、固定モードと安定ベース FPS 制限では均一な出力を優先できます。実 FPS と応答性が下がる場合があります。既定で有効です。ゲームごとに必要なら無効にしてください。",
	GAMESCOPE_VRR_MODE: "Gamescope VRR",
	GAMESCOPE_VRR_MODE_DESC: "VRR をオフにすると、GFG Extreme がフレームペーシングを制御できます。ゲームによってはフレーム生成が改善する場合がありますが、そうでない場合もあるため、ゲームごとに試してください。お使いのデバイスまたはディスプレイが VRR に対応していない場合、この設定は効果がありません。",
	GAMESCOPE_VRR_FOLLOW_STEAM: "Steam に従う",
	GAMESCOPE_VRR_ON: "オン",
	GAMESCOPE_VRR_OFF: "オフ",
	DYNAMIC_CADENCE_RECOVERY: "動的ケイデンス回復",
	DYNAMIC_CADENCE_RECOVERY_DESC: "ゲーム中 30 FPS、メニュー 60 FPS のようにネイティブレートが切り替わるゲームやエミュレーターを支援します。定期的にレートの変化を確認して正しいケイデンスを回復しますが、確認のたびにペーシングへ短く影響する場合があります。必要なゲームでのみ有効にしてください。",
	DYNAMIC_CADENCE_RECOVERY_RELATION: "回復をオンにすると安定ベース FPS 制限とベース FPS 制限が無効になり、実フレーム優先度が自動に戻ります。後で制限や優先度を変えると回復はオフになります。",
	DYNAMIC_CADENCE_PROBE_INTERVAL: "ケイデンスプローブ間隔",
	DYNAMIC_CADENCE_PROBE_INTERVAL_DESC: "回復の確認間隔。0.1 秒は引っかかりが増える場合があり、既定は 2 秒、3 秒は確認が最も少なくなります。ゲームごとに試してください。",
	ADAPTIVE_VALUE: "アダプティブ",
	CONFIG_DLL_PATH: "Lossless.dll のパス（再起動）",
	CONFIG_DLL_PATH_DESC: "Lossless.dll の完全パス（任意）。空欄にすると GFG Engine の自動検出を使用します。変更後はゲームを再起動してください。",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH: "次回の起動時に GFG Engine を無効化",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH_DESC: "問題調査用です。次回の起動だけ GFG Engine を読み込みません。生成のオン/オフには上のフレーム生成を使ってください。",
	CONFIG_DISABLE_HDR_EXPOSURE: "HDR を無効化",
	CONFIG_DISABLE_HDR_EXPOSURE_DESC: "HDR はこのリリースでは利用できません。この必須設定は安定した SDR パスを維持します。",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY: "Gamescope WSI（再起動）",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_DESC: "Gamescope の表示経路で色付き・ピクセル状の動きの乱れを減らせる場合があります。スケーリングとフレーム生成の両方で任意です。必要なゲームだけオンにしてください。",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_WARNING: "対応する 64 ビットのホスト起動専用です。不要ならオフにしてください。性能が下がる場合があります。",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY: "ゲームのスワップチェーン画像（再起動）",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_DESC: "フレーム生成で起動できないゲームでは、要求されたスワップチェーン画像の最小数を保つと改善する場合があります。該当ゲームのみ使用してください。",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_WARNING: "コンポジターに空き画像がない場合は生成フレームがスキップされ、高負荷時の滑らかさやパフォーマンスが低下することがあります。",
	FRAME_GENERATION_PROVISIONED: "Frame-gen を有効化（再起動）",
	FRAME_GENERATION_PROVISIONED_DESC: "起動前に有効にしてフレーム生成を読み込みます。スケーリングかシェーダーだけを使う場合はオフにしてください。",
	FIXED_MULTIPLIER: "固定倍率",
	FIXED_MULTIPLIER_DESC: "2x～5x は固定の出力倍率です。高リフレッシュ画面向けの 5x は負荷が高くなります。0x はリソースを解放せずに生成を一時停止します。",
	CONFIG_ALLOW_FP16: "FP16 を許可（再起動）",
	CONFIG_ALLOW_FP16_DESC: "グローバルなレンダラー設定です。すべてのプロファイルに適用され、ゲームごとに変更できません。AMD では性能が向上する場合があります。古い NVIDIA GPU では無効にしてください。変更後はゲームを再起動してください。",
	CONFIG_GPU: "GPU（再起動）",
	CONFIG_GPU_DESC: "任意の GPU 名、vendor:device ID、または PCI バス ID。変更後はゲームを再起動してください。",
	CONFIG_ACTIVE_IN: "一致するプロセス",
	CONFIG_ACTIVE_IN_DESC: "実行ファイル名やプロセス名をカンマで区切ります。ゲーム検出で自動入力されるため、ランチャーやエミュレーターの別名が必要な場合だけ編集してください。",
	CONFIG_MANUAL_OVERRIDES_TITLE: "手動オーバーライド",
	INSTALL_REMOVE_RENDERER: "GFG Engine を削除",
	INSTALL_RENDERER: "GFG Engine をインストール",
	FLATPAK_EXTENSION_UPDATED: "Flatpak 拡張を更新しました",
	FLATPAK_EXTENSION_FAILED: "Flatpak 拡張の操作に失敗しました",
	FLATPAK_EXTENSION_ACTION_FAILED: "操作できませんでした:",
	FLATPAK_RUNTIME_EXTENSION_UPDATED: "ランタイム拡張を更新しました",
	FLATPAK_RUNTIME_EXTENSION: "ランタイム拡張",
	FLATPAK_APPLICATION_UPDATED: "Flatpak アプリケーションを更新しました",
	FLATPAK_UPDATED: "更新しました",
	FLATPAK_PREPARE_APPLICATION: "アプリケーションを準備",
	FLATPAK_PREPARE_APPLICATION_DESC: "対応する拡張を入れてアプリを準備します。Heroic/Lutris はゲームごとのラッパーが必要で、エミュレーターはアプリ全体に適用されます。ランチャーガイドを参照してください。",
	FLATPAK_INSTALL_ACTION: "インストール",
	FLATPAK_UNINSTALL_ACTION: "アンインストール",
	FLATPAK_APPLICATION_ACTION_FAILED: "更新できませんでした:",
	PROFILE_UNKNOWN_ERROR: "不明なエラー",
	PROFILE_LOAD_FAILED: "プロファイルの読み込みに失敗しました",
	PROFILE_LOAD_ERROR: "プロファイルの読み込み中にエラーが発生しました",
	PROFILE_SWITCHED: "プロファイルを切り替えました",
	PROFILE_SWITCHED_DESC: "切り替え先:",
	PROFILE_SWITCH_FAILED: "プロファイルの切り替えに失敗しました",
	PROFILE_SWITCH_ERROR: "プロファイル切り替え中にエラーが発生しました",
	PROFILE_DELETED: "プロファイルを削除しました",
	PROFILE_DELETED_DESC: "削除したプロファイル:",
	PROFILE_DELETE_FAILED: "プロファイルの削除に失敗しました",
	PROFILE_DELETE_ERROR: "プロファイル削除中にエラーが発生しました",
	PROFILE_RENAMED: "プロファイル名を変更しました",
	PROFILE_RENAMED_DESC: "変更後のプロファイル名:",
	PROFILE_RENAME_FAILED: "プロファイル名の変更に失敗しました",
	PROFILE_RENAME_ERROR: "プロファイル名変更中にエラーが発生しました",
	PROFILE_UPDATE_CONFIG_FAILED: "プロファイル設定の更新に失敗しました",
	PROFILE_UPDATE_CONFIG_ERROR: "プロファイル設定の更新中にエラーが発生しました",
	USAGE_MAKO_CONFIG_NOTE: "このコマンドで起動したゲームにのみ GFG Extreme が適用されます。",
	USAGE_ISOLATION_NOTE: "同じゲームで GFG Extreme と別のフレーム生成またはスケーリングツールを併用しないでください。",
	ADVANCED_DETAILS_FAILED_LOAD_DATA: "データの読み込みに失敗しました",
	STATUS_ENGINE_INSTALLED: "GFG Engine をインストールしました",
	STATUS_ENGINE_NOT_INSTALLED: "GFG Engine は未インストールです",
	STATUS_ENGINE_INSTALLING: "GFG Engine をインストール中...",
	STATUS_ENGINE_UPDATING: "GFG Engine を更新中...",
	STATUS_ENGINE_REMOVING: "GFG Engine を削除中...",
	STATUS_ENGINE_REMOVED: "GFG Engine を削除しました！",
	STATUS_INSTALL_FAILED: "インストールに失敗しました:",
	STATUS_UNINSTALL_FAILED: "アンインストールに失敗しました:",
	STATUS_LOSSLESS_INSTALLED: "Lossless Scaling はインストール済みです",
	STATUS_LOSSLESS_NOT_INSTALLED: "Lossless Scaling は未インストールです — フレーム生成と LS1 に必要です。GFG Scaler は引き続き利用できます",
	TOAST_INSTALL_COMPLETE: "インストール完了",
	TOAST_INSTALL_COMPLETE_DESC: "デバイスを再起動することをおすすめします。",
	TOAST_INSTALL_FAILED: "インストールに失敗しました",
	TOAST_UNKNOWN_ERROR: "不明なエラーが発生しました",
	TOAST_UNINSTALL_COMPLETE: "GFG Engine を削除しました",
	TOAST_UNINSTALL_COMPLETE_DESC: "GFG Engine のファイルを削除しました",
	TOAST_UNINSTALL_FAILED: "アンインストールに失敗しました",
	TOAST_CONFIG_UPDATE_FAILED: "更新に失敗しました",
	TOAST_CONFIG_UPDATE_FAILED_DESC: "設定の更新に失敗しました",
	TOAST_CLIPBOARD_SUCCESS: "クリップボードにコピーしました！",
	TOAST_CLIPBOARD_SUCCESS_DESC: "起動オプションを貼り付けられます",
	TOAST_CLIPBOARD_FAILED: "コピーに失敗しました",
	TOAST_CLIPBOARD_FAILED_DESC: "クリップボードにコピーできませんでした",
	FEATURE_UPSCALING_TAB: "アップスケーリング",
	LIVE_STATUS_TITLE: "ライブステータス",
	LIVE_STATUS_CONNECTED: "GFG Extreme は有効です",
	LIVE_STATUS_WAITING: "GFG Extreme を待機中",
	LIVE_STATUS_WAITING_DESC: "ライブ指標は利用できませんが、GFG Extreme は動作中かもしれません。一部のゲームやエミュレーターは指標を報告しません。フレーム生成かスケーリングを手動で確認してください。",
	LIVE_STATUS_FG_INACTIVE: "設定ではオンですが、現在フレームは生成されていません。",
	LIVE_STATUS_FG_MENU_SUSPENDED: "Frame Generation is disabled while a Steam or Decky menu is open.",
	LIVE_STATUS_OFF: "オフ",
	LIVE_STATUS_SCALING_INACTIVE: "設定ではオンですが、ゲーム画像はアップスケールされていません。",
	LIVE_STATUS_SCALING_MEMORY_LIMIT: "要求されたレンダー解像度が、この GPU のメモリ安全上限を超えています。ゲーム内解像度を下げてください。",
	LIVE_STATUS_SCALING_MEMORY_CONSTRAINED: "要求倍率 {requested}×。この GPU のメモリ安全上限により {effective}× に制限されています。",
	LIVE_STATUS_SCALING_NO_HEADROOM: "この入力はすでに表示先全体を満たしています。ウィンドウモードを試すか、ゲーム内解像度を下げるか、クオリティスーパーサンプリングを有効にしてください。",
	LIVE_STATUS_PENDING: "保存済みの変更が適用中か、再起動が必要です。",
	LIVE_STATUS_SUPERSAMPLING: "クオリティスーパーサンプリングが有効です",
	LIVE_STATUS_SCALING_FALLBACK: "選択されたのは {requested} ですが、GFG Extreme は代わりに {active} を使用しています。",
	LIVE_STATUS_MODE: "モード",
	LIVE_STATUS_FIXED_VALUE: "固定",
	LIVE_STATUS_ADAPTIVE_STYLE: "スタイル",
	LIVE_STATUS_STEADY_VALUE: "安定",
	LIVE_STATUS_FRACTIONAL_VALUE: "分数",
	LIVE_STATUS_TARGET: "目標",
	LIVE_STATUS_MAX_MULTIPLIER: "最大倍率",
	LIVE_STATUS_MULTIPLIER: "倍率",
	LIVE_STATUS_MODEL: "モデル",
	LIVE_STATUS_NATIVE: "ネイティブ",
	LIVE_STATUS_LS1_PERFORMANCE: "LS1 Perf",
	LIVE_STATUS_ORIGINAL_RESOLUTION: "入力",
	LIVE_STATUS_RENDER_RESOLUTION: "レンダー",
	LIVE_STATUS_DISPLAY_RESOLUTION: "ディスプレイ",
	LIVE_STATUS_SCALED_RESOLUTION: "出力",
	LIVE_STATUS_SCALING_UNAVAILABLE: "この実行サーフェスでは利用できません。",
	MODEL_WARNING_TITLE: "Lossless Scalingモデルの警告",
	MODEL_WARNING_DESCRIPTION: "Lossless Scaling の一部の機能が利用できない可能性があります：",
	MODEL_WARNING_LS1: "LS1の利用可否チェックに失敗しました。LS1を読み込めない場合は、GFG Scalerが自動的に使用されます。",
	MODEL_WARNING_LSFG: "LSFGモデルのチェックに失敗しました。選択した精度設定ではフレーム生成を利用できない可能性があります。",
	MODEL_WARNING_UPDATE: "GFG Extreme と Renderer の更新があれば適用し、再起動してください。解決しなければ Lossless Scaling のファイルを確認し、診断情報を収集してください。",
	MODEL_WARNING_CHECK_UPDATES: "レンダラーのリリースを開く"
};
var ko = {
	CONFIG_VKBASALT_ADVANCED_GLOBAL_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. The Default profile uses this global file.",
	CONFIG_VKBASALT_ADVANCED_PROFILE_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. This file belongs to the selected profile and is removed when that profile is deleted.",
	CONFIG_VKBASALT_SHARPENING: "Sharpening",
	CONFIG_VKBASALT_SHARPENING_DESC: "CAS is a crisp general-purpose sharpener. DLS can preserve noisy or grainy detail better when paired with denoise.",
	CONFIG_VKBASALT_EFFECT_NONE: "Off",
	CONFIG_VKBASALT_SHARPENING_CAS: "CAS",
	CONFIG_VKBASALT_SHARPENING_DLS: "DLS",
	CONFIG_VKBASALT_SHARPNESS: "Sharpness ({value}%)",
	CONFIG_VKBASALT_SHARPNESS_DESC: "Higher values produce a stronger effect but can exaggerate grain and create halos around high-contrast edges.",
	CONFIG_VKBASALT_DLS_DENOISE: "DLS Denoise ({value}%)",
	CONFIG_VKBASALT_DLS_DENOISE_DESC: "Limits how strongly DLS sharpens film grain and fine noise.",
	CONFIG_VKBASALT_ANTIALIASING: "Anti-aliasing",
	CONFIG_VKBASALT_ANTIALIASING_DESC: "Optionally smooth jagged edges before sharpening. FXAA is lighter and softer; SMAA is more selective and may cost more GPU time.",
	CONFIG_VKBASALT_ANTIALIASING_FXAA: "FXAA",
	CONFIG_VKBASALT_ANTIALIASING_SMAA: "SMAA",
	CONFIG_VKBASALT_SHADER: "효과",
	CONFIG_VKBASALT_SHADER_DESC: "Effects run in selection order; uncheck and recheck to move one last. Stacking increases GPU load, especially with heavier effects such as HDR Look. Test per game and monitor GPU usage.",
	CONFIG_VKBASALT_EFFECTS_SELECTED: "Choose effects ({value} selected)",
	CONFIG_VKBASALT_EFFECTS_CLEAR: "Clear all",
	CONFIG_VKBASALT_EFFECTS_DONE: "Done",
	CONFIG_VKBASALT_EFFECTS_PREVIOUS_PAGE: "Previous effects page",
	CONFIG_VKBASALT_EFFECTS_NEXT_PAGE: "Next effects page",
	CONFIG_VKBASALT_SHADER_VIBRANCE: "Vibrance",
	CONFIG_VKBASALT_SHADER_CURVES: "Curves",
	CONFIG_VKBASALT_SHADER_DEBAND: "Deband",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR: "Technicolor",
	CONFIG_VKBASALT_SHADER_SEPIA: "Sepia",
	CONFIG_VKBASALT_SHADER_MONOCHROME: "Monochrome",
	CONFIG_VKBASALT_SHADER_VIGNETTE: "Vignette",
	CONFIG_VKBASALT_SHADER_HDR_LOOK: "HDR Look (SDR)",
	CONFIG_VKBASALT_SHADER_CLARITY: "Clarity",
	CONFIG_VKBASALT_SHADER_LEVELS_PLUS: "Levels Plus",
	CONFIG_VKBASALT_SHADER_COLOURFULNESS: "Colourfulness",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR2: "Technicolor 2",
	CONFIG_VKBASALT_SHADER_DPX: "DPX / Cineon",
	CONFIG_VKBASALT_SHADER_BLEACH_BYPASS: "Bleach Bypass",
	CONFIG_VKBASALT_SHADER_NOIR: "Noir",
	CONFIG_VKBASALT_SHADER_FILM_GRAIN: "Film Grain",
	CONFIG_VKBASALT_SHADER_CARTOON: "Cartoon",
	CONFIG_VKBASALT_SHADER_NOSTALGIA: "Nostalgia",
	CONFIG_VKBASALT_SHADER_CHROMATIC_ABERRATION: "Chromatic Aberration",
	CONTENT_HIDE_INFO: "정보 숨기기",
	CONTENT_SHOW_INFO: "정보 표시",
	DEVELOPMENT_DEPLOYMENT_TITLE: "로컬 개발 배포",
	DEVELOPMENT_DETAILS: "상세 정보",
	DEVELOPMENT_HIDE: "숨기기",
	DEVELOPMENT_DEPLOYED: "배포됨",
	DEVELOPMENT_DEPLOYED_AT: "배포됨",
	DEVELOPMENT_UNCHANGED: "변경 없음",
	DEVELOPMENT_COMMIT: "커밋",
	DEVELOPMENT_FRONTEND: "프런트엔드",
	DEVELOPMENT_BACKEND: "백엔드",
	DEVELOPMENT_LOCAL_EDITS: "+ 로컬 변경 사항",
	DEVELOPMENT_LAYER_64: "64비트 레이어",
	DEVELOPMENT_LAYER_32: "32비트 레이어",
	DEVELOPMENT_FLATPAK_BUNDLES: "Flatpak 번들",
	DEVELOPMENT_UNCHANGED_BY_DEPLOYMENT: "이번 배포에서 변경 없음",
	CONTENT_IMAGE_PROCESSING: "이미지 처리",
	IMAGE_PROCESSING_PERFORMANCE_INFO: "프레임 생성, 스케일링, 셰이더를 함께 쓰면 성능이 낮아질 수 있습니다. 불필요한 기능은 끄고 게임별로 창 모드와 전체 화면을 시험하세요.",
	CONTENT_TAB_FRAME_GENERATION: "프레임 생성",
	CONTENT_TAB_SCALING: "스케일링",
	CONTENT_TAB_SHADERS: "셰이더",
	CONTENT_SCALING: "스케일링",
	CONTENT_SHADERS: "셰이더",
	SCALING_ENABLED: "스케일링 사용 (재시작)",
	EXPERIMENTAL_LABEL: "실험적",
	SCALING_ENABLED_DESC: "시작 전에 켜면 Lossless Scaling이나 GFG Scaler를 사용합니다. 끄면 스케일링이 비활성화됩니다. 일부 게임에서는 창 모드가 필요할 수 있으며, 테두리 없는 전체 화면에서도 작동할 수 있습니다.",
	SCALING_RUNTIME_SURFACE_UNSUPPORTED: "This running surface does not support GFG Extreme scaling. Quality Supersampling, Scale Factor, and Sharpness are locked until a supported surface is detected. Frame Generation remains available.",
	SCALING_METHOD: "스케일링 방식",
	SCALING_METHOD_DESC: "스케일링 모델을 선택합니다. 게임 실행 중에도 변경할 수 있습니다.",
	SCALING_LS1_ACTIVE_FALLBACK: "LS1 is unavailable for this game. GFG Scaler is active. Your LS1 selection is preserved.",
	SCALING_LS1_UNAVAILABLE: "LS1 사용 가능 여부 확인에 실패했습니다. 모델을 불러오지 못하면 GFG Scaler로 대체되며 LS1 선택은 유지됩니다.",
	SCALING_METHOD_COMPARISON_TIP: "스케일링 작동 방식:\n1. Steam에서 게임 해상도를 디스플레이의 최대 해상도로 설정하세요(Steam Deck: 1280 × 800, Steam Machine: 3840 × 2160).\n2. 게임에서는 480p, 720p 또는 그 이상의 낮은 해상도를 선택하세요.\n3. 스케일 팩터로 이미지를 확대하세요. 2x는 입력의 가로와 세로를 각각 두 배로 늘리는 목표값입니다(640×360 → 1280×720).\n\n게임의 렌더링 해상도를 낮춘 뒤 다시 확대하면 화질의 절충은 있지만 성능을 크게 향상할 수 있습니다.",
	SCALING_METHOD_NATIVE: "네이티브 해상도",
	SCALING_METHOD_MAKO: "GFG Scaler",
	SCALING_METHOD_LS1: "LS1 Quality",
	SCALING_METHOD_LS1_PERFORMANCE: "LS1 Performance",
	SCALING_FACTOR: "스케일 배율",
	SCALING_FACTOR_DESC: "2x는 게임 렌더링 영상의 가로와 세로를 각각 두 배로 늘리는 목표값입니다(640×360 → 1280×720). 출력 크기가 고정되면 GFG Extreme가 게임에 더 작은 영상을 요청합니다. 게임이 창 크기를 정한다면 먼저 게임 내 해상도를 낮추세요. GFG Extreme가 출력을 확대하되 화면과 GPU 제한을 따릅니다.",
	SCALING_FACTOR_LIMIT_SUFFIX: "디스플레이 제한",
	SCALING_FACTOR_DEVICE_LIMIT: "현재 디스플레이 제한: {factor}x. 저장된 {saved}x 값은 유지됩니다. 사용하려면 품질 슈퍼샘플링을 켜세요.",
	SCALING_FACTOR_NO_HEADROOM: "이 입력은 이미 디스플레이 대상을 가득 채웁니다. 창 모드를 사용하거나, 게임 내 해상도를 낮추거나, 품질 슈퍼샘플링을 켜세요.",
	SCALING_SUPERSAMPLING: "품질 슈퍼샘플링",
	SCALING_SUPERSAMPLING_DESC: "Gamescope 출력 제한을 초과하여 더 높은 품질로 다운샘플링할 수 있게 하며, GPU와 메모리 사용량이 증가합니다. 다른 데스크톱 표면의 스케일링에는 영향을 주지 않습니다.",
	SCALING_SUPERSAMPLING_WARNING: "슈퍼샘플링을 켜면 GFG Extreme가 더 선명한 다운샘플링을 위해 Gamescope 출력 제한을 넘을 수 있습니다.",
	SCALING_SHARPNESS: "스케일링 선명도",
	SCALING_SHARPNESS_DESC: "GFG Scaler: 3x 선명도 기준의 0~100%. LS1: 학습된 다섯 선명도 변형 중 하나.",
	CONTENT_FPS_MULTIPLIER: "프레임 생성",
	CONTENT_PERFORMANCE_SETTINGS: "성능 설정",
	CONTENT_ADVANCED_DETAILS: "상세 정보",
	CONTENT_FLATPAK_SETUP: "Flatpak 설정",
	CONFIG_SECTION_TITLE: "고급 렌더링 설정",
	CONFIG_WORKAROUNDS_TITLE: "호환성 설정",
	CONFIG_FLOW_SCALE: "흐름 배율",
	CONFIG_FLOW_SCALE_DESC: "프레임 생성의 모션 추정 해상도입니다. 낮추면 GPU 부담이 줄고 높이면 화질을 우선합니다.",
	CONFIG_BASE_FPS_CAP: "기본 FPS 상한",
	CONFIG_BASE_FPS_CAP_OFF: "끄기",
	CONFIG_BASE_FPS_CAP_DESC: "프레임 생성 전에 실제 애플리케이션 프레임을 제한합니다. DirectX, Zink 기반 OpenGL 및 Vulkan에서 작동합니다.",
	CONFIG_BASE_FPS_CAP_STEADY_RELATION: "안정적 기본 FPS 제한({fps} FPS)이 제어합니다. 수동 값은 저장된 상태로 유지됩니다.",
	CONFIG_BASE_FPS_CAP_FRACTIONAL_PRIORITY_RELATION: "실제 프레임 우선순위({fps} FPS)가 제어합니다. 수동 값은 저장된 상태로 유지됩니다.",
	CONFIG_BASE_FPS_CAP_RECOVERY_RELATION: "이 제한을 변경하면 동적 케이던스 복구가 꺼집니다.",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD: "주사율에 따라 프레임 생성 자동 비활성화",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD_DESC: "선택한 Gamescope 주사율 이하에서는 프레임 생성을 일시 중지하고, 그보다 높으면 재개합니다. 주사율 피드백이 필요합니다.",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD: "주사율 임계값",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD_DESC: "프레임 생성을 일시 중지할 최대 주사율을 선택합니다.",
	CONFIG_ULTRA_PERFORMANCE: "울트라 성능 (재시작)",
	CONFIG_ULTRA_PERFORMANCE_DESC: "저전력 기기에서 GFG Extreme의 GPU 부하를 줄입니다. 흐름 배율 70%, 경량 FG 모델, 지원되는 경우 FP16, 스케일링이 활성화되면 LS1 Performance를 사용합니다. 활성화된 GFG Extreme 기능 전반에서 화질과 성능을 맞바꿉니다.",
	CONFIG_ULTRA_PERFORMANCE_WARNING: "Ultra Performance를 켜거나 끄려면 게임을 다시 시작해야 합니다. 그 밖의 호환되는 프로필 설정은 시작 후에도 사용할 수 있습니다.",
	CONFIG_PERFORMANCE_MODE: "경량 FG 모델",
	CONFIG_PERFORMANCE_MODE_DESC: "가벼운 FG 모델은 GPU 부담을 줄이지만 고스팅을 늘립니다. 울트라 성능은 이를 강제로 켭니다.",
	CONFIG_DISABLE_STEAMDECK_MODE: "Steam Deck 모드 비활성화 (재시작)",
	CONFIG_DISABLE_STEAMDECK_MODE_DESC: "Steam Deck 모드를 비활성화합니다. 일부 게임의 숨겨진 설정을 해제합니다.",
	CONFIG_ENABLE_ZINK: "OpenGL 게임에 Zink 활성화 (재시작)",
	CONFIG_ENABLE_ZINK_DESC: "OpenGL 게임을 Vulkan으로 실행합니다. 일부 게임에서 충돌이나 멈춤이 생길 수 있습니다.",
	CONFIG_FORCE_ALSA_AUDIO: "ALSA 오디오 강제 사용 (재시작)",
	CONFIG_FORCE_ALSA_AUDIO_DESC: "Zink 호환성, 오디오 끊김 또는 갑작스러운 큰 소리에 도움이 될 수 있습니다. 끄면 기본 오디오 설정으로 돌아갑니다.",
	CONFIG_EXTERNAL_TOOLS_TITLE: "외부 도구",
	CONFIG_ENABLE_MANGOHUD: "MangoHud 활성화 (재시작)",
	CONFIG_ENABLE_MANGOHUD_DESC: "설치된 MangoHud와 그 설정을 사용합니다. 게임별 변경은 전문가 가이드를 보세요.",
	CONFIG_ENABLE_VKBASALT: "셰이더 사용 (재시작)",
	CONFIG_ENABLE_VKBASALT_DESC: "게임 시작 전에 켜면 포함된 선명화, 안티앨리어싱, 셰이더를 사용합니다. 별도 설치는 필요 없습니다. 효과가 보이지 않으면 창 모드 또는 테두리 없는 전체 화면을 사용해 보세요.",
	INSTALL_INSTALLING: "GFG Engine 설치 중...",
	INSTALL_UNINSTALLING: "GFG Engine 제거 중...",
	FLATPAK_MODAL_TITLE: "Flatpak 확장",
	FLATPAK_RUNTIME_INSTALLER: "런타임 확장 설치",
	FLATPAK_RUNTIME_VERSION: "런타임 {version}",
	FLATPAK_INSTALLED: "설치됨",
	FLATPAK_NOT_INSTALLED: "설치 안 됨",
	FLATPAK_UNINSTALL_TITLE: "런타임 확장 제거",
	FLATPAK_UNINSTALL_CONFIRM_PREFIX: "정말로",
	FLATPAK_UNINSTALL_CONFIRM_SUFFIX: "런타임 확장을 제거하시겠습니까?",
	FLATPAK_UNINSTALL_BTN: "제거",
	FLATPAK_INSTALL_BTN: "설치",
	FLATPAK_UPDATE_BTN: "업데이트",
	FLATPAK_INSTALLING_BTN: "설치 중...",
	FLATPAK_UNINSTALLING_BTN: "제거 중...",
	FLATPAK_UPDATING_BTN: "업데이트 중...",
	FLATPAK_APPS_TITLE: "Flatpak 애플리케이션",
	FLATPAK_NO_APPS: "Flatpak 앱 없음",
	FLATPAK_NO_APPS_DESC: "현재 설치된 Flatpak 애플리케이션이 없습니다",
	FLATPAK_STATUS_CONFIGURED: "준비됨",
	FLATPAK_STATUS_PARTIAL: "부분 설정",
	FLATPAK_STATUS_NO_OVERRIDES: "오버라이드 없음",
	FLATPAK_ERROR: "오류",
	FLATPAK_ERROR_STATUS: "확장 상태 확인 실패",
	FLATPAK_ERROR_APPS: "Flatpak 애플리케이션 로드 실패",
	FLATPAK_STEAM_CONFIG_TITLE: "수동 Steam 바로가기 참고",
	FLATPAK_STEAM_CONFIG_HEADER: "대상 예시 (Steam을 자동 설정하지 않음)",
	FLATPAK_STEAM_CONFIG_DESC: "원래 대상이 /usr/bin/flatpak인 수동 추가 Steam 바로 가기에만 사용합니다. 먼저 위에서 앱을 준비하고 시작 위치와 실행 옵션은 유지하세요. Heroic, Lutris, EmuDeck은 실행기 설정 가이드를 따르세요.",
	FLATPAK_IMPORTANT_LABEL: "중요:",
	FLATPAK_STEAM_CONFIG_IMPORTANT: "TARGET만 바꾸세요. 실행 옵션에 붙여 넣지 마세요.",
	FLATPAK_PER_GAME_APP_DESC: "{app_id} - {status}. {wrapper_path}를 사용해 게임별로 GFG Extreme를 활성화하세요. 올바른 입력란은 런처 설정 가이드를 확인하세요.",
	FLATPAK_DIRECT_APP_DESC: "{app_id} - {status}. 준비는 이 Flatpak 앱 전체에 적용됩니다. EmuDeck과 Steam 바로가기는 런처 설정 가이드를 따르세요.",
	FLATPAK_STEP_WRAPPER_PATH: "이 장치에 설치된 래퍼:",
	FLATPAK_STEP_FINAL: "원래 \"/usr/bin/flatpak\"을 사용한 바로가기의 대상:",
	FLATPAK_OPEN_README: "런처 설정 가이드 열기",
	FLATPAK_CLOSE: "닫기",
	ADVANCED_DETAILS_LOADING: "정보 불러오는 중...",
	ADVANCED_DETAILS_ERROR_PREFIX: "오류:",
	ADVANCED_DETAILS_DLL_PATH: "DLL 경로",
	ADVANCED_DETAILS_LIBRARY: "Lossless Scaling 라이브러리",
	ADVANCED_DETAILS_RENDERER: "GFG Engine",
	ADVANCED_DETAILS_INSTALLATION: "Installation",
	ADVANCED_DETAILS_INSTALLED_VERSION: "Installed version",
	ADVANCED_DETAILS_BUNDLED_VERSION: "Bundled version",
	ADVANCED_DETAILS_HOST_ARCHITECTURE: "Host architecture",
	ADVANCED_DETAILS_LAYER_PATH: "Renderer library",
	ADVANCED_DETAILS_MANIFEST_PATH: "Vulkan manifest",
	ADVANCED_DETAILS_LAUNCHER_PATH: "Launch wrapper",
	ADVANCED_DETAILS_DETECTION: "Detection",
	ADVANCED_DETAILS_DLL_NOT_DETECTED: "Lossless Scaling not detected",
	ADVANCED_DETAILS_UNSUPPORTED_HOST: "Unsupported host",
	ADVANCED_DETAILS_UPDATE_REQUIRED: "Bundled update available",
	ADVANCED_DETAILS_INCOMPLETE: "Incomplete installation",
	ADVANCED_DETAILS_NOT_AVAILABLE: "사용 불가",
	ADVANCED_DETAILS_DETECTION_SOURCE: "감지 소스",
	ADVANCED_DETAILS_CLOSE: "닫기",
	WELCOME_TITLE: "GFG Extreme 팀에서 인사드립니다!",
	WELCOME_TIPS_COLLAPSE: "팁 숨기기",
	WELCOME_TIPS_EXPAND: "팁 표시",
	WELCOME_LIVE_UPDATES: "많은 설정은 실시간으로 적용됩니다.",
	WELCOME_RESTART_REQUIRED: "'재시작'이라고 표시된 옵션은 게임을 다시 시작해야 합니다.",
	WELCOME_PERFORMANCE_NOTE: "게임 해상도와 스케일링 변경은 성능에 영향을 줄 수 있습니다.",
	WELCOME_CLEAN_SESSION_PREFIX: "만약 ",
	WELCOME_CLEAN_SESSION_WRONG: "화면이나 플레이 감각에 문제가 있다면",
	WELCOME_CLEAN_SESSION_AFTER: ", ",
	WELCOME_CLEAN_SESSION_CHANGES: "여러 설정을 바꾼 뒤",
	WELCOME_CLEAN_SESSION_RESTART_SEPARATOR: " ",
	WELCOME_CLEAN_SESSION_RESTART: "게임을 다시 시작해 깨끗한 새 세션에서 확인하세요.",
	WELCOME_ENJOY: "최적의 설정은 게임마다 다릅니다. 직접 시험해 보고 GFG Extreme 업데이트는 출시 페이지에서 확인하세요.",
	PROFILE_CAPTURE_READY: "저장된 프로필은 GFG Extreme가 자동으로 선택합니다. 새로운 게임이라면 아래에서 저장하세요. 재시작 전용 설정을 바꾼 뒤에는 게임을 다시 시작하세요.",
	PROFILE_HELP: "게임 프로세스를 한 번 저장하면 프로필이 자동 선택됩니다. 게임 밖에서는 드롭다운으로 편집할 프로필을 고릅니다.",
	PROFILE_SECTION_TITLE: "게임 / 프로세스 프로필",
	PROFILE_DEFAULT: "기본",
	PROFILE_SAVED_LABEL: "저장된 프로필",
	PROFILE_GAME_SAVED: "게임 프로필 저장됨",
	PROFILE_GAME_SAVE_FAILED: "게임 프로필을 저장할 수 없음",
	PROFILE_SAVE_RUNNING: "{game} 프로필 저장",
	PROFILE_DETAIL_DEFAULT: "게임을 열어 프로필을 저장하세요",
	PROFILE_DETAIL_GAME: "저장된 게임",
	PROFILE_DETAIL_PROCESS: "저장된 프로세스",
	PROFILE_STEAM_APP_ID: "Steam 앱 ID: {app_id}",
	PROFILE_PROCESSES: "프로세스: {processes}",
	PROFILE_PROCESSES_EMPTY: "프로세스: 아래의 일치하는 프로세스에 입력하세요",
	PROFILE_MANAGE_WHEN_IDLE: "실행 중인 게임을 종료하면 프로필 이름을 변경하거나 삭제할 수 있습니다.",
	PROFILE_NAME_LABEL: "이름",
	PROFILE_CANCEL_BTN: "취소",
	PROFILE_RENAME_TITLE: "프로필 이름 변경",
	PROFILE_RENAME_DESC_PREFIX: "이 게임 또는 프로세스 프로필의 알아보기 쉬운 이름을 선택하세요.",
	PROFILE_RENAME_BTN: "이름 변경",
	PROFILE_CANNOT_DELETE_TITLE: "기본 프로필 삭제 불가",
	PROFILE_CANNOT_DELETE_MSG: "기본 프로필은 삭제할 수 없습니다",
	PROFILE_DELETE_TITLE: "게임 / 프로세스 프로필 삭제",
	PROFILE_DELETE_CONFIRM: "\"{profile}\" 및 저장된 설정을 모두 삭제할까요?",
	PROFILE_DELETE_BTN: "삭제",
	PROFILE_CANNOT_RENAME_TITLE: "기본 프로필 이름 변경 불가",
	PROFILE_CANNOT_RENAME_MSG: "기본 프로필의 이름은 변경할 수 없습니다",
	USAGE_TITLE: "사용 방법",
	USAGE_DESC: "이 Steam 실행 옵션을 추가하면 GFG Extreme 프레임 생성, 스케일링 또는 둘 다 사용할 수 있습니다.",
	CLIPBOARD_COPIED: "클립보드에 복사됨",
	CLIPBOARD_COPYING: "복사 중...",
	CLIPBOARD_COPY_LAUNCH: "실행 옵션 복사",
	CLIPBOARD_MAKO_FGMOD: "GFG Extreme + DeckyFG",
	CONTENT_RUNNING: "실행 중입니다.",
	CONTENT_ENGINE_UPDATE_REQUIRED: "GFG Engine 업데이트 필요",
	CONTENT_ENGINE_INSTALLED: "설치됨:",
	CONTENT_ENGINE_NOT_RECORDED: "기록되지 않음",
	CONTENT_ENGINE_EXPECTS: "이 플러그인에서 필요한 버전:",
	CONTENT_ENGINE_BUNDLED_VERSION: "번들 버전",
	CONTENT_ENGINE_PREDATES_TRACKING: "설치된 페이로드는 버전 추적 이전의 것입니다.",
	CONTENT_ENGINE_UPDATE_DESC: "포함된 GFG Engine를 다시 설치하고 준비된 Flatpak의 런타임 확장도 업데이트하세요.",
	CONTENT_UPDATE_RENDERER: "GFG Engine 업데이트",
	CONTENT_UPDATING_RENDERER: "GFG Engine 업데이트 중...",
	ADAPTIVE_TITLE: "적응형 프레임 생성",
	ADAPTIVE_DESC: "목표 출력 FPS에 맞춥니다. 기본 안정적 기본 FPS 제한은 부드러운 페이싱을 우선하고, 소수 배율 적응형은 실제 프레임을 더 많이 남깁니다. 게임별로 시험하세요.",
	FRACTIONAL_ADAPTIVE_PRESET: "소수 배율 적응형",
	FRACTIONAL_ADAPTIVE_PRESET_DESC: "생성 비율을 혼합해 실제 60 FPS → 표시 90 FPS와 같은 목표에 맞춥니다. 실제 프레임을 더 유지하고 입력 지연과 고스팅을 줄일 수 있지만, 일부 게임에서는 덜 부드럽게 느껴질 수 있습니다.",
	FRACTIONAL_ADAPTIVE_PRESET_RELATION: "안정적 기본 FPS 제한과 함께 사용할 수 없습니다. 이 옵션을 변경하면 동적 케이던스 복구도 꺼집니다.",
	ADAPTIVE_REAL_FRAME_PRIORITY: "실제 프레임 우선순위",
	ADAPTIVE_REAL_FRAME_PRIORITY_DESC: "표시된 FPS는 목표 FPS를 바탕으로 추정한 실제 프레임 상한이며, 게임에서 보장되는 프레임 속도가 아닙니다. 우선순위가 높을수록 실제 프레임이 늘어나 지연과 고스팅을 줄일 수 있지만 균일함이 떨어질 수 있습니다.",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO: "자동",
	ADAPTIVE_REAL_FRAME_PRIORITY_LOW: "낮음",
	ADAPTIVE_REAL_FRAME_PRIORITY_MEDIUM: "중간",
	ADAPTIVE_REAL_FRAME_PRIORITY_HIGH: "높음",
	ADAPTIVE_REAL_FRAME_PRIORITY_VERY_HIGH: "매우 높음",
	ADAPTIVE_REAL_FRAME_PRIORITY_OPTION: "{priority} — 최대 {cap} 실제 FPS (목표의 {percent}%)",
	ADAPTIVE_REAL_FRAME_PRIORITY_ACTIVE_RELATION: "목표 {target} FPS 달성 시 실제 {cap} / 생성 {generated_fps} FPS(약 {real}:{generated})입니다. 실제 수치는 다를 수 있으며 기본 FPS 제한보다 우선합니다.",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO_RELATION: "자동은 소수 배율 적응형의 현재 동작을 유지합니다. 기본 FPS 상한은 계속 사용할 수 있습니다.",
	ADAPTIVE_TARGET_FPS: "목표 FPS",
	ADAPTIVE_TARGET_FPS_DESC: "목표 출력 FPS입니다. 소수 배율은 배율을 섞고, 안정적 기본 FPS 제한은 절반에서 시작해 검증된 낮은 정수 배율로 맞출 수 있습니다.",
	ADAPTIVE_AUTO_BASE_FPS_CAP: "안정적 기본 FPS 제한",
	ADAPTIVE_AUTO_BASE_FPS_CAP_DESC: "기본 적응형 모드입니다. 목표의 절반에서 시작하고 부드러운 케이던스로 검증된 3x–5x 배율에 맞출 수 있습니다. 대체로 더 부드럽지만 실제 프레임이 줄고 지연이나 잔상이 늘 수 있습니다.",
	ADAPTIVE_AUTO_BASE_FPS_CAP_RELATION: "기본 FPS 제한을 재정의합니다. 소수 배율 적응형 또는 동적 케이던스 복구와 함께 사용할 수 없습니다.",
	ADAPTIVE_MAX_MULTIPLIER: "최대 적응형 배율",
	ADAPTIVE_MAX_MULTIPLIER_DESC: "0x를 사용하면 리소스를 해제하지 않고 프레임 생성을 실시간으로 일시 중지하거나 재개할 수 있습니다. 그 외 값은 고정 비율이 아닌 보간 상한이며, 적응형 모드는 더 낮거나 분수 배율을 사용할 수 있습니다. 목표 FPS에 도달하는 데 필요한 만큼만 높게 설정하세요. 게임별로 2x–5x를 테스트하세요.",
	ADAPTIVE_SMOOTH_CADENCE: "부드러운 케이던스",
	ADAPTIVE_SMOOTH_CADENCE_DESC: "검증된 순서 보장 Gamescope 표시로 더 안정적인 케이던스를 제공합니다. 분수형 적응 모드는 실제 프레임을 유지하고, 고정 모드와 안정적 기본 FPS 제한은 균일한 출력을 우선할 수 있습니다. 실제 FPS와 반응성이 낮아질 수 있습니다. 기본값으로 활성화되며, 필요하면 게임별로 비활성화하세요.",
	GAMESCOPE_VRR_MODE: "Gamescope VRR",
	GAMESCOPE_VRR_MODE_DESC: "VRR을 끄면 GFG Extreme가 프레임 페이싱을 제어할 수 있습니다. 일부 게임에서는 프레임 생성이 개선될 수 있지만 다른 게임에서는 그렇지 않을 수 있으므로 게임별로 테스트하세요. 기기 또는 디스플레이가 VRR을 지원하지 않으면 이 설정은 적용되지 않습니다.",
	GAMESCOPE_VRR_FOLLOW_STEAM: "Steam 따르기",
	GAMESCOPE_VRR_ON: "켜기",
	GAMESCOPE_VRR_OFF: "끄기",
	DYNAMIC_CADENCE_RECOVERY: "동적 케이던스 복구",
	DYNAMIC_CADENCE_RECOVERY_DESC: "게임 중 30 FPS, 메뉴 60 FPS처럼 네이티브 프레임률이 바뀌는 게임과 에뮬레이터를 지원합니다. 주기적으로 변화를 확인해 올바른 케이던스를 복구하지만, 확인할 때마다 페이싱에 잠시 영향이 있을 수 있습니다. 필요한 게임에서만 사용하세요.",
	DYNAMIC_CADENCE_RECOVERY_RELATION: "복구는 안정적 기본 FPS 제한과 기본 FPS 제한을 끄고 실제 프레임 우선순위를 자동으로 되돌립니다. 이후 제한이나 우선순위를 바꾸면 복구가 꺼집니다.",
	DYNAMIC_CADENCE_PROBE_INTERVAL: "케이던스 검사 간격",
	DYNAMIC_CADENCE_PROBE_INTERVAL_DESC: "복구 확인 간격입니다. 0.1초는 자주 끊길 수 있고, 기본값은 2초이며, 3초는 가장 적게 확인합니다. 게임별로 시험하세요.",
	ADAPTIVE_VALUE: "적응형",
	CONFIG_DLL_PATH: "Lossless.dll 경로 (재시작)",
	CONFIG_DLL_PATH_DESC: "Lossless.dll의 전체 경로입니다. 비워 두면 GFG Engine 자동 검색을 사용합니다. 변경 후 게임을 다시 시작하세요.",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH: "다음 실행 시 GFG Engine 비활성화",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH_DESC: "문제 진단용입니다. 다음 실행 한 번 GFG Engine를 불러오지 않습니다. 생성만 켜거나 끄려면 위의 프레임 생성을 사용하세요.",
	CONFIG_DISABLE_HDR_EXPOSURE: "HDR 비활성화",
	CONFIG_DISABLE_HDR_EXPOSURE_DESC: "HDR은 이 릴리스에서 사용할 수 없습니다. 이 필수 설정은 안정적인 SDR 경로를 유지합니다.",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY: "Gamescope WSI (재시작)",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_DESC: "Gamescope 표시 경로로 색이 번지거나 픽셀화된 움직임 아티팩트를 줄일 수 있습니다. 스케일링과 프레임 생성 모두에서 선택 사항이며 필요한 게임에서만 켜세요.",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_WARNING: "지원되는 64비트 호스트 실행 전용입니다. 필요하지 않으면 끄세요. 성능이 낮아질 수 있습니다.",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY: "게임 스왑체인 이미지 (재시작)",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_DESC: "프레임 생성 때문에 시작하지 못하는 게임에서 요청한 스왑체인 이미지 최소 수를 유지하면 해결될 수 있습니다. 해당 게임에서만 사용하세요.",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_WARNING: "컴포지터에 여유 이미지가 없으면 생성 프레임을 건너뛸 수 있으며, 부하가 높을 때 부드러움이나 성능이 저하될 수 있습니다.",
	FRAME_GENERATION_PROVISIONED: "Frame-gen 사용 (재시작)",
	FRAME_GENERATION_PROVISIONED_DESC: "게임 시작 전에 켜서 프레임 생성을 불러옵니다. 스케일링이나 셰이더만 쓸 때는 끄세요.",
	FIXED_MULTIPLIER: "고정 배율",
	FIXED_MULTIPLIER_DESC: "2x–5x는 고정 출력 배율입니다. 높은 주사율 화면용 5x는 비용이 큽니다. 0x는 리소스를 해제하지 않고 생성을 일시 중지합니다.",
	CONFIG_ALLOW_FP16: "FP16 허용 (재시작)",
	CONFIG_ALLOW_FP16_DESC: "전역 렌더러 설정입니다. 모든 프로필에 적용되며 게임별로 변경할 수 없습니다. AMD에서 성능을 향상할 수 있습니다. 오래된 NVIDIA GPU에서는 비활성화하세요. 변경 후 게임을 다시 시작하세요.",
	CONFIG_GPU: "GPU (재시작)",
	CONFIG_GPU_DESC: "선택적 GPU 이름, vendor:device ID 또는 PCI 버스 ID입니다. 변경 후 게임을 다시 시작하세요.",
	CONFIG_ACTIVE_IN: "일치하는 프로세스",
	CONFIG_ACTIVE_IN_DESC: "실행 파일명이나 프로세스명을 쉼표로 구분합니다. 실행 중 게임 캡처가 자동 입력하므로 실행기나 에뮬레이터 별칭이 필요할 때만 수정하세요.",
	CONFIG_MANUAL_OVERRIDES_TITLE: "수동 재정의",
	INSTALL_REMOVE_RENDERER: "GFG Engine 제거",
	INSTALL_RENDERER: "GFG Engine 설치",
	FLATPAK_EXTENSION_UPDATED: "Flatpak 확장을 업데이트했습니다",
	FLATPAK_EXTENSION_FAILED: "Flatpak 확장 작업에 실패했습니다",
	FLATPAK_EXTENSION_ACTION_FAILED: "실행할 수 없습니다:",
	FLATPAK_RUNTIME_EXTENSION_UPDATED: "런타임 확장을 업데이트했습니다",
	FLATPAK_RUNTIME_EXTENSION: "런타임 확장",
	FLATPAK_APPLICATION_UPDATED: "Flatpak 애플리케이션을 업데이트했습니다",
	FLATPAK_UPDATED: "업데이트됨",
	FLATPAK_PREPARE_APPLICATION: "애플리케이션 준비",
	FLATPAK_PREPARE_APPLICATION_DESC: "맞는 확장을 설치하고 앱을 준비합니다. Heroic/Lutris는 게임별 래퍼가 필요하고 에뮬레이터는 앱 전체에 적용됩니다. 실행기 가이드를 보세요.",
	FLATPAK_INSTALL_ACTION: "설치",
	FLATPAK_UNINSTALL_ACTION: "제거",
	FLATPAK_APPLICATION_ACTION_FAILED: "업데이트할 수 없습니다:",
	PROFILE_UNKNOWN_ERROR: "알 수 없는 오류",
	PROFILE_LOAD_FAILED: "프로필을 불러오지 못했습니다",
	PROFILE_LOAD_ERROR: "프로필을 불러오는 중 오류가 발생했습니다",
	PROFILE_SWITCHED: "프로필을 전환했습니다",
	PROFILE_SWITCHED_DESC: "전환한 프로필:",
	PROFILE_SWITCH_FAILED: "프로필 전환에 실패했습니다",
	PROFILE_SWITCH_ERROR: "프로필 전환 중 오류가 발생했습니다",
	PROFILE_DELETED: "프로필을 삭제했습니다",
	PROFILE_DELETED_DESC: "삭제한 프로필:",
	PROFILE_DELETE_FAILED: "프로필 삭제에 실패했습니다",
	PROFILE_DELETE_ERROR: "프로필 삭제 중 오류가 발생했습니다",
	PROFILE_RENAMED: "프로필 이름을 변경했습니다",
	PROFILE_RENAMED_DESC: "변경한 프로필 이름:",
	PROFILE_RENAME_FAILED: "프로필 이름 변경에 실패했습니다",
	PROFILE_RENAME_ERROR: "프로필 이름 변경 중 오류가 발생했습니다",
	PROFILE_UPDATE_CONFIG_FAILED: "프로필 설정 업데이트에 실패했습니다",
	PROFILE_UPDATE_CONFIG_ERROR: "프로필 설정 업데이트 중 오류가 발생했습니다",
	USAGE_MAKO_CONFIG_NOTE: "이 명령으로 실행한 게임에만 GFG Extreme가 적용됩니다.",
	USAGE_ISOLATION_NOTE: "같은 게임에서 GFG Extreme를 다른 프레임 생성 또는 스케일링 도구와 함께 사용하지 마세요.",
	ADVANCED_DETAILS_FAILED_LOAD_DATA: "데이터를 불러오지 못했습니다",
	STATUS_ENGINE_INSTALLED: "GFG Engine가 설치되었습니다",
	STATUS_ENGINE_NOT_INSTALLED: "GFG Engine가 설치되지 않았습니다",
	STATUS_ENGINE_INSTALLING: "GFG Engine 설치 중...",
	STATUS_ENGINE_UPDATING: "GFG Engine 업데이트 중...",
	STATUS_ENGINE_REMOVING: "GFG Engine 제거 중...",
	STATUS_ENGINE_REMOVED: "GFG Engine를 제거했습니다!",
	STATUS_INSTALL_FAILED: "설치 실패:",
	STATUS_UNINSTALL_FAILED: "제거 실패:",
	STATUS_LOSSLESS_INSTALLED: "Lossless Scaling이 설치되었습니다",
	STATUS_LOSSLESS_NOT_INSTALLED: "Lossless Scaling이 설치되지 않았습니다 — 프레임 생성 및 LS1에 필요합니다. GFG Scaler는 계속 사용할 수 있습니다",
	TOAST_INSTALL_COMPLETE: "설치 완료",
	TOAST_INSTALL_COMPLETE_DESC: "기기를 다시 시작하는 것이 좋습니다.",
	TOAST_INSTALL_FAILED: "설치 실패",
	TOAST_UNKNOWN_ERROR: "알 수 없는 오류가 발생했습니다",
	TOAST_UNINSTALL_COMPLETE: "GFG Engine 제거됨",
	TOAST_UNINSTALL_COMPLETE_DESC: "GFG Engine 파일을 제거했습니다",
	TOAST_UNINSTALL_FAILED: "제거 실패",
	TOAST_CONFIG_UPDATE_FAILED: "업데이트 실패",
	TOAST_CONFIG_UPDATE_FAILED_DESC: "설정 업데이트에 실패했습니다",
	TOAST_CLIPBOARD_SUCCESS: "클립보드에 복사했습니다!",
	TOAST_CLIPBOARD_SUCCESS_DESC: "실행 옵션을 붙여넣을 수 있습니다",
	TOAST_CLIPBOARD_FAILED: "복사 실패",
	TOAST_CLIPBOARD_FAILED_DESC: "클립보드에 복사할 수 없습니다",
	FEATURE_UPSCALING_TAB: "Upscaling",
	LIVE_STATUS_TITLE: "Live Status",
	LIVE_STATUS_CONNECTED: "GFG Extreme is active",
	LIVE_STATUS_WAITING: "Waiting for GFG Extreme",
	LIVE_STATUS_WAITING_DESC: "실시간 지표가 없어도 GFG Extreme는 작동할 수 있습니다. 일부 게임이나 에뮬레이터는 지표를 보고하지 않을 수 있습니다. 프레임 생성이나 스케일링을 직접 확인하세요.",
	LIVE_STATUS_FG_INACTIVE: "On in settings, but not currently generating frames.",
	LIVE_STATUS_FG_MENU_SUSPENDED: "Frame Generation is disabled while a Steam or Decky menu is open.",
	LIVE_STATUS_OFF: "Off",
	LIVE_STATUS_SCALING_INACTIVE: "On in settings, but the game image is not being upscaled.",
	LIVE_STATUS_SCALING_MEMORY_LIMIT: "The requested render resolution exceeds this GPU's memory safety limit. Lower the in-game resolution.",
	LIVE_STATUS_SCALING_MEMORY_CONSTRAINED: "Requested {requested}×; limited to {effective}× by this GPU's memory safety limit.",
	LIVE_STATUS_SCALING_NO_HEADROOM: "이 입력은 이미 디스플레이 대상을 가득 채웁니다. 창 모드를 사용하거나, 게임 내 해상도를 낮추거나, 품질 슈퍼샘플링을 켜세요.",
	LIVE_STATUS_PENDING: "A saved change is still applying or needs a restart.",
	LIVE_STATUS_SUPERSAMPLING: "Quality Supersampling active.",
	LIVE_STATUS_SCALING_FALLBACK: "You selected {requested}; GFG Extreme is using {active} instead.",
	LIVE_STATUS_MODE: "Mode",
	LIVE_STATUS_FIXED_VALUE: "Fixed",
	LIVE_STATUS_ADAPTIVE_STYLE: "Style",
	LIVE_STATUS_STEADY_VALUE: "Steady",
	LIVE_STATUS_FRACTIONAL_VALUE: "Fractional",
	LIVE_STATUS_TARGET: "Target",
	LIVE_STATUS_MAX_MULTIPLIER: "Max factor",
	LIVE_STATUS_MULTIPLIER: "Factor",
	LIVE_STATUS_MODEL: "Model",
	LIVE_STATUS_NATIVE: "Native",
	LIVE_STATUS_LS1_PERFORMANCE: "LS1 Perf",
	LIVE_STATUS_ORIGINAL_RESOLUTION: "Input",
	LIVE_STATUS_RENDER_RESOLUTION: "Render",
	LIVE_STATUS_DISPLAY_RESOLUTION: "Display",
	LIVE_STATUS_SCALED_RESOLUTION: "Output",
	LIVE_STATUS_SCALING_UNAVAILABLE: "Unavailable for this running surface.",
	MODEL_WARNING_TITLE: "Lossless Scaling 모델 경고",
	MODEL_WARNING_DESCRIPTION: "Lossless Scaling의 일부 기능을 사용하지 못할 수 있습니다:",
	MODEL_WARNING_LS1: "LS1 사용 가능 여부 확인에 실패했습니다. LS1을 불러올 수 없으면 GFG Scaler가 자동으로 사용됩니다.",
	MODEL_WARNING_LSFG: "LSFG 모델 확인에 실패했습니다. 선택한 정밀도 설정에서는 프레임 생성을 사용하지 못할 수 있습니다.",
	MODEL_WARNING_UPDATE: "GFG Extreme와 Renderer 업데이트가 있으면 적용하고 재시작하세요. 해결되지 않으면 Lossless Scaling 파일을 확인하고 진단 정보를 수집하세요.",
	MODEL_WARNING_CHECK_UPDATES: "렌더러 릴리스 열기"
};
var language_metadata = {
	en: {
		name: "English"
	},
	"pt-BR": {
		name: "Português (Brasil)"
	},
	"pt-PT": {
		name: "Português (Portugal)"
	},
	es: {
		name: "Español"
	},
	ko: {
		name: "한국어"
	},
	ja: {
		name: "日本語"
	},
	uk: {
		name: "Українська"
	},
	zh: {
		name: "简体中文"
	}
};
var steam_language_map = {
	english: "en",
	brazilian: "pt-BR",
	portuguese: "pt-PT",
	spanish: "es",
	latam: "es",
	korean: "ko",
	koreana: "ko",
	japanese: "ja",
	schinese: "zh",
	tchinese: "zh",
	ukrainian: "uk"
};
var template = {
	CONFIG_VKBASALT_ADVANCED_GLOBAL_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. The Default profile uses this global file.",
	CONFIG_VKBASALT_ADVANCED_PROFILE_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. This file belongs to the selected profile and is removed when that profile is deleted.",
	CONFIG_VKBASALT_SHARPENING: "Sharpening",
	CONFIG_VKBASALT_SHARPENING_DESC: "CAS is a crisp general-purpose sharpener. DLS can preserve noisy or grainy detail better when paired with denoise.",
	CONFIG_VKBASALT_EFFECT_NONE: "Off",
	CONFIG_VKBASALT_SHARPENING_CAS: "CAS",
	CONFIG_VKBASALT_SHARPENING_DLS: "DLS",
	CONFIG_VKBASALT_SHARPNESS: "Sharpness ({value}%)",
	CONFIG_VKBASALT_SHARPNESS_DESC: "Higher values produce a stronger effect but can exaggerate grain and create halos around high-contrast edges.",
	CONFIG_VKBASALT_DLS_DENOISE: "DLS Denoise ({value}%)",
	CONFIG_VKBASALT_DLS_DENOISE_DESC: "Limits how strongly DLS sharpens film grain and fine noise.",
	CONFIG_VKBASALT_ANTIALIASING: "Anti-aliasing",
	CONFIG_VKBASALT_ANTIALIASING_DESC: "Optionally smooth jagged edges before sharpening. FXAA is lighter and softer; SMAA is more selective and may cost more GPU time.",
	CONFIG_VKBASALT_ANTIALIASING_FXAA: "FXAA",
	CONFIG_VKBASALT_ANTIALIASING_SMAA: "SMAA",
	CONFIG_VKBASALT_SHADER: "Effects",
	CONFIG_VKBASALT_SHADER_DESC: "Effects run in selection order; uncheck and recheck to move one last. Stacking increases GPU load, especially with heavier effects such as HDR Look. Test per game and monitor GPU usage.",
	CONFIG_VKBASALT_EFFECTS_SELECTED: "Choose effects ({value} selected)",
	CONFIG_VKBASALT_EFFECTS_CLEAR: "Clear all",
	CONFIG_VKBASALT_EFFECTS_DONE: "Done",
	CONFIG_VKBASALT_EFFECTS_PREVIOUS_PAGE: "Previous effects page",
	CONFIG_VKBASALT_EFFECTS_NEXT_PAGE: "Next effects page",
	CONFIG_VKBASALT_SHADER_VIBRANCE: "Vibrance",
	CONFIG_VKBASALT_SHADER_CURVES: "Curves",
	CONFIG_VKBASALT_SHADER_DEBAND: "Deband",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR: "Technicolor",
	CONFIG_VKBASALT_SHADER_SEPIA: "Sepia",
	CONFIG_VKBASALT_SHADER_MONOCHROME: "Monochrome",
	CONFIG_VKBASALT_SHADER_VIGNETTE: "Vignette",
	CONFIG_VKBASALT_SHADER_HDR_LOOK: "HDR Look (SDR)",
	CONFIG_VKBASALT_SHADER_CLARITY: "Clarity",
	CONFIG_VKBASALT_SHADER_LEVELS_PLUS: "Levels Plus",
	CONFIG_VKBASALT_SHADER_COLOURFULNESS: "Colourfulness",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR2: "Technicolor 2",
	CONFIG_VKBASALT_SHADER_DPX: "DPX / Cineon",
	CONFIG_VKBASALT_SHADER_BLEACH_BYPASS: "Bleach Bypass",
	CONFIG_VKBASALT_SHADER_NOIR: "Noir",
	CONFIG_VKBASALT_SHADER_FILM_GRAIN: "Film Grain",
	CONFIG_VKBASALT_SHADER_CARTOON: "Cartoon",
	CONFIG_VKBASALT_SHADER_NOSTALGIA: "Nostalgia",
	CONFIG_VKBASALT_SHADER_CHROMATIC_ABERRATION: "Chromatic Aberration",
	CONTENT_HIDE_INFO: "Hide info",
	CONTENT_SHOW_INFO: "Show info",
	DEVELOPMENT_DEPLOYMENT_TITLE: "Local development deployment",
	DEVELOPMENT_DETAILS: "Details",
	DEVELOPMENT_HIDE: "Hide",
	DEVELOPMENT_DEPLOYED: "deployed",
	DEVELOPMENT_DEPLOYED_AT: "Deployed",
	DEVELOPMENT_UNCHANGED: "unchanged",
	DEVELOPMENT_COMMIT: "Commit",
	DEVELOPMENT_FRONTEND: "Frontend",
	DEVELOPMENT_BACKEND: "Backend",
	DEVELOPMENT_LOCAL_EDITS: "+ local edits",
	DEVELOPMENT_LAYER_64: "64-bit layer",
	DEVELOPMENT_LAYER_32: "32-bit layer",
	DEVELOPMENT_FLATPAK_BUNDLES: "Flatpak bundles",
	DEVELOPMENT_UNCHANGED_BY_DEPLOYMENT: "Unchanged by this deployment",
	CONTENT_IMAGE_PROCESSING: "Image Processing",
	IMAGE_PROCESSING_PERFORMANCE_INFO: "Combining Frame Generation, Scaling, and Shaders may cost performance. Disable unused features; changing display mode can change input resolution and GPU cost.",
	CONTENT_TAB_FRAME_GENERATION: "Frame-gen",
	CONTENT_TAB_SCALING: "Scaling",
	CONTENT_TAB_SHADERS: "Shaders",
	CONTENT_SCALING: "Spatial Settings",
	CONTENT_SHADERS: "Shaders",
	SCALING_ENABLED: "Enable Scaling (Restart)",
	EXPERIMENTAL_LABEL: "Experimental",
	SCALING_ENABLED_DESC: "Enable before launch for Lossless Scaling or GFG Scaler; off disables scaling. Test Fullscreen, Borderless Fullscreen, or Windowed if Scaling does not work.",
	SCALING_RUNTIME_SURFACE_UNSUPPORTED: "This running surface does not support GFG Extreme scaling. Quality Supersampling, Scale Factor, and Sharpness are locked until a supported surface is detected. Frame Generation remains available.",
	SCALING_METHOD: "Scaling Method",
	SCALING_METHOD_DESC: "Choose the scaling model. You can change it while the game is running.",
	SCALING_LS1_ACTIVE_FALLBACK: "LS1 is unavailable for this game. GFG Scaler is active. Your LS1 selection is preserved.",
	SCALING_LS1_UNAVAILABLE: "LS1 failed the availability check. GFG Scaler takes over if LS1 cannot load; your selection stays saved.",
	SCALING_METHOD_COMPARISON_TIP: "How scaling works:\n1. In Steam, set Game Resolution to your display's maximum resolution (Steam Deck: 1280 × 800; Steam Machine: 3840 × 2160).\n2. In the game, choose a lower resolution, such as 480p, 720p, or more.\n3. Set Scale Factor to enlarge the image. 2x targets twice the input width and height (640×360 → 1280×720).\n\nReducing the resolution of the game and scaling it back can substantially increase performance, with an image-quality trade-off.",
	SCALING_METHOD_NATIVE: "Native Resolution",
	SCALING_METHOD_MAKO: "GFG Scaler",
	SCALING_METHOD_LS1: "LS1 Quality",
	SCALING_METHOD_LS1_PERFORMANCE: "LS1 Performance",
	SCALING_FACTOR: "Scale Factor",
	SCALING_FACTOR_DESC: "2x targets twice the game's render width and height (640×360 → 1280×720). With fixed output, GFG Extreme requests a smaller game image. If the game sets window size, lower its resolution in-game first; GFG Extreme enlarges output instead, within display and GPU limits.",
	SCALING_FACTOR_LIMIT_SUFFIX: "display limit",
	SCALING_FACTOR_DEVICE_LIMIT: "Current display limit: {factor}x. Your saved {saved}x value is preserved; enable Quality Supersampling to use it.",
	SCALING_FACTOR_NO_HEADROOM: "This input already fills the display target. Try Windowed mode, lower the in-game resolution, or enable Quality Supersampling.",
	SCALING_SUPERSAMPLING: "Quality Supersampling",
	SCALING_SUPERSAMPLING_DESC: "Allows exceeding a Gamescope output limit for higher-quality downsampling, increasing GPU and memory use. Does not change scaling on other desktop surfaces.",
	SCALING_SUPERSAMPLING_WARNING: "With Supersampling on, GFG Extreme may exceed an applicable Gamescope output limit for sharper downsampling.",
	SCALING_SHARPNESS: "Scaling Sharpness",
	SCALING_SHARPNESS_DESC: "GFG Scaler: 0–100% of its 3x sharpening baseline. LS1: one of five learned sharpness variants.",
	CONTENT_FPS_MULTIPLIER: "Frame Generation",
	CONTENT_PERFORMANCE_SETTINGS: "Performance Settings",
	CONTENT_ADVANCED_DETAILS: "Advanced Details",
	CONTENT_FLATPAK_SETUP: "Flatpak Setup",
	CONFIG_SECTION_TITLE: "Advanced Rendering Settings",
	CONFIG_WORKAROUNDS_TITLE: "Compatibility Settings",
	CONFIG_FLOW_SCALE: "Flow Scale",
	CONFIG_FLOW_SCALE_DESC: "Frame Generation motion-estimation resolution. Lower saves GPU work; higher favors quality.",
	CONFIG_BASE_FPS_CAP: "Base FPS Cap",
	CONFIG_BASE_FPS_CAP_OFF: "Off",
	CONFIG_BASE_FPS_CAP_DESC: "Caps real application frames before frame generation. Works with DirectX, OpenGL through Zink, and Vulkan.",
	CONFIG_BASE_FPS_CAP_STEADY_RELATION: "Controlled by Steady Base Cap ({fps} FPS). Your manual value remains saved.",
	CONFIG_BASE_FPS_CAP_FRACTIONAL_PRIORITY_RELATION: "Controlled by Real Frame Priority ({fps} FPS). Your manual value remains saved.",
	CONFIG_BASE_FPS_CAP_RECOVERY_RELATION: "Changing this cap turns Dynamic Cadence Recovery off.",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD: "Auto-disable Frame Generation by Refresh Rate",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD_DESC: "Pauses generation at or below the chosen Gamescope refresh rate; resumes above it. Requires refresh feedback.",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD: "Refresh Rate Threshold",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD_DESC: "Choose the highest refresh rate where frame generation should remain paused.",
	CONFIG_ULTRA_PERFORMANCE: "Ultra Performance (Restart)",
	CONFIG_ULTRA_PERFORMANCE_DESC: "Reduces GFG Extreme's GPU workload on low-power devices. Uses 70% Flow Scale, the Lighter FG Model, FP16 when supported, and LS1 Performance when Scaling is enabled. Trades image quality for performance across the active GFG Extreme features.",
	CONFIG_ULTRA_PERFORMANCE_WARNING: "Turning Ultra Performance on or off requires a game restart. Other compatible profile controls remain available after startup.",
	CONFIG_PERFORMANCE_MODE: "Lighter FG Model",
	CONFIG_PERFORMANCE_MODE_DESC: "Lighter FG model lowers GPU cost but increases ghosting; Ultra Performance forces it on.",
	CONFIG_DISABLE_STEAMDECK_MODE: "Disable Steam Deck Mode (Restart)",
	CONFIG_DISABLE_STEAMDECK_MODE_DESC: "Disables Steam Deck mode. Unlocks hidden settings in some games.",
	CONFIG_ENABLE_ZINK: "Enable Zink for OpenGL Games (Restart)",
	CONFIG_ENABLE_ZINK_DESC: "Runs OpenGL games through Vulkan; may crash or freeze some games.",
	CONFIG_FORCE_ALSA_AUDIO: "Force ALSA Audio (Restart)",
	CONFIG_FORCE_ALSA_AUDIO_DESC: "May help Zink compatibility, audio stutter, or sudden loud sounds. Turn off to restore default audio.",
	CONFIG_EXTERNAL_TOOLS_TITLE: "External Tools",
	CONFIG_ENABLE_MANGOHUD: "Enable MangoHud (Restart)",
	CONFIG_ENABLE_MANGOHUD_DESC: "Uses installed MangoHud and its settings; see expert guide for per-game overrides.",
	CONFIG_ENABLE_VKBASALT: "Enable Shaders (Restart)",
	CONFIG_ENABLE_VKBASALT_DESC: "Enable before launch for bundled sharpening, anti-aliasing, and shaders. No separate install. If effects are invisible, try Windowed or Borderless Fullscreen mode.",
	INSTALL_INSTALLING: "Installing GFG Engine...",
	INSTALL_UNINSTALLING: "Removing GFG Engine...",
	FLATPAK_MODAL_TITLE: "Flatpak Extensions",
	FLATPAK_RUNTIME_INSTALLER: "Runtime Extension Installer",
	FLATPAK_RUNTIME_VERSION: "Runtime {version}",
	FLATPAK_INSTALLED: "Installed",
	FLATPAK_NOT_INSTALLED: "Not installed",
	FLATPAK_UNINSTALL_TITLE: "Uninstall Runtime Extension",
	FLATPAK_UNINSTALL_CONFIRM_PREFIX: "Are you sure you want to uninstall the",
	FLATPAK_UNINSTALL_CONFIRM_SUFFIX: "runtime extension?",
	FLATPAK_UNINSTALL_BTN: "Uninstall",
	FLATPAK_INSTALL_BTN: "Install",
	FLATPAK_UPDATE_BTN: "Update",
	FLATPAK_INSTALLING_BTN: "Installing...",
	FLATPAK_UNINSTALLING_BTN: "Uninstalling...",
	FLATPAK_UPDATING_BTN: "Updating...",
	FLATPAK_APPS_TITLE: "Flatpak Applications",
	FLATPAK_NO_APPS: "No Flatpak Apps Found",
	FLATPAK_NO_APPS_DESC: "No Flatpak applications are currently installed",
	FLATPAK_STATUS_CONFIGURED: "Prepared",
	FLATPAK_STATUS_PARTIAL: "Partial",
	FLATPAK_STATUS_NO_OVERRIDES: "No overrides",
	FLATPAK_ERROR: "Error",
	FLATPAK_ERROR_STATUS: "Failed to check extension status",
	FLATPAK_ERROR_APPS: "Failed to load Flatpak applications",
	FLATPAK_STEAM_CONFIG_TITLE: "Manual Steam shortcut reference",
	FLATPAK_STEAM_CONFIG_HEADER: "Target example (does not configure Steam)",
	FLATPAK_STEAM_CONFIG_DESC: "Only for manual Steam shortcuts originally targeting /usr/bin/flatpak. Prepare the app above; keep Start In and Launch Options. Heroic, Lutris, and EmuDeck use the launcher guide.",
	FLATPAK_IMPORTANT_LABEL: "IMPORTANT:",
	FLATPAK_STEAM_CONFIG_IMPORTANT: "Replace TARGET only. Do not paste this into Launch Options.",
	FLATPAK_PER_GAME_APP_DESC: "{app_id} - {status}. Enable GFG Extreme per game using {wrapper_path}. See the launcher setup guide for the correct field.",
	FLATPAK_DIRECT_APP_DESC: "{app_id} - {status}. Preparation applies to this entire Flatpak app. Follow the launcher setup guide for EmuDeck and Steam shortcuts.",
	FLATPAK_STEP_WRAPPER_PATH: "Wrapper installed on this device:",
	FLATPAK_STEP_FINAL: "Target for a shortcut that originally used \"/usr/bin/flatpak\":",
	FLATPAK_OPEN_README: "Open launcher setup guide",
	FLATPAK_CLOSE: "Close",
	ADVANCED_DETAILS_LOADING: "Loading information...",
	ADVANCED_DETAILS_ERROR_PREFIX: "Error:",
	ADVANCED_DETAILS_DLL_PATH: "DLL Path",
	ADVANCED_DETAILS_LIBRARY: "Lossless Scaling Library",
	ADVANCED_DETAILS_RENDERER: "GFG Engine",
	ADVANCED_DETAILS_INSTALLATION: "Installation",
	ADVANCED_DETAILS_INSTALLED_VERSION: "Installed version",
	ADVANCED_DETAILS_BUNDLED_VERSION: "Bundled version",
	ADVANCED_DETAILS_HOST_ARCHITECTURE: "Host architecture",
	ADVANCED_DETAILS_LAYER_PATH: "Renderer library",
	ADVANCED_DETAILS_MANIFEST_PATH: "Vulkan manifest",
	ADVANCED_DETAILS_LAUNCHER_PATH: "Launch wrapper",
	ADVANCED_DETAILS_DETECTION: "Detection",
	ADVANCED_DETAILS_DLL_NOT_DETECTED: "Lossless Scaling not detected",
	ADVANCED_DETAILS_UNSUPPORTED_HOST: "Unsupported host",
	ADVANCED_DETAILS_UPDATE_REQUIRED: "Bundled update available",
	ADVANCED_DETAILS_INCOMPLETE: "Incomplete installation",
	ADVANCED_DETAILS_NOT_AVAILABLE: "Not available",
	ADVANCED_DETAILS_DETECTION_SOURCE: "Detection Source",
	ADVANCED_DETAILS_CLOSE: "Close",
	WELCOME_TITLE: "Hello from the GFG Extreme Team!",
	WELCOME_TIPS_COLLAPSE: "Hide tips",
	WELCOME_TIPS_EXPAND: "Show tips",
	WELCOME_LIVE_UPDATES: "Many settings apply live.",
	WELCOME_RESTART_REQUIRED: "Options marked Restart require a game restart.",
	WELCOME_PERFORMANCE_NOTE: "Game resolution and scaling changes can affect performance.",
	WELCOME_CLEAN_SESSION_PREFIX: "If anything ",
	WELCOME_CLEAN_SESSION_WRONG: "looks or feels wrong",
	WELCOME_CLEAN_SESSION_AFTER: " after ",
	WELCOME_CLEAN_SESSION_CHANGES: "several changes",
	WELCOME_CLEAN_SESSION_RESTART_SEPARATOR: ", ",
	WELCOME_CLEAN_SESSION_RESTART: "restart the game for a clean new session.",
	WELCOME_ENJOY: "Settings vary by game. Test what works for you; check the release page for GFG Extreme updates.",
	PROFILE_CAPTURE_READY: "GFG Extreme selects saved profiles automatically. If this game is new, save it below; restart the game after changing restart-only settings.",
	PROFILE_HELP: "Save a game's process once for automatic profile selection. Outside a game, the dropdown selects the profile to edit.",
	PROFILE_SECTION_TITLE: "Game / Process Profiles",
	PROFILE_DEFAULT: "Default",
	PROFILE_SAVED_LABEL: "Saved profile",
	PROFILE_GAME_SAVED: "Game profile saved",
	PROFILE_GAME_SAVE_FAILED: "Could not save game profile",
	PROFILE_SAVE_RUNNING: "Save profile for {game}",
	PROFILE_DETAIL_DEFAULT: "Open a game to save its profile",
	PROFILE_DETAIL_GAME: "Saved game",
	PROFILE_DETAIL_PROCESS: "Saved process",
	PROFILE_STEAM_APP_ID: "Steam app ID: {app_id}",
	PROFILE_PROCESSES: "Processes: {processes}",
	PROFILE_PROCESSES_EMPTY: "Processes: enter one in Matched Processes below",
	PROFILE_MANAGE_WHEN_IDLE: "Close the running game to rename or delete profiles.",
	PROFILE_NAME_LABEL: "Name",
	PROFILE_CANCEL_BTN: "Cancel",
	PROFILE_RENAME_TITLE: "Rename Profile",
	PROFILE_RENAME_DESC_PREFIX: "Choose a friendly name for this game or process profile.",
	PROFILE_RENAME_BTN: "Rename",
	PROFILE_CANNOT_DELETE_TITLE: "Cannot delete default profile",
	PROFILE_CANNOT_DELETE_MSG: "The default profile cannot be deleted",
	PROFILE_DELETE_TITLE: "Delete Game / Process Profile",
	PROFILE_DELETE_CONFIRM: "Delete \"{profile}\" and all of its saved settings?",
	PROFILE_DELETE_BTN: "Delete",
	PROFILE_CANNOT_RENAME_TITLE: "Cannot rename default profile",
	PROFILE_CANNOT_RENAME_MSG: "The default profile cannot be renamed",
	USAGE_TITLE: "Usage Instructions",
	USAGE_DESC: "Add this Steam launch option to enable GFG Extreme Frame Generation, Scaling, or both.",
	CLIPBOARD_COPIED: "Copied to clipboard",
	CLIPBOARD_COPYING: "Copying...",
	CLIPBOARD_COPY_LAUNCH: "Copy Launch Option",
	CLIPBOARD_MAKO_FGMOD: "GFG Extreme + DeckyFG",
	CONTENT_RUNNING: "running.",
	CONTENT_ENGINE_UPDATE_REQUIRED: "GFG Engine update required",
	CONTENT_ENGINE_INSTALLED: "Installed:",
	CONTENT_ENGINE_NOT_RECORDED: "not recorded",
	CONTENT_ENGINE_EXPECTS: "This plugin expects:",
	CONTENT_ENGINE_BUNDLED_VERSION: "the bundled version",
	CONTENT_ENGINE_PREDATES_TRACKING: "The installed payload predates version tracking.",
	CONTENT_ENGINE_UPDATE_DESC: "Reinstall bundled GFG Engine, then update runtime extensions for prepared Flatpaks.",
	CONTENT_UPDATE_RENDERER: "Update GFG Engine",
	CONTENT_UPDATING_RENDERER: "Updating GFG Engine...",
	ADAPTIVE_TITLE: "Adaptive Frame Generation",
	ADAPTIVE_DESC: "Targets output FPS. Steady Base Cap favors smoother pacing by default; Fractional Adaptive keeps more real frames. Test per game.",
	FRACTIONAL_ADAPTIVE_PRESET: "Fractional Adaptive",
	FRACTIONAL_ADAPTIVE_PRESET_DESC: "Mixes generation ratios to reach targets such as 60 real FPS → 90 displayed FPS. It keeps more real frames and may reduce input lag and ghosting, but can feel less smooth in some games.",
	FRACTIONAL_ADAPTIVE_PRESET_RELATION: "Cannot be combined with Steady Base Cap. Changing it also turns Dynamic Cadence Recovery off.",
	ADAPTIVE_REAL_FRAME_PRIORITY: "Real Frame Priority",
	ADAPTIVE_REAL_FRAME_PRIORITY_DESC: "The shown FPS values estimate real-frame caps from Target FPS, not rates a game is guaranteed to deliver. Higher priority allows more real frames and may reduce latency and ghosting, but can feel less even.",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO: "Automatic",
	ADAPTIVE_REAL_FRAME_PRIORITY_LOW: "Low",
	ADAPTIVE_REAL_FRAME_PRIORITY_MEDIUM: "Medium",
	ADAPTIVE_REAL_FRAME_PRIORITY_HIGH: "High",
	ADAPTIVE_REAL_FRAME_PRIORITY_VERY_HIGH: "Very High",
	ADAPTIVE_REAL_FRAME_PRIORITY_OPTION: "{priority} — up to {cap} real FPS ({percent}% of target)",
	ADAPTIVE_REAL_FRAME_PRIORITY_ACTIVE_RELATION: "At a {target} FPS target: about {cap} real / {generated_fps} generated FPS ({real}:{generated}) if reached. Actual rates vary; this overrides Base FPS Cap.",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO_RELATION: "Automatic keeps Fractional Adaptive's current behavior. Base FPS Cap remains available.",
	ADAPTIVE_TARGET_FPS: "Target FPS",
	ADAPTIVE_TARGET_FPS_DESC: "Desired output FPS. When Gamescope exposes an exact matching display mode, GFG Extreme also switches the display to the same Hz. Fractional may mix ratios; Steady Base Cap starts at half the target and can align a validated lower integer ratio.",
	ADAPTIVE_AUTO_BASE_FPS_CAP: "Steady Base Cap",
	ADAPTIVE_AUTO_BASE_FPS_CAP_DESC: "Default Adaptive mode: starts at half the target; Smooth Cadence can align validated 3x–5x ratios. Usually smoother, with fewer real frames and possible extra lag or ghosting.",
	ADAPTIVE_AUTO_BASE_FPS_CAP_RELATION: "Overrides Base FPS Cap. Cannot be combined with Fractional Adaptive or Dynamic Cadence Recovery.",
	ADAPTIVE_MAX_MULTIPLIER: "Maximum Adaptive Multiplier",
	ADAPTIVE_MAX_MULTIPLIER_DESC: "Use 0x to pause or resume Frame Generation live without unloading its resources. Otherwise this is the interpolation ceiling, not a fixed ratio; Adaptive may use lower or fractional multipliers. Set it only as high as needed to reach Target FPS. Test 2x–5x per game.",
	ADAPTIVE_SMOOTH_CADENCE: "Smooth Cadence",
	ADAPTIVE_SMOOTH_CADENCE_DESC: "Uses validated ordered Gamescope presentation for steadier pacing. Fractional Adaptive keeps real frames; Fixed and Steady Base Cap can favor even output. It may reduce real FPS and responsiveness. On by default; turn it off per game if preferred.",
	GAMESCOPE_VRR_MODE: "Gamescope VRR",
	GAMESCOPE_VRR_MODE_DESC: "Disabling VRR lets GFG Extreme control frame pacing. This can improve frame generation in some games but not others, so test it per game. If your device or display does not support VRR, this setting has no effect.",
	GAMESCOPE_VRR_FOLLOW_STEAM: "Follow Steam",
	GAMESCOPE_VRR_ON: "On",
	GAMESCOPE_VRR_OFF: "Off",
	DYNAMIC_CADENCE_RECOVERY: "Dynamic Cadence Recovery",
	DYNAMIC_CADENCE_RECOVERY_DESC: "Helps games and emulators that switch native rates, such as 30 FPS gameplay and 60 FPS menus. It periodically checks for a rate change and recovers the correct cadence, but each check can briefly affect pacing. Enable it only for affected games.",
	DYNAMIC_CADENCE_RECOVERY_RELATION: "Recovery disables Steady Base Cap and Base FPS Cap and resets Real Frame Priority to Automatic. Changing either cap or priority turns Recovery off.",
	DYNAMIC_CADENCE_PROBE_INTERVAL: "Cadence Probe Interval",
	DYNAMIC_CADENCE_PROBE_INTERVAL_DESC: "Recovery check interval: 0.1 s may hitch often; 2 s is default; 3 s checks least often. Test per game.",
	ADAPTIVE_VALUE: "Adaptive",
	CONFIG_DLL_PATH: "Lossless.dll Path (Restart)",
	CONFIG_DLL_PATH_DESC: "Optional full path to Lossless.dll. Leave blank to use GFG Engine automatic discovery.",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH: "Disable GFG Engine on Next Launch",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH_DESC: "For troubleshooting: skips GFG Engine on the next launch. Use Frame Generation above to toggle synthesis.",
	CONFIG_DISABLE_HDR_EXPOSURE: "Disable HDR",
	CONFIG_DISABLE_HDR_EXPOSURE_DESC: "HDR is unavailable in this release. This required setting keeps the stable SDR path active.",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY: "Gamescope WSI (Restart)",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_DESC: "May reduce coloured or pixelated motion artifacts through Gamescope presentation. Optional with Scaling and Frame Generation; enable only if needed.",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_WARNING: "Only supported 64-bit host launches. Leave off unless needed; it may reduce performance.",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY: "Game Swapchain Images (Restart)",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_DESC: "May fix startup failures with Frame Generation by keeping the game's requested swapchain image minimum. Use only for affected games.",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_WARNING: "Generated frames may be skipped when the compositor has no spare image, which can reduce smoothness or performance under pressure.",
	FRAME_GENERATION_PROVISIONED: "Enable Frame-gen (Restart)",
	FRAME_GENERATION_PROVISIONED_DESC: "Enable before launch to load Frame Generation; turn off for Scaling or Shaders only.",
	FIXED_MULTIPLIER: "Fixed Multiplier",
	FIXED_MULTIPLIER_DESC: "2x–5x sets a constant output ratio; 5x costs more and suits high-refresh displays. 0x pauses generation live without unloading resources.",
	CONFIG_ALLOW_FP16: "Allow FP16 (Restart)",
	CONFIG_ALLOW_FP16_DESC: "Global renderer setting: applies to all profiles and cannot be changed per game. Improves performance on AMD; disable for older NVIDIA GPUs. Restart the game after changing it.",
	CONFIG_GPU: "GPU (Restart)",
	CONFIG_GPU_DESC: "Optional GPU name, vendor:device ID, or PCI bus ID. Restart the game after changing it.",
	CONFIG_ACTIVE_IN: "Matched Processes",
	CONFIG_ACTIVE_IN_DESC: "Comma-separated process names. Game capture fills these; edit only to add a launcher or emulator alias.",
	CONFIG_MANUAL_OVERRIDES_TITLE: "Manual Overrides",
	INSTALL_REMOVE_RENDERER: "Remove GFG Engine",
	INSTALL_RENDERER: "Install GFG Engine",
	FLATPAK_EXTENSION_UPDATED: "Flatpak extension updated",
	FLATPAK_EXTENSION_FAILED: "Flatpak extension failed",
	FLATPAK_EXTENSION_ACTION_FAILED: "Could not",
	FLATPAK_RUNTIME_EXTENSION_UPDATED: "runtime extension updated",
	FLATPAK_RUNTIME_EXTENSION: "runtime extension",
	FLATPAK_APPLICATION_UPDATED: "Flatpak application updated",
	FLATPAK_UPDATED: "updated",
	FLATPAK_PREPARE_APPLICATION: "Prepare an application",
	FLATPAK_PREPARE_APPLICATION_DESC: "Install the matching extension and prepare the app. Heroic/Lutris need a per-game wrapper; emulators apply app-wide. See launcher guide.",
	FLATPAK_INSTALL_ACTION: "install",
	FLATPAK_UNINSTALL_ACTION: "uninstall",
	FLATPAK_APPLICATION_ACTION_FAILED: "Could not update",
	PROFILE_UNKNOWN_ERROR: "Unknown error",
	PROFILE_LOAD_FAILED: "Failed to load profiles",
	PROFILE_LOAD_ERROR: "Error loading profiles",
	PROFILE_SWITCHED: "Profile switched",
	PROFILE_SWITCHED_DESC: "Switched to profile:",
	PROFILE_SWITCH_FAILED: "Failed to switch profile",
	PROFILE_SWITCH_ERROR: "Error switching profile",
	PROFILE_DELETED: "Profile deleted",
	PROFILE_DELETED_DESC: "Deleted profile:",
	PROFILE_DELETE_FAILED: "Failed to delete profile",
	PROFILE_DELETE_ERROR: "Error deleting profile",
	PROFILE_RENAMED: "Profile renamed",
	PROFILE_RENAMED_DESC: "Renamed profile to:",
	PROFILE_RENAME_FAILED: "Failed to rename profile",
	PROFILE_RENAME_ERROR: "Error renaming profile",
	PROFILE_UPDATE_CONFIG_FAILED: "Failed to update profile config",
	PROFILE_UPDATE_CONFIG_ERROR: "Error updating profile config",
	USAGE_MAKO_CONFIG_NOTE: "This command applies GFG Extreme only to the game you launch with it.",
	USAGE_ISOLATION_NOTE: "Do not combine GFG Extreme with another frame-generation or scaling tool for the same game.",
	ADVANCED_DETAILS_FAILED_LOAD_DATA: "Failed to load data",
	STATUS_ENGINE_INSTALLED: "GFG Engine installed",
	STATUS_ENGINE_NOT_INSTALLED: "GFG Engine not installed",
	STATUS_ENGINE_INSTALLING: "Installing GFG Engine...",
	STATUS_ENGINE_UPDATING: "Updating GFG Engine...",
	STATUS_ENGINE_REMOVING: "Removing GFG Engine...",
	STATUS_ENGINE_REMOVED: "GFG Engine removed successfully!",
	STATUS_INSTALL_FAILED: "Installation failed:",
	STATUS_UNINSTALL_FAILED: "Uninstallation failed:",
	STATUS_LOSSLESS_INSTALLED: "Lossless Scaling installed",
	STATUS_LOSSLESS_NOT_INSTALLED: "Lossless Scaling not installed — required for Frame Generation and LS1; GFG Scaler remains available",
	TOAST_INSTALL_COMPLETE: "Installation Complete",
	TOAST_INSTALL_COMPLETE_DESC: "Restarting your device is recommended.",
	TOAST_INSTALL_FAILED: "Installation Failed",
	TOAST_UNKNOWN_ERROR: "Unknown error occurred",
	TOAST_UNINSTALL_COMPLETE: "GFG Engine Removed",
	TOAST_UNINSTALL_COMPLETE_DESC: "GFG Engine files have been removed",
	TOAST_UNINSTALL_FAILED: "Uninstallation Failed",
	TOAST_CONFIG_UPDATE_FAILED: "Update Failed",
	TOAST_CONFIG_UPDATE_FAILED_DESC: "Failed to update configuration",
	TOAST_CLIPBOARD_SUCCESS: "Copied to Clipboard!",
	TOAST_CLIPBOARD_SUCCESS_DESC: "Launch option ready to paste",
	TOAST_CLIPBOARD_FAILED: "Copy Failed",
	TOAST_CLIPBOARD_FAILED_DESC: "Unable to copy to clipboard",
	FEATURE_UPSCALING_TAB: "Upscaling",
	LIVE_STATUS_TITLE: "Live Status",
	LIVE_STATUS_CONNECTED: "GFG Extreme is active",
	LIVE_STATUS_WAITING: "Waiting for GFG Extreme",
	LIVE_STATUS_WAITING_DESC: "Live metrics unavailable; GFG Extreme may still work. Some games/emulators may not report them. Check Frame Generation or Scaling manually.",
	LIVE_STATUS_FG_INACTIVE: "On in settings, but not currently generating frames.",
	LIVE_STATUS_FG_MENU_SUSPENDED: "Frame Generation is disabled while a Steam or Decky menu is open.",
	LIVE_STATUS_OFF: "Off",
	LIVE_STATUS_SCALING_INACTIVE: "On in settings, but the game image is not being upscaled.",
	LIVE_STATUS_SCALING_MEMORY_LIMIT: "The requested render resolution exceeds this GPU's memory safety limit. Lower the in-game resolution.",
	LIVE_STATUS_SCALING_MEMORY_CONSTRAINED: "Requested {requested}×; limited to {effective}× by this GPU's memory safety limit.",
	LIVE_STATUS_SCALING_NO_HEADROOM: "This input already fills the display target. Try Windowed mode, lower the in-game resolution, or enable Quality Supersampling.",
	LIVE_STATUS_PENDING: "A saved change is still applying or needs a restart.",
	LIVE_STATUS_SUPERSAMPLING: "Quality Supersampling active.",
	LIVE_STATUS_SCALING_FALLBACK: "You selected {requested}; GFG Extreme is using {active} instead.",
	LIVE_STATUS_MODE: "Mode",
	LIVE_STATUS_FIXED_VALUE: "Fixed",
	LIVE_STATUS_ADAPTIVE_STYLE: "Style",
	LIVE_STATUS_STEADY_VALUE: "Steady",
	LIVE_STATUS_FRACTIONAL_VALUE: "Fractional",
	LIVE_STATUS_TARGET: "Target",
	LIVE_STATUS_MAX_MULTIPLIER: "Max factor",
	LIVE_STATUS_MULTIPLIER: "Factor",
	LIVE_STATUS_MODEL: "Model",
	LIVE_STATUS_NATIVE: "Native",
	LIVE_STATUS_LS1_PERFORMANCE: "LS1 Perf",
	LIVE_STATUS_ORIGINAL_RESOLUTION: "Input",
	LIVE_STATUS_RENDER_RESOLUTION: "Render",
	LIVE_STATUS_DISPLAY_RESOLUTION: "Display",
	LIVE_STATUS_SCALED_RESOLUTION: "Output",
	LIVE_STATUS_SCALING_UNAVAILABLE: "Unavailable for this running surface.",
	MODEL_WARNING_TITLE: "Lossless Scaling model warning",
	MODEL_WARNING_DESCRIPTION: "Some Lossless Scaling features may be unavailable:",
	MODEL_WARNING_LS1: "LS1 failed its availability check. GFG Scaler is used automatically if LS1 cannot load.",
	MODEL_WARNING_LSFG: "An LSFG model check failed. Frame Generation may be unavailable with the selected precision setting.",
	MODEL_WARNING_UPDATE: "Apply available GFG Extreme and Renderer updates, then restart. If unresolved, verify Lossless Scaling files and collect diagnostics.",
	MODEL_WARNING_CHECK_UPDATES: "Open renderer releases"
};
var uk = {
	CONFIG_VKBASALT_ADVANCED_GLOBAL_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. The Default profile uses this global file.",
	CONFIG_VKBASALT_ADVANCED_PROFILE_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. This file belongs to the selected profile and is removed when that profile is deleted.",
	CONFIG_VKBASALT_SHARPENING: "Sharpening",
	CONFIG_VKBASALT_SHARPENING_DESC: "CAS is a crisp general-purpose sharpener. DLS can preserve noisy or grainy detail better when paired with denoise.",
	CONFIG_VKBASALT_EFFECT_NONE: "Off",
	CONFIG_VKBASALT_SHARPENING_CAS: "CAS",
	CONFIG_VKBASALT_SHARPENING_DLS: "DLS",
	CONFIG_VKBASALT_SHARPNESS: "Sharpness ({value}%)",
	CONFIG_VKBASALT_SHARPNESS_DESC: "Higher values produce a stronger effect but can exaggerate grain and create halos around high-contrast edges.",
	CONFIG_VKBASALT_DLS_DENOISE: "DLS Denoise ({value}%)",
	CONFIG_VKBASALT_DLS_DENOISE_DESC: "Limits how strongly DLS sharpens film grain and fine noise.",
	CONFIG_VKBASALT_ANTIALIASING: "Anti-aliasing",
	CONFIG_VKBASALT_ANTIALIASING_DESC: "Optionally smooth jagged edges before sharpening. FXAA is lighter and softer; SMAA is more selective and may cost more GPU time.",
	CONFIG_VKBASALT_ANTIALIASING_FXAA: "FXAA",
	CONFIG_VKBASALT_ANTIALIASING_SMAA: "SMAA",
	CONFIG_VKBASALT_SHADER: "Ефекти",
	CONFIG_VKBASALT_SHADER_DESC: "Effects run in selection order; uncheck and recheck to move one last. Stacking increases GPU load, especially with heavier effects such as HDR Look. Test per game and monitor GPU usage.",
	CONFIG_VKBASALT_EFFECTS_SELECTED: "Choose effects ({value} selected)",
	CONFIG_VKBASALT_EFFECTS_CLEAR: "Clear all",
	CONFIG_VKBASALT_EFFECTS_DONE: "Done",
	CONFIG_VKBASALT_EFFECTS_PREVIOUS_PAGE: "Previous effects page",
	CONFIG_VKBASALT_EFFECTS_NEXT_PAGE: "Next effects page",
	CONFIG_VKBASALT_SHADER_VIBRANCE: "Vibrance",
	CONFIG_VKBASALT_SHADER_CURVES: "Curves",
	CONFIG_VKBASALT_SHADER_DEBAND: "Deband",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR: "Technicolor",
	CONFIG_VKBASALT_SHADER_SEPIA: "Sepia",
	CONFIG_VKBASALT_SHADER_MONOCHROME: "Monochrome",
	CONFIG_VKBASALT_SHADER_VIGNETTE: "Vignette",
	CONFIG_VKBASALT_SHADER_HDR_LOOK: "HDR Look (SDR)",
	CONFIG_VKBASALT_SHADER_CLARITY: "Clarity",
	CONFIG_VKBASALT_SHADER_LEVELS_PLUS: "Levels Plus",
	CONFIG_VKBASALT_SHADER_COLOURFULNESS: "Colourfulness",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR2: "Technicolor 2",
	CONFIG_VKBASALT_SHADER_DPX: "DPX / Cineon",
	CONFIG_VKBASALT_SHADER_BLEACH_BYPASS: "Bleach Bypass",
	CONFIG_VKBASALT_SHADER_NOIR: "Noir",
	CONFIG_VKBASALT_SHADER_FILM_GRAIN: "Film Grain",
	CONFIG_VKBASALT_SHADER_CARTOON: "Cartoon",
	CONFIG_VKBASALT_SHADER_NOSTALGIA: "Nostalgia",
	CONFIG_VKBASALT_SHADER_CHROMATIC_ABERRATION: "Chromatic Aberration",
	CONTENT_HIDE_INFO: "Сховати інформацію",
	CONTENT_SHOW_INFO: "Показати інформацію",
	DEVELOPMENT_DEPLOYMENT_TITLE: "Локальне розгортання для розробки",
	DEVELOPMENT_DETAILS: "Подробиці",
	DEVELOPMENT_HIDE: "Приховати",
	DEVELOPMENT_DEPLOYED: "розгорнуто",
	DEVELOPMENT_DEPLOYED_AT: "Розгорнуто",
	DEVELOPMENT_UNCHANGED: "без змін",
	DEVELOPMENT_COMMIT: "Коміт",
	DEVELOPMENT_FRONTEND: "Фронтенд",
	DEVELOPMENT_BACKEND: "Бекенд",
	DEVELOPMENT_LOCAL_EDITS: "+ локальні зміни",
	DEVELOPMENT_LAYER_64: "64-бітний шар",
	DEVELOPMENT_LAYER_32: "32-бітний шар",
	DEVELOPMENT_FLATPAK_BUNDLES: "Пакети Flatpak",
	DEVELOPMENT_UNCHANGED_BY_DEPLOYMENT: "Без змін у цьому розгортанні",
	CONTENT_IMAGE_PROCESSING: "Обробка зображення",
	IMAGE_PROCESSING_PERFORMANCE_INFO: "Поєднання генерації кадрів, масштабування й шейдерів може знизити продуктивність. Вимкніть зайве; перевірте віконний і повноекранний режими для кожної гри.",
	CONTENT_TAB_FRAME_GENERATION: "Генерація",
	CONTENT_TAB_SCALING: "Масштабування",
	CONTENT_TAB_SHADERS: "Шейдери",
	CONTENT_SCALING: "Масштабування",
	CONTENT_SHADERS: "Шейдери",
	SCALING_ENABLED: "Увімкнути масштабування (перезапуск)",
	EXPERIMENTAL_LABEL: "Експериментально",
	SCALING_ENABLED_DESC: "Увімкніть до запуску для Lossless Scaling або GFG Scaler; вимкнення зупиняє масштабування. У деяких іграх може знадобитися віконний режим; повноекранний режим без рамки також може працювати.",
	SCALING_RUNTIME_SURFACE_UNSUPPORTED: "This running surface does not support GFG Extreme scaling. Quality Supersampling, Scale Factor, and Sharpness are locked until a supported surface is detected. Frame Generation remains available.",
	SCALING_METHOD: "Метод масштабування",
	SCALING_METHOD_DESC: "Виберіть модель масштабування. Її можна змінювати під час роботи гри.",
	SCALING_LS1_ACTIVE_FALLBACK: "LS1 is unavailable for this game. GFG Scaler is active. Your LS1 selection is preserved.",
	SCALING_LS1_UNAVAILABLE: "LS1 не пройшов перевірку доступності. Якщо модель не завантажиться, її замінить GFG Scaler; ваш вибір збережеться.",
	SCALING_METHOD_COMPARISON_TIP: "Як працює масштабування:\n1. У Steam установіть роздільну здатність гри на максимальну роздільну здатність дисплея (Steam Deck: 1280 × 800; Steam Machine: 3840 × 2160).\n2. У грі виберіть нижчу роздільну здатність, наприклад 480p, 720p або більше.\n3. Налаштуйте коефіцієнт масштабування для збільшення зображення. 2x має подвоїти ширину й висоту входу (640×360 → 1280×720).\n\nЗменшення роздільної здатності гри з подальшим масштабуванням може значно підвищити продуктивність, але з компромісом у якості зображення.",
	SCALING_METHOD_NATIVE: "Нативна роздільна здатність",
	SCALING_METHOD_MAKO: "GFG Scaler",
	SCALING_METHOD_LS1: "LS1 Quality",
	SCALING_METHOD_LS1_PERFORMANCE: "LS1 Performance",
	SCALING_FACTOR: "Коефіцієнт масштабування",
	SCALING_FACTOR_DESC: "2x має подвоїти ширину й висоту зображення гри (640×360 → 1280×720). За фіксованого виведення GFG Extreme запитує в гри менше зображення. Якщо гра задає розмір вікна, спершу зменште роздільність у грі; GFG Extreme збільшує вихідне зображення в межах дисплея та GPU.",
	SCALING_FACTOR_LIMIT_SUFFIX: "межа дисплея",
	SCALING_FACTOR_DEVICE_LIMIT: "Поточна межа дисплея: {factor}x. Збережене значення {saved}x не змінено; увімкніть Якісний суперсемплінг, щоб використати його.",
	SCALING_FACTOR_NO_HEADROOM: "Це вхідне зображення вже заповнює цільовий дисплей. Спробуйте віконний режим, знизьте роздільну здатність у грі або ввімкніть якісну супердискретизацію.",
	SCALING_SUPERSAMPLING: "Якісний суперсемплінг",
	SCALING_SUPERSAMPLING_DESC: "Дозволяє перевищувати обмеження розміру виведення Gamescope для якіснішого зменшення зображення, збільшуючи використання GPU та пам’яті. Не змінює масштабування на інших поверхнях стільниці.",
	SCALING_SUPERSAMPLING_WARNING: "За ввімкненої супердискретизації GFG Extreme може перевищити ліміт виведення Gamescope для чіткішого зменшення зображення.",
	SCALING_SHARPNESS: "Різкість масштабування",
	SCALING_SHARPNESS_DESC: "GFG Scaler: 0–100% від базової різкості 3x. LS1: один із п’яти навчених варіантів різкості.",
	CONTENT_FPS_MULTIPLIER: "Генерація кадрів",
	CONTENT_PERFORMANCE_SETTINGS: "Налаштування продуктивності",
	CONTENT_ADVANCED_DETAILS: "Докладна інформація",
	CONTENT_FLATPAK_SETUP: "Налаштування Flatpak",
	CONFIG_SECTION_TITLE: "Розширені налаштування рендерингу",
	CONFIG_WORKAROUNDS_TITLE: "Налаштування сумісності",
	CONFIG_FLOW_SCALE: "Масштаб оптичного потоку",
	CONFIG_FLOW_SCALE_DESC: "Роздільність оцінки руху для генерації кадрів. Нижча зменшує навантаження на GPU; вища покращує якість.",
	CONFIG_BASE_FPS_CAP: "Базовий ліміт FPS",
	CONFIG_BASE_FPS_CAP_OFF: "Вимк.",
	CONFIG_BASE_FPS_CAP_DESC: "Обмежує реальні кадри застосунку до генерації кадрів. Працює з DirectX, OpenGL через Zink і Vulkan.",
	CONFIG_BASE_FPS_CAP_STEADY_RELATION: "Керується стабільним базовим лімітом FPS ({fps} FPS). Ручне значення залишається збереженим.",
	CONFIG_BASE_FPS_CAP_FRACTIONAL_PRIORITY_RELATION: "Керується пріоритетом реальних кадрів ({fps} FPS). Ручне значення залишається збереженим.",
	CONFIG_BASE_FPS_CAP_RECOVERY_RELATION: "Зміна цього ліміту вимикає відновлення динамічного ритму кадрів.",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD: "Автоматично вимикати генерацію кадрів за частотою оновлення",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD_DESC: "Призупиняє генерацію кадрів за вибраної частоти Gamescope або нижче й відновлює вище неї. Потрібні дані про частоту оновлення.",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD: "Поріг частоти оновлення",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD_DESC: "Виберіть найвищу частоту оновлення, за якої генерація кадрів має залишатися призупиненою.",
	CONFIG_ULTRA_PERFORMANCE: "Ультрапродуктивність (перезапуск)",
	CONFIG_ULTRA_PERFORMANCE_DESC: "Зменшує навантаження GFG Extreme на GPU малопотужних пристроїв. Використовує масштаб оптичного потоку 70%, легшу модель FG, FP16 за підтримки та LS1 Performance, коли масштабування увімкнено. Обмінює якість зображення на продуктивність активних функцій GFG Extreme.",
	CONFIG_ULTRA_PERFORMANCE_WARNING: "Увімкнення або вимкнення Ultra Performance потребує перезапуску гри. Інші сумісні параметри профілю залишаються доступними після запуску.",
	CONFIG_PERFORMANCE_MODE: "Легша модель FG",
	CONFIG_PERFORMANCE_MODE_DESC: "Легка модель FG знижує навантаження на GPU, але посилює шлейфи; Ультрапродуктивність примусово її вмикає.",
	CONFIG_DISABLE_STEAMDECK_MODE: "Вимкнути режим Steam Deck (перезапуск)",
	CONFIG_DISABLE_STEAMDECK_MODE_DESC: "Вимикає режим Steam Deck. У деяких іграх це відкриває приховані налаштування.",
	CONFIG_ENABLE_ZINK: "Увімкнути Zink для ігор OpenGL (перезапуск)",
	CONFIG_ENABLE_ZINK_DESC: "Запускає ігри OpenGL через Vulkan; іноді спричиняє збої чи зависання.",
	CONFIG_FORCE_ALSA_AUDIO: "Примусово використовувати ALSA (перезапуск)",
	CONFIG_FORCE_ALSA_AUDIO_DESC: "Може поліпшити сумісність із Zink, усунути заїкання звуку чи раптові гучні звуки. Вимкніть, щоб повернути типові налаштування аудіо.",
	CONFIG_EXTERNAL_TOOLS_TITLE: "Зовнішні інструменти",
	CONFIG_ENABLE_MANGOHUD: "Увімкнути MangoHud (перезапуск)",
	CONFIG_ENABLE_MANGOHUD_DESC: "Використовує встановлений MangoHud і його налаштування; зміни для окремих ігор описано в посібнику для досвідчених.",
	CONFIG_ENABLE_VKBASALT: "Увімкнути шейдери (перезапуск)",
	CONFIG_ENABLE_VKBASALT_DESC: "Увімкніть до запуску гри для вбудованого підвищення різкості, згладжування та шейдерів. Окреме встановлення не потрібне. Якщо ефекти не видно, спробуйте віконний або повноекранний режим без рамки.",
	INSTALL_INSTALLING: "Встановлення GFG Engine...",
	INSTALL_UNINSTALLING: "Видалення GFG Engine...",
	FLATPAK_MODAL_TITLE: "Розширення Flatpak",
	FLATPAK_RUNTIME_INSTALLER: "Інсталятор розширень середовища виконання",
	FLATPAK_RUNTIME_VERSION: "Середовище виконання {version}",
	FLATPAK_INSTALLED: "Встановлено",
	FLATPAK_NOT_INSTALLED: "Не встановлено",
	FLATPAK_UNINSTALL_TITLE: "Видалити розширення середовища виконання",
	FLATPAK_UNINSTALL_CONFIRM_PREFIX: "Видалити розширення середовища виконання версії",
	FLATPAK_UNINSTALL_CONFIRM_SUFFIX: "— ви впевнені?",
	FLATPAK_UNINSTALL_BTN: "Видалити",
	FLATPAK_INSTALL_BTN: "Встановити",
	FLATPAK_UPDATE_BTN: "Оновити",
	FLATPAK_INSTALLING_BTN: "Встановлення...",
	FLATPAK_UNINSTALLING_BTN: "Видалення...",
	FLATPAK_UPDATING_BTN: "Оновлення...",
	FLATPAK_APPS_TITLE: "Застосунки Flatpak",
	FLATPAK_NO_APPS: "Застосунки Flatpak не знайдено",
	FLATPAK_NO_APPS_DESC: "Зараз застосунки Flatpak не встановлені",
	FLATPAK_STATUS_CONFIGURED: "Підготовлено",
	FLATPAK_STATUS_PARTIAL: "Частково",
	FLATPAK_STATUS_NO_OVERRIDES: "Без перевизначень",
	FLATPAK_ERROR: "Помилка",
	FLATPAK_ERROR_STATUS: "Не вдалося перевірити стан розширення",
	FLATPAK_ERROR_APPS: "Не вдалося завантажити список застосунків Flatpak",
	FLATPAK_STEAM_CONFIG_TITLE: "Необов’язкові ярлики Flatpak у Steam",
	FLATPAK_STEAM_CONFIG_HEADER: "Налаштування ярликів Flatpak у Steam",
	FLATPAK_STEAM_CONFIG_DESC: "Лише для вручну доданих ярликів Steam, початковою ціллю яких був /usr/bin/flatpak. Спершу підготуйте застосунок вище; не змінюйте «Почати в» та параметри запуску. Для Heroic, Lutris і EmuDeck дивіться посібник із запуску.",
	FLATPAK_IMPORTANT_LABEL: "ВАЖЛИВО:",
	FLATPAK_STEAM_CONFIG_IMPORTANT: "Вкажіть це в TARGET (НЕ В ПАРАМЕТРАХ ЗАПУСКУ)",
	FLATPAK_PER_GAME_APP_DESC: "{app_id} - {status}. Увімкніть GFG Extreme для окремої гри за допомогою {wrapper_path}. Потрібне поле вказано в посібнику з налаштування лаунчерів.",
	FLATPAK_DIRECT_APP_DESC: "{app_id} - {status}. Підготовка діє для всього цього застосунку Flatpak. Для EmuDeck і ярликів Steam дотримуйтеся посібника з налаштування лаунчерів.",
	FLATPAK_STEP_WRAPPER_PATH: "Шлях до обгортки (Wrapper) на цьому пристрої:",
	FLATPAK_STEP_FINAL: "Кінцевий результат має виглядати так:",
	FLATPAK_OPEN_README: "Відкрити посібник із налаштування лаунчерів",
	FLATPAK_CLOSE: "Закрити",
	ADVANCED_DETAILS_LOADING: "Завантаження інформації...",
	ADVANCED_DETAILS_ERROR_PREFIX: "Помилка:",
	ADVANCED_DETAILS_DLL_PATH: "Шлях до DLL",
	ADVANCED_DETAILS_LIBRARY: "Бібліотека Lossless Scaling",
	ADVANCED_DETAILS_RENDERER: "GFG Engine",
	ADVANCED_DETAILS_INSTALLATION: "Installation",
	ADVANCED_DETAILS_INSTALLED_VERSION: "Installed version",
	ADVANCED_DETAILS_BUNDLED_VERSION: "Bundled version",
	ADVANCED_DETAILS_HOST_ARCHITECTURE: "Host architecture",
	ADVANCED_DETAILS_LAYER_PATH: "Renderer library",
	ADVANCED_DETAILS_MANIFEST_PATH: "Vulkan manifest",
	ADVANCED_DETAILS_LAUNCHER_PATH: "Launch wrapper",
	ADVANCED_DETAILS_DETECTION: "Detection",
	ADVANCED_DETAILS_DLL_NOT_DETECTED: "Lossless Scaling not detected",
	ADVANCED_DETAILS_UNSUPPORTED_HOST: "Unsupported host",
	ADVANCED_DETAILS_UPDATE_REQUIRED: "Bundled update available",
	ADVANCED_DETAILS_INCOMPLETE: "Incomplete installation",
	ADVANCED_DETAILS_NOT_AVAILABLE: "Недоступно",
	ADVANCED_DETAILS_DETECTION_SOURCE: "Джерело виявлення",
	ADVANCED_DETAILS_CLOSE: "Закрити",
	WELCOME_TITLE: "Вітаємо від команди GFG Extreme!",
	WELCOME_TIPS_COLLAPSE: "Сховати поради",
	WELCOME_TIPS_EXPAND: "Показати поради",
	WELCOME_LIVE_UPDATES: "Багато налаштувань застосовуються наживо.",
	WELCOME_RESTART_REQUIRED: "Параметри з позначкою «Перезапуск» потребують перезапуску гри.",
	WELCOME_PERFORMANCE_NOTE: "Зміни роздільної здатності та масштабування гри можуть впливати на продуктивність.",
	WELCOME_CLEAN_SESSION_PREFIX: "Якщо щось ",
	WELCOME_CLEAN_SESSION_WRONG: "виглядає або відчувається не так",
	WELCOME_CLEAN_SESSION_AFTER: " після ",
	WELCOME_CLEAN_SESSION_CHANGES: "кількох змін",
	WELCOME_CLEAN_SESSION_RESTART_SEPARATOR: ", ",
	WELCOME_CLEAN_SESSION_RESTART: "перезапустіть гру для нового чистого сеансу.",
	WELCOME_ENJOY: "Найкращі налаштування залежать від гри. Перевіряйте їх самі; оновлення GFG Extreme — на сторінці випусків.",
	PROFILE_CAPTURE_READY: "GFG Extreme автоматично вибирає збережені профілі. Якщо ця гра нова, збережіть її нижче; після зміни налаштувань, що потребують перезапуску, перезапустіть гру.",
	PROFILE_HELP: "Збережіть процес гри один раз для автоматичного вибору профілю. Поза грою список вибирає профіль для редагування.",
	PROFILE_SECTION_TITLE: "Профілі ігор / процесів",
	PROFILE_DEFAULT: "За замовчуванням",
	PROFILE_SAVED_LABEL: "Збережений профіль",
	PROFILE_GAME_SAVED: "Профіль гри збережено",
	PROFILE_GAME_SAVE_FAILED: "Не вдалося зберегти профіль гри",
	PROFILE_SAVE_RUNNING: "Зберегти профіль для {game}",
	PROFILE_DETAIL_DEFAULT: "Відкрийте гру, щоб зберегти її профіль",
	PROFILE_DETAIL_GAME: "Збережена гра",
	PROFILE_DETAIL_PROCESS: "Збережений процес",
	PROFILE_STEAM_APP_ID: "Steam App ID: {app_id}",
	PROFILE_PROCESSES: "Процеси: {processes}",
	PROFILE_PROCESSES_EMPTY: "Процеси: вкажіть один нижче в полі «Процеси, що відповідають профілю»",
	PROFILE_MANAGE_WHEN_IDLE: "Закрийте запущену гру, щоб перейменовувати або видаляти профілі.",
	PROFILE_NAME_LABEL: "Назва",
	PROFILE_CANCEL_BTN: "Скасувати",
	PROFILE_RENAME_TITLE: "Перейменувати профіль",
	PROFILE_RENAME_DESC_PREFIX: "Виберіть зрозумілу назву для профілю цієї гри або процесу.",
	PROFILE_RENAME_BTN: "Перейменувати",
	PROFILE_CANNOT_DELETE_TITLE: "Не можна видалити профіль за замовчуванням",
	PROFILE_CANNOT_DELETE_MSG: "Профіль за замовчуванням видалити не можна",
	PROFILE_DELETE_TITLE: "Видалити профіль гри / процесу",
	PROFILE_DELETE_CONFIRM: "Видалити «{profile}» і всі збережені для нього налаштування?",
	PROFILE_DELETE_BTN: "Видалити",
	PROFILE_CANNOT_RENAME_TITLE: "Не можна перейменувати профіль за замовчуванням",
	PROFILE_CANNOT_RENAME_MSG: "Профіль за замовчуванням перейменувати не можна",
	USAGE_TITLE: "Як користуватися",
	USAGE_DESC: "Додайте цей параметр запуску в Steam для генерації кадрів, масштабування або обох функцій GFG Extreme.",
	CLIPBOARD_COPIED: "Скопійовано в буфер обміну",
	CLIPBOARD_COPYING: "Копіювання...",
	CLIPBOARD_COPY_LAUNCH: "Копіювати параметр запуску",
	CLIPBOARD_MAKO_FGMOD: "GFG Extreme + DeckyFG",
	CONTENT_RUNNING: "запущено.",
	CONTENT_ENGINE_UPDATE_REQUIRED: "Потрібне оновлення GFG Engine",
	CONTENT_ENGINE_INSTALLED: "Встановлено:",
	CONTENT_ENGINE_NOT_RECORDED: "версію не записано",
	CONTENT_ENGINE_EXPECTS: "Цьому плагіну потрібна версія:",
	CONTENT_ENGINE_BUNDLED_VERSION: "вбудована версія",
	CONTENT_ENGINE_PREDATES_TRACKING: "Встановлений пакет створено до появи відстеження версій.",
	CONTENT_ENGINE_UPDATE_DESC: "Перевстановіть комплектний GFG Engine і оновіть розширення середовища для підготовлених Flatpak-застосунків.",
	CONTENT_UPDATE_RENDERER: "Оновити GFG Engine",
	CONTENT_UPDATING_RENDERER: "Оновлення GFG Engine...",
	ADAPTIVE_TITLE: "Адаптивна генерація кадрів",
	ADAPTIVE_DESC: "Прагне до цільового вихідного FPS. Типовий стабільний базовий ліміт дає рівніший ритм; дробовий адаптивний режим залишає більше справжніх кадрів. Перевіряйте для кожної гри.",
	FRACTIONAL_ADAPTIVE_PRESET: "Адаптивний режим із дробовим множником (пресет)",
	FRACTIONAL_ADAPTIVE_PRESET_DESC: "Поєднує коефіцієнти генерації, щоб досягати цілей на кшталт 60 реальних FPS → 90 відображуваних FPS. Зберігає більше реальних кадрів і може зменшити затримку введення та кількість шлейфів, але в деяких іграх може бути менш плавним.",
	FRACTIONAL_ADAPTIVE_PRESET_RELATION: "Не можна поєднувати зі стабільним базовим лімітом FPS. Зміна цього параметра також вимикає відновлення динамічного ритму кадрів.",
	ADAPTIVE_REAL_FRAME_PRIORITY: "Пріоритет реальних кадрів",
	ADAPTIVE_REAL_FRAME_PRIORITY_DESC: "Показані значення FPS — це оцінка ліміту реальних кадрів за цільовим FPS, а не гарантована частота в грі. Вищий пріоритет дозволяє більше реальних кадрів і може зменшити затримку та шлейфи, але ритм може бути менш рівномірним.",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO: "Автоматично",
	ADAPTIVE_REAL_FRAME_PRIORITY_LOW: "Низький",
	ADAPTIVE_REAL_FRAME_PRIORITY_MEDIUM: "Середній",
	ADAPTIVE_REAL_FRAME_PRIORITY_HIGH: "Високий",
	ADAPTIVE_REAL_FRAME_PRIORITY_VERY_HIGH: "Дуже високий",
	ADAPTIVE_REAL_FRAME_PRIORITY_OPTION: "{priority} — до {cap} реальних FPS ({percent}% від цілі)",
	ADAPTIVE_REAL_FRAME_PRIORITY_ACTIVE_RELATION: "За цілі {target} FPS: близько {cap} справжніх / {generated_fps} згенерованих FPS ({real}:{generated}), якщо її досягнуто. Фактичні значення різняться; це замінює базовий ліміт FPS.",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO_RELATION: "Автоматичний режим зберігає поточну поведінку дробового адаптивного режиму. Базовий ліміт FPS залишається доступним.",
	ADAPTIVE_TARGET_FPS: "Цільовий FPS",
	ADAPTIVE_TARGET_FPS_DESC: "Бажаний вихідний FPS. Дробовий адаптивний режим може поєднувати множники; стабільний базовий ліміт починає з половини цілі й може узгодити перевірений нижчий цілий множник.",
	ADAPTIVE_AUTO_BASE_FPS_CAP: "Стабільний базовий ліміт FPS",
	ADAPTIVE_AUTO_BASE_FPS_CAP_DESC: "Типовий адаптивний режим: починає з половини цілі; рівномірний ритм кадрів може узгодити перевірені множники 3x–5x. Зазвичай плавніше, але справжніх кадрів менше, а затримка чи шлейфи можуть зрости.",
	ADAPTIVE_AUTO_BASE_FPS_CAP_RELATION: "Перевизначає базовий ліміт FPS. Не можна поєднувати з адаптивним режимом із дробовим множником або відновленням динамічного ритму кадрів.",
	ADAPTIVE_MAX_MULTIPLIER: "Максимальний адаптивний множник",
	ADAPTIVE_MAX_MULTIPLIER_DESC: "Використовуйте 0x, щоб наживо призупинити або відновити генерацію кадрів без вивантаження її ресурсів. Інші значення задають межу інтерполяції, а не фіксований коефіцієнт; адаптивний режим може використовувати нижчі або дробові множники. Установлюйте межу лише настільки високою, наскільки потрібно для досягнення цільового FPS. Перевіряйте 2x–5x окремо для кожної гри.",
	ADAPTIVE_SMOOTH_CADENCE: "Рівномірний ритм кадрів",
	ADAPTIVE_SMOOTH_CADENCE_DESC: "Використовує перевірений впорядкований показ Gamescope для рівнішого ритму. У дробовому адаптивному режимі зберігає реальні кадри; фіксований режим і Стабільне базове обмеження можуть віддавати перевагу рівномірному виводу. Це може знизити реальний FPS і чутливість. Увімкнено за замовчуванням; вимкніть для окремої гри за потреби.",
	GAMESCOPE_VRR_MODE: "VRR Gamescope",
	GAMESCOPE_VRR_MODE_DESC: "Вимкнення VRR дає GFG Extreme змогу керувати ритмом кадрів. Це може покращити генерацію кадрів в одних іграх, але не в інших, тому перевіряйте кожну гру окремо. Якщо пристрій або дисплей не підтримує VRR, це налаштування не матиме ефекту.",
	GAMESCOPE_VRR_FOLLOW_STEAM: "Слідувати Steam",
	GAMESCOPE_VRR_ON: "Увімкнено",
	GAMESCOPE_VRR_OFF: "Вимкнено",
	DYNAMIC_CADENCE_RECOVERY: "Відновлення динамічного ритму кадрів",
	DYNAMIC_CADENCE_RECOVERY_DESC: "Допомагає іграм та емуляторам, у яких змінюється власна частота кадрів, наприклад 30 FPS у грі та 60 FPS у меню. Періодично перевіряє зміну й відновлює правильний ритм кадрів, але кожна перевірка може коротко вплинути на плавність. Увімкніть лише для відповідних ігор.",
	DYNAMIC_CADENCE_RECOVERY_RELATION: "Відновлення вимикає стабільний базовий і базовий ліміти FPS та скидає пріоритет справжніх кадрів на Автоматично. Зміна ліміту або пріоритету вимикає Відновлення.",
	DYNAMIC_CADENCE_PROBE_INTERVAL: "Інтервал перевірки ритму кадрів",
	DYNAMIC_CADENCE_PROBE_INTERVAL_DESC: "Інтервал перевірки: 0,1 с може часто спричиняти ривки; типово 2 с; 3 с перевіряє найрідше. Перевіряйте для кожної гри.",
	ADAPTIVE_VALUE: "Адаптив.",
	CONFIG_DLL_PATH: "Шлях до Lossless.dll (перезапуск)",
	CONFIG_DLL_PATH_DESC: "Необов’язковий повний шлях до Lossless.dll. Залиште порожнім, щоб GFG Engine виконав автоматичний пошук. Після зміни перезапустіть гру.",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH: "Вимкнути GFG Engine під час наступного запуску",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH_DESC: "Для діагностики: пропускає GFG Engine під час наступного запуску. Для вмикання чи вимикання лише генерації використовуйте налаштування вище.",
	CONFIG_DISABLE_HDR_EXPOSURE: "Вимкнути HDR",
	CONFIG_DISABLE_HDR_EXPOSURE_DESC: "HDR у цьому випуску недоступний. Це обов’язкове налаштування зберігає стабільний шлях SDR.",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY: "Gamescope WSI (перезапуск)",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_DESC: "Показ через Gamescope може зменшити кольорові або піксельні артефакти руху. Необов’язково для масштабування й генерації кадрів; умикайте лише за потреби.",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_WARNING: "Лише для підтримуваних 64-бітних запусків на хості. Залишайте вимкненим без потреби; може знизити продуктивність.",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY: "Зображення swapchain гри (перезапуск)",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_DESC: "Якщо гра не запускається з генерацією кадрів, збереження запитаного мінімуму зображень swapchain може допомогти. Використовуйте лише для таких ігор.",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_WARNING: "Згенеровані кадри можуть пропускатися, коли композитору бракує вільного зображення, що може знизити плавність або продуктивність під навантаженням.",
	FRAME_GENERATION_PROVISIONED: "Увімкнути Frame-gen (перезапуск)",
	FRAME_GENERATION_PROVISIONED_DESC: "Увімкніть до запуску гри, щоб завантажити генерацію кадрів; вимкніть, якщо потрібні лише масштабування чи шейдери.",
	FIXED_MULTIPLIER: "Фіксований множник",
	FIXED_MULTIPLIER_DESC: "2x–5x задає сталий вихідний множник; 5x потребує більше ресурсів і підходить екранам із високою частотою. 0x призупиняє генерацію без вивантаження ресурсів.",
	CONFIG_ALLOW_FP16: "Дозволити FP16 (перезапуск)",
	CONFIG_ALLOW_FP16_DESC: "Підвищує продуктивність на AMD; вимкніть для старіших GPU NVIDIA. Після зміни перезапустіть гру.",
	CONFIG_GPU: "GPU (перезапуск)",
	CONFIG_GPU_DESC: "Необов’язково: назва GPU, ID vendor:device або PCI Bus ID. Після зміни перезапустіть гру.",
	CONFIG_ACTIVE_IN: "Процеси, що відповідають профілю",
	CONFIG_ACTIVE_IN_DESC: "Назви виконуваних файлів або процесів через коми. Захоплення гри заповнює їх автоматично; редагуйте лише для додаткового псевдоніма лаунчера чи емулятора.",
	CONFIG_MANUAL_OVERRIDES_TITLE: "Ручні перевизначення",
	INSTALL_REMOVE_RENDERER: "Видалити GFG Engine",
	INSTALL_RENDERER: "Встановити GFG Engine",
	FLATPAK_EXTENSION_UPDATED: "Розширення Flatpak оновлено",
	FLATPAK_EXTENSION_FAILED: "Помилка розширення Flatpak",
	FLATPAK_EXTENSION_ACTION_FAILED: "Не вдалося",
	FLATPAK_RUNTIME_EXTENSION_UPDATED: "розширення середовища виконання оновлено",
	FLATPAK_RUNTIME_EXTENSION: "розширення середовища виконання",
	FLATPAK_APPLICATION_UPDATED: "Застосунок Flatpak оновлено",
	FLATPAK_UPDATED: "оновлено",
	FLATPAK_PREPARE_APPLICATION: "Підготувати застосунок",
	FLATPAK_PREPARE_APPLICATION_DESC: "Встановіть відповідне розширення й підготуйте застосунок. Heroic/Lutris потребують обгортки для кожної гри; емулятори налаштовуються для всього застосунку. Дивіться посібник із запуску.",
	FLATPAK_INSTALL_ACTION: "встановити",
	FLATPAK_UNINSTALL_ACTION: "видалити",
	FLATPAK_APPLICATION_ACTION_FAILED: "Не вдалося оновити",
	PROFILE_UNKNOWN_ERROR: "Невідома помилка",
	PROFILE_LOAD_FAILED: "Не вдалося завантажити профілі",
	PROFILE_LOAD_ERROR: "Помилка завантаження профілів",
	PROFILE_SWITCHED: "Профіль перемкнено",
	PROFILE_SWITCHED_DESC: "Вибрано профіль:",
	PROFILE_SWITCH_FAILED: "Не вдалося перемкнути профіль",
	PROFILE_SWITCH_ERROR: "Помилка перемикання профілю",
	PROFILE_DELETED: "Профіль видалено",
	PROFILE_DELETED_DESC: "Видалено профіль:",
	PROFILE_DELETE_FAILED: "Не вдалося видалити профіль",
	PROFILE_DELETE_ERROR: "Помилка видалення профілю",
	PROFILE_RENAMED: "Профіль перейменовано",
	PROFILE_RENAMED_DESC: "Нова назва профілю:",
	PROFILE_RENAME_FAILED: "Не вдалося перейменувати профіль",
	PROFILE_RENAME_ERROR: "Помилка перейменування профілю",
	PROFILE_UPDATE_CONFIG_FAILED: "Не вдалося оновити налаштування профілю",
	PROFILE_UPDATE_CONFIG_ERROR: "Помилка оновлення налаштувань профілю",
	USAGE_MAKO_CONFIG_NOTE: "Ця команда застосовує GFG Extreme лише до гри, запущеної через неї.",
	USAGE_ISOLATION_NOTE: "Не поєднуйте GFG Extreme з іншим інструментом генерації кадрів або масштабування в одній грі.",
	ADVANCED_DETAILS_FAILED_LOAD_DATA: "Не вдалося завантажити дані",
	STATUS_ENGINE_INSTALLED: "GFG Engine встановлено",
	STATUS_ENGINE_NOT_INSTALLED: "GFG Engine не встановлено",
	STATUS_ENGINE_INSTALLING: "Встановлення GFG Engine...",
	STATUS_ENGINE_UPDATING: "Оновлення GFG Engine...",
	STATUS_ENGINE_REMOVING: "Видалення GFG Engine...",
	STATUS_ENGINE_REMOVED: "GFG Engine успішно видалено!",
	STATUS_INSTALL_FAILED: "Помилка встановлення:",
	STATUS_UNINSTALL_FAILED: "Помилка видалення:",
	STATUS_LOSSLESS_INSTALLED: "Lossless Scaling встановлено",
	STATUS_LOSSLESS_NOT_INSTALLED: "Lossless Scaling не встановлено — він потрібен для генерації кадрів і LS1; GFG Scaler залишається доступним",
	TOAST_INSTALL_COMPLETE: "Встановлення завершено",
	TOAST_INSTALL_COMPLETE_DESC: "Рекомендується перезапустити пристрій.",
	TOAST_INSTALL_FAILED: "Помилка встановлення",
	TOAST_UNKNOWN_ERROR: "Сталася невідома помилка",
	TOAST_UNINSTALL_COMPLETE: "GFG Engine видалено",
	TOAST_UNINSTALL_COMPLETE_DESC: "Файли GFG Engine видалено",
	TOAST_UNINSTALL_FAILED: "Помилка видалення",
	TOAST_CONFIG_UPDATE_FAILED: "Помилка оновлення",
	TOAST_CONFIG_UPDATE_FAILED_DESC: "Не вдалося оновити конфігурацію",
	TOAST_CLIPBOARD_SUCCESS: "Скопійовано в буфер обміну!",
	TOAST_CLIPBOARD_SUCCESS_DESC: "Параметр запуску готовий до вставлення",
	TOAST_CLIPBOARD_FAILED: "Помилка копіювання",
	TOAST_CLIPBOARD_FAILED_DESC: "Не вдалося скопіювати в буфер обміну",
	FEATURE_UPSCALING_TAB: "Upscaling",
	LIVE_STATUS_TITLE: "Live Status",
	LIVE_STATUS_CONNECTED: "GFG Extreme is active",
	LIVE_STATUS_WAITING: "Waiting for GFG Extreme",
	LIVE_STATUS_WAITING_DESC: "Показники недоступні, але GFG Extreme може працювати. Деякі ігри чи емулятори їх не повідомляють. Перевірте генерацію кадрів або масштабування вручну.",
	LIVE_STATUS_FG_INACTIVE: "On in settings, but not currently generating frames.",
	LIVE_STATUS_FG_MENU_SUSPENDED: "Frame Generation is disabled while a Steam or Decky menu is open.",
	LIVE_STATUS_OFF: "Off",
	LIVE_STATUS_SCALING_INACTIVE: "On in settings, but the game image is not being upscaled.",
	LIVE_STATUS_SCALING_MEMORY_LIMIT: "The requested render resolution exceeds this GPU's memory safety limit. Lower the in-game resolution.",
	LIVE_STATUS_SCALING_MEMORY_CONSTRAINED: "Requested {requested}×; limited to {effective}× by this GPU's memory safety limit.",
	LIVE_STATUS_SCALING_NO_HEADROOM: "Це вхідне зображення вже заповнює цільовий дисплей. Спробуйте віконний режим, знизьте роздільну здатність у грі або ввімкніть якісну супердискретизацію.",
	LIVE_STATUS_PENDING: "A saved change is still applying or needs a restart.",
	LIVE_STATUS_SUPERSAMPLING: "Quality Supersampling active.",
	LIVE_STATUS_SCALING_FALLBACK: "You selected {requested}; GFG Extreme is using {active} instead.",
	LIVE_STATUS_MODE: "Mode",
	LIVE_STATUS_FIXED_VALUE: "Fixed",
	LIVE_STATUS_ADAPTIVE_STYLE: "Style",
	LIVE_STATUS_STEADY_VALUE: "Steady",
	LIVE_STATUS_FRACTIONAL_VALUE: "Fractional",
	LIVE_STATUS_TARGET: "Target",
	LIVE_STATUS_MAX_MULTIPLIER: "Max factor",
	LIVE_STATUS_MULTIPLIER: "Factor",
	LIVE_STATUS_MODEL: "Model",
	LIVE_STATUS_NATIVE: "Native",
	LIVE_STATUS_LS1_PERFORMANCE: "LS1 Perf",
	LIVE_STATUS_ORIGINAL_RESOLUTION: "Input",
	LIVE_STATUS_RENDER_RESOLUTION: "Render",
	LIVE_STATUS_DISPLAY_RESOLUTION: "Display",
	LIVE_STATUS_SCALED_RESOLUTION: "Output",
	LIVE_STATUS_SCALING_UNAVAILABLE: "Unavailable for this running surface.",
	MODEL_WARNING_TITLE: "Попередження щодо моделей Lossless Scaling",
	MODEL_WARNING_DESCRIPTION: "Деякі функції Lossless Scaling можуть бути недоступні:",
	MODEL_WARNING_LS1: "LS1 не пройшла перевірку доступності. Якщо LS1 не вдається завантажити, автоматично використовується GFG Scaler.",
	MODEL_WARNING_LSFG: "Перевірка моделі LSFG завершилася невдало. Генерація кадрів може бути недоступною з вибраним налаштуванням точності.",
	MODEL_WARNING_UPDATE: "Застосуйте доступні оновлення GFG Extreme й Renderer та перезапустіть гру. Якщо не допоможе, перевірте файли Lossless Scaling і зберіть діагностику.",
	MODEL_WARNING_CHECK_UPDATES: "Відкрити релізи рендерера"
};
var zh = {
	CONFIG_VKBASALT_ADVANCED_GLOBAL_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. The Default profile uses this global file.",
	CONFIG_VKBASALT_ADVANCED_PROFILE_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. This file belongs to the selected profile and is removed when that profile is deleted.",
	CONFIG_VKBASALT_SHARPENING: "Sharpening",
	CONFIG_VKBASALT_SHARPENING_DESC: "CAS is a crisp general-purpose sharpener. DLS can preserve noisy or grainy detail better when paired with denoise.",
	CONFIG_VKBASALT_EFFECT_NONE: "Off",
	CONFIG_VKBASALT_SHARPENING_CAS: "CAS",
	CONFIG_VKBASALT_SHARPENING_DLS: "DLS",
	CONFIG_VKBASALT_SHARPNESS: "Sharpness ({value}%)",
	CONFIG_VKBASALT_SHARPNESS_DESC: "Higher values produce a stronger effect but can exaggerate grain and create halos around high-contrast edges.",
	CONFIG_VKBASALT_DLS_DENOISE: "DLS Denoise ({value}%)",
	CONFIG_VKBASALT_DLS_DENOISE_DESC: "Limits how strongly DLS sharpens film grain and fine noise.",
	CONFIG_VKBASALT_ANTIALIASING: "Anti-aliasing",
	CONFIG_VKBASALT_ANTIALIASING_DESC: "Optionally smooth jagged edges before sharpening. FXAA is lighter and softer; SMAA is more selective and may cost more GPU time.",
	CONFIG_VKBASALT_ANTIALIASING_FXAA: "FXAA",
	CONFIG_VKBASALT_ANTIALIASING_SMAA: "SMAA",
	CONFIG_VKBASALT_SHADER: "效果",
	CONFIG_VKBASALT_SHADER_DESC: "Effects run in selection order; uncheck and recheck to move one last. Stacking increases GPU load, especially with heavier effects such as HDR Look. Test per game and monitor GPU usage.",
	CONFIG_VKBASALT_EFFECTS_SELECTED: "Choose effects ({value} selected)",
	CONFIG_VKBASALT_EFFECTS_CLEAR: "Clear all",
	CONFIG_VKBASALT_EFFECTS_DONE: "Done",
	CONFIG_VKBASALT_EFFECTS_PREVIOUS_PAGE: "Previous effects page",
	CONFIG_VKBASALT_EFFECTS_NEXT_PAGE: "Next effects page",
	CONFIG_VKBASALT_SHADER_VIBRANCE: "Vibrance",
	CONFIG_VKBASALT_SHADER_CURVES: "Curves",
	CONFIG_VKBASALT_SHADER_DEBAND: "Deband",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR: "Technicolor",
	CONFIG_VKBASALT_SHADER_SEPIA: "Sepia",
	CONFIG_VKBASALT_SHADER_MONOCHROME: "Monochrome",
	CONFIG_VKBASALT_SHADER_VIGNETTE: "Vignette",
	CONFIG_VKBASALT_SHADER_HDR_LOOK: "HDR Look (SDR)",
	CONFIG_VKBASALT_SHADER_CLARITY: "Clarity",
	CONFIG_VKBASALT_SHADER_LEVELS_PLUS: "Levels Plus",
	CONFIG_VKBASALT_SHADER_COLOURFULNESS: "Colourfulness",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR2: "Technicolor 2",
	CONFIG_VKBASALT_SHADER_DPX: "DPX / Cineon",
	CONFIG_VKBASALT_SHADER_BLEACH_BYPASS: "Bleach Bypass",
	CONFIG_VKBASALT_SHADER_NOIR: "Noir",
	CONFIG_VKBASALT_SHADER_FILM_GRAIN: "Film Grain",
	CONFIG_VKBASALT_SHADER_CARTOON: "Cartoon",
	CONFIG_VKBASALT_SHADER_NOSTALGIA: "Nostalgia",
	CONFIG_VKBASALT_SHADER_CHROMATIC_ABERRATION: "Chromatic Aberration",
	CONTENT_HIDE_INFO: "隐藏信息",
	CONTENT_SHOW_INFO: "显示信息",
	DEVELOPMENT_DEPLOYMENT_TITLE: "本地开发部署",
	DEVELOPMENT_DETAILS: "详情",
	DEVELOPMENT_HIDE: "隐藏",
	DEVELOPMENT_DEPLOYED: "已部署",
	DEVELOPMENT_DEPLOYED_AT: "已部署",
	DEVELOPMENT_UNCHANGED: "未更改",
	DEVELOPMENT_COMMIT: "提交",
	DEVELOPMENT_FRONTEND: "前端",
	DEVELOPMENT_BACKEND: "后端",
	DEVELOPMENT_LOCAL_EDITS: "+ 本地修改",
	DEVELOPMENT_LAYER_64: "64 位层",
	DEVELOPMENT_LAYER_32: "32 位层",
	DEVELOPMENT_FLATPAK_BUNDLES: "Flatpak 软件包",
	DEVELOPMENT_UNCHANGED_BY_DEPLOYMENT: "本次部署未更改",
	CONTENT_IMAGE_PROCESSING: "图像处理",
	IMAGE_PROCESSING_PERFORMANCE_INFO: "同时使用帧生成、缩放和着色器可能降低性能。关闭不需要的功能，并逐个游戏测试窗口和全屏模式。",
	CONTENT_TAB_FRAME_GENERATION: "帧生成",
	CONTENT_TAB_SCALING: "图像缩放",
	CONTENT_TAB_SHADERS: "着色器",
	CONTENT_SCALING: "图像缩放",
	CONTENT_SHADERS: "着色器",
	SCALING_ENABLED: "启用缩放（重启）",
	EXPERIMENTAL_LABEL: "实验性",
	SCALING_ENABLED_DESC: "启动前启用 Lossless Scaling 或 GFG Scaler；关闭后缩放完全停用。部分游戏可能需要窗口模式；无边框全屏模式也可能有效。",
	SCALING_RUNTIME_SURFACE_UNSUPPORTED: "This running surface does not support GFG Extreme scaling. Quality Supersampling, Scale Factor, and Sharpness are locked until a supported surface is detected. Frame Generation remains available.",
	SCALING_METHOD: "缩放方法",
	SCALING_METHOD_DESC: "选择缩放模型。可在游戏运行时更改。",
	SCALING_LS1_ACTIVE_FALLBACK: "LS1 is unavailable for this game. GFG Scaler is active. Your LS1 selection is preserved.",
	SCALING_LS1_UNAVAILABLE: "LS1 未通过可用性检查。若模型无法加载，GFG Scaler 会接替；LS1 选择仍会保留。",
	SCALING_METHOD_COMPARISON_TIP: "缩放如何工作：\n1. 在 Steam 中，将游戏分辨率设为显示器的最高分辨率（Steam Deck：1280 × 800；Steam Machine：3840 × 2160）。\n2. 在游戏内选择较低分辨率，例如 480p、720p 或更高。\n3. 调整缩放倍率以放大画面。2x 的目标是将输入画面的宽和高各放大一倍（640×360 → 1280×720）。\n\n降低游戏渲染分辨率后再进行缩放可以显著提升性能，但会牺牲一些图像质量。",
	SCALING_METHOD_NATIVE: "原生分辨率",
	SCALING_METHOD_MAKO: "GFG Scaler",
	SCALING_METHOD_LS1: "LS1 Quality",
	SCALING_METHOD_LS1_PERFORMANCE: "LS1 Performance",
	SCALING_FACTOR: "缩放倍率",
	SCALING_FACTOR_DESC: "2x 的目标是将游戏渲染画面的宽和高各放大一倍（640×360 → 1280×720）。输出尺寸固定时，GFG Extreme 会请求游戏渲染较小画面。如果游戏决定窗口大小，请先降低游戏内分辨率；GFG Extreme 则放大输出，但仍受显示器和 GPU 限制。",
	SCALING_FACTOR_LIMIT_SUFFIX: "显示上限",
	SCALING_FACTOR_DEVICE_LIMIT: "当前显示上限：{factor}x。已保存的 {saved}x 值会保留；启用质量超级采样即可使用。",
	SCALING_FACTOR_NO_HEADROOM: "此输入已填满显示目标。请尝试窗口模式、降低游戏内分辨率或启用质量超采样。",
	SCALING_SUPERSAMPLING: "质量超级采样",
	SCALING_SUPERSAMPLING_DESC: "允许超出 Gamescope 的输出尺寸限制，以获得更高质量的下采样效果，但会增加 GPU 和内存使用量。不会改变其他桌面表面的缩放行为。",
	SCALING_SUPERSAMPLING_WARNING: "启用超采样后，GFG Extreme 可能超出 Gamescope 输出限制，以获得更清晰的下采样效果。",
	SCALING_SHARPNESS: "缩放锐度",
	SCALING_SHARPNESS_DESC: "GFG Scaler：3x 锐化基准的 0–100%；LS1：五种训练锐度变体之一。",
	CONTENT_FPS_MULTIPLIER: "帧生成",
	CONTENT_PERFORMANCE_SETTINGS: "性能设置",
	CONTENT_ADVANCED_DETAILS: "高级详情",
	CONTENT_FLATPAK_SETUP: "Flatpak 设置",
	CONFIG_SECTION_TITLE: "高级渲染设置",
	CONFIG_WORKAROUNDS_TITLE: "兼容性设置",
	CONFIG_FLOW_SCALE: "光流缩放",
	CONFIG_FLOW_SCALE_DESC: "帧生成的运动估计分辨率。较低值节省 GPU 开销，较高值偏重画质。",
	CONFIG_BASE_FPS_CAP: "基础 FPS 上限",
	CONFIG_BASE_FPS_CAP_OFF: "关闭",
	CONFIG_BASE_FPS_CAP_DESC: "在帧生成前限制应用的真实帧率。支持 DirectX、通过 Zink 运行的 OpenGL 和 Vulkan。",
	CONFIG_BASE_FPS_CAP_STEADY_RELATION: "由稳定基础 FPS 上限（{fps} FPS）控制。手动设置值仍会保留。",
	CONFIG_BASE_FPS_CAP_FRACTIONAL_PRIORITY_RELATION: "由真实帧优先级（{fps} FPS）控制。手动设置值仍会保留。",
	CONFIG_BASE_FPS_CAP_RECOVERY_RELATION: "更改此上限会关闭动态节奏恢复。",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD: "按刷新率自动禁用帧生成",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD_DESC: "显示器处于所选 Gamescope 刷新率或更低时暂停帧生成，高于该值时恢复。需要刷新率反馈。",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD: "刷新率阈值",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD_DESC: "选择帧生成应保持暂停的最高刷新率。",
	CONFIG_ULTRA_PERFORMANCE: "极致性能（重启）",
	CONFIG_ULTRA_PERFORMANCE_DESC: "降低 GFG Extreme 在低功耗设备上的 GPU 负载。它使用 70% 光流缩放、轻量帧生成模型、受支持时的 FP16，并在启用缩放时使用 LS1 Performance。以画质换取所有已启用 GFG Extreme 功能的性能。",
	CONFIG_ULTRA_PERFORMANCE_WARNING: "开启或关闭 Ultra Performance 需要重启游戏。其他兼容的配置文件控件在启动后仍可使用。",
	CONFIG_PERFORMANCE_MODE: "轻量帧生成模型",
	CONFIG_PERFORMANCE_MODE_DESC: "轻量 FG 模型降低 GPU 开销，但增加重影；极致性能会强制开启。",
	CONFIG_DISABLE_STEAMDECK_MODE: "禁用 Steam Deck 模式（重启）",
	CONFIG_DISABLE_STEAMDECK_MODE_DESC: "禁用 Steam Deck 模式，可解锁部分游戏中的隐藏设置。",
	CONFIG_ENABLE_ZINK: "为 OpenGL 游戏启用 Zink（重启）",
	CONFIG_ENABLE_ZINK_DESC: "通过 Vulkan 运行 OpenGL 游戏；部分游戏可能崩溃或卡死。",
	CONFIG_FORCE_ALSA_AUDIO: "强制使用 ALSA 音频（重启）",
	CONFIG_FORCE_ALSA_AUDIO_DESC: "可能改善 Zink 兼容性、音频卡顿或突然的高音量。关闭后恢复默认音频设置。",
	CONFIG_EXTERNAL_TOOLS_TITLE: "外部工具",
	CONFIG_ENABLE_MANGOHUD: "启用 MangoHud（重启）",
	CONFIG_ENABLE_MANGOHUD_DESC: "使用已安装的 MangoHud 及其设置；按游戏修改的方法见专家指南。",
	CONFIG_ENABLE_VKBASALT: "启用着色器（重启）",
	CONFIG_ENABLE_VKBASALT_DESC: "启动游戏前启用，即可使用内置锐化、抗锯齿和着色器。无需另行安装。如果看不到效果，请尝试窗口模式或无边框全屏模式。",
	INSTALL_INSTALLING: "正在安装 GFG Engine...",
	INSTALL_UNINSTALLING: "正在移除 GFG Engine...",
	FLATPAK_MODAL_TITLE: "Flatpak 扩展",
	FLATPAK_RUNTIME_INSTALLER: "运行时扩展安装器",
	FLATPAK_RUNTIME_VERSION: "运行时 {version}",
	FLATPAK_INSTALLED: "已安装",
	FLATPAK_NOT_INSTALLED: "未安装",
	FLATPAK_UNINSTALL_TITLE: "卸载运行时扩展",
	FLATPAK_UNINSTALL_CONFIRM_PREFIX: "确定要卸载",
	FLATPAK_UNINSTALL_CONFIRM_SUFFIX: "运行时扩展吗？",
	FLATPAK_UNINSTALL_BTN: "卸载",
	FLATPAK_INSTALL_BTN: "安装",
	FLATPAK_UPDATE_BTN: "更新",
	FLATPAK_INSTALLING_BTN: "正在安装...",
	FLATPAK_UNINSTALLING_BTN: "正在卸载...",
	FLATPAK_UPDATING_BTN: "正在更新...",
	FLATPAK_APPS_TITLE: "Flatpak 应用",
	FLATPAK_NO_APPS: "未找到 Flatpak 应用",
	FLATPAK_NO_APPS_DESC: "当前没有安装任何 Flatpak 应用",
	FLATPAK_STATUS_CONFIGURED: "已准备",
	FLATPAK_STATUS_PARTIAL: "部分完成",
	FLATPAK_STATUS_NO_OVERRIDES: "无覆盖设置",
	FLATPAK_ERROR: "错误",
	FLATPAK_ERROR_STATUS: "无法检查扩展状态",
	FLATPAK_ERROR_APPS: "无法加载 Flatpak 应用",
	FLATPAK_STEAM_CONFIG_TITLE: "手动 Steam 快捷方式参考",
	FLATPAK_STEAM_CONFIG_HEADER: "目标示例（不会自动配置 Steam）",
	FLATPAK_STEAM_CONFIG_DESC: "仅用于原始目标为 /usr/bin/flatpak 的手动添加 Steam 快捷方式。先在上方准备应用，并保留“起始位置”和“启动选项”。Heroic、Lutris 和 EmuDeck 请参阅启动器指南。",
	FLATPAK_IMPORTANT_LABEL: "重要：",
	FLATPAK_STEAM_CONFIG_IMPORTANT: "只替换“目标”。不要将此内容粘贴到“启动选项”中。",
	FLATPAK_PER_GAME_APP_DESC: "{app_id} - {status}。使用 {wrapper_path} 为每个游戏启用 GFG Extreme。请查看启动器设置指南以确认应填写的字段。",
	FLATPAK_DIRECT_APP_DESC: "{app_id} - {status}。准备对整个 Flatpak 应用生效。EmuDeck 和 Steam 快捷方式的步骤请参阅启动器设置指南。",
	FLATPAK_STEP_WRAPPER_PATH: "此设备上安装的包装器：",
	FLATPAK_STEP_FINAL: "原来使用 \"/usr/bin/flatpak\" 的快捷方式目标：",
	FLATPAK_OPEN_README: "打开启动器设置指南",
	FLATPAK_CLOSE: "关闭",
	ADVANCED_DETAILS_LOADING: "正在加载信息...",
	ADVANCED_DETAILS_ERROR_PREFIX: "错误：",
	ADVANCED_DETAILS_DLL_PATH: "DLL 路径",
	ADVANCED_DETAILS_LIBRARY: "Lossless Scaling 库",
	ADVANCED_DETAILS_RENDERER: "GFG Engine",
	ADVANCED_DETAILS_INSTALLATION: "Installation",
	ADVANCED_DETAILS_INSTALLED_VERSION: "Installed version",
	ADVANCED_DETAILS_BUNDLED_VERSION: "Bundled version",
	ADVANCED_DETAILS_HOST_ARCHITECTURE: "Host architecture",
	ADVANCED_DETAILS_LAYER_PATH: "Renderer library",
	ADVANCED_DETAILS_MANIFEST_PATH: "Vulkan manifest",
	ADVANCED_DETAILS_LAUNCHER_PATH: "Launch wrapper",
	ADVANCED_DETAILS_DETECTION: "Detection",
	ADVANCED_DETAILS_DLL_NOT_DETECTED: "Lossless Scaling not detected",
	ADVANCED_DETAILS_UNSUPPORTED_HOST: "Unsupported host",
	ADVANCED_DETAILS_UPDATE_REQUIRED: "Bundled update available",
	ADVANCED_DETAILS_INCOMPLETE: "Incomplete installation",
	ADVANCED_DETAILS_NOT_AVAILABLE: "不可用",
	ADVANCED_DETAILS_DETECTION_SOURCE: "检测来源",
	ADVANCED_DETAILS_CLOSE: "关闭",
	WELCOME_TITLE: "GFG Extreme 团队向你问好！",
	WELCOME_TIPS_COLLAPSE: "隐藏提示",
	WELCOME_TIPS_EXPAND: "显示提示",
	WELCOME_LIVE_UPDATES: "许多设置可实时生效。",
	WELCOME_RESTART_REQUIRED: "标有“重启”的选项需要重启游戏。",
	WELCOME_PERFORMANCE_NOTE: "更改游戏分辨率和缩放可能会影响性能。",
	WELCOME_CLEAN_SESSION_PREFIX: "如果",
	WELCOME_CLEAN_SESSION_WRONG: "画面或操作感觉异常",
	WELCOME_CLEAN_SESSION_AFTER: "，尤其是在",
	WELCOME_CLEAN_SESSION_CHANGES: "多次调整",
	WELCOME_CLEAN_SESSION_RESTART_SEPARATOR: "后",
	WELCOME_CLEAN_SESSION_RESTART: "，请重启游戏，以全新干净的会话重新开始。",
	WELCOME_ENJOY: "最佳设置因游戏而异。请自行测试；GFG Extreme 更新见发布页面。",
	PROFILE_CAPTURE_READY: "GFG Extreme 会自动选择已保存的配置文件。如果这是新游戏，请在下方保存；更改仅在重启后生效的设置后，请重启游戏。",
	PROFILE_HELP: "保存一次游戏进程后，GFG Extreme 会自动选择配置文件。游戏外的下拉菜单只选择要编辑的配置文件。",
	PROFILE_SECTION_TITLE: "游戏 / 进程配置文件",
	PROFILE_DEFAULT: "默认",
	PROFILE_SAVED_LABEL: "已保存的配置文件",
	PROFILE_GAME_SAVED: "游戏配置文件已保存",
	PROFILE_GAME_SAVE_FAILED: "无法保存游戏配置文件",
	PROFILE_SAVE_RUNNING: "为 {game} 保存配置文件",
	PROFILE_DETAIL_DEFAULT: "打开游戏以保存其配置文件",
	PROFILE_DETAIL_GAME: "已保存的游戏",
	PROFILE_DETAIL_PROCESS: "已保存的进程",
	PROFILE_STEAM_APP_ID: "Steam 应用 ID：{app_id}",
	PROFILE_PROCESSES: "进程：{processes}",
	PROFILE_PROCESSES_EMPTY: "进程：请在下方“匹配的进程”中输入",
	PROFILE_MANAGE_WHEN_IDLE: "关闭正在运行的游戏后才能重命名或删除配置文件。",
	PROFILE_NAME_LABEL: "名称",
	PROFILE_CANCEL_BTN: "取消",
	PROFILE_RENAME_TITLE: "重命名配置文件",
	PROFILE_RENAME_DESC_PREFIX: "为此游戏或进程配置文件选择一个易于识别的名称。",
	PROFILE_RENAME_BTN: "重命名",
	PROFILE_CANNOT_DELETE_TITLE: "无法删除默认配置文件",
	PROFILE_CANNOT_DELETE_MSG: "不能删除默认配置文件",
	PROFILE_DELETE_TITLE: "删除游戏 / 进程配置文件",
	PROFILE_DELETE_CONFIRM: "要删除“{profile}”及其所有已保存设置吗？",
	PROFILE_DELETE_BTN: "删除",
	PROFILE_CANNOT_RENAME_TITLE: "无法重命名默认配置文件",
	PROFILE_CANNOT_RENAME_MSG: "不能重命名默认配置文件",
	USAGE_TITLE: "使用说明",
	USAGE_DESC: "将此启动选项添加到 Steam 游戏，即可使用 GFG Extreme 帧生成、缩放或两者同时启用。",
	CLIPBOARD_COPIED: "已复制到剪贴板",
	CLIPBOARD_COPYING: "正在复制...",
	CLIPBOARD_COPY_LAUNCH: "复制启动选项",
	CLIPBOARD_MAKO_FGMOD: "GFG Extreme + DeckyFG",
	CONTENT_RUNNING: "正在运行。",
	CONTENT_ENGINE_UPDATE_REQUIRED: "需要更新 GFG Engine",
	CONTENT_ENGINE_INSTALLED: "已安装：",
	CONTENT_ENGINE_NOT_RECORDED: "未记录",
	CONTENT_ENGINE_EXPECTS: "此插件需要：",
	CONTENT_ENGINE_BUNDLED_VERSION: "随附版本",
	CONTENT_ENGINE_PREDATES_TRACKING: "已安装的内容早于版本跟踪功能。",
	CONTENT_ENGINE_UPDATE_DESC: "重新安装插件附带的 GFG Engine，并更新已准备 Flatpak 的运行时扩展。",
	CONTENT_UPDATE_RENDERER: "更新 GFG Engine",
	CONTENT_UPDATING_RENDERER: "正在更新 GFG Engine...",
	ADAPTIVE_TITLE: "自适应帧生成",
	ADAPTIVE_DESC: "以目标输出 FPS 为准。默认的稳定基础 FPS 上限优先保证平滑，小数倍率自适应保留更多真实帧。请逐个游戏测试。",
	FRACTIONAL_ADAPTIVE_PRESET: "小数倍率自适应",
	FRACTIONAL_ADAPTIVE_PRESET_DESC: "混合生成倍率以达到诸如 60 实际 FPS → 90 显示 FPS 的目标。可保留更多真实帧并可能降低输入延迟和重影，但在某些游戏中可能不够流畅。",
	FRACTIONAL_ADAPTIVE_PRESET_RELATION: "不能与稳定基础 FPS 上限同时使用。更改此选项也会关闭动态节奏恢复。",
	ADAPTIVE_REAL_FRAME_PRIORITY: "真实帧优先级",
	ADAPTIVE_REAL_FRAME_PRIORITY_DESC: "显示的 FPS 是根据目标 FPS 估算的真实帧上限，并不保证游戏能达到该帧率。较高优先级允许更多真实帧，并可能减少延迟和重影，但节奏可能不够均匀。",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO: "自动",
	ADAPTIVE_REAL_FRAME_PRIORITY_LOW: "低",
	ADAPTIVE_REAL_FRAME_PRIORITY_MEDIUM: "中",
	ADAPTIVE_REAL_FRAME_PRIORITY_HIGH: "高",
	ADAPTIVE_REAL_FRAME_PRIORITY_VERY_HIGH: "很高",
	ADAPTIVE_REAL_FRAME_PRIORITY_OPTION: "{priority} — 最高 {cap} 真实 FPS（目标的 {percent}%）",
	ADAPTIVE_REAL_FRAME_PRIORITY_ACTIVE_RELATION: "达到 {target} FPS 时：约 {cap} 真实帧 / {generated_fps} 生成帧（{real}:{generated}）。实际帧率可能不同；此设置覆盖基础 FPS 上限。",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO_RELATION: "自动会保持小数倍率自适应的当前行为。基础 FPS 上限仍然可用。",
	ADAPTIVE_TARGET_FPS: "目标 FPS",
	ADAPTIVE_TARGET_FPS_DESC: "目标输出 FPS。小数倍率可混合倍率；稳定基础 FPS 上限从目标的一半开始，可对齐已验证的较低整数倍率。",
	ADAPTIVE_AUTO_BASE_FPS_CAP: "稳定基础 FPS 上限",
	ADAPTIVE_AUTO_BASE_FPS_CAP_DESC: "默认自适应模式：从目标的一半开始；平滑节奏可对齐已验证的 3x–5x 倍率。通常更平滑，但真实帧更少，延迟或重影可能增加。",
	ADAPTIVE_AUTO_BASE_FPS_CAP_RELATION: "会覆盖基础 FPS 上限。不能与小数倍率自适应或动态节奏恢复同时使用。",
	ADAPTIVE_MAX_MULTIPLIER: "最大自适应倍率",
	ADAPTIVE_MAX_MULTIPLIER_DESC: "使用 0x 可实时暂停或恢复帧生成，而不卸载其资源。其他值是插帧上限，而非固定比率；自适应模式可能使用更低或小数倍率。只需将其设为达到目标 FPS 所需的最低值。请针对每个游戏测试 2x–5x。",
	ADAPTIVE_SMOOTH_CADENCE: "平滑节奏",
	ADAPTIVE_SMOOTH_CADENCE_DESC: "使用经验证的有序 Gamescope 呈现来获得更稳定的帧节奏。分数自适应保留真实帧；固定模式和稳定基础帧率上限可优先保持均匀输出。它可能降低真实 FPS 和响应性。默认启用；可按游戏关闭。",
	GAMESCOPE_VRR_MODE: "Gamescope VRR",
	GAMESCOPE_VRR_MODE_DESC: "关闭 VRR 后，GFG Extreme 可以控制帧节奏。这可能改善某些游戏的帧生成效果，但对其他游戏无效，因此请逐个游戏测试。如果设备或显示器不支持 VRR，此设置不会生效。",
	GAMESCOPE_VRR_FOLLOW_STEAM: "跟随 Steam",
	GAMESCOPE_VRR_ON: "开启",
	GAMESCOPE_VRR_OFF: "关闭",
	DYNAMIC_CADENCE_RECOVERY: "动态节奏恢复",
	DYNAMIC_CADENCE_RECOVERY_DESC: "帮助原生帧率会切换的游戏和模拟器，例如游戏中 30 FPS、菜单中 60 FPS。它会定期检查变化并恢复正确的帧节奏，但每次检查都可能短暂影响帧节奏。只应在受影响的游戏中启用。",
	DYNAMIC_CADENCE_RECOVERY_RELATION: "恢复功能会关闭稳定基础 FPS 上限和基础 FPS 上限，并将真实帧优先级重置为自动。之后更改任一上限或优先级会关闭恢复。",
	DYNAMIC_CADENCE_PROBE_INTERVAL: "节奏探测间隔",
	DYNAMIC_CADENCE_PROBE_INTERVAL_DESC: "恢复检测间隔：0.1 秒可能频繁卡顿；默认 2 秒；3 秒检测最少。请逐个游戏测试。",
	ADAPTIVE_VALUE: "自适应",
	CONFIG_DLL_PATH: "Lossless.dll 路径（重启）",
	CONFIG_DLL_PATH_DESC: "Lossless.dll 的可选完整路径。留空则使用 GFG Engine 自动查找。更改后请重启游戏。",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH: "下次启动时禁用 GFG Engine",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH_DESC: "仅供排障：下次启动时跳过 GFG Engine。若只想开关帧生成，请使用上方的帧生成设置。",
	CONFIG_DISABLE_HDR_EXPOSURE: "禁用 HDR",
	CONFIG_DISABLE_HDR_EXPOSURE_DESC: "此版本不支持 HDR。此必需设置会保持稳定的 SDR 路径启用。",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY: "Gamescope WSI（重启）",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_DESC: "通过 Gamescope 呈现路径，可能减少彩色或像素化的运动伪影。缩放和帧生成均可选用；仅在需要的游戏中启用。",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_WARNING: "仅限受支持的 64 位主机启动方式。不需要时请关闭；它可能降低性能。",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY: "游戏交换链图像（重启）",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_DESC: "帧生成导致游戏无法启动时，保留最小交换链图像数可能解决问题。仅用于受影响的游戏。",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_WARNING: "当合成器没有可用图像时，生成帧可能会被跳过，从而在压力下降低流畅度或性能。",
	FRAME_GENERATION_PROVISIONED: "启用 Frame-gen（重启）",
	FRAME_GENERATION_PROVISIONED_DESC: "启动游戏前启用以加载帧生成；如果只用缩放或着色器，请关闭。",
	FIXED_MULTIPLIER: "固定倍率",
	FIXED_MULTIPLIER_DESC: "2x–5x 是固定输出倍率；5x 开销较大，适合高刷新率屏幕。0x 可暂停帧生成而不卸载资源。",
	CONFIG_ALLOW_FP16: "允许 FP16（重启）",
	CONFIG_ALLOW_FP16_DESC: "这是全局渲染器设置：适用于所有配置文件，不能按游戏更改。可提升 AMD GPU 的性能；较旧的 NVIDIA GPU 请禁用。更改后请重启游戏。",
	CONFIG_GPU: "GPU（重启）",
	CONFIG_GPU_DESC: "可选的 GPU 名称、厂商:设备 ID 或 PCI 总线 ID。更改后请重启游戏。",
	CONFIG_ACTIVE_IN: "匹配的进程",
	CONFIG_ACTIVE_IN_DESC: "用逗号分隔可执行文件或进程名。游戏捕获会自动填写；仅在启动器或模拟器需要额外别名时编辑。",
	CONFIG_MANUAL_OVERRIDES_TITLE: "手动覆盖",
	INSTALL_REMOVE_RENDERER: "移除 GFG Engine",
	INSTALL_RENDERER: "安装 GFG Engine",
	FLATPAK_EXTENSION_UPDATED: "Flatpak 扩展已更新",
	FLATPAK_EXTENSION_FAILED: "Flatpak 扩展操作失败",
	FLATPAK_EXTENSION_ACTION_FAILED: "无法",
	FLATPAK_RUNTIME_EXTENSION_UPDATED: "运行时扩展已更新",
	FLATPAK_RUNTIME_EXTENSION: "运行时扩展",
	FLATPAK_APPLICATION_UPDATED: "Flatpak 应用已更新",
	FLATPAK_UPDATED: "已更新",
	FLATPAK_PREPARE_APPLICATION: "准备应用",
	FLATPAK_PREPARE_APPLICATION_DESC: "安装对应扩展并准备应用。Heroic/Lutris 需要按游戏配置包装器；模拟器则应用于整个程序。参阅启动器指南。",
	FLATPAK_INSTALL_ACTION: "安装",
	FLATPAK_UNINSTALL_ACTION: "卸载",
	FLATPAK_APPLICATION_ACTION_FAILED: "无法更新",
	PROFILE_UNKNOWN_ERROR: "未知错误",
	PROFILE_LOAD_FAILED: "无法加载配置文件",
	PROFILE_LOAD_ERROR: "加载配置文件时出错",
	PROFILE_SWITCHED: "配置文件已切换",
	PROFILE_SWITCHED_DESC: "已切换到配置文件：",
	PROFILE_SWITCH_FAILED: "无法切换配置文件",
	PROFILE_SWITCH_ERROR: "切换配置文件时出错",
	PROFILE_DELETED: "配置文件已删除",
	PROFILE_DELETED_DESC: "已删除配置文件：",
	PROFILE_DELETE_FAILED: "无法删除配置文件",
	PROFILE_DELETE_ERROR: "删除配置文件时出错",
	PROFILE_RENAMED: "配置文件已重命名",
	PROFILE_RENAMED_DESC: "已重命名为：",
	PROFILE_RENAME_FAILED: "无法重命名配置文件",
	PROFILE_RENAME_ERROR: "重命名配置文件时出错",
	PROFILE_UPDATE_CONFIG_FAILED: "无法更新配置文件设置",
	PROFILE_UPDATE_CONFIG_ERROR: "更新配置文件设置时出错",
	USAGE_MAKO_CONFIG_NOTE: "此命令只会将 GFG Extreme 应用于通过它启动的游戏。",
	USAGE_ISOLATION_NOTE: "请勿在同一游戏中同时使用 GFG Extreme 与其他帧生成或图像缩放工具。",
	ADVANCED_DETAILS_FAILED_LOAD_DATA: "无法加载数据",
	STATUS_ENGINE_INSTALLED: "GFG Engine 已安装",
	STATUS_ENGINE_NOT_INSTALLED: "GFG Engine 未安装",
	STATUS_ENGINE_INSTALLING: "正在安装 GFG Engine...",
	STATUS_ENGINE_UPDATING: "正在更新 GFG Engine...",
	STATUS_ENGINE_REMOVING: "正在移除 GFG Engine...",
	STATUS_ENGINE_REMOVED: "GFG Engine 已成功移除！",
	STATUS_INSTALL_FAILED: "安装失败：",
	STATUS_UNINSTALL_FAILED: "卸载失败：",
	STATUS_LOSSLESS_INSTALLED: "Lossless Scaling 已安装",
	STATUS_LOSSLESS_NOT_INSTALLED: "Lossless Scaling 未安装 — 帧生成和 LS1 需要它；GFG Scaler 仍然可用",
	TOAST_INSTALL_COMPLETE: "安装完成",
	TOAST_INSTALL_COMPLETE_DESC: "建议重新启动设备。",
	TOAST_INSTALL_FAILED: "安装失败",
	TOAST_UNKNOWN_ERROR: "发生未知错误",
	TOAST_UNINSTALL_COMPLETE: "GFG Engine 已移除",
	TOAST_UNINSTALL_COMPLETE_DESC: "GFG Engine 文件已移除",
	TOAST_UNINSTALL_FAILED: "卸载失败",
	TOAST_CONFIG_UPDATE_FAILED: "更新失败",
	TOAST_CONFIG_UPDATE_FAILED_DESC: "无法更新配置",
	TOAST_CLIPBOARD_SUCCESS: "已复制到剪贴板！",
	TOAST_CLIPBOARD_SUCCESS_DESC: "启动选项已可粘贴",
	TOAST_CLIPBOARD_FAILED: "复制失败",
	TOAST_CLIPBOARD_FAILED_DESC: "无法复制到剪贴板",
	FEATURE_UPSCALING_TAB: "Upscaling",
	LIVE_STATUS_TITLE: "Live Status",
	LIVE_STATUS_CONNECTED: "GFG Extreme is active",
	LIVE_STATUS_WAITING: "Waiting for GFG Extreme",
	LIVE_STATUS_WAITING_DESC: "实时指标不可用，但 GFG Extreme 可能仍在运行。部分游戏或模拟器可能不报告指标。请手动检查帧生成或缩放。",
	LIVE_STATUS_FG_INACTIVE: "On in settings, but not currently generating frames.",
	LIVE_STATUS_FG_MENU_SUSPENDED: "Frame Generation is disabled while a Steam or Decky menu is open.",
	LIVE_STATUS_OFF: "Off",
	LIVE_STATUS_SCALING_INACTIVE: "On in settings, but the game image is not being upscaled.",
	LIVE_STATUS_SCALING_MEMORY_LIMIT: "The requested render resolution exceeds this GPU's memory safety limit. Lower the in-game resolution.",
	LIVE_STATUS_SCALING_MEMORY_CONSTRAINED: "Requested {requested}×; limited to {effective}× by this GPU's memory safety limit.",
	LIVE_STATUS_SCALING_NO_HEADROOM: "此输入已填满显示目标。请尝试窗口模式、降低游戏内分辨率或启用质量超采样。",
	LIVE_STATUS_PENDING: "A saved change is still applying or needs a restart.",
	LIVE_STATUS_SUPERSAMPLING: "Quality Supersampling active.",
	LIVE_STATUS_SCALING_FALLBACK: "You selected {requested}; GFG Extreme is using {active} instead.",
	LIVE_STATUS_MODE: "Mode",
	LIVE_STATUS_FIXED_VALUE: "Fixed",
	LIVE_STATUS_ADAPTIVE_STYLE: "Style",
	LIVE_STATUS_STEADY_VALUE: "Steady",
	LIVE_STATUS_FRACTIONAL_VALUE: "Fractional",
	LIVE_STATUS_TARGET: "Target",
	LIVE_STATUS_MAX_MULTIPLIER: "Max factor",
	LIVE_STATUS_MULTIPLIER: "Factor",
	LIVE_STATUS_MODEL: "Model",
	LIVE_STATUS_NATIVE: "Native",
	LIVE_STATUS_LS1_PERFORMANCE: "LS1 Perf",
	LIVE_STATUS_ORIGINAL_RESOLUTION: "Input",
	LIVE_STATUS_RENDER_RESOLUTION: "Render",
	LIVE_STATUS_DISPLAY_RESOLUTION: "Display",
	LIVE_STATUS_SCALED_RESOLUTION: "Output",
	LIVE_STATUS_SCALING_UNAVAILABLE: "Unavailable for this running surface.",
	MODEL_WARNING_TITLE: "Lossless Scaling 模型警告",
	MODEL_WARNING_DESCRIPTION: "Lossless Scaling 的部分功能可能无法使用：",
	MODEL_WARNING_LS1: "LS1 可用性检查失败。如果无法加载 LS1，将自动使用 GFG Scaler。",
	MODEL_WARNING_LSFG: "LSFG 模型检查失败。在所选精度设置下，帧生成可能不可用。",
	MODEL_WARNING_UPDATE: "安装可用的 GFG Extreme 和 Renderer 更新并重启。若问题仍在，请验证 Lossless Scaling 文件并收集诊断信息。",
	MODEL_WARNING_CHECK_UPDATES: "打开渲染器发布页面"
};
var languageBundle = {
	es: es,
	ja: ja,
	ko: ko,
	language_metadata: language_metadata,
	"pt-BR": {
	CONFIG_VKBASALT_ADVANCED_GLOBAL_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. The Default profile uses this global file.",
	CONFIG_VKBASALT_ADVANCED_PROFILE_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. This file belongs to the selected profile and is removed when that profile is deleted.",
	CONFIG_VKBASALT_SHARPENING: "Sharpening",
	CONFIG_VKBASALT_SHARPENING_DESC: "CAS is a crisp general-purpose sharpener. DLS can preserve noisy or grainy detail better when paired with denoise.",
	CONFIG_VKBASALT_EFFECT_NONE: "Off",
	CONFIG_VKBASALT_SHARPENING_CAS: "CAS",
	CONFIG_VKBASALT_SHARPENING_DLS: "DLS",
	CONFIG_VKBASALT_SHARPNESS: "Sharpness ({value}%)",
	CONFIG_VKBASALT_SHARPNESS_DESC: "Higher values produce a stronger effect but can exaggerate grain and create halos around high-contrast edges.",
	CONFIG_VKBASALT_DLS_DENOISE: "DLS Denoise ({value}%)",
	CONFIG_VKBASALT_DLS_DENOISE_DESC: "Limits how strongly DLS sharpens film grain and fine noise.",
	CONFIG_VKBASALT_ANTIALIASING: "Anti-aliasing",
	CONFIG_VKBASALT_ANTIALIASING_DESC: "Optionally smooth jagged edges before sharpening. FXAA is lighter and softer; SMAA is more selective and may cost more GPU time.",
	CONFIG_VKBASALT_ANTIALIASING_FXAA: "FXAA",
	CONFIG_VKBASALT_ANTIALIASING_SMAA: "SMAA",
	CONFIG_VKBASALT_SHADER: "Efeitos",
	CONFIG_VKBASALT_SHADER_DESC: "Effects run in selection order; uncheck and recheck to move one last. Stacking increases GPU load, especially with heavier effects such as HDR Look. Test per game and monitor GPU usage.",
	CONFIG_VKBASALT_EFFECTS_SELECTED: "Choose effects ({value} selected)",
	CONFIG_VKBASALT_EFFECTS_CLEAR: "Clear all",
	CONFIG_VKBASALT_EFFECTS_DONE: "Done",
	CONFIG_VKBASALT_EFFECTS_PREVIOUS_PAGE: "Previous effects page",
	CONFIG_VKBASALT_EFFECTS_NEXT_PAGE: "Next effects page",
	CONFIG_VKBASALT_SHADER_VIBRANCE: "Vibrance",
	CONFIG_VKBASALT_SHADER_CURVES: "Curves",
	CONFIG_VKBASALT_SHADER_DEBAND: "Deband",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR: "Technicolor",
	CONFIG_VKBASALT_SHADER_SEPIA: "Sepia",
	CONFIG_VKBASALT_SHADER_MONOCHROME: "Monochrome",
	CONFIG_VKBASALT_SHADER_VIGNETTE: "Vignette",
	CONFIG_VKBASALT_SHADER_HDR_LOOK: "HDR Look (SDR)",
	CONFIG_VKBASALT_SHADER_CLARITY: "Clarity",
	CONFIG_VKBASALT_SHADER_LEVELS_PLUS: "Levels Plus",
	CONFIG_VKBASALT_SHADER_COLOURFULNESS: "Colourfulness",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR2: "Technicolor 2",
	CONFIG_VKBASALT_SHADER_DPX: "DPX / Cineon",
	CONFIG_VKBASALT_SHADER_BLEACH_BYPASS: "Bleach Bypass",
	CONFIG_VKBASALT_SHADER_NOIR: "Noir",
	CONFIG_VKBASALT_SHADER_FILM_GRAIN: "Film Grain",
	CONFIG_VKBASALT_SHADER_CARTOON: "Cartoon",
	CONFIG_VKBASALT_SHADER_NOSTALGIA: "Nostalgia",
	CONFIG_VKBASALT_SHADER_CHROMATIC_ABERRATION: "Chromatic Aberration",
	CONTENT_HIDE_INFO: "Ocultar informações",
	CONTENT_SHOW_INFO: "Mostrar informações",
	DEVELOPMENT_DEPLOYMENT_TITLE: "Implantação local de desenvolvimento",
	DEVELOPMENT_DETAILS: "Detalhes",
	DEVELOPMENT_HIDE: "Ocultar",
	DEVELOPMENT_DEPLOYED: "implantado",
	DEVELOPMENT_DEPLOYED_AT: "Implantado",
	DEVELOPMENT_UNCHANGED: "sem alterações",
	DEVELOPMENT_COMMIT: "Commit",
	DEVELOPMENT_FRONTEND: "Interface",
	DEVELOPMENT_BACKEND: "Backend",
	DEVELOPMENT_LOCAL_EDITS: "+ alterações locais",
	DEVELOPMENT_LAYER_64: "Camada de 64 bits",
	DEVELOPMENT_LAYER_32: "Camada de 32 bits",
	DEVELOPMENT_FLATPAK_BUNDLES: "Pacotes Flatpak",
	DEVELOPMENT_UNCHANGED_BY_DEPLOYMENT: "Sem alterações nesta implantação",
	CONTENT_IMAGE_PROCESSING: "Processamento de imagem",
	IMAGE_PROCESSING_PERFORMANCE_INFO: "Combinar Geração de Quadros, Scaling e Shaders pode reduzir o desempenho. Desative o que não usa; teste Janela e Tela Cheia por jogo.",
	CONTENT_TAB_FRAME_GENERATION: "Geração",
	CONTENT_TAB_SCALING: "Escala",
	CONTENT_TAB_SHADERS: "Shaders",
	CONTENT_SCALING: "Redimensionamento",
	CONTENT_SHADERS: "Shaders",
	SCALING_ENABLED: "Ativar redimensionamento (Reiniciar)",
	EXPERIMENTAL_LABEL: "Experimental",
	SCALING_ENABLED_DESC: "Ative antes do jogo para usar Lossless Scaling ou GFG Scaler; desligar desativa o redimensionamento. Alguns jogos podem exigir o modo Janela; Tela Cheia sem Bordas também pode funcionar.",
	SCALING_RUNTIME_SURFACE_UNSUPPORTED: "This running surface does not support GFG Extreme scaling. Quality Supersampling, Scale Factor, and Sharpness are locked until a supported surface is detected. Frame Generation remains available.",
	SCALING_METHOD: "Método de redimensionamento",
	SCALING_METHOD_DESC: "Escolha o modelo de redimensionamento. Você pode alterá-lo enquanto o jogo está em execução.",
	SCALING_LS1_ACTIVE_FALLBACK: "LS1 is unavailable for this game. GFG Scaler is active. Your LS1 selection is preserved.",
	SCALING_LS1_UNAVAILABLE: "LS1 falhou na verificação. O GFG Scaler substitui o modelo se ele não carregar; sua escolha fica salva.",
	SCALING_METHOD_COMPARISON_TIP: "Como a escala funciona:\n1. No Steam, defina a resolução do jogo para a resolução máxima da tela (Steam Deck: 1280 × 800; Steam Machine: 3840 × 2160).\n2. No jogo, escolha uma resolução menor, como 480p, 720p ou mais.\n3. Ajuste o fator de escala para ampliar a imagem. 2x tenta dobrar a largura e a altura da entrada (640×360 → 1280×720).\n\nReduzir a resolução do jogo e ampliá-la novamente pode melhorar muito o desempenho, com uma troca na qualidade da imagem.",
	SCALING_METHOD_NATIVE: "Resolução nativa",
	SCALING_METHOD_MAKO: "GFG Scaler",
	SCALING_METHOD_LS1: "LS1 Quality",
	SCALING_METHOD_LS1_PERFORMANCE: "LS1 Performance",
	SCALING_FACTOR: "Fator de escala",
	SCALING_FACTOR_DESC: "2x tenta dobrar a largura e a altura da imagem renderizada pelo jogo (640×360 → 1280×720). Com saída fixa, GFG Extreme solicita uma imagem menor ao jogo. Se o jogo define o tamanho da janela, reduza primeiro a resolução nele; GFG Extreme amplia a saída, respeitando os limites da tela e da GPU.",
	SCALING_FACTOR_LIMIT_SUFFIX: "limite da tela",
	SCALING_FACTOR_DEVICE_LIMIT: "Limite atual da tela: {factor}x. O valor salvo de {saved}x é preservado; ative Superamostragem de qualidade para usá-lo.",
	SCALING_FACTOR_NO_HEADROOM: "Esta entrada já preenche a tela de destino. Tente o modo janela, reduza a resolução no jogo ou ative a Superamostragem de qualidade.",
	SCALING_SUPERSAMPLING: "Superamostragem de qualidade",
	SCALING_SUPERSAMPLING_DESC: "Permite ultrapassar um limite de saída do Gamescope para reduzir a imagem com mais qualidade, aumentando o uso de GPU e memória. Não altera o escalonamento em outras superfícies da área de trabalho.",
	SCALING_SUPERSAMPLING_WARNING: "Com a superamostragem ligada, o GFG Extreme pode superar o limite de saída do Gamescope para melhorar a nitidez.",
	SCALING_SHARPNESS: "Nitidez do redimensionamento",
	SCALING_SHARPNESS_DESC: "GFG Scaler: 0–100% da base de nitidez 3x. LS1: uma das cinco variantes de nitidez aprendidas.",
	CONTENT_FPS_MULTIPLIER: "Geração de quadros",
	CONTENT_PERFORMANCE_SETTINGS: "Configurações de desempenho",
	CONTENT_ADVANCED_DETAILS: "Detalhes avançados",
	CONTENT_FLATPAK_SETUP: "Configuração do Flatpak",
	CONFIG_SECTION_TITLE: "Configurações avançadas de renderização",
	CONFIG_WORKAROUNDS_TITLE: "Configurações de compatibilidade",
	CONFIG_FLOW_SCALE: "Escala de fluxo",
	CONFIG_FLOW_SCALE_DESC: "Resolução de estimativa de movimento da geração de quadros. Menor poupa GPU; maior prioriza qualidade.",
	CONFIG_BASE_FPS_CAP: "Limite de FPS base",
	CONFIG_BASE_FPS_CAP_OFF: "Desativado",
	CONFIG_BASE_FPS_CAP_DESC: "Limita os quadros reais do aplicativo antes da geração de quadros. Funciona com DirectX, OpenGL por meio do Zink e Vulkan.",
	CONFIG_BASE_FPS_CAP_STEADY_RELATION: "Controlado pelo Limite base estável ({fps} FPS). O valor manual continua salvo.",
	CONFIG_BASE_FPS_CAP_FRACTIONAL_PRIORITY_RELATION: "Controlado pela Prioridade de quadros reais ({fps} FPS). O valor manual continua salvo.",
	CONFIG_BASE_FPS_CAP_RECOVERY_RELATION: "Alterar este limite desativa a Recuperação de cadência dinâmica.",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD: "Desativar automaticamente pela taxa de atualização",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD_DESC: "Pausa a geração na taxa de atualização do Gamescope escolhida ou abaixo dela; retoma acima. Requer dados da taxa de atualização.",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD: "Limite da taxa de atualização",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD_DESC: "Escolha a maior taxa de atualização em que a geração de quadros deve permanecer pausada.",
	CONFIG_ULTRA_PERFORMANCE: "Desempenho ultra (Reiniciar)",
	CONFIG_ULTRA_PERFORMANCE_DESC: "Reduz a carga da GPU do GFG Extreme em dispositivos de baixo consumo. Usa escala de fluxo de 70%, o modelo de FG mais leve, FP16 quando houver suporte e LS1 Performance quando a escala estiver ativada. Troca qualidade de imagem por desempenho nos recursos ativos do GFG Extreme.",
	CONFIG_ULTRA_PERFORMANCE_WARNING: "Ativar ou desativar o Ultra Performance requer reiniciar o jogo. Outros controles de perfil compatíveis continuam disponíveis após a inicialização.",
	CONFIG_PERFORMANCE_MODE: "Modelo de FG mais leve",
	CONFIG_PERFORMANCE_MODE_DESC: "O modelo FG leve reduz o uso da GPU, mas aumenta fantasmas; Desempenho ultra força sua ativação.",
	CONFIG_DISABLE_STEAMDECK_MODE: "Desativar o modo Steam Deck (Reiniciar)",
	CONFIG_DISABLE_STEAMDECK_MODE_DESC: "Desativa o modo Steam Deck. Desbloqueia configurações ocultas em alguns jogos.",
	CONFIG_ENABLE_ZINK: "Ativar o Zink para jogos OpenGL (Reiniciar)",
	CONFIG_ENABLE_ZINK_DESC: "Executa jogos OpenGL via Vulkan; pode causar travamentos ou congelamentos.",
	CONFIG_FORCE_ALSA_AUDIO: "Forçar áudio ALSA (Reiniciar)",
	CONFIG_FORCE_ALSA_AUDIO_DESC: "Pode ajudar na compatibilidade com Zink, engasgos de áudio ou sons altos repentinos. Desative para restaurar o áudio padrão.",
	CONFIG_EXTERNAL_TOOLS_TITLE: "Ferramentas externas",
	CONFIG_ENABLE_MANGOHUD: "Ativar o MangoHud (Reiniciar)",
	CONFIG_ENABLE_MANGOHUD_DESC: "Usa o MangoHud instalado e suas configurações; veja o guia avançado para ajustes por jogo.",
	CONFIG_ENABLE_VKBASALT: "Ativar shaders (Reiniciar)",
	CONFIG_ENABLE_VKBASALT_DESC: "Ative antes do jogo para usar nitidez, anti-aliasing e shaders incluídos. Não exige instalação separada. Se os efeitos não aparecerem, tente o modo Janela ou Tela Cheia sem Bordas.",
	INSTALL_INSTALLING: "Instalando o GFG Engine...",
	INSTALL_UNINSTALLING: "Removendo o GFG Engine...",
	FLATPAK_MODAL_TITLE: "Extensões Flatpak",
	FLATPAK_RUNTIME_INSTALLER: "Instalador de extensões de ambiente",
	FLATPAK_RUNTIME_VERSION: "Ambiente {version}",
	FLATPAK_INSTALLED: "Instalado",
	FLATPAK_NOT_INSTALLED: "Não instalado",
	FLATPAK_UNINSTALL_TITLE: "Desinstalar extensão de ambiente",
	FLATPAK_UNINSTALL_CONFIRM_PREFIX: "Tem certeza de que deseja desinstalar o ambiente",
	FLATPAK_UNINSTALL_CONFIRM_SUFFIX: "selecionado?",
	FLATPAK_UNINSTALL_BTN: "Desinstalar",
	FLATPAK_INSTALL_BTN: "Instalar",
	FLATPAK_UPDATE_BTN: "Atualizar",
	FLATPAK_INSTALLING_BTN: "Instalando...",
	FLATPAK_UNINSTALLING_BTN: "Desinstalando...",
	FLATPAK_UPDATING_BTN: "Atualizando...",
	FLATPAK_APPS_TITLE: "Aplicativos Flatpak",
	FLATPAK_NO_APPS: "Nenhum aplicativo Flatpak encontrado",
	FLATPAK_NO_APPS_DESC: "Nenhum aplicativo Flatpak está instalado no momento",
	FLATPAK_STATUS_CONFIGURED: "Preparado",
	FLATPAK_STATUS_PARTIAL: "Parcial",
	FLATPAK_STATUS_NO_OVERRIDES: "Sem substituições",
	FLATPAK_ERROR: "Erro",
	FLATPAK_ERROR_STATUS: "Falha ao verificar o status da extensão",
	FLATPAK_ERROR_APPS: "Falha ao carregar os aplicativos Flatpak",
	FLATPAK_STEAM_CONFIG_TITLE: "Referência para atalhos manuais do Steam",
	FLATPAK_STEAM_CONFIG_HEADER: "Exemplo de destino (não configura o Steam)",
	FLATPAK_STEAM_CONFIG_DESC: "Só para atalhos do Steam adicionados manualmente cujo destino original era /usr/bin/flatpak. Prepare o app acima; mantenha Iniciar em e Opções de inicialização. Heroic, Lutris e EmuDeck usam o guia de inicializadores.",
	FLATPAK_IMPORTANT_LABEL: "IMPORTANTE:",
	FLATPAK_STEAM_CONFIG_IMPORTANT: "Substitua somente o DESTINO. Não cole isto nas Opções de inicialização.",
	FLATPAK_PER_GAME_APP_DESC: "{app_id} - {status}. Ative o GFG Extreme por jogo usando {wrapper_path}. Consulte o campo correto no guia de inicializadores.",
	FLATPAK_DIRECT_APP_DESC: "{app_id} - {status}. A preparação se aplica a todo este aplicativo Flatpak. Siga o guia de inicializadores para EmuDeck e atalhos do Steam.",
	FLATPAK_STEP_WRAPPER_PATH: "Wrapper instalado neste dispositivo:",
	FLATPAK_STEP_FINAL: "Destino para um atalho que originalmente usava \"/usr/bin/flatpak\":",
	FLATPAK_OPEN_README: "Abrir guia de inicializadores",
	FLATPAK_CLOSE: "Fechar",
	ADVANCED_DETAILS_LOADING: "Carregando informações...",
	ADVANCED_DETAILS_ERROR_PREFIX: "Erro:",
	ADVANCED_DETAILS_DLL_PATH: "Caminho da DLL",
	ADVANCED_DETAILS_LIBRARY: "Biblioteca do Lossless Scaling",
	ADVANCED_DETAILS_RENDERER: "GFG Engine",
	ADVANCED_DETAILS_INSTALLATION: "Installation",
	ADVANCED_DETAILS_INSTALLED_VERSION: "Installed version",
	ADVANCED_DETAILS_BUNDLED_VERSION: "Bundled version",
	ADVANCED_DETAILS_HOST_ARCHITECTURE: "Host architecture",
	ADVANCED_DETAILS_LAYER_PATH: "Renderer library",
	ADVANCED_DETAILS_MANIFEST_PATH: "Vulkan manifest",
	ADVANCED_DETAILS_LAUNCHER_PATH: "Launch wrapper",
	ADVANCED_DETAILS_DETECTION: "Detection",
	ADVANCED_DETAILS_DLL_NOT_DETECTED: "Lossless Scaling not detected",
	ADVANCED_DETAILS_UNSUPPORTED_HOST: "Unsupported host",
	ADVANCED_DETAILS_UPDATE_REQUIRED: "Bundled update available",
	ADVANCED_DETAILS_INCOMPLETE: "Incomplete installation",
	ADVANCED_DETAILS_NOT_AVAILABLE: "Não disponível",
	ADVANCED_DETAILS_DETECTION_SOURCE: "Origem da detecção",
	ADVANCED_DETAILS_CLOSE: "Fechar",
	WELCOME_TITLE: "Olá da equipe GFG Extreme!",
	WELCOME_TIPS_COLLAPSE: "Ocultar dicas",
	WELCOME_TIPS_EXPAND: "Mostrar dicas",
	WELCOME_LIVE_UPDATES: "Muitas configurações são aplicadas em tempo real.",
	WELCOME_RESTART_REQUIRED: "As opções marcadas como “Reiniciar” exigem que o jogo seja reiniciado.",
	WELCOME_PERFORMANCE_NOTE: "Alterações na resolução e no redimensionamento do jogo podem afetar o desempenho.",
	WELCOME_CLEAN_SESSION_PREFIX: "Se algo ",
	WELCOME_CLEAN_SESSION_WRONG: "parecer errado",
	WELCOME_CLEAN_SESSION_AFTER: " após ",
	WELCOME_CLEAN_SESSION_CHANGES: "várias mudanças",
	WELCOME_CLEAN_SESSION_RESTART_SEPARATOR: ", ",
	WELCOME_CLEAN_SESSION_RESTART: "reinicie o jogo para começar uma sessão nova e limpa.",
	WELCOME_ENJOY: "Os melhores ajustes variam por jogo. Teste o que funciona; veja novidades do GFG Extreme na página de lançamentos.",
	PROFILE_CAPTURE_READY: "O GFG Extreme seleciona perfis salvos automaticamente. Se este jogo for novo, salve-o abaixo; reinicie o jogo após alterar configurações que exigem reinício.",
	PROFILE_HELP: "Salve o processo do jogo uma vez para seleção automática do perfil. Fora do jogo, a lista escolhe o perfil a editar.",
	PROFILE_SECTION_TITLE: "Perfis de jogo / processo",
	PROFILE_DEFAULT: "Padrão",
	PROFILE_SAVED_LABEL: "Perfil salvo",
	PROFILE_GAME_SAVED: "Perfil do jogo salvo",
	PROFILE_GAME_SAVE_FAILED: "Não foi possível salvar o perfil do jogo",
	PROFILE_SAVE_RUNNING: "Salvar perfil para {game}",
	PROFILE_DETAIL_DEFAULT: "Abra um jogo para salvar seu perfil",
	PROFILE_DETAIL_GAME: "Jogo salvo",
	PROFILE_DETAIL_PROCESS: "Processo salvo",
	PROFILE_STEAM_APP_ID: "ID do aplicativo Steam: {app_id}",
	PROFILE_PROCESSES: "Processos: {processes}",
	PROFILE_PROCESSES_EMPTY: "Processos: insira um em Processos correspondentes abaixo",
	PROFILE_MANAGE_WHEN_IDLE: "Feche o jogo em execução para renomear ou excluir perfis.",
	PROFILE_NAME_LABEL: "Nome",
	PROFILE_CANCEL_BTN: "Cancelar",
	PROFILE_RENAME_TITLE: "Renomear perfil",
	PROFILE_RENAME_DESC_PREFIX: "Escolha um nome amigável para este perfil de jogo ou processo.",
	PROFILE_RENAME_BTN: "Renomear",
	PROFILE_CANNOT_DELETE_TITLE: "Não é possível excluir o perfil padrão",
	PROFILE_CANNOT_DELETE_MSG: "O perfil padrão não pode ser excluído",
	PROFILE_DELETE_TITLE: "Excluir perfil de jogo / processo",
	PROFILE_DELETE_CONFIRM: "Excluir \"{profile}\" e todas as configurações salvas?",
	PROFILE_DELETE_BTN: "Excluir",
	PROFILE_CANNOT_RENAME_TITLE: "Não é possível renomear o perfil padrão",
	PROFILE_CANNOT_RENAME_MSG: "O perfil padrão não pode ser renomeado",
	USAGE_TITLE: "Instruções de uso",
	USAGE_DESC: "Adicione esta opção de inicialização no Steam para usar Geração de Quadros, Scaling ou ambos no GFG Extreme.",
	CLIPBOARD_COPIED: "Copiado para a área de transferência",
	CLIPBOARD_COPYING: "Copiando...",
	CLIPBOARD_COPY_LAUNCH: "Copiar opção de inicialização",
	CLIPBOARD_MAKO_FGMOD: "GFG Extreme + DeckyFG",
	CONTENT_RUNNING: "em execução.",
	CONTENT_ENGINE_UPDATE_REQUIRED: "Atualização do GFG Engine necessária",
	CONTENT_ENGINE_INSTALLED: "Instalado:",
	CONTENT_ENGINE_NOT_RECORDED: "não registrado",
	CONTENT_ENGINE_EXPECTS: "Este plugin espera:",
	CONTENT_ENGINE_BUNDLED_VERSION: "a versão incluída",
	CONTENT_ENGINE_PREDATES_TRACKING: "A carga instalada é anterior ao rastreamento de versões.",
	CONTENT_ENGINE_UPDATE_DESC: "Reinstale o GFG Engine incluído e atualize as extensões de runtime dos Flatpaks preparados.",
	CONTENT_UPDATE_RENDERER: "Atualizar o GFG Engine",
	CONTENT_UPDATING_RENDERER: "Atualizando o GFG Engine...",
	ADAPTIVE_TITLE: "Geração de quadros adaptativa",
	ADAPTIVE_DESC: "Busca o FPS de saída desejado. Limite base estável prioriza ritmo uniforme por padrão; Adaptativo fracionário mantém mais quadros reais. Teste por jogo.",
	FRACTIONAL_ADAPTIVE_PRESET: "Adaptativo fracionário",
	FRACTIONAL_ADAPTIVE_PRESET_DESC: "Combina proporções de geração para atingir metas como 60 FPS reais → 90 FPS exibidos. Mantém mais quadros reais e pode reduzir a latência de entrada e os fantasmas, mas pode parecer menos suave em alguns jogos.",
	FRACTIONAL_ADAPTIVE_PRESET_RELATION: "Não pode ser combinado com o Limite base estável. Alterar esta opção também desativa a Recuperação de cadência dinâmica.",
	ADAPTIVE_REAL_FRAME_PRIORITY: "Prioridade de quadros reais",
	ADAPTIVE_REAL_FRAME_PRIORITY_DESC: "Os valores de FPS exibidos estimam os limites de quadros reais com base no FPS alvo, não taxas garantidas pelo jogo. Uma prioridade maior permite mais quadros reais e pode reduzir a latência e os fantasmas, mas pode parecer menos uniforme.",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO: "Automática",
	ADAPTIVE_REAL_FRAME_PRIORITY_LOW: "Baixa",
	ADAPTIVE_REAL_FRAME_PRIORITY_MEDIUM: "Média",
	ADAPTIVE_REAL_FRAME_PRIORITY_HIGH: "Alta",
	ADAPTIVE_REAL_FRAME_PRIORITY_VERY_HIGH: "Muito alta",
	ADAPTIVE_REAL_FRAME_PRIORITY_OPTION: "{priority} — até {cap} FPS reais ({percent}% da meta)",
	ADAPTIVE_REAL_FRAME_PRIORITY_ACTIVE_RELATION: "Com meta de {target} FPS: cerca de {cap} reais / {generated_fps} gerados ({real}:{generated}) se alcançada. As taxas variam; substitui o Limite de FPS base.",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO_RELATION: "Automática mantém o comportamento atual do Adaptativo fracionário. O Limite de FPS base continua disponível.",
	ADAPTIVE_TARGET_FPS: "FPS alvo",
	ADAPTIVE_TARGET_FPS_DESC: "FPS de saída. O Adaptativo fracionário mistura proporções; o Limite base estável parte da metade e pode usar um inteiro menor validado.",
	ADAPTIVE_AUTO_BASE_FPS_CAP: "Limite base estável",
	ADAPTIVE_AUTO_BASE_FPS_CAP_DESC: "Modo Adaptativo padrão: começa na metade da meta; Cadência suave pode alinhar proporções 3x–5x validadas. Geralmente mais suave, com menos quadros reais e possível atraso ou ghosting extra.",
	ADAPTIVE_AUTO_BASE_FPS_CAP_RELATION: "Substitui o Limite de FPS base. Não pode ser combinado com o Adaptativo fracionário ou a Recuperação de cadência dinâmica.",
	ADAPTIVE_MAX_MULTIPLIER: "Multiplicador adaptativo máximo",
	ADAPTIVE_MAX_MULTIPLIER_DESC: "Use 0x para pausar ou retomar a geração de quadros ao vivo sem descarregar seus recursos. Caso contrário, este é o limite de interpolação, não uma proporção fixa; o modo Adaptativo pode usar multiplicadores menores ou fracionários. Ajuste-o apenas até o necessário para atingir o FPS alvo. Teste 2x–5x em cada jogo.",
	ADAPTIVE_SMOOTH_CADENCE: "Cadência suave",
	ADAPTIVE_SMOOTH_CADENCE_DESC: "Usa a apresentação ordenada validada do Gamescope para um ritmo mais estável. O Adaptativo Fracionário mantém os quadros reais; o modo Fixo e o Limite de FPS Base Estável podem priorizar uma saída uniforme. Pode reduzir os FPS reais e a responsividade. Ativada por padrão; desative por jogo se preferir.",
	GAMESCOPE_VRR_MODE: "VRR do Gamescope",
	GAMESCOPE_VRR_MODE_DESC: "Desativar o VRR permite que o GFG Extreme controle o ritmo dos quadros. Isso pode melhorar a geração de quadros em alguns jogos, mas não em outros; teste em cada jogo. Se o dispositivo ou a tela não forem compatíveis com VRR, esta opção não terá efeito.",
	GAMESCOPE_VRR_FOLLOW_STEAM: "Seguir o Steam",
	GAMESCOPE_VRR_ON: "Ligado",
	GAMESCOPE_VRR_OFF: "Desligado",
	DYNAMIC_CADENCE_RECOVERY: "Recuperação de cadência dinâmica",
	DYNAMIC_CADENCE_RECOVERY_DESC: "Ajuda jogos e emuladores que alternam taxas nativas, como 30 FPS durante o jogo e 60 FPS nos menus. Verifica periodicamente a mudança e recupera a cadência correta, mas cada verificação pode afetar brevemente o ritmo. Ative apenas nos jogos afetados.",
	DYNAMIC_CADENCE_RECOVERY_RELATION: "Recuperação desativa Limite base estável e Limite de FPS base e redefine Prioridade de quadros reais como Automática. Mudar um limite ou a prioridade desativa a Recuperação.",
	DYNAMIC_CADENCE_PROBE_INTERVAL: "Intervalo de verificação da cadência",
	DYNAMIC_CADENCE_PROBE_INTERVAL_DESC: "Intervalo de checagem: 0,1 s pode causar engasgos frequentes; 2 s é o padrão; 3 s checa menos. Teste por jogo.",
	ADAPTIVE_VALUE: "Adaptativo",
	CONFIG_DLL_PATH: "Caminho do Lossless.dll (Reiniciar)",
	CONFIG_DLL_PATH_DESC: "Caminho completo opcional para Lossless.dll. Deixe em branco para usar a detecção automática do GFG Engine. Reinicie o jogo após alterar.",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH: "Desativar o GFG Engine na próxima inicialização",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH_DESC: "Para diagnóstico: ignora o GFG Engine na próxima abertura. Use Geração de Quadros acima para ligar ou desligar a geração.",
	CONFIG_DISABLE_HDR_EXPOSURE: "Desativar HDR",
	CONFIG_DISABLE_HDR_EXPOSURE_DESC: "HDR não está disponível nesta versão. Esta configuração obrigatória mantém o caminho SDR estável ativo.",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY: "Gamescope WSI (Reiniciar)",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_DESC: "Pode reduzir artefatos de movimento coloridos ou pixelados pela apresentação do Gamescope. Opcional com Scaling e Geração de Quadros; ative só se necessário.",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_WARNING: "Só em inicializações de host de 64 bits compatíveis. Deixe desligado se não precisar; pode reduzir o desempenho.",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY: "Imagens de swapchain do jogo (Reiniciar)",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_DESC: "Pode corrigir falhas na abertura com Geração de Quadros ao manter o mínimo de imagens de swapchain pedido pelo jogo. Use só nos jogos afetados.",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_WARNING: "Quadros gerados podem ser ignorados quando o compositor não tem uma imagem livre, o que pode reduzir a fluidez ou o desempenho sob pressão.",
	FRAME_GENERATION_PROVISIONED: "Ativar Frame-gen (Reiniciar)",
	FRAME_GENERATION_PROVISIONED_DESC: "Ative antes do jogo para carregar a Geração de Quadros; desative se usar só Scaling ou Shaders.",
	FIXED_MULTIPLIER: "Multiplicador fixo",
	FIXED_MULTIPLIER_DESC: "2x–5x define uma proporção de saída fixa; 5x custa mais e serve para telas de alta taxa de atualização. 0x pausa a geração sem liberar recursos.",
	CONFIG_ALLOW_FP16: "Permitir FP16 (Reiniciar)",
	CONFIG_ALLOW_FP16_DESC: "Configuração global do renderizador: aplica-se a todos os perfis e não pode ser alterada por jogo. Melhora o desempenho em AMD; desative para GPUs NVIDIA mais antigas. Reinicie o jogo após alterar.",
	CONFIG_GPU: "GPU (Reiniciar)",
	CONFIG_GPU_DESC: "Nome opcional da GPU, ID fornecedor:dispositivo ou ID do barramento PCI. Reinicie o jogo após a alteração.",
	CONFIG_ACTIVE_IN: "Processos correspondentes",
	CONFIG_ACTIVE_IN_DESC: "Nomes de processos separados por vírgulas. A captura do jogo preenche estes campos; edite só para adicionar um alias de inicializador ou emulador.",
	CONFIG_MANUAL_OVERRIDES_TITLE: "Substituições manuais",
	INSTALL_REMOVE_RENDERER: "Remover o GFG Engine",
	INSTALL_RENDERER: "Instalar o GFG Engine",
	FLATPAK_EXTENSION_UPDATED: "Extensão Flatpak atualizada",
	FLATPAK_EXTENSION_FAILED: "Falha na extensão Flatpak",
	FLATPAK_EXTENSION_ACTION_FAILED: "Não foi possível",
	FLATPAK_RUNTIME_EXTENSION_UPDATED: "extensão de ambiente atualizada",
	FLATPAK_RUNTIME_EXTENSION: "extensão de ambiente",
	FLATPAK_APPLICATION_UPDATED: "Aplicativo Flatpak atualizado",
	FLATPAK_UPDATED: "atualizado",
	FLATPAK_PREPARE_APPLICATION: "Preparar um aplicativo",
	FLATPAK_PREPARE_APPLICATION_DESC: "Instale a extensão correspondente e prepare o app. Heroic/Lutris precisam de wrapper por jogo; emuladores são preparados para o app inteiro. Veja o guia de inicializadores.",
	FLATPAK_INSTALL_ACTION: "instalar",
	FLATPAK_UNINSTALL_ACTION: "desinstalar",
	FLATPAK_APPLICATION_ACTION_FAILED: "Não foi possível atualizar",
	PROFILE_UNKNOWN_ERROR: "Erro desconhecido",
	PROFILE_LOAD_FAILED: "Falha ao carregar os perfis",
	PROFILE_LOAD_ERROR: "Erro ao carregar os perfis",
	PROFILE_SWITCHED: "Perfil alterado",
	PROFILE_SWITCHED_DESC: "Perfil alterado para:",
	PROFILE_SWITCH_FAILED: "Falha ao alterar o perfil",
	PROFILE_SWITCH_ERROR: "Erro ao alterar o perfil",
	PROFILE_DELETED: "Perfil excluído",
	PROFILE_DELETED_DESC: "Perfil excluído:",
	PROFILE_DELETE_FAILED: "Falha ao excluir o perfil",
	PROFILE_DELETE_ERROR: "Erro ao excluir o perfil",
	PROFILE_RENAMED: "Perfil renomeado",
	PROFILE_RENAMED_DESC: "Perfil renomeado para:",
	PROFILE_RENAME_FAILED: "Falha ao renomear o perfil",
	PROFILE_RENAME_ERROR: "Erro ao renomear o perfil",
	PROFILE_UPDATE_CONFIG_FAILED: "Falha ao atualizar a configuração do perfil",
	PROFILE_UPDATE_CONFIG_ERROR: "Erro ao atualizar a configuração do perfil",
	USAGE_MAKO_CONFIG_NOTE: "Este comando aplica o GFG Extreme apenas ao jogo iniciado com ele.",
	USAGE_ISOLATION_NOTE: "Não combine o GFG Extreme com outra ferramenta de geração de quadros ou redimensionamento no mesmo jogo.",
	ADVANCED_DETAILS_FAILED_LOAD_DATA: "Falha ao carregar os dados",
	STATUS_ENGINE_INSTALLED: "GFG Engine instalado",
	STATUS_ENGINE_NOT_INSTALLED: "GFG Engine não instalado",
	STATUS_ENGINE_INSTALLING: "Instalando o GFG Engine...",
	STATUS_ENGINE_UPDATING: "Atualizando o GFG Engine...",
	STATUS_ENGINE_REMOVING: "Removendo o GFG Engine...",
	STATUS_ENGINE_REMOVED: "GFG Engine removido com sucesso!",
	STATUS_INSTALL_FAILED: "Falha na instalação:",
	STATUS_UNINSTALL_FAILED: "Falha na desinstalação:",
	STATUS_LOSSLESS_INSTALLED: "Lossless Scaling instalado",
	STATUS_LOSSLESS_NOT_INSTALLED: "Lossless Scaling não instalado — necessário para geração de quadros e LS1; o GFG Scaler continua disponível",
	TOAST_INSTALL_COMPLETE: "Instalação concluída",
	TOAST_INSTALL_COMPLETE_DESC: "É recomendável reiniciar o dispositivo.",
	TOAST_INSTALL_FAILED: "Falha na instalação",
	TOAST_UNKNOWN_ERROR: "Ocorreu um erro desconhecido",
	TOAST_UNINSTALL_COMPLETE: "GFG Engine removido",
	TOAST_UNINSTALL_COMPLETE_DESC: "Os arquivos do GFG Engine foram removidos",
	TOAST_UNINSTALL_FAILED: "Falha na desinstalação",
	TOAST_CONFIG_UPDATE_FAILED: "Falha na atualização",
	TOAST_CONFIG_UPDATE_FAILED_DESC: "Falha ao atualizar a configuração",
	TOAST_CLIPBOARD_SUCCESS: "Copiado para a área de transferência!",
	TOAST_CLIPBOARD_SUCCESS_DESC: "Opção de inicialização pronta para colar",
	TOAST_CLIPBOARD_FAILED: "Falha ao copiar",
	TOAST_CLIPBOARD_FAILED_DESC: "Não foi possível copiar para a área de transferência",
	FEATURE_UPSCALING_TAB: "Upscaling",
	LIVE_STATUS_TITLE: "Live Status",
	LIVE_STATUS_CONNECTED: "GFG Extreme is active",
	LIVE_STATUS_WAITING: "Waiting for GFG Extreme",
	LIVE_STATUS_WAITING_DESC: "Sem métricas ao vivo; o GFG Extreme pode continuar ativo. Alguns jogos ou emuladores não as informam. Confira a Geração de Quadros ou o Scaling manualmente.",
	LIVE_STATUS_FG_INACTIVE: "On in settings, but not currently generating frames.",
	LIVE_STATUS_FG_MENU_SUSPENDED: "Frame Generation is disabled while a Steam or Decky menu is open.",
	LIVE_STATUS_OFF: "Off",
	LIVE_STATUS_SCALING_INACTIVE: "On in settings, but the game image is not being upscaled.",
	LIVE_STATUS_SCALING_MEMORY_LIMIT: "The requested render resolution exceeds this GPU's memory safety limit. Lower the in-game resolution.",
	LIVE_STATUS_SCALING_MEMORY_CONSTRAINED: "Requested {requested}×; limited to {effective}× by this GPU's memory safety limit.",
	LIVE_STATUS_SCALING_NO_HEADROOM: "Esta entrada já preenche a tela de destino. Tente o modo janela, reduza a resolução no jogo ou ative a Superamostragem de qualidade.",
	LIVE_STATUS_PENDING: "A saved change is still applying or needs a restart.",
	LIVE_STATUS_SUPERSAMPLING: "Quality Supersampling active.",
	LIVE_STATUS_SCALING_FALLBACK: "You selected {requested}; GFG Extreme is using {active} instead.",
	LIVE_STATUS_MODE: "Mode",
	LIVE_STATUS_FIXED_VALUE: "Fixed",
	LIVE_STATUS_ADAPTIVE_STYLE: "Style",
	LIVE_STATUS_STEADY_VALUE: "Steady",
	LIVE_STATUS_FRACTIONAL_VALUE: "Fractional",
	LIVE_STATUS_TARGET: "Target",
	LIVE_STATUS_MAX_MULTIPLIER: "Max factor",
	LIVE_STATUS_MULTIPLIER: "Factor",
	LIVE_STATUS_MODEL: "Model",
	LIVE_STATUS_NATIVE: "Native",
	LIVE_STATUS_LS1_PERFORMANCE: "LS1 Perf",
	LIVE_STATUS_ORIGINAL_RESOLUTION: "Input",
	LIVE_STATUS_RENDER_RESOLUTION: "Render",
	LIVE_STATUS_DISPLAY_RESOLUTION: "Display",
	LIVE_STATUS_SCALED_RESOLUTION: "Output",
	LIVE_STATUS_SCALING_UNAVAILABLE: "Unavailable for this running surface.",
	MODEL_WARNING_TITLE: "Aviso sobre os modelos do Lossless Scaling",
	MODEL_WARNING_DESCRIPTION: "Alguns recursos do Lossless Scaling podem estar indisponíveis:",
	MODEL_WARNING_LS1: "O LS1 falhou na verificação de disponibilidade. O GFG Scaler é usado automaticamente se o LS1 não puder ser carregado.",
	MODEL_WARNING_LSFG: "Uma verificação de modelos LSFG falhou. A geração de quadros pode estar indisponível com a precisão selecionada.",
	MODEL_WARNING_UPDATE: "Aplique as atualizações disponíveis do GFG Extreme e Renderer e reinicie. Se persistir, confira os arquivos de Lossless Scaling e colete diagnósticos.",
	MODEL_WARNING_CHECK_UPDATES: "Abrir versões do renderizador"
},
	"pt-PT": {
	CONFIG_VKBASALT_ADVANCED_GLOBAL_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. The Default profile uses this global file.",
	CONFIG_VKBASALT_ADVANCED_PROFILE_NOTE: "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. This file belongs to the selected profile and is removed when that profile is deleted.",
	CONFIG_VKBASALT_SHARPENING: "Sharpening",
	CONFIG_VKBASALT_SHARPENING_DESC: "CAS is a crisp general-purpose sharpener. DLS can preserve noisy or grainy detail better when paired with denoise.",
	CONFIG_VKBASALT_EFFECT_NONE: "Off",
	CONFIG_VKBASALT_SHARPENING_CAS: "CAS",
	CONFIG_VKBASALT_SHARPENING_DLS: "DLS",
	CONFIG_VKBASALT_SHARPNESS: "Sharpness ({value}%)",
	CONFIG_VKBASALT_SHARPNESS_DESC: "Higher values produce a stronger effect but can exaggerate grain and create halos around high-contrast edges.",
	CONFIG_VKBASALT_DLS_DENOISE: "DLS Denoise ({value}%)",
	CONFIG_VKBASALT_DLS_DENOISE_DESC: "Limits how strongly DLS sharpens film grain and fine noise.",
	CONFIG_VKBASALT_ANTIALIASING: "Anti-aliasing",
	CONFIG_VKBASALT_ANTIALIASING_DESC: "Optionally smooth jagged edges before sharpening. FXAA is lighter and softer; SMAA is more selective and may cost more GPU time.",
	CONFIG_VKBASALT_ANTIALIASING_FXAA: "FXAA",
	CONFIG_VKBASALT_ANTIALIASING_SMAA: "SMAA",
	CONFIG_VKBASALT_SHADER: "Efeitos",
	CONFIG_VKBASALT_SHADER_DESC: "Effects run in selection order; uncheck and recheck to move one last. Stacking increases GPU load, especially with heavier effects such as HDR Look. Test per game and monitor GPU usage.",
	CONFIG_VKBASALT_EFFECTS_SELECTED: "Choose effects ({value} selected)",
	CONFIG_VKBASALT_EFFECTS_CLEAR: "Clear all",
	CONFIG_VKBASALT_EFFECTS_DONE: "Done",
	CONFIG_VKBASALT_EFFECTS_PREVIOUS_PAGE: "Previous effects page",
	CONFIG_VKBASALT_EFFECTS_NEXT_PAGE: "Next effects page",
	CONFIG_VKBASALT_SHADER_VIBRANCE: "Vibrance",
	CONFIG_VKBASALT_SHADER_CURVES: "Curves",
	CONFIG_VKBASALT_SHADER_DEBAND: "Deband",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR: "Technicolor",
	CONFIG_VKBASALT_SHADER_SEPIA: "Sepia",
	CONFIG_VKBASALT_SHADER_MONOCHROME: "Monochrome",
	CONFIG_VKBASALT_SHADER_VIGNETTE: "Vignette",
	CONFIG_VKBASALT_SHADER_HDR_LOOK: "HDR Look (SDR)",
	CONFIG_VKBASALT_SHADER_CLARITY: "Clarity",
	CONFIG_VKBASALT_SHADER_LEVELS_PLUS: "Levels Plus",
	CONFIG_VKBASALT_SHADER_COLOURFULNESS: "Colourfulness",
	CONFIG_VKBASALT_SHADER_TECHNICOLOR2: "Technicolor 2",
	CONFIG_VKBASALT_SHADER_DPX: "DPX / Cineon",
	CONFIG_VKBASALT_SHADER_BLEACH_BYPASS: "Bleach Bypass",
	CONFIG_VKBASALT_SHADER_NOIR: "Noir",
	CONFIG_VKBASALT_SHADER_FILM_GRAIN: "Film Grain",
	CONFIG_VKBASALT_SHADER_CARTOON: "Cartoon",
	CONFIG_VKBASALT_SHADER_NOSTALGIA: "Nostalgia",
	CONFIG_VKBASALT_SHADER_CHROMATIC_ABERRATION: "Chromatic Aberration",
	CONTENT_HIDE_INFO: "Ocultar informações",
	CONTENT_SHOW_INFO: "Mostrar informações",
	DEVELOPMENT_DEPLOYMENT_TITLE: "Implementação local de desenvolvimento",
	DEVELOPMENT_DETAILS: "Detalhes",
	DEVELOPMENT_HIDE: "Ocultar",
	DEVELOPMENT_DEPLOYED: "implementado",
	DEVELOPMENT_DEPLOYED_AT: "Implementado",
	DEVELOPMENT_UNCHANGED: "sem alterações",
	DEVELOPMENT_COMMIT: "Commit",
	DEVELOPMENT_FRONTEND: "Interface",
	DEVELOPMENT_BACKEND: "Backend",
	DEVELOPMENT_LOCAL_EDITS: "+ alterações locais",
	DEVELOPMENT_LAYER_64: "Camada de 64 bits",
	DEVELOPMENT_LAYER_32: "Camada de 32 bits",
	DEVELOPMENT_FLATPAK_BUNDLES: "Pacotes Flatpak",
	DEVELOPMENT_UNCHANGED_BY_DEPLOYMENT: "Sem alterações nesta implementação",
	CONTENT_IMAGE_PROCESSING: "Processamento de imagem",
	IMAGE_PROCESSING_PERFORMANCE_INFO: "Combinar geração de fotogramas, redimensionamento e shaders pode reduzir o desempenho. Desative o que não usa; teste Janela e Ecrã inteiro por jogo.",
	CONTENT_TAB_FRAME_GENERATION: "Geração",
	CONTENT_TAB_SCALING: "Escala",
	CONTENT_TAB_SHADERS: "Shaders",
	CONTENT_SCALING: "Redimensionamento",
	CONTENT_SHADERS: "Shaders",
	SCALING_ENABLED: "Ativar redimensionamento (Reiniciar)",
	EXPERIMENTAL_LABEL: "Experimental",
	SCALING_ENABLED_DESC: "Ative antes de iniciar para usar Lossless Scaling ou GFG Scaler; desligar desativa o redimensionamento. Alguns jogos podem exigir o modo Janela; Ecrã Inteiro sem Bordas também pode funcionar.",
	SCALING_RUNTIME_SURFACE_UNSUPPORTED: "This running surface does not support GFG Extreme scaling. Quality Supersampling, Scale Factor, and Sharpness are locked until a supported surface is detected. Frame Generation remains available.",
	SCALING_METHOD: "Método de redimensionamento",
	SCALING_METHOD_DESC: "Escolha o modelo de redimensionamento. Pode alterá-lo enquanto o jogo está em execução.",
	SCALING_LS1_ACTIVE_FALLBACK: "LS1 is unavailable for this game. GFG Scaler is active. Your LS1 selection is preserved.",
	SCALING_LS1_UNAVAILABLE: "LS1 falhou na verificação. O GFG Scaler substitui o modelo se não carregar; a seleção fica guardada.",
	SCALING_METHOD_COMPARISON_TIP: "Como funciona o redimensionamento:\n1. No Steam, defina a resolução do jogo para a resolução máxima do ecrã (Steam Deck: 1280 × 800; Steam Machine: 3840 × 2160).\n2. No jogo, escolha uma resolução mais baixa, como 480p, 720p ou mais.\n3. Ajuste o fator de redimensionamento para ampliar a imagem. 2x procura duplicar a largura e a altura da entrada (640×360 → 1280×720).\n\nReduzir a resolução do jogo e ampliá-la novamente pode melhorar muito o desempenho, com uma contrapartida na qualidade de imagem.",
	SCALING_METHOD_NATIVE: "Resolução nativa",
	SCALING_METHOD_MAKO: "GFG Scaler",
	SCALING_METHOD_LS1: "LS1 Quality",
	SCALING_METHOD_LS1_PERFORMANCE: "LS1 Performance",
	SCALING_FACTOR: "Fator de escala",
	SCALING_FACTOR_DESC: "2x procura duplicar a largura e a altura da imagem renderizada pelo jogo (640×360 → 1280×720). Com saída fixa, a GFG Extreme pede uma imagem menor ao jogo. Se o jogo definir o tamanho da janela, reduza primeiro a resolução nele; a GFG Extreme amplia a saída, sujeita aos limites do ecrã e da GPU.",
	SCALING_FACTOR_LIMIT_SUFFIX: "limite do ecrã",
	SCALING_FACTOR_DEVICE_LIMIT: "Limite atual do ecrã: {factor}x. O valor guardado de {saved}x é preservado; ative a Superamostragem de qualidade para o utilizar.",
	SCALING_FACTOR_NO_HEADROOM: "Esta entrada já preenche o ecrã de destino. Experimente o modo de janela, reduza a resolução no jogo ou ative a Superamostragem de qualidade.",
	SCALING_SUPERSAMPLING: "Superamostragem de qualidade",
	SCALING_SUPERSAMPLING_DESC: "Permite ultrapassar um limite de saída do Gamescope para reduzir a imagem com mais qualidade, aumentando a utilização de GPU e memória. Não altera o escalonamento noutras superfícies do ambiente de trabalho.",
	SCALING_SUPERSAMPLING_WARNING: "Com a superamostragem ligada, a GFG Extreme pode superar o limite de saída do Gamescope para melhorar a nitidez.",
	SCALING_SHARPNESS: "Nitidez do redimensionamento",
	SCALING_SHARPNESS_DESC: "GFG Scaler: 0–100% da base de nitidez 3x. LS1: uma de cinco variantes de nitidez aprendidas.",
	CONTENT_FPS_MULTIPLIER: "Geração de fotogramas",
	CONTENT_PERFORMANCE_SETTINGS: "Definições de desempenho",
	CONTENT_ADVANCED_DETAILS: "Detalhes avançados",
	CONTENT_FLATPAK_SETUP: "Configuração do Flatpak",
	CONFIG_SECTION_TITLE: "Definições avançadas de renderização",
	CONFIG_WORKAROUNDS_TITLE: "Definições de compatibilidade",
	CONFIG_FLOW_SCALE: "Escala de fluxo",
	CONFIG_FLOW_SCALE_DESC: "Resolução de estimação de movimento da geração de fotogramas. Menor poupa GPU; maior favorece a qualidade.",
	CONFIG_BASE_FPS_CAP: "Limite de FPS base",
	CONFIG_BASE_FPS_CAP_OFF: "Desativado",
	CONFIG_BASE_FPS_CAP_DESC: "Limita os fotogramas reais da aplicação antes da geração de fotogramas. Funciona com DirectX, OpenGL através do Zink e Vulkan.",
	CONFIG_BASE_FPS_CAP_STEADY_RELATION: "Controlado pelo Limite base estável ({fps} FPS). O valor manual permanece guardado.",
	CONFIG_BASE_FPS_CAP_FRACTIONAL_PRIORITY_RELATION: "Controlado pela Prioridade de fotogramas reais ({fps} FPS). O valor manual permanece guardado.",
	CONFIG_BASE_FPS_CAP_RECOVERY_RELATION: "Alterar este limite desativa a Recuperação de cadência dinâmica.",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD: "Desativar automaticamente pela taxa de atualização",
	CONFIG_FRAME_GENERATION_REFRESH_GUARD_DESC: "Pausa a geração na taxa de atualização do Gamescope escolhida ou abaixo dela; retoma acima. Requer dados da taxa de atualização.",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD: "Limite da taxa de atualização",
	CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD_DESC: "Escolha a taxa de atualização mais alta em que a geração de fotogramas deve permanecer pausada.",
	CONFIG_ULTRA_PERFORMANCE: "Desempenho ultra (Reiniciar)",
	CONFIG_ULTRA_PERFORMANCE_DESC: "Reduz a carga da GPU do GFG Extreme em dispositivos de baixo consumo. Utiliza uma escala de fluxo de 70%, o modelo de FG mais leve, FP16 quando suportado e LS1 Performance quando o redimensionamento está ativado. Troca qualidade de imagem por desempenho nas funcionalidades ativas do GFG Extreme.",
	CONFIG_ULTRA_PERFORMANCE_WARNING: "Ativar ou desativar o Ultra Performance requer reiniciar o jogo. Os outros controlos de perfil compatíveis continuam disponíveis após o arranque.",
	CONFIG_PERFORMANCE_MODE: "Modelo de FG mais leve",
	CONFIG_PERFORMANCE_MODE_DESC: "O modelo FG leve reduz o uso da GPU, mas aumenta as imagens fantasma; Desempenho ultra obriga a ativá-lo.",
	CONFIG_DISABLE_STEAMDECK_MODE: "Desativar o modo Steam Deck (Reiniciar)",
	CONFIG_DISABLE_STEAMDECK_MODE_DESC: "Desativa o modo Steam Deck. Desbloqueia definições ocultas em alguns jogos.",
	CONFIG_ENABLE_ZINK: "Ativar o Zink para jogos OpenGL (Reiniciar)",
	CONFIG_ENABLE_ZINK_DESC: "Executa jogos OpenGL através de Vulkan; pode causar falhas ou bloqueios.",
	CONFIG_FORCE_ALSA_AUDIO: "Forçar áudio ALSA (Reiniciar)",
	CONFIG_FORCE_ALSA_AUDIO_DESC: "Pode ajudar na compatibilidade com Zink, falhas de áudio ou sons altos repentinos. Desative para restaurar o áudio predefinido.",
	CONFIG_EXTERNAL_TOOLS_TITLE: "Ferramentas externas",
	CONFIG_ENABLE_MANGOHUD: "Ativar o MangoHud (Reiniciar)",
	CONFIG_ENABLE_MANGOHUD_DESC: "Usa o MangoHud instalado e as respetivas definições; consulte o guia avançado para alterações por jogo.",
	CONFIG_ENABLE_VKBASALT: "Ativar shaders (Reiniciar)",
	CONFIG_ENABLE_VKBASALT_DESC: "Ative antes de iniciar o jogo para usar nitidez, anti-aliasing e shaders incluídos. Não exige instalação separada. Se os efeitos não aparecerem, experimente o modo Janela ou Ecrã Inteiro sem Bordas.",
	INSTALL_INSTALLING: "A instalar o GFG Engine...",
	INSTALL_UNINSTALLING: "A remover o GFG Engine...",
	FLATPAK_MODAL_TITLE: "Extensões Flatpak",
	FLATPAK_RUNTIME_INSTALLER: "Instalador de extensões de ambiente",
	FLATPAK_RUNTIME_VERSION: "Ambiente {version}",
	FLATPAK_INSTALLED: "Instalado",
	FLATPAK_NOT_INSTALLED: "Não instalado",
	FLATPAK_UNINSTALL_TITLE: "Desinstalar extensão de ambiente",
	FLATPAK_UNINSTALL_CONFIRM_PREFIX: "Tem a certeza de que pretende desinstalar o ambiente",
	FLATPAK_UNINSTALL_CONFIRM_SUFFIX: "selecionado?",
	FLATPAK_UNINSTALL_BTN: "Desinstalar",
	FLATPAK_INSTALL_BTN: "Instalar",
	FLATPAK_UPDATE_BTN: "Atualizar",
	FLATPAK_INSTALLING_BTN: "A instalar...",
	FLATPAK_UNINSTALLING_BTN: "A desinstalar...",
	FLATPAK_UPDATING_BTN: "A atualizar...",
	FLATPAK_APPS_TITLE: "Aplicações Flatpak",
	FLATPAK_NO_APPS: "Nenhuma aplicação Flatpak encontrada",
	FLATPAK_NO_APPS_DESC: "Não existem aplicações Flatpak instaladas neste momento",
	FLATPAK_STATUS_CONFIGURED: "Preparada",
	FLATPAK_STATUS_PARTIAL: "Parcial",
	FLATPAK_STATUS_NO_OVERRIDES: "Sem substituições",
	FLATPAK_ERROR: "Erro",
	FLATPAK_ERROR_STATUS: "Falha ao verificar o estado da extensão",
	FLATPAK_ERROR_APPS: "Falha ao carregar as aplicações Flatpak",
	FLATPAK_STEAM_CONFIG_TITLE: "Referência para atalhos manuais do Steam",
	FLATPAK_STEAM_CONFIG_HEADER: "Exemplo de destino (não configura o Steam)",
	FLATPAK_STEAM_CONFIG_DESC: "Só para atalhos do Steam adicionados manualmente cujo destino original era /usr/bin/flatpak. Prepare a aplicação acima; mantenha Iniciar em e Opções de arranque. Heroic, Lutris e EmuDeck usam o guia de lançadores.",
	FLATPAK_IMPORTANT_LABEL: "IMPORTANTE:",
	FLATPAK_STEAM_CONFIG_IMPORTANT: "Substitua apenas o DESTINO. Não cole isto nas Opções de arranque.",
	FLATPAK_PER_GAME_APP_DESC: "{app_id} - {status}. Ative o GFG Extreme por jogo usando {wrapper_path}. Consulte o campo correto no guia de lançadores.",
	FLATPAK_DIRECT_APP_DESC: "{app_id} - {status}. A preparação aplica-se a toda esta aplicação Flatpak. Siga o guia de lançadores para EmuDeck e atalhos do Steam.",
	FLATPAK_STEP_WRAPPER_PATH: "Wrapper instalado neste dispositivo:",
	FLATPAK_STEP_FINAL: "Destino para um atalho que originalmente utilizava \"/usr/bin/flatpak\":",
	FLATPAK_OPEN_README: "Abrir guia de lançadores",
	FLATPAK_CLOSE: "Fechar",
	ADVANCED_DETAILS_LOADING: "A carregar informações...",
	ADVANCED_DETAILS_ERROR_PREFIX: "Erro:",
	ADVANCED_DETAILS_DLL_PATH: "Caminho da DLL",
	ADVANCED_DETAILS_LIBRARY: "Biblioteca do Lossless Scaling",
	ADVANCED_DETAILS_RENDERER: "GFG Engine",
	ADVANCED_DETAILS_INSTALLATION: "Installation",
	ADVANCED_DETAILS_INSTALLED_VERSION: "Installed version",
	ADVANCED_DETAILS_BUNDLED_VERSION: "Bundled version",
	ADVANCED_DETAILS_HOST_ARCHITECTURE: "Host architecture",
	ADVANCED_DETAILS_LAYER_PATH: "Renderer library",
	ADVANCED_DETAILS_MANIFEST_PATH: "Vulkan manifest",
	ADVANCED_DETAILS_LAUNCHER_PATH: "Launch wrapper",
	ADVANCED_DETAILS_DETECTION: "Detection",
	ADVANCED_DETAILS_DLL_NOT_DETECTED: "Lossless Scaling not detected",
	ADVANCED_DETAILS_UNSUPPORTED_HOST: "Unsupported host",
	ADVANCED_DETAILS_UPDATE_REQUIRED: "Bundled update available",
	ADVANCED_DETAILS_INCOMPLETE: "Incomplete installation",
	ADVANCED_DETAILS_NOT_AVAILABLE: "Não disponível",
	ADVANCED_DETAILS_DETECTION_SOURCE: "Origem da deteção",
	ADVANCED_DETAILS_CLOSE: "Fechar",
	WELCOME_TITLE: "Olá da equipa GFG Extreme!",
	WELCOME_TIPS_COLLAPSE: "Ocultar dicas",
	WELCOME_TIPS_EXPAND: "Mostrar dicas",
	WELCOME_LIVE_UPDATES: "Muitas definições são aplicadas em tempo real.",
	WELCOME_RESTART_REQUIRED: "As opções assinaladas com «Reiniciar» exigem o reinício do jogo.",
	WELCOME_PERFORMANCE_NOTE: "Alterações à resolução e ao redimensionamento do jogo podem afetar o desempenho.",
	WELCOME_CLEAN_SESSION_PREFIX: "Se algo ",
	WELCOME_CLEAN_SESSION_WRONG: "parecer errado",
	WELCOME_CLEAN_SESSION_AFTER: " após ",
	WELCOME_CLEAN_SESSION_CHANGES: "várias mudanças",
	WELCOME_CLEAN_SESSION_RESTART_SEPARATOR: ", ",
	WELCOME_CLEAN_SESSION_RESTART: "reinicie o jogo para começar uma sessão nova e limpa.",
	WELCOME_ENJOY: "Os melhores ajustes variam por jogo. Teste o que funciona; veja novidades do GFG Extreme na página de lançamentos.",
	PROFILE_CAPTURE_READY: "O GFG Extreme seleciona automaticamente os perfis guardados. Se este jogo for novo, guarde-o abaixo; reinicie o jogo após alterar definições que exijam reinício.",
	PROFILE_HELP: "Guarde o processo do jogo uma vez para seleção automática do perfil. Fora do jogo, a lista escolhe o perfil a editar.",
	PROFILE_SECTION_TITLE: "Perfis de jogo / processo",
	PROFILE_DEFAULT: "Predefinido",
	PROFILE_SAVED_LABEL: "Perfil guardado",
	PROFILE_GAME_SAVED: "Perfil do jogo guardado",
	PROFILE_GAME_SAVE_FAILED: "Não foi possível guardar o perfil do jogo",
	PROFILE_SAVE_RUNNING: "Guardar perfil para {game}",
	PROFILE_DETAIL_DEFAULT: "Abra um jogo para guardar o respetivo perfil",
	PROFILE_DETAIL_GAME: "Jogo guardado",
	PROFILE_DETAIL_PROCESS: "Processo guardado",
	PROFILE_STEAM_APP_ID: "ID da aplicação Steam: {app_id}",
	PROFILE_PROCESSES: "Processos: {processes}",
	PROFILE_PROCESSES_EMPTY: "Processos: introduza um em Processos correspondentes abaixo",
	PROFILE_MANAGE_WHEN_IDLE: "Feche o jogo em execução para mudar o nome ou eliminar perfis.",
	PROFILE_NAME_LABEL: "Nome",
	PROFILE_CANCEL_BTN: "Cancelar",
	PROFILE_RENAME_TITLE: "Mudar o nome do perfil",
	PROFILE_RENAME_DESC_PREFIX: "Escolha um nome reconhecível para este perfil de jogo ou processo.",
	PROFILE_RENAME_BTN: "Mudar o nome",
	PROFILE_CANNOT_DELETE_TITLE: "Não é possível eliminar o perfil predefinido",
	PROFILE_CANNOT_DELETE_MSG: "O perfil predefinido não pode ser eliminado",
	PROFILE_DELETE_TITLE: "Eliminar perfil de jogo / processo",
	PROFILE_DELETE_CONFIRM: "Eliminar \"{profile}\" e todas as definições guardadas?",
	PROFILE_DELETE_BTN: "Eliminar",
	PROFILE_CANNOT_RENAME_TITLE: "Não é possível mudar o nome do perfil predefinido",
	PROFILE_CANNOT_RENAME_MSG: "Não é possível mudar o nome do perfil predefinido",
	USAGE_TITLE: "Instruções de utilização",
	USAGE_DESC: "Adicione esta opção de arranque ao jogo no Steam para ativar a geração de fotogramas, o redimensionamento ou ambos no GFG Extreme.",
	CLIPBOARD_COPIED: "Copiado para a área de transferência",
	CLIPBOARD_COPYING: "A copiar...",
	CLIPBOARD_COPY_LAUNCH: "Copiar opção de arranque",
	CLIPBOARD_MAKO_FGMOD: "GFG Extreme + DeckyFG",
	CONTENT_RUNNING: "em execução.",
	CONTENT_ENGINE_UPDATE_REQUIRED: "É necessário atualizar o GFG Engine",
	CONTENT_ENGINE_INSTALLED: "Instalado:",
	CONTENT_ENGINE_NOT_RECORDED: "não registado",
	CONTENT_ENGINE_EXPECTS: "Este plugin espera:",
	CONTENT_ENGINE_BUNDLED_VERSION: "a versão incluída",
	CONTENT_ENGINE_PREDATES_TRACKING: "A carga instalada é anterior ao registo de versões.",
	CONTENT_ENGINE_UPDATE_DESC: "Reinstale o GFG Engine incluído e atualize as extensões de ambiente das aplicações Flatpak preparadas.",
	CONTENT_UPDATE_RENDERER: "Atualizar o GFG Engine",
	CONTENT_UPDATING_RENDERER: "A atualizar o GFG Engine...",
	ADAPTIVE_TITLE: "Geração de fotogramas adaptativa",
	ADAPTIVE_DESC: "Procura os FPS de saída pretendidos. O limite base estável privilegia um ritmo suave por predefinição; o Adaptativo fracionário mantém mais fotogramas reais. Teste jogo a jogo.",
	FRACTIONAL_ADAPTIVE_PRESET: "Adaptativo fracionário",
	FRACTIONAL_ADAPTIVE_PRESET_DESC: "Combina proporções de geração para atingir objetivos como 60 FPS reais → 90 FPS apresentados. Mantém mais fotogramas reais e pode reduzir a latência de entrada e as imagens fantasma, mas pode parecer menos suave em alguns jogos.",
	FRACTIONAL_ADAPTIVE_PRESET_RELATION: "Não pode ser combinado com o Limite base estável. Alterar esta opção também desativa a Recuperação de cadência dinâmica.",
	ADAPTIVE_REAL_FRAME_PRIORITY: "Prioridade de fotogramas reais",
	ADAPTIVE_REAL_FRAME_PRIORITY_DESC: "Os valores de FPS apresentados estimam os limites de fotogramas reais com base nos FPS alvo, não taxas garantidas pelo jogo. Uma prioridade maior permite mais fotogramas reais e pode reduzir a latência e as imagens fantasma, mas pode parecer menos uniforme.",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO: "Automática",
	ADAPTIVE_REAL_FRAME_PRIORITY_LOW: "Baixa",
	ADAPTIVE_REAL_FRAME_PRIORITY_MEDIUM: "Média",
	ADAPTIVE_REAL_FRAME_PRIORITY_HIGH: "Alta",
	ADAPTIVE_REAL_FRAME_PRIORITY_VERY_HIGH: "Muito alta",
	ADAPTIVE_REAL_FRAME_PRIORITY_OPTION: "{priority} — até {cap} FPS reais ({percent}% do alvo)",
	ADAPTIVE_REAL_FRAME_PRIORITY_ACTIVE_RELATION: "Com alvo de {target} FPS: cerca de {cap} reais / {generated_fps} gerados ({real}:{generated}) se alcançado. As taxas variam; sobrepõe-se ao limite de FPS base.",
	ADAPTIVE_REAL_FRAME_PRIORITY_AUTO_RELATION: "Automática mantém o comportamento atual do Adaptativo fracionário. O Limite de FPS base continua disponível.",
	ADAPTIVE_TARGET_FPS: "FPS alvo",
	ADAPTIVE_TARGET_FPS_DESC: "FPS de saída. O Adaptativo fracionário combina proporções; o limite base estável parte de metade do alvo e pode usar um inteiro inferior validado.",
	ADAPTIVE_AUTO_BASE_FPS_CAP: "Limite base estável",
	ADAPTIVE_AUTO_BASE_FPS_CAP_DESC: "Modo Adaptativo predefinido: começa a metade do alvo; a Cadência suave pode alinhar proporções 3x–5x validadas. Geralmente mais suave, com menos fotogramas reais e possível latência ou imagens fantasma adicionais.",
	ADAPTIVE_AUTO_BASE_FPS_CAP_RELATION: "Substitui o Limite de FPS base. Não pode ser combinado com o Adaptativo fracionário ou a Recuperação de cadência dinâmica.",
	ADAPTIVE_MAX_MULTIPLIER: "Multiplicador adaptativo máximo",
	ADAPTIVE_MAX_MULTIPLIER_DESC: "Utilize 0x para pausar ou retomar a geração de fotogramas em direto sem descarregar os respetivos recursos. Caso contrário, este é o limite de interpolação, não uma proporção fixa; o modo Adaptativo pode utilizar multiplicadores inferiores ou fracionários. Ajuste-o apenas até ao necessário para atingir os FPS alvo. Teste 2x–5x em cada jogo.",
	ADAPTIVE_SMOOTH_CADENCE: "Cadência suave",
	ADAPTIVE_SMOOTH_CADENCE_DESC: "Usa a apresentação ordenada validada do Gamescope para um ritmo mais estável. O Adaptativo Fracionário mantém os fotogramas reais; o modo Fixo e o Limite de FPS Base Estável podem privilegiar uma saída uniforme. Pode reduzir os FPS reais e a capacidade de resposta. Ativada por predefinição; desative-a por jogo se preferir.",
	GAMESCOPE_VRR_MODE: "VRR do Gamescope",
	GAMESCOPE_VRR_MODE_DESC: "Desativar o VRR permite à GFG Extreme controlar o ritmo dos fotogramas. Isto pode melhorar a geração de fotogramas em alguns jogos, mas não noutros; teste jogo a jogo. Se o dispositivo ou o ecrã não suportarem VRR, esta opção não terá efeito.",
	GAMESCOPE_VRR_FOLLOW_STEAM: "Seguir o Steam",
	GAMESCOPE_VRR_ON: "Ligado",
	GAMESCOPE_VRR_OFF: "Desligado",
	DYNAMIC_CADENCE_RECOVERY: "Recuperação de cadência dinâmica",
	DYNAMIC_CADENCE_RECOVERY_DESC: "Ajuda jogos e emuladores que alternam taxas nativas, como 30 FPS no jogo e 60 FPS nos menus. Verifica periodicamente a alteração e recupera a cadência correta, mas cada verificação pode afetar brevemente o ritmo. Ative apenas nos jogos afetados.",
	DYNAMIC_CADENCE_RECOVERY_RELATION: "A Recuperação desativa o limite base estável e o limite de FPS base e repõe a prioridade de fotogramas reais em Automática. Alterar um limite ou a prioridade desativa-a.",
	DYNAMIC_CADENCE_PROBE_INTERVAL: "Intervalo de verificação da cadência",
	DYNAMIC_CADENCE_PROBE_INTERVAL_DESC: "Intervalo de verificação: 0,1 s pode causar falhas frequentes; 2 s é a predefinição; 3 s verifica menos vezes. Teste jogo a jogo.",
	ADAPTIVE_VALUE: "Adaptativo",
	CONFIG_DLL_PATH: "Caminho do Lossless.dll (Reiniciar)",
	CONFIG_DLL_PATH_DESC: "Caminho completo opcional para Lossless.dll. Deixe em branco para utilizar a deteção automática do GFG Engine. Reinicie o jogo após alterar.",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH: "Desativar o GFG Engine no próximo arranque",
	CONFIG_DISABLE_MAKO_NEXT_LAUNCH_DESC: "Para diagnóstico: ignora o GFG Engine no próximo arranque. Use a Geração de fotogramas acima para ligar ou desligar a geração.",
	CONFIG_DISABLE_HDR_EXPOSURE: "Desativar HDR",
	CONFIG_DISABLE_HDR_EXPOSURE_DESC: "O HDR não está disponível nesta versão. Esta definição obrigatória mantém ativo o caminho SDR estável.",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY: "Gamescope WSI (Reiniciar)",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_DESC: "Pode reduzir artefactos de movimento coloridos ou pixelizados pela apresentação do Gamescope. Opcional com redimensionamento e geração de fotogramas; ative apenas se necessário.",
	CONFIG_GAMESCOPE_WSI_COMPATIBILITY_WARNING: "Só em arranques de host de 64 bits compatíveis. Deixe desligado se não precisar; pode reduzir o desempenho.",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY: "Imagens de swapchain do jogo (Reiniciar)",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_DESC: "Pode corrigir falhas no arranque com geração de fotogramas ao manter o mínimo de imagens de swapchain pedido pelo jogo. Use apenas nos jogos afetados.",
	CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_WARNING: "Os fotogramas gerados podem ser ignorados quando o compositor não tem uma imagem livre, o que pode reduzir a fluidez ou o desempenho sob pressão.",
	FRAME_GENERATION_PROVISIONED: "Ativar Frame-gen (Reiniciar)",
	FRAME_GENERATION_PROVISIONED_DESC: "Ative antes de iniciar o jogo para carregar a geração de fotogramas; desative se usar apenas Escalonamento ou Shaders.",
	FIXED_MULTIPLIER: "Multiplicador fixo",
	FIXED_MULTIPLIER_DESC: "2x–5x define uma proporção de saída fixa; 5x custa mais e destina-se a ecrãs de alta taxa de atualização. 0x pausa a geração sem libertar recursos.",
	CONFIG_ALLOW_FP16: "Permitir FP16 (Reiniciar)",
	CONFIG_ALLOW_FP16_DESC: "Definição global do renderizador: aplica-se a todos os perfis e não pode ser alterada por jogo. Melhora o desempenho em AMD; desative para GPUs NVIDIA mais antigas. Reinicie o jogo após alterar.",
	CONFIG_GPU: "GPU (Reiniciar)",
	CONFIG_GPU_DESC: "Nome opcional da GPU, ID fornecedor:dispositivo ou ID do barramento PCI. Reinicie o jogo após a alteração.",
	CONFIG_ACTIVE_IN: "Processos correspondentes",
	CONFIG_ACTIVE_IN_DESC: "Nomes de processos separados por vírgulas. A captura do jogo preenche estes campos; edite só para adicionar um alias de lançador ou emulador.",
	CONFIG_MANUAL_OVERRIDES_TITLE: "Substituições manuais",
	INSTALL_REMOVE_RENDERER: "Remover o GFG Engine",
	INSTALL_RENDERER: "Instalar o GFG Engine",
	FLATPAK_EXTENSION_UPDATED: "Extensão Flatpak atualizada",
	FLATPAK_EXTENSION_FAILED: "Falha na extensão Flatpak",
	FLATPAK_EXTENSION_ACTION_FAILED: "Não foi possível",
	FLATPAK_RUNTIME_EXTENSION_UPDATED: "extensão de ambiente atualizada",
	FLATPAK_RUNTIME_EXTENSION: "extensão de ambiente",
	FLATPAK_APPLICATION_UPDATED: "Aplicação Flatpak atualizada",
	FLATPAK_UPDATED: "atualizada",
	FLATPAK_PREPARE_APPLICATION: "Preparar uma aplicação",
	FLATPAK_PREPARE_APPLICATION_DESC: "Instale a extensão correspondente e prepare a aplicação. Heroic/Lutris precisam de um wrapper por jogo; os emuladores são preparados para toda a aplicação. Consulte o guia de lançadores.",
	FLATPAK_INSTALL_ACTION: "instalar",
	FLATPAK_UNINSTALL_ACTION: "desinstalar",
	FLATPAK_APPLICATION_ACTION_FAILED: "Não foi possível atualizar",
	PROFILE_UNKNOWN_ERROR: "Erro desconhecido",
	PROFILE_LOAD_FAILED: "Falha ao carregar os perfis",
	PROFILE_LOAD_ERROR: "Erro ao carregar os perfis",
	PROFILE_SWITCHED: "Perfil alterado",
	PROFILE_SWITCHED_DESC: "Perfil alterado para:",
	PROFILE_SWITCH_FAILED: "Falha ao alterar o perfil",
	PROFILE_SWITCH_ERROR: "Erro ao alterar o perfil",
	PROFILE_DELETED: "Perfil eliminado",
	PROFILE_DELETED_DESC: "Perfil eliminado:",
	PROFILE_DELETE_FAILED: "Falha ao eliminar o perfil",
	PROFILE_DELETE_ERROR: "Erro ao eliminar o perfil",
	PROFILE_RENAMED: "Nome do perfil alterado",
	PROFILE_RENAMED_DESC: "Nome do perfil alterado para:",
	PROFILE_RENAME_FAILED: "Falha ao mudar o nome do perfil",
	PROFILE_RENAME_ERROR: "Erro ao mudar o nome do perfil",
	PROFILE_UPDATE_CONFIG_FAILED: "Falha ao atualizar a configuração do perfil",
	PROFILE_UPDATE_CONFIG_ERROR: "Erro ao atualizar a configuração do perfil",
	USAGE_MAKO_CONFIG_NOTE: "Este comando aplica o GFG Extreme apenas ao jogo iniciado com ele.",
	USAGE_ISOLATION_NOTE: "Não combine o GFG Extreme com outra ferramenta de geração de fotogramas ou redimensionamento no mesmo jogo.",
	ADVANCED_DETAILS_FAILED_LOAD_DATA: "Falha ao carregar os dados",
	STATUS_ENGINE_INSTALLED: "GFG Engine instalado",
	STATUS_ENGINE_NOT_INSTALLED: "GFG Engine não instalado",
	STATUS_ENGINE_INSTALLING: "A instalar o GFG Engine...",
	STATUS_ENGINE_UPDATING: "A atualizar o GFG Engine...",
	STATUS_ENGINE_REMOVING: "A remover o GFG Engine...",
	STATUS_ENGINE_REMOVED: "GFG Engine removido com sucesso!",
	STATUS_INSTALL_FAILED: "Falha na instalação:",
	STATUS_UNINSTALL_FAILED: "Falha na desinstalação:",
	STATUS_LOSSLESS_INSTALLED: "Lossless Scaling instalado",
	STATUS_LOSSLESS_NOT_INSTALLED: "Lossless Scaling não instalado — necessário para geração de fotogramas e LS1; o GFG Scaler continua disponível",
	TOAST_INSTALL_COMPLETE: "Instalação concluída",
	TOAST_INSTALL_COMPLETE_DESC: "Recomenda-se reiniciar o dispositivo.",
	TOAST_INSTALL_FAILED: "Falha na instalação",
	TOAST_UNKNOWN_ERROR: "Ocorreu um erro desconhecido",
	TOAST_UNINSTALL_COMPLETE: "GFG Engine removido",
	TOAST_UNINSTALL_COMPLETE_DESC: "Os ficheiros do GFG Engine foram removidos",
	TOAST_UNINSTALL_FAILED: "Falha na desinstalação",
	TOAST_CONFIG_UPDATE_FAILED: "Falha na atualização",
	TOAST_CONFIG_UPDATE_FAILED_DESC: "Falha ao atualizar a configuração",
	TOAST_CLIPBOARD_SUCCESS: "Copiado para a área de transferência!",
	TOAST_CLIPBOARD_SUCCESS_DESC: "Opção de arranque pronta para colar",
	TOAST_CLIPBOARD_FAILED: "Falha ao copiar",
	TOAST_CLIPBOARD_FAILED_DESC: "Não foi possível copiar para a área de transferência",
	FEATURE_UPSCALING_TAB: "Upscaling",
	LIVE_STATUS_TITLE: "Live Status",
	LIVE_STATUS_CONNECTED: "GFG Extreme is active",
	LIVE_STATUS_WAITING: "Waiting for GFG Extreme",
	LIVE_STATUS_WAITING_DESC: "Sem métricas em direto; o GFG Extreme pode funcionar. Alguns jogos não as comunicam. Verifique a geração de fotogramas ou o redimensionamento manualmente.",
	LIVE_STATUS_FG_INACTIVE: "On in settings, but not currently generating frames.",
	LIVE_STATUS_FG_MENU_SUSPENDED: "Frame Generation is disabled while a Steam or Decky menu is open.",
	LIVE_STATUS_OFF: "Off",
	LIVE_STATUS_SCALING_INACTIVE: "On in settings, but the game image is not being upscaled.",
	LIVE_STATUS_SCALING_MEMORY_LIMIT: "The requested render resolution exceeds this GPU's memory safety limit. Lower the in-game resolution.",
	LIVE_STATUS_SCALING_MEMORY_CONSTRAINED: "Requested {requested}×; limited to {effective}× by this GPU's memory safety limit.",
	LIVE_STATUS_SCALING_NO_HEADROOM: "Esta entrada já preenche o ecrã de destino. Experimente o modo de janela, reduza a resolução no jogo ou ative a Superamostragem de qualidade.",
	LIVE_STATUS_PENDING: "A saved change is still applying or needs a restart.",
	LIVE_STATUS_SUPERSAMPLING: "Quality Supersampling active.",
	LIVE_STATUS_SCALING_FALLBACK: "You selected {requested}; GFG Extreme is using {active} instead.",
	LIVE_STATUS_MODE: "Mode",
	LIVE_STATUS_FIXED_VALUE: "Fixed",
	LIVE_STATUS_ADAPTIVE_STYLE: "Style",
	LIVE_STATUS_STEADY_VALUE: "Steady",
	LIVE_STATUS_FRACTIONAL_VALUE: "Fractional",
	LIVE_STATUS_TARGET: "Target",
	LIVE_STATUS_MAX_MULTIPLIER: "Max factor",
	LIVE_STATUS_MULTIPLIER: "Factor",
	LIVE_STATUS_MODEL: "Model",
	LIVE_STATUS_NATIVE: "Native",
	LIVE_STATUS_LS1_PERFORMANCE: "LS1 Perf",
	LIVE_STATUS_ORIGINAL_RESOLUTION: "Input",
	LIVE_STATUS_RENDER_RESOLUTION: "Render",
	LIVE_STATUS_DISPLAY_RESOLUTION: "Display",
	LIVE_STATUS_SCALED_RESOLUTION: "Output",
	LIVE_STATUS_SCALING_UNAVAILABLE: "Unavailable for this running surface.",
	MODEL_WARNING_TITLE: "Aviso sobre os modelos do Lossless Scaling",
	MODEL_WARNING_DESCRIPTION: "Algumas funcionalidades do Lossless Scaling podem estar indisponíveis:",
	MODEL_WARNING_LS1: "O LS1 falhou na verificação de disponibilidade. O GFG Scaler é utilizado automaticamente se não for possível carregar o LS1.",
	MODEL_WARNING_LSFG: "Uma verificação de modelos LSFG falhou. A geração de fotogramas pode estar indisponível com a precisão selecionada.",
	MODEL_WARNING_UPDATE: "Aplique as atualizações disponíveis do GFG Extreme e Renderer e reinicie. Se persistir, confirme os ficheiros do Lossless Scaling e recolha diagnósticos.",
	MODEL_WARNING_CHECK_UPDATES: "Abrir versões do renderizador"
},
	steam_language_map: steam_language_map,
	template: template,
	uk: uk,
	zh: zh
};

// Generated from defaults/i18n by the normal frontend build.
const steamLanguageMap = languageBundle.steam_language_map;
const languageMetadata = languageBundle.language_metadata;
const translationSets = languageBundle;
const canonicalLanguageCodes = new Map(Object.keys(languageMetadata).map((language) => [language.toLowerCase(), language]));
const normalizeLanguage = (language) => {
    const normalized = (language || "en").trim().toLowerCase().replace(/_/g, "-");
    const mapped = steamLanguageMap[normalized] ?? normalized;
    // Steam has used both language names (such as `schinese`) and standard
    // locale identifiers (such as `pt-BR`) here. Prefer an exact advertised
    // locale before falling back to its base language so regional Portuguese
    // dictionaries remain distinct while ja-JP and zh-CN resolve normally.
    const exact = canonicalLanguageCodes.get(mapped.toLowerCase());
    if (exact)
        return exact;
    const base = mapped.split("-", 1)[0] || "en";
    return canonicalLanguageCodes.get(base) ?? base;
};
function getLangs() {
    const langs = Object.fromEntries(Object.entries(languageMetadata).map(([language, metadata]) => [language, { ...metadata }]));
    for (const [language, metadata] of Object.entries(langs)) {
        const strings = translationSets[language];
        if (strings && metadata.name) {
            metadata.strings = strings;
        }
    }
    return langs;
}
const LANGS = getLangs();
const getCurrentLanguage = () => {
    return normalizeLanguage(window.LocalizationManager?.m_rgLocalesToUse?.[0]);
};
/**
 * Translate a key to the current language
 *
 * @param key - Translation key
 * @param originalString - Original text (fallback)
 * @param replacements - Named values for placeholders such as {profile}
 * @returns Translated string or original text if translation not found
 *
 * @example
 * t('CONTENT_FPS_MULTIPLIER', 'FPS Multiplier')
 */
const t = (key, originalString, replacements = {}) => {
    const lang = getCurrentLanguage();
    const translated = lang === "en"
        ? originalString
        : LANGS[lang]?.strings?.[key] ?? originalString;
    return Object.entries(replacements).reduce((text, [name, value]) => text.split(`{${name}}`).join(String(value)), translated);
};

/**
 * Centralized toast notification utilities
 * Provides consistent success/error messaging patterns
 */
/**
 * Show a success toast notification
 */
function showSuccessToast(title, body) {
    toaster.toast({
        title,
        body,
    });
}
/**
 * Show an error toast notification
 */
function showErrorToast(title, body) {
    toaster.toast({
        title,
        body,
    });
}
/**
 * Standard success messages for common operations
 */
const ToastMessages = {
    get INSTALL_ERROR() {
        return {
            title: t("TOAST_INSTALL_FAILED", "Installation Failed"),
            body: t("TOAST_UNKNOWN_ERROR", "Unknown error occurred"),
        };
    },
    get UNINSTALL_SUCCESS() {
        return {
            title: t("TOAST_UNINSTALL_COMPLETE", "GFG Engine Removed"),
            body: t("TOAST_UNINSTALL_COMPLETE_DESC", "GFG Engine files have been removed"),
        };
    },
    get UNINSTALL_ERROR() {
        return {
            title: t("TOAST_UNINSTALL_FAILED", "Uninstallation Failed"),
            body: t("TOAST_UNKNOWN_ERROR", "Unknown error occurred"),
        };
    },
    get CONFIG_UPDATE_ERROR() {
        return {
            title: t("TOAST_CONFIG_UPDATE_FAILED", "Update Failed"),
            body: t("TOAST_CONFIG_UPDATE_FAILED_DESC", "Failed to update configuration"),
        };
    },
    get CLIPBOARD_SUCCESS() {
        return {
            title: t("TOAST_CLIPBOARD_SUCCESS", "Copied to Clipboard!"),
            body: t("TOAST_CLIPBOARD_SUCCESS_DESC", "Launch option ready to paste"),
        };
    },
    get CLIPBOARD_ERROR() {
        return {
            title: t("TOAST_CLIPBOARD_FAILED", "Copy Failed"),
            body: t("TOAST_CLIPBOARD_FAILED_DESC", "Unable to copy to clipboard"),
        };
    },
};
/**
 * Show installation error toast
 */
function showInstallErrorToast(error) {
    showErrorToast(ToastMessages.INSTALL_ERROR.title, error || ToastMessages.INSTALL_ERROR.body);
}
/**
 * Show uninstallation success toast
 */
function showUninstallSuccessToast() {
    showSuccessToast(ToastMessages.UNINSTALL_SUCCESS.title, ToastMessages.UNINSTALL_SUCCESS.body);
}
/**
 * Show uninstallation error toast
 */
function showUninstallErrorToast(error) {
    showErrorToast(ToastMessages.UNINSTALL_ERROR.title, error || ToastMessages.UNINSTALL_ERROR.body);
}
/**
 * Show clipboard error toast
 */
function showClipboardErrorToast() {
    showErrorToast(ToastMessages.CLIPBOARD_ERROR.title, ToastMessages.CLIPBOARD_ERROR.body);
}

function useInstallationStatus() {
    const [isInstalled, setIsInstalled] = SP_REACT.useState(false);
    const [installationStatus, setInstallationStatus] = SP_REACT.useState("");
    const [engineUpdateRequired, setEngineUpdateRequired] = SP_REACT.useState(false);
    const [hostArchitectureSupported, setHostArchitectureSupported] = SP_REACT.useState(true);
    const [installedEngineVersion, setInstalledEngineVersion] = SP_REACT.useState();
    const [expectedEngineVersion, setExpectedEngineVersion] = SP_REACT.useState();
    const checkInstallation = async () => {
        try {
            const status = await checkGFGInstalled();
            setIsInstalled(status.installed);
            setEngineUpdateRequired(Boolean(status.engine_update_required));
            setInstalledEngineVersion(status.installed_engine_version);
            setExpectedEngineVersion(status.expected_engine_version);
            setHostArchitectureSupported(status.host_architecture_supported !== false);
            if (status.installed) {
                setInstallationStatus(t("STATUS_ENGINE_INSTALLED", "GFG Engine installed"));
            }
            else if (status.host_architecture_supported === false && status.error) {
                setInstallationStatus(status.error);
            }
            else {
                setInstallationStatus(t("STATUS_ENGINE_NOT_INSTALLED", "GFG Engine not installed"));
            }
            return status.installed;
        }
        catch (error) {
            setInstallationStatus(t("STATUS_ENGINE_NOT_INSTALLED", "GFG Engine not installed"));
            setEngineUpdateRequired(false);
            // A transient RPC failure is not evidence that the native host is
            // unsupported. Only the backend's explicit compatibility result should
            // disable the installation action.
            setHostArchitectureSupported(true);
            setInstalledEngineVersion(undefined);
            setExpectedEngineVersion(undefined);
            return false;
        }
    };
    SP_REACT.useEffect(() => {
        checkInstallation();
    }, []);
    return {
        isInstalled,
        installationStatus,
        engineUpdateRequired,
        hostArchitectureSupported,
        installedEngineVersion,
        expectedEngineVersion,
        setIsInstalled,
        setInstallationStatus,
        checkInstallation,
    };
}
function useDllDetection() {
    const [dllDetected, setDllDetected] = SP_REACT.useState(false);
    const [dllDetectionStatus, setDllDetectionStatus] = SP_REACT.useState("");
    const checkDllDetection = async () => {
        try {
            const result = await checkLosslessScalingDll();
            setDllDetected(result.detected);
            if (result.detected) {
                setDllDetectionStatus(t("STATUS_LOSSLESS_INSTALLED", "Lossless Scaling installed"));
            }
            else {
                setDllDetectionStatus(t("STATUS_LOSSLESS_NOT_INSTALLED", "Lossless Scaling not installed — required for Frame Generation and LS1; GFG Scaler remains available"));
            }
        }
        catch (error) {
            setDllDetectionStatus(t("STATUS_LOSSLESS_NOT_INSTALLED", "Lossless Scaling not installed — required for Frame Generation and LS1; GFG Scaler remains available"));
        }
    };
    SP_REACT.useEffect(() => {
        checkDllDetection();
    }, []);
    return {
        dllDetected,
        dllDetectionStatus,
    };
}
function useRuntimeScalingStatus(profileName, enabled) {
    const [runtimeState, setRuntimeState] = SP_REACT.useState({
        ...EMPTY_RUNTIME_SCALING_UI_STATE,
    });
    SP_REACT.useEffect(() => {
        let active = true;
        const refresh = async () => {
            if (!enabled) {
                if (active) {
                    setRuntimeState({ ...EMPTY_RUNTIME_SCALING_UI_STATE });
                }
                return;
            }
            try {
                const status = await getRuntimeStatus(profileName);
                if (active) {
                    setRuntimeState(runtimeScalingUiState(status, profileName));
                }
            }
            catch {
                if (active) {
                    setRuntimeState({ ...EMPTY_RUNTIME_SCALING_UI_STATE });
                }
            }
        };
        let timeout;
        const poll = async () => {
            await refresh();
            if (active)
                timeout = setTimeout(poll, RUNTIME_STATUS_POLL_INTERVAL_MS);
        };
        void poll();
        return () => {
            active = false;
            if (timeout !== undefined)
                clearTimeout(timeout);
        };
    }, [enabled, profileName]);
    return runtimeState;
}
function useGFGConfig() {
    const [config, setConfig] = SP_REACT.useState(() => getDefaults());
    const [vkBasaltConfigPath, setVkBasaltConfigPath] = SP_REACT.useState("");
    const loadRequestId = SP_REACT.useRef(0);
    const loadGFGConfig = SP_REACT.useCallback(async (profileName) => {
        const requestId = ++loadRequestId.current;
        setVkBasaltConfigPath("");
        try {
            const result = profileName
                ? await getProfileConfig(profileName)
                : await getGFGConfig();
            if (requestId !== loadRequestId.current)
                return;
            if (result.success && result.config) {
                // Older installed configurations (or a backend that has not yet been
                // reloaded) may not contain fields introduced by a newer frontend.
                // Preserve the generated defaults for any fields missing from the
                // response so an in-place plugin update never renders undefined values.
                setConfig({ ...getDefaults(), ...result.config });
                setVkBasaltConfigPath(result.vkbasalt_config_path || "");
            }
            else {
                console.log("GFG Engine config not available, using defaults:", result.error);
                setConfig(getDefaults());
                setVkBasaltConfigPath("");
            }
        }
        catch (error) {
            if (requestId !== loadRequestId.current)
                return;
            console.error("Error loading GFG Engine config:", error);
            setConfig(getDefaults());
            setVkBasaltConfigPath("");
        }
    }, []);
    const updateConfig = SP_REACT.useCallback(async (newConfig) => {
        try {
            const normalizedConfig = { ...getDefaults(), ...newConfig };
            const result = await updateGFGConfigFromObject(normalizedConfig);
            if (result.success) {
                setConfig(normalizedConfig);
            }
            else {
                showErrorToast(ToastMessages.CONFIG_UPDATE_ERROR.title, result.error || ToastMessages.CONFIG_UPDATE_ERROR.body);
            }
            return result;
        }
        catch (error) {
            showErrorToast(ToastMessages.CONFIG_UPDATE_ERROR.title, String(error));
            return configFailureResult(String(error));
        }
    }, []);
    const updateField = SP_REACT.useCallback(async (fieldName, value) => {
        const newConfig = { ...config, [fieldName]: value };
        return updateConfig(newConfig);
    }, [config, updateConfig]);
    const applyConfigPatch = SP_REACT.useCallback((changes) => {
        setConfig((currentConfig) => ({ ...currentConfig, ...changes }));
    }, []);
    const replaceConfig = SP_REACT.useCallback((canonicalConfig) => {
        setConfig({ ...getDefaults(), ...canonicalConfig });
    }, []);
    SP_REACT.useEffect(() => {
        loadGFGConfig();
    }, []);
    return {
        config,
        vkBasaltConfigPath,
        setConfig,
        applyConfigPatch,
        replaceConfig,
        loadGFGConfig,
        updateConfig,
        updateField,
    };
}

function useProfileManagement() {
    const [profiles, setProfiles] = SP_REACT.useState([]);
    const [currentProfile, setCurrentProfileState] = SP_REACT.useState(DEFAULT_PROFILE_NAME);
    const [isLoading, setIsLoading] = SP_REACT.useState(false);
    // Load profiles on hook initialization
    const loadProfiles = SP_REACT.useCallback(async () => {
        try {
            const result = await getProfiles();
            if (result.success && result.profiles) {
                setProfiles(result.profiles);
                const resolvedProfile = result.current_profile &&
                    result.profiles.includes(result.current_profile)
                    ? result.current_profile
                    : result.profiles.includes(DEFAULT_PROFILE_NAME)
                        ? DEFAULT_PROFILE_NAME
                        : result.profiles[0];
                if (resolvedProfile)
                    setCurrentProfileState(resolvedProfile);
                return result;
            }
            else {
                console.error("Failed to load profiles:", result.error);
                showErrorToast(t("PROFILE_LOAD_FAILED", "Failed to load profiles"), result.error || t("PROFILE_UNKNOWN_ERROR", "Unknown error"));
                return result;
            }
        }
        catch (error) {
            console.error("Error loading profiles:", error);
            showErrorToast(t("PROFILE_LOAD_ERROR", "Error loading profiles"), String(error));
            return profilesFailureResult(String(error));
        }
    }, []);
    // Delete a profile
    const handleDeleteProfile = SP_REACT.useCallback(async (profileName) => {
        if (profileName === DEFAULT_PROFILE_NAME) {
            showErrorToast(t("PROFILE_CANNOT_DELETE_TITLE", "Cannot delete default profile"), t("PROFILE_CANNOT_DELETE_MSG", "The default profile cannot be deleted"));
            return profileFailureResult(t("PROFILE_CANNOT_DELETE_TITLE", "Cannot delete default profile"));
        }
        setIsLoading(true);
        try {
            const result = await deleteProfile(profileName);
            if (result.success) {
                showSuccessToast(t("PROFILE_DELETED", "Profile deleted"), `${t("PROFILE_DELETED_DESC", "Deleted profile:")} ${profileName}`);
                await loadProfiles();
                // If we deleted the current profile, it should have switched to default
                if (currentProfile === profileName) {
                    setCurrentProfileState(DEFAULT_PROFILE_NAME);
                }
                return result;
            }
            else {
                console.error("Failed to delete profile:", result.error);
                showErrorToast(t("PROFILE_DELETE_FAILED", "Failed to delete profile"), result.error || t("PROFILE_UNKNOWN_ERROR", "Unknown error"));
                return result;
            }
        }
        catch (error) {
            console.error("Error deleting profile:", error);
            showErrorToast(t("PROFILE_DELETE_ERROR", "Error deleting profile"), String(error));
            return profileFailureResult(String(error));
        }
        finally {
            setIsLoading(false);
        }
    }, [currentProfile, loadProfiles]);
    // Rename a profile
    const handleRenameProfile = SP_REACT.useCallback(async (oldName, newName) => {
        if (oldName === DEFAULT_PROFILE_NAME) {
            showErrorToast(t("PROFILE_CANNOT_RENAME_TITLE", "Cannot rename default profile"), t("PROFILE_CANNOT_RENAME_MSG", "The default profile cannot be renamed"));
            return profileFailureResult(t("PROFILE_CANNOT_RENAME_TITLE", "Cannot rename default profile"));
        }
        setIsLoading(true);
        try {
            const result = await renameProfile(oldName, newName);
            if (result.success) {
                // Use the normalized name returned from backend (spaces converted to dashes)
                const actualNewName = result.profile_name || newName;
                showSuccessToast(t("PROFILE_RENAMED", "Profile renamed"), `${t("PROFILE_RENAMED_DESC", "Renamed profile to:")} ${actualNewName}`);
                await loadProfiles();
                // Update current profile if it was renamed
                if (currentProfile === oldName) {
                    setCurrentProfileState(actualNewName);
                }
                return result;
            }
            else {
                console.error("Failed to rename profile:", result.error);
                showErrorToast(t("PROFILE_RENAME_FAILED", "Failed to rename profile"), result.error || t("PROFILE_UNKNOWN_ERROR", "Unknown error"));
                return result;
            }
        }
        catch (error) {
            console.error("Error renaming profile:", error);
            showErrorToast(t("PROFILE_RENAME_ERROR", "Error renaming profile"), String(error));
            return profileFailureResult(String(error));
        }
        finally {
            setIsLoading(false);
        }
    }, [currentProfile, loadProfiles]);
    // Set the current active profile
    const handleSetCurrentProfile = SP_REACT.useCallback(async (profileName) => {
        setIsLoading(true);
        try {
            const result = await setCurrentProfile(profileName);
            if (result.success) {
                setCurrentProfileState(profileName);
                showSuccessToast(t("PROFILE_SWITCHED", "Profile switched"), `${t("PROFILE_SWITCHED_DESC", "Switched to profile:")} ${profileName}`);
                return result;
            }
            else {
                console.error("Failed to switch profile:", result.error);
                showErrorToast(t("PROFILE_SWITCH_FAILED", "Failed to switch profile"), result.error || t("PROFILE_UNKNOWN_ERROR", "Unknown error"));
                return result;
            }
        }
        catch (error) {
            console.error("Error switching profile:", error);
            showErrorToast(t("PROFILE_SWITCH_ERROR", "Error switching profile"), String(error));
            return profileFailureResult(String(error));
        }
        finally {
            setIsLoading(false);
        }
    }, []);
    const handleSyncCurrentProfile = SP_REACT.useCallback(async (appId) => {
        try {
            const result = await syncCurrentProfile(appId || "");
            if (result.success && result.profile_name) {
                setCurrentProfileState(result.profile_name);
            }
            else if (!result.success) {
                console.error("Failed to synchronise current profile:", result.error);
            }
            return result;
        }
        catch (error) {
            console.error("Error synchronising current profile:", error);
            return profileFailureResult(String(error), { changed: false });
        }
    }, []);
    // Update configuration for a specific profile
    const handleUpdateProfileConfig = SP_REACT.useCallback(async (profileName, config) => {
        setIsLoading(true);
        try {
            const result = await updateProfileConfig(profileName, config);
            if (result.success) {
                return result;
            }
            else {
                console.error("Failed to update profile config:", result.error);
                showErrorToast(t("PROFILE_UPDATE_CONFIG_FAILED", "Failed to update profile config"), result.error || t("PROFILE_UNKNOWN_ERROR", "Unknown error"));
                return result;
            }
        }
        catch (error) {
            console.error("Error updating profile config:", error);
            showErrorToast(t("PROFILE_UPDATE_CONFIG_ERROR", "Error updating profile config"), String(error));
            return configFailureResult(String(error));
        }
        finally {
            setIsLoading(false);
        }
    }, [currentProfile]);
    const handleUpdateProfileConfigFields = SP_REACT.useCallback(async (profileName, changes) => {
        setIsLoading(true);
        try {
            const result = await updateProfileConfigFields(profileName, changes);
            if (!result.success) {
                console.error("Failed to update profile fields:", result.error);
                showErrorToast(t("PROFILE_UPDATE_CONFIG_FAILED", "Failed to update profile config"), result.error || t("PROFILE_UNKNOWN_ERROR", "Unknown error"));
            }
            return result;
        }
        catch (error) {
            console.error("Error updating profile fields:", error);
            showErrorToast(t("PROFILE_UPDATE_CONFIG_ERROR", "Error updating profile config"), String(error));
            return configFailureResult(String(error));
        }
        finally {
            setIsLoading(false);
        }
    }, []);
    // Initialize profiles on mount
    SP_REACT.useEffect(() => {
        loadProfiles();
    }, [loadProfiles]);
    return {
        profiles,
        currentProfile,
        isLoading,
        loadProfiles,
        deleteProfile: handleDeleteProfile,
        renameProfile: handleRenameProfile,
        setCurrentProfile: handleSetCurrentProfile,
        syncCurrentProfile: handleSyncCurrentProfile,
        updateProfileConfig: handleUpdateProfileConfig,
        updateProfileConfigFields: handleUpdateProfileConfigFields,
    };
}

function useInstallationActions() {
    const [isInstalling, setIsInstalling] = SP_REACT.useState(false);
    const [isUninstalling, setIsUninstalling] = SP_REACT.useState(false);
    const [isInstallCompletionVisible, setIsInstallCompletionVisible] = SP_REACT.useState(false);
    const handleInstall = async (setIsInstalled, setInstallationStatus, reloadConfig, operation = "install") => {
        setIsInstalling(true);
        setInstallationStatus(operation === "update"
            ? t("STATUS_ENGINE_UPDATING", "Updating GFG Engine...")
            : t("STATUS_ENGINE_INSTALLING", "Installing GFG Engine..."));
        try {
            const result = await installGFG();
            if (result.success) {
                setInstallationStatus(result.message ||
                    t("STATUS_ENGINE_INSTALLED", "GFG Engine installed"));
                setIsInstallCompletionVisible(true);
                const completionDelay = new Promise((resolve) => {
                    setTimeout(resolve, MAKO_INSTALL_COMPLETION_DURATION_MS);
                });
                if (reloadConfig) {
                    await Promise.all([reloadConfig(), completionDelay]);
                }
                else {
                    await completionDelay;
                }
                setIsInstallCompletionVisible(false);
                setIsInstalled(true);
            }
            else {
                setInstallationStatus(`${t("STATUS_INSTALL_FAILED", "Installation failed:")} ${result.error}`);
                showInstallErrorToast(result.error);
            }
        }
        catch (error) {
            setInstallationStatus(`${t("STATUS_INSTALL_FAILED", "Installation failed:")} ${error}`);
            showInstallErrorToast(String(error));
        }
        finally {
            setIsInstallCompletionVisible(false);
            setIsInstalling(false);
        }
    };
    const handleUninstall = async (setIsInstalled, setInstallationStatus) => {
        setIsUninstalling(true);
        setInstallationStatus(t("STATUS_ENGINE_REMOVING", "Removing GFG Engine..."));
        try {
            const result = await uninstallGFG();
            if (result.success) {
                setIsInstalled(false);
                setInstallationStatus(t("STATUS_ENGINE_REMOVED", "GFG Engine removed successfully!"));
                showUninstallSuccessToast();
            }
            else {
                setInstallationStatus(`${t("STATUS_UNINSTALL_FAILED", "Uninstallation failed:")} ${result.error}`);
                showUninstallErrorToast(result.error);
            }
        }
        catch (error) {
            setInstallationStatus(`${t("STATUS_UNINSTALL_FAILED", "Uninstallation failed:")} ${error}`);
            showUninstallErrorToast(String(error));
        }
        finally {
            setIsUninstalling(false);
        }
    };
    return {
        isInstalling,
        isUninstalling,
        isInstallCompletionVisible,
        handleInstall,
        handleUninstall,
    };
}

const PROFILE_SYNC_INTERVAL_MS = 2000;
/**
 * Coordinates the profile being edited with Decky's running-game state.
 *
 * A live game locks the editor to its resolved profile. After that game exits,
 * the editor returns to Default exactly once; later offline profile selections
 * remain untouched until another game starts.
 */
function useProfileSession({ isInstalled, loadProfileConfig, syncCurrentProfile, }) {
    const [mainRunningApp, setMainRunningApp] = SP_REACT.useState(undefined);
    const [editingProfile, setEditingProfile] = SP_REACT.useState(DEFAULT_PROFILE_NAME);
    const editingProfileRef = SP_REACT.useRef(DEFAULT_PROFILE_NAME);
    const gameWasRunningRef = SP_REACT.useRef(false);
    SP_REACT.useEffect(() => {
        if (isInstalled) {
            void loadProfileConfig(editingProfileRef.current);
        }
    }, [isInstalled, loadProfileConfig]);
    SP_REACT.useEffect(() => {
        let cancelled = false;
        let syncInFlight = false;
        const checkRunningApp = async () => {
            const runningApp = DFL.Router.MainRunningApp;
            if (syncInFlight)
                return;
            syncInFlight = true;
            try {
                const result = await syncCurrentProfile(runningApp ? String(runningApp.appid) : undefined);
                if (!cancelled && result.success) {
                    const gameIsRunning = Boolean(result.game_running && runningApp);
                    const nextEditingProfile = gameIsRunning
                        ? result.profile_name || DEFAULT_PROFILE_NAME
                        : gameWasRunningRef.current
                            ? DEFAULT_PROFILE_NAME
                            : undefined;
                    const editingProfileChanged = Boolean(nextEditingProfile &&
                        nextEditingProfile !== editingProfileRef.current);
                    // On exit, reset the editor before unlocking profile controls. On
                    // launch, lock controls before following the detected game profile.
                    if (!gameIsRunning && editingProfileChanged && nextEditingProfile) {
                        editingProfileRef.current = nextEditingProfile;
                        setEditingProfile(nextEditingProfile);
                    }
                    setMainRunningApp(gameIsRunning ? runningApp : undefined);
                    gameWasRunningRef.current = gameIsRunning;
                    if (gameIsRunning && editingProfileChanged && nextEditingProfile) {
                        editingProfileRef.current = nextEditingProfile;
                        setEditingProfile(nextEditingProfile);
                    }
                    if (editingProfileChanged && nextEditingProfile) {
                        await loadProfileConfig(nextEditingProfile);
                    }
                }
            }
            finally {
                syncInFlight = false;
            }
        };
        void checkRunningApp();
        const interval = setInterval(() => void checkRunningApp(), PROFILE_SYNC_INTERVAL_MS);
        return () => {
            cancelled = true;
            clearInterval(interval);
        };
    }, [loadProfileConfig, syncCurrentProfile]);
    const selectEditingProfile = SP_REACT.useCallback((profileName) => {
        editingProfileRef.current = profileName;
        setEditingProfile(profileName);
    }, []);
    const getEditingProfile = SP_REACT.useCallback(() => editingProfileRef.current, []);
    return {
        mainRunningApp,
        editingProfile,
        selectEditingProfile,
        getEditingProfile,
    };
}

const PROFILE_CONFIG_SAVE_DELAY_MS = 250;
const BASE_FPS_CAP_SAVE_DELAY_MS = 1000;
function saveDelayForChanges(changes) {
    const keys = Object.keys(changes);
    const baseFpsCapDrag = keys.includes("base_fps_cap") &&
        keys.every((key) => key === "base_fps_cap" ||
            (key === "dynamic_cadence_recovery" &&
                changes.dynamic_cadence_recovery === false));
    return baseFpsCapDrag
        ? BASE_FPS_CAP_SAVE_DELAY_MS
        : PROFILE_CONFIG_SAVE_DELAY_MS;
}
/**
 * Creates one bounded persistence boundary for every profile control.
 *
 * UI state updates optimistically, while rapid edits merge by profile and only
 * one backend request can be active at a time. Each callback retains the
 * profile selected in the render that created it, so queued writes cannot move
 * to a newly selected profile. Pending writes flush when Decky unmounts the
 * quick-access panel.
 */
function useProfileConfigWriter({ editingProfile, getEditingProfile, updateProfileConfigFields, loadProfileConfig, applyConfigPatch, replaceConfig, }) {
    const pendingWrites = SP_REACT.useRef(new Map());
    const pendingOrder = SP_REACT.useRef([]);
    const saveTimer = SP_REACT.useRef(null);
    const writeInFlight = SP_REACT.useRef(false);
    const flushImmediately = SP_REACT.useRef(false);
    const mounted = SP_REACT.useRef(true);
    const flushNextWriteRef = SP_REACT.useRef(() => undefined);
    const scheduleWrite = SP_REACT.useCallback((delay = PROFILE_CONFIG_SAVE_DELAY_MS) => {
        if (saveTimer.current !== null)
            clearTimeout(saveTimer.current);
        saveTimer.current = setTimeout(() => {
            saveTimer.current = null;
            flushNextWriteRef.current();
        }, delay);
    }, []);
    const reconcileProfile = SP_REACT.useCallback(async (profileName) => {
        if (mounted.current && getEditingProfile() === profileName) {
            try {
                await loadProfileConfig(profileName);
            }
            catch {
                return;
            }
            const newerChanges = pendingWrites.current.get(profileName)?.changes;
            if (newerChanges && getEditingProfile() === profileName) {
                applyConfigPatch(newerChanges);
            }
        }
    }, [applyConfigPatch, getEditingProfile, loadProfileConfig]);
    const flushNextWrite = SP_REACT.useCallback(async () => {
        if (writeInFlight.current)
            return;
        const profileName = pendingOrder.current.shift();
        if (!profileName) {
            flushImmediately.current = false;
            return;
        }
        const pendingWrite = pendingWrites.current.get(profileName);
        if (!pendingWrite) {
            flushNextWriteRef.current();
            return;
        }
        pendingWrites.current.delete(profileName);
        writeInFlight.current = true;
        try {
            const result = await updateProfileConfigFields(profileName, pendingWrite.changes);
            if (mounted.current && getEditingProfile() === profileName) {
                if (result.success && result.config) {
                    const newerChanges = pendingWrites.current.get(profileName)?.changes;
                    replaceConfig({
                        ...result.config,
                        ...(newerChanges || {}),
                    });
                }
                else {
                    await reconcileProfile(profileName);
                }
            }
        }
        catch {
            await reconcileProfile(profileName);
        }
        finally {
            writeInFlight.current = false;
            if (pendingOrder.current.length > 0) {
                if (flushImmediately.current || !mounted.current) {
                    flushNextWriteRef.current();
                }
                else {
                    const nextProfile = pendingOrder.current[0];
                    scheduleWrite(pendingWrites.current.get(nextProfile)?.delayMs ??
                        PROFILE_CONFIG_SAVE_DELAY_MS);
                }
            }
            else {
                flushImmediately.current = false;
            }
        }
    }, [
        getEditingProfile,
        reconcileProfile,
        replaceConfig,
        scheduleWrite,
        updateProfileConfigFields,
    ]);
    flushNextWriteRef.current = () => void flushNextWrite();
    SP_REACT.useEffect(() => {
        mounted.current = true;
        return () => {
            mounted.current = false;
            flushImmediately.current = true;
            if (saveTimer.current !== null) {
                clearTimeout(saveTimer.current);
                saveTimer.current = null;
            }
            flushNextWriteRef.current();
        };
    }, []);
    const saveConfigChanges = SP_REACT.useCallback((changes) => {
        const targetProfile = editingProfile;
        const ownedChanges = { ...changes };
        if (getEditingProfile() === targetProfile) {
            applyConfigPatch(ownedChanges);
        }
        let pendingWrite = pendingWrites.current.get(targetProfile);
        const requestedDelay = saveDelayForChanges(ownedChanges);
        if (!pendingWrite) {
            pendingWrite = { changes: {}, delayMs: requestedDelay };
            pendingWrites.current.set(targetProfile, pendingWrite);
            pendingOrder.current.push(targetProfile);
        }
        else {
            pendingWrite.delayMs = Math.min(pendingWrite.delayMs, requestedDelay);
        }
        pendingWrite.changes = {
            ...pendingWrite.changes,
            ...ownedChanges,
        };
        scheduleWrite(pendingWrite.delayMs);
        return Promise.resolve();
    }, [applyConfigPatch, editingProfile, getEditingProfile, scheduleWrite]);
    const saveConfigField = SP_REACT.useCallback(async (fieldName, value) => {
        return saveConfigChanges({
            [fieldName]: value,
        });
    }, [saveConfigChanges]);
    return { saveConfigChanges, saveConfigField };
}

// THIS FILE IS AUTO GENERATED
function FiAlertCircle (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24","fill":"none","stroke":"currentColor","strokeWidth":"2","strokeLinecap":"round","strokeLinejoin":"round"},"child":[{"tag":"circle","attr":{"cx":"12","cy":"12","r":"10"},"child":[]},{"tag":"line","attr":{"x1":"12","y1":"8","x2":"12","y2":"12"},"child":[]},{"tag":"line","attr":{"x1":"12","y1":"16","x2":"12.01","y2":"16"},"child":[]}]})(props);
}function FiAlertTriangle (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24","fill":"none","stroke":"currentColor","strokeWidth":"2","strokeLinecap":"round","strokeLinejoin":"round"},"child":[{"tag":"path","attr":{"d":"M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"},"child":[]},{"tag":"line","attr":{"x1":"12","y1":"9","x2":"12","y2":"13"},"child":[]},{"tag":"line","attr":{"x1":"12","y1":"17","x2":"12.01","y2":"17"},"child":[]}]})(props);
}function FiCheckCircle (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24","fill":"none","stroke":"currentColor","strokeWidth":"2","strokeLinecap":"round","strokeLinejoin":"round"},"child":[{"tag":"path","attr":{"d":"M22 11.08V12a10 10 0 1 1-5.93-9.14"},"child":[]},{"tag":"polyline","attr":{"points":"22 4 12 14.01 9 11.01"},"child":[]}]})(props);
}function FiFastForward (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24","fill":"none","stroke":"currentColor","strokeWidth":"2","strokeLinecap":"round","strokeLinejoin":"round"},"child":[{"tag":"polygon","attr":{"points":"13 19 22 12 13 5 13 19"},"child":[]},{"tag":"polygon","attr":{"points":"2 19 11 12 2 5 2 19"},"child":[]}]})(props);
}function FiInfo (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24","fill":"none","stroke":"currentColor","strokeWidth":"2","strokeLinecap":"round","strokeLinejoin":"round"},"child":[{"tag":"circle","attr":{"cx":"12","cy":"12","r":"10"},"child":[]},{"tag":"line","attr":{"x1":"12","y1":"16","x2":"12","y2":"12"},"child":[]},{"tag":"line","attr":{"x1":"12","y1":"8","x2":"12.01","y2":"8"},"child":[]}]})(props);
}function FiLayers (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24","fill":"none","stroke":"currentColor","strokeWidth":"2","strokeLinecap":"round","strokeLinejoin":"round"},"child":[{"tag":"polygon","attr":{"points":"12 2 2 7 12 12 22 7 12 2"},"child":[]},{"tag":"polyline","attr":{"points":"2 17 12 22 22 17"},"child":[]},{"tag":"polyline","attr":{"points":"2 12 12 17 22 12"},"child":[]}]})(props);
}function FiLink (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24","fill":"none","stroke":"currentColor","strokeWidth":"2","strokeLinecap":"round","strokeLinejoin":"round"},"child":[{"tag":"path","attr":{"d":"M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"},"child":[]},{"tag":"path","attr":{"d":"M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"},"child":[]}]})(props);
}function FiMaximize2 (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24","fill":"none","stroke":"currentColor","strokeWidth":"2","strokeLinecap":"round","strokeLinejoin":"round"},"child":[{"tag":"polyline","attr":{"points":"15 3 21 3 21 9"},"child":[]},{"tag":"polyline","attr":{"points":"9 21 3 21 3 15"},"child":[]},{"tag":"line","attr":{"x1":"21","y1":"3","x2":"14","y2":"10"},"child":[]},{"tag":"line","attr":{"x1":"3","y1":"21","x2":"10","y2":"14"},"child":[]}]})(props);
}

function StatusRow$1({ ready, text, separated = false }) {
    const accent = ready ? "#ff513d" : "#ff745f";
    const Icon = ready ? FiCheckCircle : FiAlertCircle;
    return (window.SP_REACT.createElement("div", { style: {
            minHeight: "38px",
            padding: "7px 10px",
            boxSizing: "border-box",
            display: "flex",
            alignItems: "center",
            gap: "9px",
            borderTop: separated ? "1px solid rgba(255, 81, 61, 0.14)" : "none",
            color: "#f5f7fa",
            fontSize: "13px",
            fontWeight: "500",
            lineHeight: "1.3"
        } },
        window.SP_REACT.createElement(Icon, { "aria-hidden": "true", style: {
                width: "16px",
                height: "16px",
                flex: "0 0 16px",
                color: accent
            } }),
        window.SP_REACT.createElement("span", null, text)));
}
function StatusDisplay({ dllDetected, dllDetectionStatus, isInstalled, installationStatus, topMargin = "0" }) {
    return (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { style: {
                marginTop: topMargin,
                marginBottom: "0",
                width: "100%",
                boxSizing: "border-box",
                overflow: "hidden",
                background: "linear-gradient(135deg, rgba(14, 15, 19, 0.72), rgba(37, 19, 21, 0.46))",
                border: "1px solid rgba(255, 82, 62, 0.34)",
                borderRadius: "6px",
                boxShadow: "inset 0 1px 0 rgba(255, 255, 255, 0.035), 0 2px 5px rgba(0, 0, 0, 0.16)"
            } },
            window.SP_REACT.createElement(StatusRow$1, { ready: dllDetected, text: dllDetectionStatus }),
            window.SP_REACT.createElement(StatusRow$1, { ready: isInstalled, text: installationStatus, separated: true }))));
}

// THIS FILE IS AUTO GENERATED
function FaCheck (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M173.898 439.404l-166.4-166.4c-9.997-9.997-9.997-26.206 0-36.204l36.203-36.204c9.997-9.998 26.207-9.998 36.204 0L192 312.69 432.095 72.596c9.997-9.997 26.207-9.997 36.204 0l36.203 36.204c9.997 9.997 9.997 26.206 0 36.204l-294.4 294.401c-9.998 9.997-26.207 9.997-36.204-.001z"},"child":[]}]})(props);
}function FaClipboard (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 384 512"},"child":[{"tag":"path","attr":{"d":"M384 112v352c0 26.51-21.49 48-48 48H48c-26.51 0-48-21.49-48-48V112c0-26.51 21.49-48 48-48h80c0-35.29 28.71-64 64-64s64 28.71 64 64h80c26.51 0 48 21.49 48 48zM192 40c-13.255 0-24 10.745-24 24s10.745 24 24 24 24-10.745 24-24-10.745-24-24-24m96 114v-20a6 6 0 0 0-6-6H102a6 6 0 0 0-6 6v20a6 6 0 0 0 6 6h180a6 6 0 0 0 6-6z"},"child":[]}]})(props);
}function FaCog (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M487.4 315.7l-42.6-24.6c4.3-23.2 4.3-47 0-70.2l42.6-24.6c4.9-2.8 7.1-8.6 5.5-14-11.1-35.6-30-67.8-54.7-94.6-3.8-4.1-10-5.1-14.8-2.3L380.8 110c-17.9-15.4-38.5-27.3-60.8-35.1V25.8c0-5.6-3.9-10.5-9.4-11.7-36.7-8.2-74.3-7.8-109.2 0-5.5 1.2-9.4 6.1-9.4 11.7V75c-22.2 7.9-42.8 19.8-60.8 35.1L88.7 85.5c-4.9-2.8-11-1.9-14.8 2.3-24.7 26.7-43.6 58.9-54.7 94.6-1.7 5.4.6 11.2 5.5 14L67.3 221c-4.3 23.2-4.3 47 0 70.2l-42.6 24.6c-4.9 2.8-7.1 8.6-5.5 14 11.1 35.6 30 67.8 54.7 94.6 3.8 4.1 10 5.1 14.8 2.3l42.6-24.6c17.9 15.4 38.5 27.3 60.8 35.1v49.2c0 5.6 3.9 10.5 9.4 11.7 36.7 8.2 74.3 7.8 109.2 0 5.5-1.2 9.4-6.1 9.4-11.7v-49.2c22.2-7.9 42.8-19.8 60.8-35.1l42.6 24.6c4.9 2.8 11 1.9 14.8-2.3 24.7-26.7 43.6-58.9 54.7-94.6 1.5-5.5-.7-11.3-5.6-14.1zM256 336c-44.1 0-80-35.9-80-80s35.9-80 80-80 80 35.9 80 80-35.9 80-80 80z"},"child":[]}]})(props);
}function FaDownload (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M216 0h80c13.3 0 24 10.7 24 24v168h87.7c17.8 0 26.7 21.5 14.1 34.1L269.7 378.3c-7.5 7.5-19.8 7.5-27.3 0L90.1 226.1c-12.6-12.6-3.7-34.1 14.1-34.1H192V24c0-13.3 10.7-24 24-24zm296 376v112c0 13.3-10.7 24-24 24H24c-13.3 0-24-10.7-24-24V376c0-13.3 10.7-24 24-24h146.7l49 49c20.1 20.1 52.5 20.1 72.6 0l49-49H488c13.3 0 24 10.7 24 24zm-124 88c0-11-9-20-20-20s-20 9-20 20 9 20 20 20 20-9 20-20zm64 0c0-11-9-20-20-20s-20 9-20 20 9 20 20 20 20-9 20-20z"},"child":[]}]})(props);
}function FaTimes (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 352 512"},"child":[{"tag":"path","attr":{"d":"M242.72 256l100.07-100.07c12.28-12.28 12.28-32.19 0-44.48l-22.24-22.24c-12.28-12.28-32.19-12.28-44.48 0L176 189.28 75.93 89.21c-12.28-12.28-32.19-12.28-44.48 0L9.21 111.45c-12.28 12.28-12.28 32.19 0 44.48L109.28 256 9.21 356.07c-12.28 12.28-12.28 32.19 0 44.48l22.24 22.24c12.28 12.28 32.2 12.28 44.48 0L176 322.72l100.07 100.07c12.28 12.28 32.2 12.28 44.48 0l22.24-22.24c12.28-12.28 12.28-32.19 0-44.48L242.72 256z"},"child":[]}]})(props);
}function FaTrash (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 448 512"},"child":[{"tag":"path","attr":{"d":"M432 32H312l-9.4-18.7A24 24 0 0 0 281.1 0H166.8a23.72 23.72 0 0 0-21.4 13.3L136 32H16A16 16 0 0 0 0 48v32a16 16 0 0 0 16 16h416a16 16 0 0 0 16-16V48a16 16 0 0 0-16-16zM53.2 467a48 48 0 0 0 47.9 45h245.8a48 48 0 0 0 47.9-45L416 128H32z"},"child":[]}]})(props);
}

const InfoHiddenContext = SP_REACT.createContext(false);
/** Unmount informational rows and controls so Steam removes their focus targets. */
function GFGInfo({ as: Component = "div", ...props }) {
    return SP_REACT.useContext(InfoHiddenContext) ? null : window.SP_REACT.createElement(Component, { ...props });
}

/** Restrict Decky's open string type to directions supported by Steam. */
function GFGFocusable(props) {
    return window.SP_REACT.createElement(DFL.Focusable, { ...props });
}
const makoPanelDivider = "1px solid rgba(255, 82, 62, 0.24)";
const gfgAccentColor = "#ff513d";
const makoSectionGap = "26px";
const makoSectionTailGap = "12px";
const makoPanelStyle = {
    overflow: "hidden",
    border: "1px solid rgba(255, 82, 62, 0.34)",
    borderRadius: "2px",
    background: "linear-gradient(135deg, rgba(12, 13, 17, 0.96), rgba(28, 18, 20, 0.82))",
    boxShadow: "inset 0 1px 0 rgba(255, 255, 255, 0.035), 0 2px 6px rgba(0, 0, 0, 0.18)",
};
const makoPanelSectionHeaderStyle = {
    padding: "12px 14px 9px",
    color: "#f5f7fa",
    fontSize: "14px",
    fontWeight: 600,
    lineHeight: 1.25,
    letterSpacing: "0.15px",
};
function GFGSectionTail({ children }) {
    return (window.SP_REACT.createElement("div", { "data-gfg-section-tail": "true", style: {
            width: "100%",
            boxSizing: "border-box",
            paddingBottom: makoSectionTailGap,
        } }, children));
}
const makoPanelItemStyle = {
    padding: "12px 14px",
    borderTop: makoPanelDivider,
};
const trailingParentheticalPattern = /(\s*)(\([^()]+\)|（[^（）]+）)\s*$/u;
/** Render a translated restart-bound label while keeping its qualifier visually secondary. */
function GFGRestartLabel({ label }) {
    const match = trailingParentheticalPattern.exec(label);
    if (!match || match.index === undefined)
        return window.SP_REACT.createElement("span", null, label);
    return (window.SP_REACT.createElement("span", null,
        label.slice(0, match.index),
        match[1],
        window.SP_REACT.createElement("span", { "data-gfg-restart-marker": "true", style: {
                fontSize: "0.72em",
                fontWeight: 500,
                opacity: 0.72,
                verticalAlign: "0.08em",
                whiteSpace: "nowrap",
            } }, match[2])));
}
/** Mark an intentionally early-access control without turning the label into a warning. */
function GFGExperimentalBadge({ label }) {
    return (window.SP_REACT.createElement(GFGInfo, { as: "span", "data-gfg-experimental-badge": "true", "data-gfg-info": "true", style: {
            display: "inline-flex",
            alignItems: "center",
            alignSelf: "flex-start",
            padding: "1px 5px",
            border: "1px solid rgba(255, 116, 95, 0.50)",
            borderRadius: "999px",
            background: "rgba(84, 25, 22, 0.58)",
            color: "#ffc5bc",
            fontSize: "0.62em",
            fontWeight: 600,
            lineHeight: 1.35,
            letterSpacing: "0.15px",
            textTransform: "uppercase",
            whiteSpace: "nowrap",
        } }, label));
}
/** Place the experimental badge on its own line below the complete setting label. */
function GFGExperimentalSettingLabel({ label, badgeLabel, }) {
    return (window.SP_REACT.createElement("span", { "data-gfg-experimental-setting-label": "true", style: {
            display: "inline-flex",
            alignItems: "flex-start",
            flexDirection: "column",
            rowGap: "4px",
        } },
        window.SP_REACT.createElement(GFGRestartLabel, { label: label }),
        window.SP_REACT.createElement(GFGExperimentalBadge, { label: badgeLabel })));
}
/** Use info for context and potential performance effects; reserve warning for known added runtime cost. */
function GFGInlineTip({ children, tone = "info", alwaysVisible = false, }) {
    const isWarning = tone === "warning";
    const accentColor = isWarning ? "#ff745f" : gfgAccentColor;
    const Icon = isWarning ? FiAlertTriangle : FiInfo;
    const Container = alwaysVisible ? "div" : GFGInfo;
    return (window.SP_REACT.createElement(Container, { role: "note", className: alwaysVisible ? undefined : "GFG_OptionMessage", "data-gfg-info": alwaysVisible ? undefined : "true", "data-tone": tone, style: {
            display: "flex",
            alignItems: "flex-start",
            gap: "6px",
            marginTop: "7px",
            padding: "6px 8px",
            border: isWarning
                ? "1px solid rgba(255, 116, 95, 0.34)"
                : "1px solid rgba(255, 81, 61, 0.18)",
            borderLeft: isWarning
                ? "2px solid rgba(255, 116, 95, 0.86)"
                : "2px solid rgba(255, 116, 95, 0.78)",
            borderRadius: "5px",
            background: isWarning
                ? "linear-gradient(90deg, rgba(84, 25, 22, 0.50), rgba(84, 25, 22, 0.20))"
                : "linear-gradient(90deg, rgba(37, 19, 21, 0.42), rgba(20, 13, 15, 0.18))",
            color: isWarning ? "#ffc5bc" : "#c6c8ce",
            fontSize: "10px",
            fontWeight: 450,
            lineHeight: 1.35,
            letterSpacing: "0.05px",
        } },
        window.SP_REACT.createElement(Icon, { "aria-hidden": "true", size: 11, style: {
                flex: "0 0 11px",
                marginTop: "1px",
                color: accentColor,
            } }),
        window.SP_REACT.createElement("span", { style: {
                minWidth: 0,
                overflowWrap: "anywhere",
                wordBreak: "break-word",
            } }, children)));
}
function GFGSettingRelationship({ children }) {
    return (window.SP_REACT.createElement(GFGInfo, { className: "GFG_OptionMessage", "data-gfg-setting-relationship": "true", "data-gfg-info": "true", style: {
            display: "flex",
            alignItems: "flex-start",
            gap: "5px",
            marginTop: "5px",
            color: "#9da3ad",
            fontSize: "9.5px",
            fontWeight: 450,
            lineHeight: 1.35,
            letterSpacing: "0.03px",
        } },
        window.SP_REACT.createElement(FiLink, { "aria-hidden": "true", size: 10, style: {
                flex: "0 0 10px",
                marginTop: "1px",
                color: "rgba(255, 116, 95, 0.78)",
            } }),
        window.SP_REACT.createElement("span", { style: { minWidth: 0 } }, children)));
}
function GfgExtremeHeader() {
    return (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { className: "GFG_ExtremeHeader", "aria-label": "GFG Extreme" },
            window.SP_REACT.createElement("div", { className: "GFG_ExtremeHeaderEdge" }),
            window.SP_REACT.createElement("div", { className: "GFG_ExtremeHeaderIcon", "aria-hidden": "true" },
                window.SP_REACT.createElement(MdBolt, { size: 30 })),
            window.SP_REACT.createElement("div", { className: "GFG_ExtremeHeaderText" },
                window.SP_REACT.createElement("div", { className: "GFG_ExtremeWordmark" },
                    window.SP_REACT.createElement("span", null, "GFG"),
                    window.SP_REACT.createElement("span", { className: "GFG_ExtremeSlash" }, "//"),
                    window.SP_REACT.createElement("span", { className: "GFG_ExtremeName" }, "EXTREME")),
                window.SP_REACT.createElement("div", { className: "GFG_ExtremeTagline" }, "FRAME GENERATION / REDLINE")),
            window.SP_REACT.createElement("div", { className: "GFG_ExtremePulse", "aria-hidden": "true" }))));
}
function GFGReleaseIdentity({ version, codename, bottomMargin = "2px", }) {
    const codenameSlug = codename
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
    return (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { "aria-label": `Current release: GFG Extreme v${version}, ${codename}`, style: {
                width: "100%",
                boxSizing: "border-box",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "-2px 0 0",
                marginBottom: bottomMargin,
                padding: "2px 4px 4px",
                opacity: 0.5,
                color: "#9da3ad",
                fontSize: "10px",
                fontWeight: 600,
                lineHeight: 1.2,
                letterSpacing: "0.55px",
                whiteSpace: "nowrap",
            } },
            window.SP_REACT.createElement("span", null,
                "v",
                version),
            window.SP_REACT.createElement("span", { "aria-hidden": "true", style: { padding: "0 6px", color: "#6e737c" } }, "-"),
            window.SP_REACT.createElement("span", { style: { color: gfgAccentColor } }, codenameSlug))));
}
function GFGSectionHeader({ children, description, topMargin = makoSectionGap, }) {
    return (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { style: {
                width: "100%",
                boxSizing: "border-box",
                marginTop: topMargin,
                marginBottom: "6px",
                color: "#f5f7fa",
                fontSize: "14px",
                fontWeight: "600",
                lineHeight: "1.25",
                letterSpacing: "0.15px",
            } },
            window.SP_REACT.createElement("div", { style: {
                    paddingBottom: "8px",
                    textAlign: "center",
                    borderBottom: "3px solid #ff513d",
                } }, children),
            description && (window.SP_REACT.createElement(GFGInfo, { "data-gfg-info": "true", style: {
                    marginTop: "8px",
                    color: "#9da3ad",
                    fontSize: "11px",
                    fontWeight: "400",
                    lineHeight: "1.35",
                    letterSpacing: "normal",
                } }, description)))));
}
function GFGCompactSpinner({ size = 18 }) {
    return (window.SP_REACT.createElement("span", { "aria-hidden": "true", style: {
            width: `${size}px`,
            height: `${size}px`,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            flex: `0 0 ${size}px`,
            overflow: "hidden",
        } },
        window.SP_REACT.createElement(DFL.Spinner, { width: size, height: size, style: {
                width: `${size}px`,
                height: `${size}px`,
                maxWidth: `${size}px`,
                maxHeight: `${size}px`,
                display: "block",
                flex: `0 0 ${size}px`,
            } })));
}
function makoDialogButtonStyle(isFocused, variant = "normal") {
    const danger = variant === "danger";
    const focusColor = danger ? "#ff745f" : "#ff513d";
    return {
        color: danger ? "#fff3f1" : "#f5f7fa",
        background: danger
            ? "linear-gradient(135deg, #190d0e 0%, #351516 58%, #4b1b18 100%)"
            : "linear-gradient(135deg, #0b0d11 0%, #171319 58%, #2a1517 100%)",
        border: danger
            ? "1px solid rgba(255, 81, 61, 0.48)"
            : "1px solid rgba(255, 81, 61, 0.48)",
        borderRadius: "4px",
        outline: isFocused ? `2px solid ${focusColor}` : "none",
        outlineOffset: "2px",
        boxShadow: isFocused
            ? danger
                ? "0 0 0 3px rgba(255, 81, 61, 0.20), 0 0 10px rgba(255, 81, 61, 0.26)"
                : "0 0 0 3px rgba(255, 81, 61, 0.20), 0 0 10px rgba(255, 81, 61, 0.24)"
            : "inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 2px 5px rgba(0, 0, 0, 0.22)",
        transition: "background 120ms ease, box-shadow 120ms ease",
    };
}
function GFGButtonTheme() {
    return (window.SP_REACT.createElement("style", null, `
      .GFG_DialogButton:not(.disabled):not([disabled]):not([aria-disabled="true"]):hover,
      .GFG_DialogButton button:hover:not(:disabled) {
        background: linear-gradient(135deg, #121419 0%, #251315 58%, #321719 100%) !important;
        border-color: rgba(255, 116, 95, 0.74) !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 0 9px rgba(255, 81, 61, 0.22) !important;
      }

      .GFG_DialogButton--danger:not(.disabled):not([disabled]):not([aria-disabled="true"]):hover,
      .GFG_DialogButton--danger button:hover:not(:disabled) {
        background: linear-gradient(135deg, #221011 0%, #421817 58%, #5c201d 100%) !important;
        border-color: rgba(255, 116, 95, 0.74) !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1), 0 0 9px rgba(255, 81, 61, 0.20) !important;
      }

      .GFG_BrandButton button {
        color: #f5f7fa !important;
        background: linear-gradient(135deg, #0b0d11 0%, #171319 58%, #2a1517 100%) !important;
        border: 1px solid rgba(255, 81, 61, 0.48) !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 2px 5px rgba(0, 0, 0, 0.22) !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.72);
        transition: background 120ms ease, box-shadow 120ms ease, filter 120ms ease;
      }

      .GFG_BrandButton button:hover:not(:disabled) {
        background: linear-gradient(135deg, #121419 0%, #251315 58%, #321719 100%) !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 0 9px rgba(255, 81, 61, 0.22) !important;
      }

      .GFG_BrandButton button:focus,
      .GFG_BrandButton button:focus-visible {
        outline: 2px solid #ff513d !important;
        outline-offset: 2px !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 0 0 3px rgba(255, 81, 61, 0.20), 0 0 10px rgba(255, 81, 61, 0.24) !important;
      }

      .GFG_BrandButton button:disabled {
        filter: saturate(0.4) brightness(0.68);
      }

      .GFG_BrandButton--danger button {
        background: linear-gradient(135deg, #190d0e 0%, #351516 58%, #4b1b18 100%) !important;
        border-color: rgba(255, 81, 61, 0.48) !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.07), 0 2px 5px rgba(0, 0, 0, 0.24) !important;
      }

      .GFG_BrandButton--danger button:hover:not(:disabled) {
        background: linear-gradient(135deg, #221011 0%, #421817 58%, #5c201d 100%) !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1), 0 0 9px rgba(255, 81, 61, 0.20) !important;
      }

      .GFG_BrandButton--danger button:focus,
      .GFG_BrandButton--danger button:focus-visible {
        outline: 2px solid #ff745f !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1), 0 0 0 3px rgba(255, 81, 61, 0.20), 0 0 10px rgba(255, 81, 61, 0.26) !important;
      }
    `));
}

function GFGInstallCountdown({ durationMs, }) {
    return (window.SP_REACT.createElement("svg", { "aria-hidden": "true", width: "24", height: "24", viewBox: "0 0 24 24", style: { display: "block", transform: "rotate(-90deg)" } },
        window.SP_REACT.createElement("circle", { cx: "12", cy: "12", r: "9", fill: "none", stroke: "rgba(255, 81, 61, 0.24)", strokeWidth: "2.5" }),
        window.SP_REACT.createElement("circle", { cx: "12", cy: "12", r: "9", pathLength: "1", fill: "none", stroke: "#ff745f", strokeWidth: "2.5", strokeLinecap: "round", strokeDasharray: "1", strokeDashoffset: "0" },
            window.SP_REACT.createElement("animate", { attributeName: "stroke-dashoffset", from: "0", to: "1", dur: `${durationMs}ms`, fill: "freeze" }))));
}
function GFGInstallCompletion() {
    return (window.SP_REACT.createElement("div", { style: { display: "flex", alignItems: "center", gap: "10px" } },
        window.SP_REACT.createElement(GFGInstallCountdown, { durationMs: MAKO_INSTALL_COMPLETION_DURATION_MS }),
        window.SP_REACT.createElement("div", { style: {
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                gap: "2px",
            } },
            window.SP_REACT.createElement("div", { style: { fontWeight: 600 } }, t("TOAST_INSTALL_COMPLETE", "Installation Complete")),
            window.SP_REACT.createElement("div", { style: { fontSize: "12px", opacity: 0.82 } }, t("TOAST_INSTALL_COMPLETE_DESC", "Restarting your device is recommended.")))));
}

function InstallationButton({ isInstalled, isInstalling, isInstallCompletionVisible, isUninstalling, hostArchitectureSupported, onInstall, onUninstall, topMargin = "0" }) {
    const renderButtonContent = () => {
        if (isInstallCompletionVisible) {
            return window.SP_REACT.createElement(GFGInstallCompletion, null);
        }
        if (isInstalling) {
            return (window.SP_REACT.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
                window.SP_REACT.createElement(GFGCompactSpinner, null),
                window.SP_REACT.createElement("div", null, t("INSTALL_INSTALLING", "Installing GFG Engine..."))));
        }
        if (isUninstalling) {
            return (window.SP_REACT.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
                window.SP_REACT.createElement(GFGCompactSpinner, null),
                window.SP_REACT.createElement("div", null, t("INSTALL_UNINSTALLING", "Removing GFG Engine..."))));
        }
        if (isInstalled) {
            return (window.SP_REACT.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
                window.SP_REACT.createElement(FaTrash, null),
                window.SP_REACT.createElement("div", null, t("INSTALL_REMOVE_RENDERER", "Remove GFG Engine"))));
        }
        return (window.SP_REACT.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
            window.SP_REACT.createElement(FaDownload, null),
            window.SP_REACT.createElement("div", null, t("INSTALL_RENDERER", "Install GFG Engine"))));
    };
    return (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { className: `GFG_BrandButton${isInstalled ? " GFG_BrandButton--danger" : ""}`, style: { marginTop: topMargin } },
            window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", onClick: isInstalled ? onUninstall : onInstall, disabled: isInstalling || isInstallCompletionVisible || isUninstalling || !hostArchitectureSupported }, renderButtonContent()))));
}

/**
 * Keeps a Decky section's collapsed/hidden preference in local storage.
 *
 * Reading intentionally fails silently so damaged or unavailable browser
 * storage falls back to the product default. Writes retain the existing
 * warning because a storage failure should not make the controls unusable.
 */
function usePersistentCollapseState(storageKey, defaultCollapsed, warningLabel) {
    const [collapsed, setCollapsed] = SP_REACT.useState(() => {
        try {
            const saved = localStorage.getItem(storageKey);
            const parsed = saved !== null ? JSON.parse(saved) : null;
            return typeof parsed === "boolean" ? parsed : defaultCollapsed;
        }
        catch {
            return defaultCollapsed;
        }
    });
    SP_REACT.useEffect(() => {
        try {
            localStorage.setItem(storageKey, JSON.stringify(collapsed));
        }
        catch (error) {
            console.warn(`Failed to save ${warningLabel} collapse state:`, error);
        }
    }, [collapsed, storageKey, warningLabel]);
    return [collapsed, setCollapsed];
}

const DEFAULT_CONFIGURATION$2 = getDefaults();
function adaptiveModeChanges(enabled) {
    return { adaptive: enabled };
}
function baseFpsCapChanges(value) {
    return {
        base_fps_cap: value,
        adaptive_fractional_real_frame_priority: ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_AUTO,
        dynamic_cadence_recovery: false,
    };
}
function fractionalRealFramePriorityChanges(value) {
    return {
        adaptive_fractional_real_frame_priority: value,
        dynamic_cadence_recovery: false,
    };
}
function fractionalRealFramePriorityCap(targetFps, priority) {
    switch (priority) {
        case ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_LOW:
            return (targetFps * 3) / 5;
        case ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_MEDIUM:
            return (targetFps * 2) / 3;
        case ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_HIGH:
            return (targetFps * 3) / 4;
        case ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_VERY_HIGH:
            return (targetFps * 4) / 5;
        case ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_AUTO:
            return undefined;
    }
}
function dynamicCadenceRecoveryChanges(enabled) {
    if (!enabled) {
        return { dynamic_cadence_recovery: false };
    }
    return {
        dynamic_cadence_recovery: true,
        adaptive_auto_base_fps_cap: false,
        adaptive_fractional_real_frame_priority: ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_AUTO,
        base_fps_cap: 0,
    };
}
function isFractionalAdaptivePresetEnabled(config) {
    return (config.adaptive &&
        !(config.adaptive_auto_base_fps_cap ??
            DEFAULT_CONFIGURATION$2.adaptive_auto_base_fps_cap));
}
function fractionalAdaptivePresetChanges(enabled) {
    if (!enabled) {
        return {
            adaptive_auto_base_fps_cap: true,
            dynamic_cadence_recovery: false,
        };
    }
    return {
        adaptive: true,
        adaptive_auto_base_fps_cap: false,
        dynamic_cadence_recovery: false,
    };
}
function steadyBaseCapChanges(enabled) {
    return {
        adaptive_auto_base_fps_cap: enabled,
        dynamic_cadence_recovery: false,
    };
}

// THIS FILE IS AUTO GENERATED
function RiArrowDownSFill (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24","fill":"currentColor"},"child":[{"tag":"path","attr":{"d":"M12 16L6 10H18L12 16Z"},"child":[]}]})(props);
}function RiArrowUpSFill (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24","fill":"currentColor"},"child":[{"tag":"path","attr":{"d":"M12 8L18 14H6L12 8Z"},"child":[]}]})(props);
}function RiEditLine (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24","fill":"currentColor"},"child":[{"tag":"path","attr":{"d":"M6.41421 15.89L16.5563 5.74785L15.1421 4.33363L5 14.4758V15.89H6.41421ZM7.24264 17.89H3V13.6473L14.435 2.21231C14.8256 1.82179 15.4587 1.82179 15.8492 2.21231L18.6777 5.04074C19.0682 5.43126 19.0682 6.06443 18.6777 6.45495L7.24264 17.89ZM3 19.89H21V21.89H3V19.89Z"},"child":[]}]})(props);
}function RiDeleteBinLine (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24","fill":"currentColor"},"child":[{"tag":"path","attr":{"d":"M17 6H22V8H20V21C20 21.5523 19.5523 22 19 22H5C4.44772 22 4 21.5523 4 21V8H2V6H7V3C7 2.44772 7.44772 2 8 2H16C16.5523 2 17 2.44772 17 3V6ZM18 8H6V20H18V8ZM9 11H11V17H9V11ZM13 11H15V17H13V11ZM9 4V6H15V4H9Z"},"child":[]}]})(props);
}

function CollapseControl({ containerClassName, collapsed, onToggle, }) {
    return (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { className: containerClassName, style: { marginTop: "2px", marginBottom: "4px" } },
            window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", bottomSeparator: "none", onClick: onToggle }, collapsed ? (window.SP_REACT.createElement(RiArrowDownSFill, { style: { transform: "translate(0, -13px)", fontSize: "1.5em" } })) : (window.SP_REACT.createElement(RiArrowUpSFill, { style: { transform: "translate(0, -12px)", fontSize: "1.5em" } }))))));
}

function AdvancedRenderingConfigurationGroup({ config, onConfigChange, onConfigUpdate, collapsed, onToggle, }) {
    const steadyBaseFpsCap = Math.max(ADAPTIVE_MINIMUM_BASE_FPS, config.target_fps / 2);
    const steadyBaseFpsCapLabel = Number.isInteger(steadyBaseFpsCap)
        ? steadyBaseFpsCap.toFixed(0)
        : steadyBaseFpsCap.toFixed(1);
    const fractionalPriority = (config.adaptive_fractional_real_frame_priority ??
        ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_AUTO);
    const fractionalPriorityCap = fractionalRealFramePriorityCap(config.target_fps, fractionalPriority);
    const fractionalPriorityCapLabel = fractionalPriorityCap === undefined
        ? undefined
        : Number.isInteger(fractionalPriorityCap)
            ? fractionalPriorityCap.toFixed(0)
            : fractionalPriorityCap.toFixed(1);
    const fractionalPriorityOwnsCap = isFractionalAdaptivePresetEnabled(config) &&
        fractionalPriorityCapLabel !== undefined;
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGSectionHeader, null, t("CONFIG_SECTION_TITLE", "Advanced Rendering Settings")),
        window.SP_REACT.createElement(CollapseControl, { containerClassName: "GFG_ConfigCollapseButton_Container", collapsed: collapsed, onToggle: onToggle }),
        !collapsed && (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.SliderField, { label: `${t("CONFIG_BASE_FPS_CAP", "Base FPS Cap")}${config.base_fps_cap > 0 ? ` (${config.base_fps_cap} FPS)` : ` (${t("CONFIG_BASE_FPS_CAP_OFF", "Off")})`}`, description: window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                        window.SP_REACT.createElement("div", null, t("CONFIG_BASE_FPS_CAP_DESC", "Caps real application frames before frame generation. Works with DirectX, OpenGL through Zink, and Vulkan.")),
                        config.adaptive && config.adaptive_auto_base_fps_cap ? (window.SP_REACT.createElement(GFGSettingRelationship, null, t("CONFIG_BASE_FPS_CAP_STEADY_RELATION", "Controlled by Steady Base Cap ({fps} FPS). Your manual value remains saved.", { fps: steadyBaseFpsCapLabel }))) : fractionalPriorityOwnsCap ? (window.SP_REACT.createElement(GFGSettingRelationship, null, t("CONFIG_BASE_FPS_CAP_FRACTIONAL_PRIORITY_RELATION", "Controlled by Real Frame Priority ({fps} FPS). Your manual value remains saved.", { fps: fractionalPriorityCapLabel }))) : config.dynamic_cadence_recovery ? (window.SP_REACT.createElement(GFGSettingRelationship, null, t("CONFIG_BASE_FPS_CAP_RECOVERY_RELATION", "Changing this cap turns Dynamic Cadence Recovery off."))) : null), value: config.base_fps_cap, min: BASE_FPS_CAP_MIN, max: BASE_FPS_CAP_UI_MAX, step: 1, disabled: !config.frame_generation_enabled ||
                        (config.adaptive && config.adaptive_auto_base_fps_cap) ||
                        fractionalPriorityOwnsCap, onChange: (value) => onConfigUpdate(baseFpsCapChanges(value)) })),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.ToggleField, { label: t("CONFIG_DISABLE_MAKO_NEXT_LAUNCH", "Disable GFG Engine on Next Launch"), description: t("CONFIG_DISABLE_MAKO_NEXT_LAUNCH_DESC", "For troubleshooting: skips GFG Engine on the next launch. Use Frame Generation above to toggle synthesis."), checked: config.disable_mako, onChange: (value) => onConfigChange(DISABLE_MAKO, value) })),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.ToggleField, { label: t("CONFIG_FRAME_GENERATION_REFRESH_GUARD", "Auto-disable Frame Generation by Refresh Rate"), description: t("CONFIG_FRAME_GENERATION_REFRESH_GUARD_DESC", "Pauses generation at or below the chosen Gamescope refresh rate; resumes above it. Requires refresh feedback."), bottomSeparator: config.frame_generation_refresh_threshold > 0
                        ? undefined
                        : "none", checked: config.frame_generation_refresh_threshold > 0, onChange: (value) => onConfigChange(FRAME_GENERATION_REFRESH_THRESHOLD, value ? FRAME_GENERATION_REFRESH_THRESHOLD_PRESET : 0) })),
            config.frame_generation_refresh_threshold > 0 && (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.SliderField, { label: `${t("CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD", "Refresh Rate Threshold")} (${config.frame_generation_refresh_threshold} Hz)`, description: t("CONFIG_FRAME_GENERATION_REFRESH_THRESHOLD_DESC", "Choose the highest refresh rate where frame generation should remain paused."), value: config.frame_generation_refresh_threshold, min: FRAME_GENERATION_REFRESH_THRESHOLD_UI_MIN, max: FRAME_GENERATION_REFRESH_THRESHOLD_MAX, step: 1, onChange: (value) => onConfigChange(FRAME_GENERATION_REFRESH_THRESHOLD, value) })))))));
}

function CompatibilityConfigurationGroup({ config, onConfigChange, onConfigUpdate, collapsed, onToggle, }) {
    const cadenceProbeInterval = config.dynamic_cadence_probe_interval_seconds;
    const cadenceProbeIntervalValues = DYNAMIC_CADENCE_PROBE_INTERVAL_SECONDS_VALUES.includes(cadenceProbeInterval)
        ? [...DYNAMIC_CADENCE_PROBE_INTERVAL_SECONDS_VALUES]
        : [
            ...DYNAMIC_CADENCE_PROBE_INTERVAL_SECONDS_VALUES,
            cadenceProbeInterval,
        ].sort((left, right) => left - right);
    const cadenceProbeIntervalOptions = cadenceProbeIntervalValues.map((value) => ({ data: value, label: `${value}s` }));
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGSectionHeader, null, t("CONFIG_WORKAROUNDS_TITLE", "Compatibility Settings")),
        window.SP_REACT.createElement(CollapseControl, { containerClassName: "GFG_WorkaroundsCollapseButton_Container", collapsed: collapsed, onToggle: onToggle }),
        !collapsed && (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.ToggleField, { label: t("CONFIG_DISABLE_HDR_EXPOSURE", "Disable HDR"), description: t("CONFIG_DISABLE_HDR_EXPOSURE_DESC", "HDR is unavailable in this release. This required setting keeps the stable SDR path active."), checked: true, disabled: true, onChange: () => undefined })),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.ToggleField, { label: t("DYNAMIC_CADENCE_RECOVERY", "Dynamic Cadence Recovery"), description: window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                        window.SP_REACT.createElement("div", null, t("DYNAMIC_CADENCE_RECOVERY_DESC", "Helps games and emulators that switch native rates, such as 30 FPS gameplay and 60 FPS menus. It periodically checks for a rate change and recovers the correct cadence, but each check can briefly affect pacing. Enable it only for affected games.")),
                        window.SP_REACT.createElement(GFGSettingRelationship, null, t("DYNAMIC_CADENCE_RECOVERY_RELATION", "Recovery disables Steady Base Cap and Base FPS Cap and resets Real Frame Priority to Automatic. Changing either cap or priority turns Recovery off."))), checked: config.dynamic_cadence_recovery, onChange: (value) => onConfigUpdate(dynamicCadenceRecoveryChanges(value)) })),
            config.dynamic_cadence_recovery && (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: t("DYNAMIC_CADENCE_PROBE_INTERVAL", "Cadence Probe Interval"), description: window.SP_REACT.createElement("span", { style: { display: "block", paddingBottom: "6px" } }, t("DYNAMIC_CADENCE_PROBE_INTERVAL_DESC", "Recovery check interval: 0.1 s may hitch often; 2 s is default; 3 s checks least often. Test per game.")), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: cadenceProbeIntervalOptions, selectedOption: cadenceProbeInterval, onChange: (option) => onConfigChange(DYNAMIC_CADENCE_PROBE_INTERVAL_SECONDS, Number(option.data)) })))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.ToggleField, { label: window.SP_REACT.createElement(GFGRestartLabel, { label: t("CONFIG_GAMESCOPE_WSI_COMPATIBILITY", "Gamescope WSI (Restart)") }), description: window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                        window.SP_REACT.createElement("div", null, t("CONFIG_GAMESCOPE_WSI_COMPATIBILITY_DESC", "May reduce coloured or pixelated motion artifacts through Gamescope presentation. Optional with Scaling and Frame Generation; enable only if needed.")),
                        window.SP_REACT.createElement(GFGInlineTip, { tone: "warning" }, t("CONFIG_GAMESCOPE_WSI_COMPATIBILITY_WARNING", "Only supported 64-bit host launches. Leave off unless needed; it may reduce performance."))), checked: config.gamescope_wsi_compatibility, onChange: (value) => onConfigChange(GAMESCOPE_WSI_COMPATIBILITY, value) })),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.ToggleField, { label: window.SP_REACT.createElement(GFGRestartLabel, { label: t("CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY", "Game Swapchain Images (Restart)") }), description: window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                        window.SP_REACT.createElement("div", null, t("CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_DESC", "May fix startup failures with Frame Generation by keeping the game's requested swapchain image minimum. Use only for affected games.")),
                        window.SP_REACT.createElement(GFGInlineTip, { tone: "warning" }, t("CONFIG_SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY_WARNING", "Generated frames may be skipped when the compositor has no spare image, which can reduce smoothness or performance under pressure."))), checked: config.swapchain_image_count_compatibility, onChange: (value) => onConfigChange(SWAPCHAIN_IMAGE_COUNT_COMPATIBILITY, value) })),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.ToggleField, { label: window.SP_REACT.createElement(GFGRestartLabel, { label: t("CONFIG_DISABLE_STEAMDECK_MODE", "Disable Steam Deck Mode (Restart)") }), description: t("CONFIG_DISABLE_STEAMDECK_MODE_DESC", "Disables Steam Deck mode. Unlocks hidden settings in some games."), checked: config.disable_steamdeck_mode, onChange: (value) => onConfigChange(DISABLE_STEAMDECK_MODE, value) })),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.ToggleField, { label: window.SP_REACT.createElement(GFGRestartLabel, { label: t("CONFIG_ENABLE_ZINK", "Enable Zink for OpenGL Games (Restart)") }), description: t("CONFIG_ENABLE_ZINK_DESC", "Runs OpenGL games through Vulkan; may crash or freeze some games."), checked: config.enable_zink, onChange: (value) => onConfigChange(ENABLE_ZINK, value) })),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.ToggleField, { label: window.SP_REACT.createElement(GFGRestartLabel, { label: t("CONFIG_FORCE_ALSA_AUDIO", "Force ALSA Audio (Restart)") }), description: t("CONFIG_FORCE_ALSA_AUDIO_DESC", "May help Zink compatibility, audio stutter, or sudden loud sounds. Turn off to restore default audio."), bottomSeparator: "none", checked: config.force_alsa_audio, onChange: (value) => onConfigChange(FORCE_ALSA_AUDIO, value) }))))));
}

function ExternalToolsConfigurationGroup({ config, onConfigChange, collapsed, onToggle, }) {
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGSectionHeader, null, t("CONFIG_EXTERNAL_TOOLS_TITLE", "External Tools")),
        window.SP_REACT.createElement(CollapseControl, { containerClassName: "GFG_ExternalToolsCollapseButton_Container", collapsed: collapsed, onToggle: onToggle }),
        !collapsed && (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.ToggleField, { label: window.SP_REACT.createElement(GFGRestartLabel, { label: t("CONFIG_ENABLE_MANGOHUD", "Enable MangoHud (Restart)") }), description: t("CONFIG_ENABLE_MANGOHUD_DESC", "Uses installed MangoHud and its settings; see expert guide for per-game overrides."), checked: config.external_vulkan_layer === EXTERNAL_VULKAN_LAYER_MANGOHUD, onChange: (value) => onConfigChange(EXTERNAL_VULKAN_LAYER, value
                        ? EXTERNAL_VULKAN_LAYER_MANGOHUD
                        : EXTERNAL_VULKAN_LAYER_NONE), bottomSeparator: "none" }))))));
}

function ManualOverridesConfigurationGroup({ config, onConfigChange, collapsed, onToggle, }) {
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGSectionHeader, null, t("CONFIG_MANUAL_OVERRIDES_TITLE", "Manual Overrides")),
        window.SP_REACT.createElement(CollapseControl, { containerClassName: "GFG_ManualOverridesCollapseButton_Container", collapsed: collapsed, onToggle: onToggle }),
        !collapsed && (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", { className: "GFG_ManualOverrideFields" },
                window.SP_REACT.createElement(DFL.TextField, { label: window.SP_REACT.createElement(GFGRestartLabel, { label: t("CONFIG_DLL_PATH", "Lossless.dll Path (Restart)") }), description: window.SP_REACT.createElement("span", { className: "GFG_OptionDescription" }, t("CONFIG_DLL_PATH_DESC", "Optional full path to Lossless.dll. Leave blank to use GFG Engine automatic discovery.")), value: config.dll, onChange: (event) => onConfigChange(DLL, event.currentTarget.value) }),
                window.SP_REACT.createElement(DFL.TextField, { label: window.SP_REACT.createElement(GFGRestartLabel, { label: t("CONFIG_GPU", "GPU (Restart)") }), description: window.SP_REACT.createElement("span", { className: "GFG_GpuDescription GFG_OptionDescription" }, t("CONFIG_GPU_DESC", "Optional GPU name, vendor:device ID, or PCI bus ID. Restart the game after changing it.")), value: config.gpu, onChange: (event) => onConfigChange(GPU, event.currentTarget.value) }),
                window.SP_REACT.createElement(DFL.TextField, { label: t("CONFIG_ACTIVE_IN", "Matched Processes"), description: window.SP_REACT.createElement("span", { className: "GFG_OptionDescription" }, t("CONFIG_ACTIVE_IN_DESC", "Comma-separated process names. Game capture fills these; edit only to add a launcher or emulator alias.")), value: config.active_in, onChange: (event) => onConfigChange(ACTIVE_IN, event.currentTarget.value) }))))));
}

const WORKAROUNDS_COLLAPSED_KEY = "gfg-workarounds-collapsed";
const CONFIG_COLLAPSED_KEY = "gfg-config-collapsed";
const EXTERNAL_TOOLS_COLLAPSED_KEY = "gfg-external-tools-collapsed";
const MANUAL_OVERRIDES_COLLAPSED_KEY = "gfg-manual-overrides-collapsed";
const collapseControlStyles = `
  .GFG_EngineTuningCollapseButton_Container > div > div > div > button,
  .GFG_EngineTuningCollapseButton_Container > div > div > div > div > button,
  .GFG_ConfigCollapseButton_Container > div > div > div > button,
  .GFG_ConfigCollapseButton_Container > div > div > div > div > button,
  .GFG_WorkaroundsCollapseButton_Container > div > div > div > button,
  .GFG_ExternalToolsCollapseButton_Container > div > div > div > button,
  .GFG_ManualOverridesCollapseButton_Container > div > div > div > button {
    height: 10px !important;
  }
  .GFG_WorkaroundsCollapseButton_Container > div > div > div > div > button,
  .GFG_ExternalToolsCollapseButton_Container > div > div > div > div > button,
  .GFG_ManualOverridesCollapseButton_Container > div > div > div > div > button {
    height: 10px !important;
  }
`;
function FrameGenerationConfigurationSection({ config, onConfigChange, onConfigUpdate, initiallyCollapsed = true, }) {
    const [configCollapsed, setConfigCollapsed] = usePersistentCollapseState(CONFIG_COLLAPSED_KEY, initiallyCollapsed, "frame generation advanced settings");
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement("style", null, collapseControlStyles),
        window.SP_REACT.createElement(AdvancedRenderingConfigurationGroup, { config: config, onConfigChange: onConfigChange, onConfigUpdate: onConfigUpdate, collapsed: configCollapsed, onToggle: () => setConfigCollapsed(!configCollapsed) })));
}
function ConfigurationSection({ config, onConfigChange, onConfigUpdate, includeAdvancedRendering = true, }) {
    const [workaroundsCollapsed, setWorkaroundsCollapsed] = usePersistentCollapseState(WORKAROUNDS_COLLAPSED_KEY, true, "workarounds");
    const [manualOverridesCollapsed, setManualOverridesCollapsed] = usePersistentCollapseState(MANUAL_OVERRIDES_COLLAPSED_KEY, true, "manual overrides");
    const [externalToolsCollapsed, setExternalToolsCollapsed] = usePersistentCollapseState(EXTERNAL_TOOLS_COLLAPSED_KEY, true, "external tools");
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement("style", null, `${collapseControlStyles}
        .GFG_ManualOverrideFields {
          display: flex;
          flex-direction: column;
          gap: 12px;
          width: 100%;
          min-width: 0;
          margin: 10px 0 0;
        }
        .GFG_ManualOverrideFields > * {
          margin-bottom: 0 !important;
        }
        .GFG_ManualOverrideFields > * + * {
          margin-top: 0 !important;
        }
        .GFG_GpuDescription {
          display: block;
          padding-bottom: 10px;
        }
      `),
        includeAdvancedRendering && (window.SP_REACT.createElement(FrameGenerationConfigurationSection, { config: config, onConfigChange: onConfigChange, onConfigUpdate: onConfigUpdate, initiallyCollapsed: false })),
        window.SP_REACT.createElement(CompatibilityConfigurationGroup, { config: config, onConfigChange: onConfigChange, onConfigUpdate: onConfigUpdate, collapsed: workaroundsCollapsed, onToggle: () => setWorkaroundsCollapsed(!workaroundsCollapsed) }),
        window.SP_REACT.createElement(ExternalToolsConfigurationGroup, { config: config, onConfigChange: onConfigChange, collapsed: externalToolsCollapsed, onToggle: () => setExternalToolsCollapsed(!externalToolsCollapsed) }),
        window.SP_REACT.createElement(ManualOverridesConfigurationGroup, { config: config, onConfigChange: onConfigChange, collapsed: manualOverridesCollapsed, onToggle: () => setManualOverridesCollapsed(!manualOverridesCollapsed) })));
}

const DEFAULT_CONFIGURATION$1 = getDefaults();
function effectiveScalingMethod(config) {
    return config.scaling_enabled && config.ultra_performance
        ? SCALING_METHOD_LS1_PERFORMANCE
        : config.scaling_method;
}
function ultraPerformanceChanges(enabled) {
    return {
        [ULTRA_PERFORMANCE]: enabled,
        [FLOW_SCALE]: enabled
            ? ULTRA_PERFORMANCE_FLOW_SCALE
            : DEFAULT_CONFIGURATION$1.flow_scale,
        [PERFORMANCE_MODE]: enabled,
        [ALLOW_FP16]: DEFAULT_CONFIGURATION$1.allow_fp16,
    };
}

const EMPTY_STATUS = { ls1: null, lsfg: null };
async function inspect(action) {
    try {
        const status = await action();
        return {
            compatible: typeof status.compatible === "boolean" ? status.compatible : null,
            reason: typeof status.reason === "string" ? status.reason : null,
        };
    }
    catch {
        // An older/missing backend is not proof that the model has failed.
        return null;
    }
}
function useModelStatus(config, enabled) {
    const method = effectiveScalingMethod(config);
    const allowFp16 = config.ultra_performance || config.allow_fp16;
    const ls1 = enabled &&
        !config.disable_mako &&
        config.scaling_enabled &&
        (method === SCALING_METHOD_LS1 ||
            method === SCALING_METHOD_LS1_PERFORMANCE);
    const lsfg = enabled &&
        !config.disable_mako &&
        config.frame_generation_provisioned &&
        config.frame_generation_enabled;
    const key = JSON.stringify([
        config.dll,
        ls1,
        method,
        config.scaling_sharpness,
        lsfg,
        allowFp16,
    ]);
    const [result, setResult] = SP_REACT.useState(null);
    SP_REACT.useEffect(() => {
        if (!ls1 && !lsfg)
            return;
        let active = true;
        let timer;
        const refresh = async () => {
            // One sequence prevents competing inspector requests and translation queues.
            const fgStatus = lsfg
                ? await inspect(() => checkFrameGenerationModel(config.dll, allowFp16))
                : null;
            if (!active)
                return;
            const scalingStatus = ls1
                ? await inspect(() => checkScalingModel(config.dll, method, config.scaling_sharpness))
                : null;
            if (active) {
                setResult({ key, ls1: scalingStatus, lsfg: fgStatus });
                timer = setTimeout(refresh, MODEL_STATUS_POLL_INTERVAL_MS);
            }
        };
        timer = setTimeout(refresh, MODEL_STATUS_DEBOUNCE_MS);
        return () => {
            active = false;
            clearTimeout(timer);
        };
    }, [ls1, lsfg, key, config.dll, method, config.scaling_sharpness, allowFp16]);
    return (ls1 || lsfg) && result?.key === key ? result : EMPTY_STATUS;
}

/**
 * Owns the editable profile list and its backend transactions.
 *
 * This is deliberately separate from runtime profile synchronisation: the
 * offline dropdown selects a profile to edit and must never become a runtime
 * override. A running game is captured explicitly and otherwise locks the
 * editor to the profile selected by the runtime session.
 */
function useProfileEditorModel({ editingProfile, onProfileChange, mainRunningApp, }) {
    const [profiles, setProfiles] = SP_REACT.useState([]);
    const [profileDetails, setProfileDetails] = SP_REACT.useState([]);
    const [selectedProfile, setSelectedProfile] = SP_REACT.useState(editingProfile || DEFAULT_PROFILE_NAME);
    const editingProfileRef = SP_REACT.useRef(editingProfile || DEFAULT_PROFILE_NAME);
    const [isLoading, setIsLoading] = SP_REACT.useState(false);
    const loadProfiles = async (preferredProfile) => {
        try {
            const result = await getProfiles();
            if (!result.success || !result.profiles) {
                throw new Error(result.error || t("PROFILE_UNKNOWN_ERROR", "Unknown error"));
            }
            setProfiles(result.profiles);
            setProfileDetails(result.profile_details || []);
            const resolvedProfile = result.profiles.includes(editingProfileRef.current)
                ? editingProfileRef.current
                : preferredProfile && result.profiles.includes(preferredProfile)
                    ? preferredProfile
                    : result.current_profile &&
                        result.profiles.includes(result.current_profile)
                        ? result.current_profile
                        : result.profiles.includes(DEFAULT_PROFILE_NAME)
                            ? DEFAULT_PROFILE_NAME
                            : result.profiles[0];
            if (resolvedProfile)
                setSelectedProfile(resolvedProfile);
            return resolvedProfile || DEFAULT_PROFILE_NAME;
        }
        catch (error) {
            console.error("Error loading profiles:", error);
            showErrorToast(t("PROFILE_LOAD_FAILED", "Failed to load profiles"), String(error));
            return DEFAULT_PROFILE_NAME;
        }
    };
    SP_REACT.useEffect(() => {
        void loadProfiles(editingProfile || DEFAULT_PROFILE_NAME);
    }, []);
    SP_REACT.useEffect(() => {
        if (editingProfile) {
            editingProfileRef.current = editingProfile;
            setSelectedProfile(editingProfile);
        }
    }, [editingProfile]);
    const selectedDetails = SP_REACT.useMemo(() => profileDetails.find((profile) => profile.profile_name === selectedProfile), [profileDetails, selectedProfile]);
    const runningProfile = SP_REACT.useMemo(() => profileDetails.find((profile) => profile.steam_app_id &&
        profile.steam_app_id === String(mainRunningApp?.appid || "")), [profileDetails, mainRunningApp]);
    const notifyProfileChanged = async (profileName) => {
        const resolvedProfile = await loadProfiles(profileName);
        await onProfileChange?.(resolvedProfile || profileName);
        return resolvedProfile;
    };
    const switchProfile = async (profileName) => {
        setIsLoading(true);
        try {
            if (!profiles.includes(profileName)) {
                throw new Error(`Profile '${profileName}' does not exist`);
            }
            editingProfileRef.current = profileName;
            setSelectedProfile(profileName);
            await onProfileChange?.(profileName);
        }
        catch (error) {
            showErrorToast(t("PROFILE_SWITCH_FAILED", "Failed to switch profile"), String(error));
        }
        finally {
            setIsLoading(false);
        }
    };
    const saveRunningGame = async () => {
        if (!mainRunningApp)
            return;
        setIsLoading(true);
        try {
            const result = await captureGameProfile(String(mainRunningApp.appid), mainRunningApp.display_name, selectedProfile);
            if (!result.success || !result.profile_name) {
                throw new Error(result.error || "Unknown error");
            }
            showSuccessToast(t("PROFILE_GAME_SAVED", "Game profile saved"), result.profile?.processes?.length
                ? `${mainRunningApp.display_name}: ${result.profile.processes.join(", ")}`
                : mainRunningApp.display_name);
            editingProfileRef.current = result.profile_name;
            setSelectedProfile(result.profile_name);
            await notifyProfileChanged(result.profile_name);
        }
        catch (error) {
            showErrorToast(t("PROFILE_GAME_SAVE_FAILED", "Could not save game profile"), String(error));
        }
        finally {
            setIsLoading(false);
        }
    };
    const renameSelectedProfile = async (newName) => {
        setIsLoading(true);
        try {
            const result = await renameProfile(selectedProfile, newName);
            if (!result.success || !result.profile_name) {
                throw new Error(result.error || "Unknown error");
            }
            editingProfileRef.current = result.profile_name;
            setSelectedProfile(result.profile_name);
            await notifyProfileChanged(result.profile_name);
            showSuccessToast(t("PROFILE_RENAMED", "Profile renamed"), newName);
        }
        catch (error) {
            showErrorToast(t("PROFILE_RENAME_FAILED", "Failed to rename profile"), String(error));
        }
        finally {
            setIsLoading(false);
        }
    };
    const deleteSelectedProfile = async () => {
        setIsLoading(true);
        try {
            const deletedName = selectedDetails?.display_name || selectedProfile;
            const result = await deleteProfile(selectedProfile);
            if (!result.success)
                throw new Error(result.error || "Unknown error");
            const nextProfile = result.current_profile || DEFAULT_PROFILE_NAME;
            editingProfileRef.current = nextProfile;
            setSelectedProfile(nextProfile);
            await notifyProfileChanged(nextProfile);
            showSuccessToast(t("PROFILE_DELETED", "Profile deleted"), deletedName);
        }
        catch (error) {
            showErrorToast(t("PROFILE_DELETE_FAILED", "Failed to delete profile"), String(error));
        }
        finally {
            setIsLoading(false);
        }
    };
    const profileOptions = profiles.map((profileName) => {
        const detail = profileDetails.find((item) => item.profile_name === profileName);
        return {
            data: profileName,
            label: detail?.display_name ||
                (profileName === DEFAULT_PROFILE_NAME
                    ? t("PROFILE_DEFAULT", "Default")
                    : profileName),
        };
    });
    return {
        selectedProfile,
        selectedDetails,
        runningProfile,
        profileOptions,
        isLoading,
        switchProfile,
        saveRunningGame,
        renameSelectedProfile,
        deleteSelectedProfile,
    };
}

const PROFILES_COLLAPSED_KEY = "gfg-profiles-collapsed";
function TextInputModal({ title, description, defaultValue = "", okText, cancelText, onOK, closeModal, }) {
    const [value, setValue] = SP_REACT.useState(defaultValue);
    const handleOK = () => {
        if (value.trim()) {
            onOK(value.trim());
            closeModal?.();
        }
    };
    return (window.SP_REACT.createElement(DFL.ModalRoot, null,
        window.SP_REACT.createElement("div", { style: { padding: "16px", minWidth: "400px" } },
            window.SP_REACT.createElement("h2", { style: { marginBottom: "16px" } }, title),
            window.SP_REACT.createElement("p", { style: { marginBottom: "24px" } }, description),
            window.SP_REACT.createElement(DFL.Field, { label: t("PROFILE_NAME_LABEL", "Name"), childrenLayout: "below", childrenContainerWidth: "max" },
                window.SP_REACT.createElement(DFL.TextField, { value: value, onChange: (event) => setValue(event?.target?.value || ""), style: { width: "100%" } })),
            window.SP_REACT.createElement(GFGFocusable, { style: {
                    display: "flex",
                    justifyContent: "flex-end",
                    gap: "8px",
                    marginTop: "24px",
                }, "flow-children": "row" },
                window.SP_REACT.createElement(DFL.DialogButton, { onClick: closeModal }, cancelText),
                window.SP_REACT.createElement(DFL.DialogButton, { onClick: handleOK, disabled: !value.trim() }, okText)))));
}
function ProfileManagement({ editingProfile, onProfileChange, mainRunningApp, topMargin, }) {
    const [focusedAction, setFocusedAction] = SP_REACT.useState(null);
    const [profilesCollapsed, setProfilesCollapsed] = usePersistentCollapseState(PROFILES_COLLAPSED_KEY, false, "profiles");
    const { selectedProfile, selectedDetails, runningProfile, profileOptions, isLoading, switchProfile, saveRunningGame, renameSelectedProfile, deleteSelectedProfile, } = useProfileEditorModel({
        editingProfile,
        onProfileChange,
        mainRunningApp,
    });
    const showRenameProfile = () => {
        if (selectedProfile === DEFAULT_PROFILE_NAME)
            return;
        DFL.showModal(window.SP_REACT.createElement(TextInputModal, { title: t("PROFILE_RENAME_TITLE", "Rename Profile"), description: t("PROFILE_RENAME_DESC_PREFIX", "Choose a friendly name for this game or process profile."), defaultValue: selectedDetails?.display_name || selectedProfile, okText: t("PROFILE_RENAME_BTN", "Rename"), cancelText: t("PROFILE_CANCEL_BTN", "Cancel"), onOK: (name) => void renameSelectedProfile(name) }));
    };
    const showDeleteProfile = () => {
        if (selectedProfile === DEFAULT_PROFILE_NAME)
            return;
        DFL.showModal(window.SP_REACT.createElement(DFL.ConfirmModal, { strTitle: t("PROFILE_DELETE_TITLE", "Delete Game / Process Profile"), strDescription: t("PROFILE_DELETE_CONFIRM", 'Delete "{profile}" and all of its saved settings?', { profile: selectedDetails?.display_name || selectedProfile }), strOKButtonText: t("PROFILE_DELETE_BTN", "Delete"), strCancelButtonText: t("PROFILE_CANCEL_BTN", "Cancel"), onOK: () => void deleteSelectedProfile() }));
    };
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement("style", null, `
        .GFG_ProfilesCollapseButton_Container > div > div > div > button,
        .GFG_ProfilesCollapseButton_Container > div > div > div > div > button {
          height: 10px !important;
        }
      `),
        window.SP_REACT.createElement(GFGSectionHeader, { topMargin: topMargin }, t("PROFILE_SECTION_TITLE", "Game / Process Profiles")),
        window.SP_REACT.createElement(GFGInfo, { as: DFL.PanelSectionRow },
            window.SP_REACT.createElement("div", { "data-gfg-info": "true", style: {
                    fontSize: "11px",
                    lineHeight: "1.35",
                    color: "#c6c8ce",
                    marginBottom: "4px",
                } }, t("PROFILE_HELP", "Save a game's process once for automatic profile selection. Outside a game, the dropdown selects the profile to edit."))),
        mainRunningApp && !runningProfile && (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", { className: "GFG_BrandButton" },
                window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", onClick: () => void saveRunningGame(), disabled: isLoading }, t("PROFILE_SAVE_RUNNING", "Save profile for {game}", {
                    game: mainRunningApp.display_name,
                }))))),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", { className: "GFG_ProfilesCollapseButton_Container", style: { marginTop: "2px", marginBottom: "4px" } },
                window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", bottomSeparator: "none", onClick: () => setProfilesCollapsed(!profilesCollapsed) }, profilesCollapsed ? (window.SP_REACT.createElement(RiArrowDownSFill, { style: { transform: "translate(0, -13px)", fontSize: "1.5em" } })) : (window.SP_REACT.createElement(RiArrowUpSFill, { style: { transform: "translate(0, -12px)", fontSize: "1.5em" } }))))),
        !profilesCollapsed && (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: t("PROFILE_SAVED_LABEL", "Saved profile"), childrenLayout: "below", childrenContainerWidth: "max", bottomSeparator: "none" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: profileOptions, selectedOption: selectedProfile, onChange: (option) => void switchProfile(String(option.data)), disabled: isLoading || !!mainRunningApp }))),
            selectedDetails && (window.SP_REACT.createElement(GFGInfo, { as: DFL.PanelSectionRow },
                window.SP_REACT.createElement("div", { "data-gfg-info": "true", style: {
                        width: "100%",
                        padding: "6px 8px",
                        boxSizing: "border-box",
                        borderRadius: "4px",
                        background: "rgba(255,255,255,0.06)",
                        color: "#c6c8ce",
                        fontSize: "10px",
                        lineHeight: "1.35",
                        overflowWrap: "anywhere",
                    } },
                    window.SP_REACT.createElement("div", null, selectedDetails.kind === PROFILE_KIND_DEFAULT
                        ? t("PROFILE_DETAIL_DEFAULT", "Open a game to save its profile")
                        : selectedDetails.kind === PROFILE_KIND_GAME
                            ? t("PROFILE_DETAIL_GAME", "Saved game")
                            : t("PROFILE_DETAIL_PROCESS", "Saved process")),
                    selectedDetails.steam_app_id && (window.SP_REACT.createElement("div", null, t("PROFILE_STEAM_APP_ID", "Steam app ID: {app_id}", {
                        app_id: selectedDetails.steam_app_id,
                    }))),
                    selectedDetails.kind !== PROFILE_KIND_DEFAULT && (window.SP_REACT.createElement("div", null, selectedDetails.processes.length
                        ? t("PROFILE_PROCESSES", "Processes: {processes}", {
                            processes: selectedDetails.processes.join(", "),
                        })
                        : t("PROFILE_PROCESSES_EMPTY", "Processes: enter one in Matched Processes below"))),
                    mainRunningApp && (window.SP_REACT.createElement("div", { style: { marginTop: "4px", color: "#ffc5bc" } }, t("PROFILE_MANAGE_WHEN_IDLE", "Close the running game to rename or delete profiles.")))))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(GFGSectionTail, null,
                    window.SP_REACT.createElement(GFGFocusable, { style: {
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "stretch",
                            gap: "6px",
                            width: "100%",
                            marginTop: "6px",
                        }, "flow-children": "column", noFocusRing: true },
                        window.SP_REACT.createElement(DFL.DialogButton, { className: "GFG_DialogButton", style: {
                                width: "100%",
                                minWidth: 0,
                                height: "34px",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                gap: "6px",
                                padding: "4px 8px",
                                fontSize: "12px",
                                ...makoDialogButtonStyle(focusedAction === "edit"),
                            }, onClick: showRenameProfile, onGamepadFocus: () => setFocusedAction("edit"), onGamepadBlur: () => setFocusedAction(null), disabled: isLoading ||
                                selectedProfile === DEFAULT_PROFILE_NAME ||
                                !!mainRunningApp },
                            window.SP_REACT.createElement(RiEditLine, { size: 16 }),
                            window.SP_REACT.createElement("span", null, t("PROFILE_RENAME_BTN", "Rename"))),
                        window.SP_REACT.createElement(DFL.DialogButton, { className: "GFG_DialogButton GFG_DialogButton--danger", style: {
                                width: "100%",
                                minWidth: 0,
                                height: "34px",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                gap: "6px",
                                padding: "4px 8px",
                                fontSize: "12px",
                                ...makoDialogButtonStyle(focusedAction === "delete", "danger"),
                            }, onClick: showDeleteProfile, onGamepadFocus: () => setFocusedAction("delete"), onGamepadBlur: () => setFocusedAction(null), disabled: isLoading ||
                                selectedProfile === DEFAULT_PROFILE_NAME ||
                                !!mainRunningApp },
                            window.SP_REACT.createElement(RiDeleteBinLine, { size: 16 }),
                            window.SP_REACT.createElement("span", null, t("PROFILE_DELETE_BTN", "Delete"))))))))));
}

/**
 * Clipboard utilities for reliable copy operations across different environments
 */
/**
 * Reliably copy text to clipboard using multiple fallback methods
 * This is especially important in gaming mode where clipboard APIs may behave differently
 */
async function copyToClipboard(text) {
    const tempInput = document.createElement('input');
    tempInput.value = text;
    tempInput.style.position = 'absolute';
    tempInput.style.left = '-9999px';
    document.body.appendChild(tempInput);
    try {
        tempInput.focus();
        tempInput.select();
        let copySuccess = false;
        try {
            if (document.execCommand('copy')) {
                copySuccess = true;
            }
        }
        catch (e) {
            try {
                await navigator.clipboard.writeText(text);
                copySuccess = true;
            }
            catch (clipboardError) {
                console.error('Both copy methods failed:', e, clipboardError);
            }
        }
        return copySuccess;
    }
    finally {
        document.body.removeChild(tempInput);
    }
}
/**
 * Verify that text was successfully copied to clipboard
 */
async function verifyCopy(expectedText) {
    try {
        const readBack = await navigator.clipboard.readText();
        return readBack === expectedText;
    }
    catch (e) {
        return true;
    }
}
/**
 * Copy text with verification and return success status
 */
async function copyWithVerification(text) {
    const copySuccess = await copyToClipboard(text);
    if (!copySuccess) {
        return { success: false, verified: false };
    }
    const verified = await verifyCopy(text);
    return { success: true, verified };
}

function useClipboardFeedback(getText) {
    const [isLoading, setIsLoading] = SP_REACT.useState(false);
    const [showSuccess, setShowSuccess] = SP_REACT.useState(false);
    SP_REACT.useEffect(() => {
        if (!showSuccess) {
            return undefined;
        }
        const timer = setTimeout(() => setShowSuccess(false), CLIPBOARD_SUCCESS_DURATION_MS);
        return () => clearTimeout(timer);
    }, [showSuccess]);
    const copyToClipboard = async () => {
        if (isLoading || showSuccess) {
            return;
        }
        setIsLoading(true);
        try {
            const text = await getText();
            const { success, verified } = await copyWithVerification(text);
            if (!success) {
                showClipboardErrorToast();
                return;
            }
            setShowSuccess(true);
            if (!verified) {
                console.log("Copy verification failed but copy likely worked");
            }
        }
        catch {
            showClipboardErrorToast();
        }
        finally {
            setIsLoading(false);
        }
    };
    return { isLoading, showSuccess, copyToClipboard };
}

function SmartClipboardButton() {
    const getLaunchOptionText = async () => {
        try {
            const result = await getLaunchOption();
            return result.launch_option || DEFAULT_STEAM_LAUNCH_OPTION;
        }
        catch (error) {
            return DEFAULT_STEAM_LAUNCH_OPTION;
        }
    };
    const { isLoading, showSuccess, copyToClipboard } = useClipboardFeedback(getLaunchOptionText);
    return (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { className: "GFG_BrandButton", style: { marginTop: "16px" } },
            window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", bottomSeparator: "none", onClick: copyToClipboard, disabled: isLoading || showSuccess },
                window.SP_REACT.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
                    showSuccess ? (window.SP_REACT.createElement(FaCheck, { style: { color: "#ff745f" } })) : isLoading ? (window.SP_REACT.createElement(FaClipboard, { style: {
                            animation: "pulse 1s ease-in-out infinite",
                            opacity: 0.7,
                        } })) : (window.SP_REACT.createElement(FaClipboard, null)),
                    window.SP_REACT.createElement("div", { style: {
                            color: showSuccess ? "#ff745f" : "inherit",
                            fontWeight: showSuccess ? "bold" : "normal",
                        } }, showSuccess
                        ? t("CLIPBOARD_COPIED", "Copied to clipboard")
                        : isLoading
                            ? t("CLIPBOARD_COPYING", "Copying...")
                            : t("CLIPBOARD_COPY_LAUNCH", "Copy Launch Option"))))),
        window.SP_REACT.createElement("style", null, `
        @keyframes pulse {
          0% { opacity: 0.7; }
          50% { opacity: 1; }
          100% { opacity: 0.7; }
        }
      `)));
}

function UsageInstructions() {
    const [launchOption, setLaunchOption] = SP_REACT.useState(DEFAULT_STEAM_LAUNCH_OPTION);
    SP_REACT.useEffect(() => {
        getLaunchOption()
            .then((result) => setLaunchOption(result.launch_option || DEFAULT_STEAM_LAUNCH_OPTION))
            .catch(() => undefined);
    }, []);
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGSectionHeader, null, t("USAGE_TITLE", "Usage Instructions")),
        window.SP_REACT.createElement(GFGInfo, { as: DFL.PanelSectionRow },
            window.SP_REACT.createElement("div", { className: "GFG_OptionDescription", "data-gfg-info": "true", style: {
                    fontSize: "12px",
                    lineHeight: "1.4",
                    opacity: "0.8",
                    whiteSpace: "pre-wrap",
                } }, t("USAGE_DESC", "Add this Steam launch option to enable GFG Extreme Frame Generation, Scaling, or both."))),
        window.SP_REACT.createElement(GFGInfo, { as: DFL.PanelSectionRow },
            window.SP_REACT.createElement("div", { className: "GFG_OptionDescription", "data-gfg-info": "true", style: {
                    fontSize: "12px",
                    lineHeight: "1.4",
                    opacity: "0.8",
                    backgroundColor: "rgba(255, 255, 255, 0.1)",
                    padding: "8px",
                    borderRadius: "4px",
                    fontFamily: "monospace",
                    marginTop: "8px",
                    marginBottom: "8px",
                    textAlign: "center",
                } },
                window.SP_REACT.createElement("strong", null, launchOption))),
        window.SP_REACT.createElement(GFGInfo, { as: DFL.PanelSectionRow },
            window.SP_REACT.createElement("div", { className: "GFG_OptionDescription", "data-gfg-info": "true", style: {
                    fontSize: "11px",
                    lineHeight: "1.3",
                    opacity: "0.6",
                    marginTop: "8px",
                } }, t("USAGE_MAKO_CONFIG_NOTE", "This command applies GFG Extreme only to the game you launch with it."))),
        window.SP_REACT.createElement(GFGInfo, { as: DFL.PanelSectionRow },
            window.SP_REACT.createElement("div", { className: "GFG_OptionDescription", "data-gfg-info": "true", style: {
                    fontSize: "11px",
                    lineHeight: "1.3",
                    opacity: "0.6",
                    marginTop: "4px",
                } }, t("USAGE_ISOLATION_NOTE", "Do not combine GFG Extreme with another frame-generation or scaling tool for the same game."))),
        window.SP_REACT.createElement(SmartClipboardButton, null)));
}

function FgmodClipboardButton() {
    const [fgmodExists, setFgmodExists] = SP_REACT.useState(false);
    const [checkingFgmod, setCheckingFgmod] = SP_REACT.useState(true);
    // Check for fgmod directory on component mount
    SP_REACT.useEffect(() => {
        const checkFgmod = async () => {
            try {
                const result = await checkFgmodDirectory();
                setFgmodExists(result.exists);
            }
            catch (error) {
                console.error("Error checking fgmod directory:", error);
                setFgmodExists(false);
            }
            finally {
                setCheckingFgmod(false);
            }
        };
        checkFgmod();
    }, []);
    const getFgmodLaunchOptionText = async () => {
        const launchOption = await getLaunchOption();
        return `~/fgmod/fgmod ${launchOption.launch_option || DEFAULT_STEAM_LAUNCH_OPTION}`;
    };
    const { isLoading, showSuccess, copyToClipboard } = useClipboardFeedback(getFgmodLaunchOptionText);
    // Don't render if fgmod directory doesn't exist or we're still checking
    if (checkingFgmod || !fgmodExists) {
        return null;
    }
    return (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { className: "GFG_BrandButton" },
            window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", bottomSeparator: "none", onClick: copyToClipboard, disabled: isLoading || showSuccess },
                window.SP_REACT.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px" } },
                    showSuccess ? (window.SP_REACT.createElement(FaCheck, { style: { color: "#ff745f" } })) : isLoading ? (window.SP_REACT.createElement(FaClipboard, { style: {
                            animation: "pulse 1s ease-in-out infinite",
                            opacity: 0.7,
                        } })) : (window.SP_REACT.createElement(FaClipboard, null)),
                    window.SP_REACT.createElement("div", { style: {
                            color: showSuccess ? "#ff745f" : "inherit",
                            fontWeight: showSuccess ? "bold" : "normal",
                        } }, showSuccess
                        ? t("CLIPBOARD_COPIED", "Copied to clipboard")
                        : isLoading
                            ? t("CLIPBOARD_COPYING", "Copying...")
                            : t("CLIPBOARD_MAKO_FGMOD", "GFG Extreme + DeckyFG"))))),
        window.SP_REACT.createElement("style", null, `
        @keyframes pulse {
          0% { opacity: 0.7; }
          50% { opacity: 1; }
          100% { opacity: 0.7; }
        }
      `)));
}

const DEFAULT_CONFIGURATION = getDefaults();
const GENERATION_MULTIPLIER_CHOICES = [0, 2, 3, 4, 5];
const GENERATION_MULTIPLIER_SLIDER_MAX = GENERATION_MULTIPLIER_CHOICES.length - 1;
const GENERATION_MULTIPLIER_FOCUS_SELECTOR = "[role='slider'], [role='button'], button, input, select, [tabindex]:not([tabindex='-1'])";
// Steam supports navRef here even though Decky's SliderField type omits it.
const SteamSliderField = DFL.SliderField;
function multiplierSliderPosition(multiplier) {
    const position = GENERATION_MULTIPLIER_CHOICES.findIndex((choice) => choice === multiplier);
    return position >= 0 ? position : 1;
}
function multiplierAtSliderPosition(position) {
    if (!Number.isInteger(position) ||
        position < 0 ||
        position > GENERATION_MULTIPLIER_SLIDER_MAX) {
        return undefined;
    }
    return GENERATION_MULTIPLIER_CHOICES[position];
}
function FpsMultiplierControl({ config, profileName = "", onConfigChange, onConfigUpdate, }) {
    const pendingMultiplierFocus = SP_REACT.useRef();
    const adaptiveMultiplierNavigation = SP_REACT.useRef(null);
    const fixedMultiplierNavigation = SP_REACT.useRef(null);
    const fgBackend = config.fg_backend ?? FG_BACKEND_GFG;
    const optiscalerProxy = config.optiscaler_proxy ?? OPTISCALER_PROXY_AUTO;
    const [backendStatus, setBackendStatus] = SP_REACT.useState(null);
    const backendOptions = [
        { data: FG_BACKEND_GFG, label: t("GFG_BACKEND_GFG", "GFG Engine") },
        { data: FG_BACKEND_OPTISCALER, label: t("GFG_BACKEND_OPTISCALER", "OptiScaler") },
        { data: FG_BACKEND_NATIVE, label: t("GFG_BACKEND_NATIVE", "Game Native") },
        { data: FG_BACKEND_OFF, label: t("GFG_BACKEND_OFF", "Off") },
    ];
    const proxyOptions = OPTISCALER_PROXY_VALUES.map((proxy) => ({
        data: proxy,
        label: proxy === OPTISCALER_PROXY_AUTO
            ? t("GFG_OPTISCALER_PROXY_AUTO", "Auto Detect")
            : `${proxy.toUpperCase()}.dll`,
    }));
    SP_REACT.useEffect(() => {
        let active = true;
        if (fgBackend !== FG_BACKEND_OPTISCALER) {
            setBackendStatus(null);
            return () => { active = false; };
        }
        setBackendStatus(null);
        void getFgBackendStatus(profileName || "")
            .then((result) => { if (active) setBackendStatus(result); })
            .catch(() => { if (active) setBackendStatus({ success: false, optiscaler_status: "not-evaluated" }); });
        return () => { active = false; };
    }, [fgBackend, optiscalerProxy, profileName]);
    const targetFps = config.target_fps;
    const adaptiveMaxMultiplier = config.adaptive_max_multiplier ?? DEFAULT_CONFIGURATION.adaptive_max_multiplier;
    const frameGenerationEnabled = config.frame_generation_enabled ?? DEFAULT_CONFIGURATION.frame_generation_enabled;
    const frameGenerationProvisioned = config.frame_generation_provisioned ?? DEFAULT_CONFIGURATION.frame_generation_provisioned;
    const fixedMultiplier = config.multiplier ?? DEFAULT_CONFIGURATION.multiplier;
    const fractionalAdaptive = isFractionalAdaptivePresetEnabled(config);
    const frameMode = !frameGenerationProvisioned
        ? "off"
        : !config.adaptive
            ? "fixed"
            : fractionalAdaptive
                ? "adaptive-fractional"
                : "adaptive-smooth";
    const frameModeOptions = [
        { data: "off", label: t("GFG_FG_MODE_OFF", "Off") },
        { data: "fixed", label: t("GFG_FG_MODE_FIXED", "Fixed multiplier") },
        { data: "adaptive-smooth", label: t("GFG_FG_MODE_ADAPTIVE_SMOOTH", "Adaptive Smooth") },
        { data: "adaptive-fractional", label: t("GFG_FG_MODE_ADAPTIVE_FRACTIONAL", "Adaptive Fractional") },
    ];
    const displayPolicyOptions = [
        { data: "normal", label: t("GFG_DISPLAY_POLICY_NORMAL", "Standard") },
        { data: "dock-60", label: t("GFG_DISPLAY_POLICY_DOCK", "Automatic Dock · 60 FPS") },
    ];
    const fractionalPriority = (config.adaptive_fractional_real_frame_priority ?? ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_AUTO);
    const fractionalPriorityOptions = [
        { data: ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_AUTO, label: t("ADAPTIVE_REAL_FRAME_PRIORITY_AUTO", "Automatic") },
        [ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_LOW, t("ADAPTIVE_REAL_FRAME_PRIORITY_LOW", "Low")],
        [ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_MEDIUM, t("ADAPTIVE_REAL_FRAME_PRIORITY_MEDIUM", "Medium")],
        [ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_HIGH, t("ADAPTIVE_REAL_FRAME_PRIORITY_HIGH", "High")],
        [ADAPTIVE_FRACTIONAL_REAL_FRAME_PRIORITY_VERY_HIGH, t("ADAPTIVE_REAL_FRAME_PRIORITY_VERY_HIGH", "Very High")],
    ].map((entry) => {
        if (!Array.isArray(entry)) return entry;
        const [data, label] = entry;
        const cap = fractionalRealFramePriorityCap(targetFps, data);
        return { data, label: t("GFG_REAL_FRAME_PRIORITY_OPTION", "{priority} · up to {cap} real FPS", { priority: label, cap: Number(cap.toFixed(1)) }) };
    });
    SP_REACT.useLayoutEffect(() => {
        const pending = pendingMultiplierFocus.current;
        if (!pending) return;
        const navigation = pending.mode === "adaptive" ? adaptiveMultiplierNavigation.current : fixedMultiplierNavigation.current;
        if (navigation?.ChildTakeFocus() || navigation?.TakeFocus()) {
            pendingMultiplierFocus.current = undefined;
            return;
        }
        const container = pending.ownerDocument.querySelector(`.GFG_GenerationMultiplierSlider--${pending.mode}`);
        const target = container?.matches(GENERATION_MULTIPLIER_FOCUS_SELECTOR) ? container : container?.querySelector(GENERATION_MULTIPLIER_FOCUS_SELECTOR);
        target?.focus({ preventScroll: true });
        pendingMultiplierFocus.current = undefined;
    }, [frameGenerationEnabled]);
    const retainMultiplierFocus = (mode, nextEnabled) => {
        if (nextEnabled === frameGenerationEnabled) return;
        const navigation = mode === "adaptive" ? adaptiveMultiplierNavigation.current : fixedMultiplierNavigation.current;
        const activeElement = document.activeElement;
        const container = activeElement?.closest(`.GFG_GenerationMultiplierSlider--${mode}`);
        if (navigation?.BFocusWithin() || (container && activeElement)) {
            pendingMultiplierFocus.current = { mode, ownerDocument: activeElement?.ownerDocument ?? document };
        }
    };
    const selectFrameMode = (mode) => {
        if (mode === "off") {
            void onConfigUpdate({ frame_generation_provisioned: false, frame_generation_enabled: false });
            return;
        }
        const executionEnabled = frameGenerationProvisioned ? frameGenerationEnabled : true;
        if (mode === "fixed") {
            void onConfigUpdate({ frame_generation_provisioned: true, frame_generation_enabled: executionEnabled, adaptive: false });
            return;
        }
        if (mode === "adaptive-fractional") {
            void onConfigUpdate({ frame_generation_provisioned: true, frame_generation_enabled: executionEnabled, ...fractionalAdaptivePresetChanges(true) });
            return;
        }
        void onConfigUpdate({ frame_generation_provisioned: true, frame_generation_enabled: executionEnabled, adaptive: true, adaptive_auto_base_fps_cap: true, dynamic_cadence_recovery: false });
    };
    const backendField = window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement(DFL.Field, { label: window.SP_REACT.createElement(GFGRestartLabel, { label: t("GFG_FG_BACKEND", "Frame Generation Backend (Restart)") }), description: t("GFG_FG_BACKEND_DESC", "Choose who owns Frame Generation for this game. Scaling and shaders remain independent."), childrenLayout: "below", childrenContainerWidth: "max" },
            window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: backendOptions, selectedOption: fgBackend, onChange: (option) => onConfigChange(FG_BACKEND, String(option.data)) })));
    if (fgBackend === FG_BACKEND_OPTISCALER) {
        const detectedProxy = backendStatus?.optiscaler_proxy_detected
            ? `${backendStatus.optiscaler_proxy_detected}.dll`
            : "—";
        const rawStatus = backendStatus?.optiscaler_status ?? "not-evaluated";
        const statusLabel = rawStatus === "ready"
            ? t("GFG_OPTISCALER_STATUS_READY", "Ready")
            : rawStatus === "unverified"
                ? t("GFG_OPTISCALER_STATUS_UNVERIFIED", "Proxy detected (unverified)")
            : rawStatus === "proxy-not-found"
                ? t("GFG_OPTISCALER_STATUS_PROXY_NOT_FOUND", "Proxy not found")
                : rawStatus === "external-override"
                    ? t("GFG_OPTISCALER_STATUS_EXTERNAL_OVERRIDE", "External override detected")
                    : rawStatus === "configuration-conflict"
                        ? t("GFG_OPTISCALER_STATUS_CONFLICT", "Configuration conflict")
                        : t("GFG_OPTISCALER_STATUS_NOT_EVALUATED", "Not evaluated yet");
        const warning = rawStatus === "unverified" || rawStatus === "proxy-not-found" || rawStatus === "external-override" || rawStatus === "configuration-conflict";
        return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            backendField,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: t("GFG_OPTISCALER_PROXY", "Proxy DLL"), description: t("GFG_OPTISCALER_PROXY_DESC", "Auto Detect checks beside the launched game executable, under STEAM_COMPAT_INSTALL_PATH, and in the working directory. Existing Wine overrides are never overwritten."), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: proxyOptions, selectedOption: optiscalerProxy, onChange: (option) => onConfigChange(OPTISCALER_PROXY, String(option.data)) }))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: t("GFG_OPTISCALER_DETECTED", "Detected"), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement("div", { style: { color: "#e6e7ea", fontWeight: 600 } }, detectedProxy))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: t("GFG_OPTISCALER_STATUS", "Status"), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement("div", { style: { color: warning ? "#ffc5bc" : "#e6e7ea", fontWeight: 600 } }, statusLabel),
                    warning && window.SP_REACT.createElement(GFGInlineTip, { tone: "warning", alwaysVisible: true }, rawStatus === "unverified"
                        ? t("GFG_OPTISCALER_PROXY_UNVERIFIED", "A supported proxy-named DLL was found without OptiScaler.ini. It may belong to another tool; verify the game folder or choose the proxy explicitly.")
                        : rawStatus === "proxy-not-found"
                            ? t("GFG_OPTISCALER_PROXY_MISSING", "No matching OptiScaler proxy DLL was found during the last launch probe.")
                        : rawStatus === "external-override"
                            ? t("GFG_OPTISCALER_OVERRIDE_EXTERNAL", "The selected proxy already has a WINEDLLOVERRIDES entry. GFG Extreme preserved the external value instead of replacing it.")
                            : t("GFG_OPTISCALER_CONFLICT_DESC", "The current OptiScaler launch configuration conflicts with an external setting."))))));
    }
    if (fgBackend === FG_BACKEND_NATIVE) {
        return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            backendField,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(GFGInlineTip, { tone: "info", alwaysVisible: true }, t("GFG_NATIVE_FG_DESC", "Frame Generation is controlled by the game. GFG scaling and shaders remain available.")))));
    }
    if (fgBackend === FG_BACKEND_OFF) {
        return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            backendField,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(GFGInlineTip, { tone: "info", alwaysVisible: true }, t("GFG_FG_OFF_DESC", "Frame Generation is disabled. GFG scaling and shaders remain available.")))));
    }
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        backendField,
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement(DFL.Field, { label: window.SP_REACT.createElement(GFGRestartLabel, { label: t("GFG_FG_MODE", "Frame Generation Mode (Restart when enabling/disabling)") }), description: t("GFG_FG_MODE_DESC", "Choose one operating mode instead of managing several overlapping switches. Fixed uses a constant ratio; Adaptive Smooth prioritizes even pacing; Adaptive Fractional keeps more real frames."), childrenLayout: "below", childrenContainerWidth: "max" },
                window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: frameModeOptions, selectedOption: frameMode, onChange: (option) => selectFrameMode(String(option.data)) }))),
        frameGenerationProvisioned && (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: t("GFG_DISPLAY_POLICY", "Display Policy"), description: t("GFG_DISPLAY_POLICY_DESC", "Standard leaves display control alone. Automatic Dock targets a verified 60 Hz external display and restores the handheld profile after disconnect."), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: displayPolicyOptions, selectedOption: config.automatic_dock_mode ? "dock-60" : "normal", onChange: (option) => onConfigChange("automatic_dock_mode", option.data === "dock-60") }))),
            config.adaptive && (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                    window.SP_REACT.createElement(DFL.SliderField, { label: `${t("ADAPTIVE_TARGET_FPS", "Target FPS")} (${targetFps})`, description: t("GFG_TARGET_FPS_DESC", "Target displayed frame rate. When an exact Gamescope mode exists, GFG Extreme can synchronize the display to the same refresh rate."), value: targetFps, min: TARGET_FPS_MIN, max: TARGET_FPS_MAX, step: 1, onChange: (value) => onConfigChange(TARGET_FPS, value) })),
                fractionalAdaptive && (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                    window.SP_REACT.createElement(DFL.Field, { label: t("ADAPTIVE_REAL_FRAME_PRIORITY", "Real Frame Priority"), description: t("GFG_REAL_FRAME_PRIORITY_DESC", "Higher priority preserves more real frames for lower latency; lower priority gives generation more room to hit the target."), childrenLayout: "below", childrenContainerWidth: "max" },
                        window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: fractionalPriorityOptions, selectedOption: fractionalPriority, onChange: (option) => onConfigUpdate(fractionalRealFramePriorityChanges(option.data)) })))),
                window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                    window.SP_REACT.createElement(SteamSliderField, { key: `adaptive-${frameGenerationEnabled ? "active" : "paused"}`, navRef: adaptiveMultiplierNavigation, className: "GFG_GenerationMultiplierSlider GFG_GenerationMultiplierSlider--adaptive", label: `${t("ADAPTIVE_MAX_MULTIPLIER", "Maximum Multiplier")} (${frameGenerationEnabled ? adaptiveMaxMultiplier : 0}x)`, description: t("GFG_ADAPTIVE_MULTIPLIER_DESC", "0x pauses generation live. Otherwise this is the ceiling GFG Extreme may use while pursuing Target FPS."), value: frameGenerationEnabled ? multiplierSliderPosition(adaptiveMaxMultiplier) : 0, min: 0, max: GENERATION_MULTIPLIER_SLIDER_MAX, step: 1, validValues: "steps", minimumDpadGranularity: 1, notchCount: GENERATION_MULTIPLIER_CHOICES.length, notchTicksVisible: true, onChange: (position) => {
                            const value = multiplierAtSliderPosition(position);
                            if (value === 0) {
                                retainMultiplierFocus("adaptive", false);
                                void onConfigChange(FRAME_GENERATION_ENABLED, false);
                            } else if (value !== undefined) {
                                retainMultiplierFocus("adaptive", true);
                                void onConfigUpdate({ frame_generation_enabled: true, adaptive_max_multiplier: value });
                            }
                        } })))),
            !config.adaptive && (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(SteamSliderField, { key: `fixed-${frameGenerationEnabled ? "active" : "paused"}`, navRef: fixedMultiplierNavigation, className: "GFG_GenerationMultiplierSlider GFG_GenerationMultiplierSlider--fixed", label: `${t("FIXED_MULTIPLIER", "Multiplier")} (${frameGenerationEnabled ? fixedMultiplier : 0}x)`, description: t("GFG_FIXED_MULTIPLIER_DESC", "0x pauses generation live. 2x–5x uses a constant output ratio."), value: frameGenerationEnabled ? multiplierSliderPosition(fixedMultiplier) : 0, min: 0, max: GENERATION_MULTIPLIER_SLIDER_MAX, step: 1, validValues: "steps", minimumDpadGranularity: 1, notchCount: GENERATION_MULTIPLIER_CHOICES.length, notchTicksVisible: true, onChange: (position) => {
                        const value = multiplierAtSliderPosition(position);
                        if (value === 0) {
                            retainMultiplierFocus("fixed", false);
                            void onConfigChange(FRAME_GENERATION_ENABLED, false);
                        } else if (value !== undefined) {
                            retainMultiplierFocus("fixed", true);
                            void onConfigUpdate({ frame_generation_enabled: true, multiplier: value });
                        }
                    } })))))));
}
function ScalingControl({ config, disabled = false, runtimeActivationSupported = null, runtimeInactiveReason = null, runtimeFactorCeiling = null, modelCompatible = null, runtimeRequestedMethod = null, runtimeGFGFallback = false, runtimeActiveMethod = null, onConfigChange, onConfigUpdate, }) {
    const effectiveScalingMethod$1 = effectiveScalingMethod(config);
    const scalerActive = config.scaling_enabled && effectiveScalingMethod$1 !== SCALING_METHOD_NATIVE;
    const ls1Selected = config.scaling_enabled && (effectiveScalingMethod$1 === SCALING_METHOD_LS1 || effectiveScalingMethod$1 === SCALING_METHOD_LS1_PERFORMANCE);
    const activeFallback = runtimeGFGFallback && runtimeRequestedMethod === effectiveScalingMethod$1;
    const modelUnavailable = modelCompatible === false && runtimeActiveMethod !== effectiveScalingMethod$1;
    const runningSurfaceUnsupported = runtimeActivationSupported === false || runtimeInactiveReason === "gamescope-wsi-surface-unproven";
    const unavailableControlClassName = runningSurfaceUnsupported ? "GFG_ScalingUnavailableControl" : undefined;
    const steppedRuntimeCeiling = runtimeFactorCeiling === null ? null : Math.max(SCALING_FACTOR_MIN, Math.min(SCALING_FACTOR_MAX, Math.floor((runtimeFactorCeiling + 0.0001) * 10) / 10));
    const factorMaximum = !config.scaling_supersampling && steppedRuntimeCeiling !== null ? steppedRuntimeCeiling : SCALING_FACTOR_MAX;
    const displayedFactor = Math.min(config.scaling_factor, factorMaximum);
    const factorLimited = !config.scaling_supersampling && factorMaximum < SCALING_FACTOR_MAX;
    const factorHasNoHeadroom = !config.scaling_supersampling && factorMaximum <= SCALING_FACTOR_MIN + 0.0001;
    const selectedScalingMode = config.scaling_enabled ? effectiveScalingMethod$1 : "off";
    const scalingModeOptions = [
        { data: "off", label: t("GFG_SCALING_OFF", "Off") },
        ...(config.ultra_performance ? [] : [{ data: SCALING_METHOD_MAKO, label: t("GFG_SCALER", "GFG Scaler") }, { data: SCALING_METHOD_LS1, label: t("SCALING_METHOD_LS1", "LS1 Quality") }]),
        { data: SCALING_METHOD_LS1_PERFORMANCE, label: t("SCALING_METHOD_LS1_PERFORMANCE", "LS1 Performance") },
    ];
    const outputModeOptions = [
        { data: "standard", label: t("GFG_SCALING_OUTPUT_STANDARD", "Standard upscale") },
        { data: "supersampling", label: t("GFG_SCALING_OUTPUT_SUPERSAMPLING", "Quality supersampling") },
    ];
    const selectScalingMode = (mode) => {
        if (mode === "off") {
            void onConfigUpdate({ scaling_enabled: false });
            return;
        }
        void onConfigUpdate({ scaling_enabled: true, scaling_method: mode });
    };
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement("style", null, `
        .GFG_ScalingUnavailableControl { filter: grayscale(1); opacity: .72; }
      `),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement(DFL.Field, { label: window.SP_REACT.createElement(GFGExperimentalSettingLabel, { label: t("GFG_SCALING_MODE", "Scaling Mode (Restart when enabling/disabling)"), badgeLabel: t("EXPERIMENTAL_LABEL", "Experimental") }), description: t("GFG_SCALING_MODE_DESC", "Choose the scaler directly. Off unloads the scaling path on the next launch; changing between active models is live."), childrenLayout: "below", childrenContainerWidth: "max" },
                window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: scalingModeOptions, selectedOption: selectedScalingMode, disabled: disabled, onChange: (option) => selectScalingMode(String(option.data)) }),
                ls1Selected && (activeFallback || modelUnavailable) && (window.SP_REACT.createElement(GFGInlineTip, { tone: "warning" }, activeFallback
                    ? t("SCALING_LS1_ACTIVE_FALLBACK", "LS1 is unavailable for this game. GFG Scaler is active and your LS1 selection is preserved.")
                    : t("SCALING_LS1_UNAVAILABLE", "LS1 failed the availability check. GFG Scaler takes over if LS1 cannot load."))))),
        config.scaling_enabled && (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement("div", { className: unavailableControlClassName, style: { width: "100%" } },
                    window.SP_REACT.createElement(DFL.Field, { label: t("GFG_SCALING_OUTPUT", "Output Policy"), description: t("GFG_SCALING_OUTPUT_DESC", "Standard respects the display target. Quality supersampling may render above it for cleaner downsampling, at higher GPU and memory cost."), childrenLayout: "below", childrenContainerWidth: "max" },
                        window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: outputModeOptions, selectedOption: config.scaling_supersampling ? "supersampling" : "standard", disabled: disabled || runningSurfaceUnsupported, onChange: (option) => onConfigChange(SCALING_SUPERSAMPLING, option.data === "supersampling") })))),
            runningSurfaceUnsupported && (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(GFGInlineTip, { tone: "warning" }, t("SCALING_RUNTIME_SURFACE_UNSUPPORTED", "This running surface does not support GFG scaling. Scale Factor and Sharpness are locked until a supported surface is detected.")))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.SliderField, { label: `${t("SCALING_FACTOR", "Scale Factor")} (${displayedFactor.toFixed(1)}x${factorLimited ? ` ${t("SCALING_FACTOR_LIMIT_SUFFIX", "display limit")}` : ""})`, description: window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                        window.SP_REACT.createElement("span", null, t("GFG_SCALING_FACTOR_DESC", "Lower the in-game render resolution first, then use this factor to scale the image back toward the display resolution.")),
                        factorLimited && (window.SP_REACT.createElement(GFGInlineTip, { tone: "info" }, factorHasNoHeadroom
                            ? t("SCALING_FACTOR_NO_HEADROOM", "This input already fills the display target. Lower the in-game resolution or use Quality supersampling.")
                            : t("SCALING_FACTOR_DEVICE_LIMIT", "Current display limit: {factor}x. Your saved {saved}x value is preserved.", { factor: factorMaximum.toFixed(1), saved: config.scaling_factor.toFixed(1) })))), value: displayedFactor, min: SCALING_FACTOR_MIN, max: factorMaximum, step: 0.1, validValues: "steps", minimumDpadGranularity: 0.1, notchCount: factorHasNoHeadroom ? 3 : Math.round((factorMaximum - SCALING_FACTOR_MIN) / 0.1) + 1, notchTicksVisible: true, className: unavailableControlClassName, disabled: disabled || runningSurfaceUnsupported || factorHasNoHeadroom, onChange: (value) => onConfigChange(SCALING_FACTOR, Number(value.toFixed(1))) })),
            scalerActive && (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.SliderField, { label: `${t("SCALING_SHARPNESS", "Sharpness")} (${Math.round(config.scaling_sharpness * 100)}%)`, description: t("GFG_SCALING_SHARPNESS_DESC", "Adjust the scaler's sharpening strength after scaling."), value: config.scaling_sharpness, min: SCALING_SHARPNESS_MIN, max: SCALING_SHARPNESS_MAX, step: 0.01, className: unavailableControlClassName, disabled: disabled || runningSurfaceUnsupported, bottomSeparator: "none", onChange: (value) => onConfigChange(SCALING_SHARPNESS, Number(value.toFixed(2))) })))))));
}
// THIS FILE IS AUTO GENERATED
function MdBolt (props) {
  return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 24 24"},"child":[{"tag":"path","attr":{"d":"M11 21h-1l1-7H7.5c-.58 0-.57-.32-.38-.66.19-.34.05-.08.07-.12C8.48 10.94 10.42 7.54 13 3h1l-1 7h3.5c.49 0 .56.33.47.51l-.07.15C12.96 17.55 11 21 11 21z"},"child":[]}]})(props);
}

function PerformanceConfigurationGroup({ config, onConfigChange, onConfigUpdate, }) {
    const [collapsed, setCollapsed] = usePersistentCollapseState("gfg-engine-tuning-collapsed", true, "engine tuning");
    const renderPresetOptions = [
        { data: "standard", label: t("GFG_ENGINE_PRESET_STANDARD", "Standard") },
        { data: "ultra", label: t("CONFIG_ULTRA_PERFORMANCE", "Ultra Performance") },
    ];
    const modelOptions = [
        { data: "quality", label: t("GFG_FG_MODEL_QUALITY", "Quality") },
        { data: "light", label: t("CONFIG_PERFORMANCE_MODE", "Lighter") },
    ];
    const precisionOptions = [
        { data: "fp16", label: t("GFG_PRECISION_FP16", "FP16 · faster") },
        { data: "fp32", label: t("GFG_PRECISION_FP32", "FP32 · compatibility") },
    ];
    const pacingOptions = [
        { data: "smooth", label: t("GFG_PACING_SMOOTH", "Smooth cadence") },
        { data: "responsive", label: t("GFG_PACING_RESPONSIVE", "Responsive") },
    ];
    const vrrOptions = [
        { data: "follow-steam", label: t("GAMESCOPE_VRR_FOLLOW_STEAM", "Follow Steam") },
        { data: "on", label: t("GAMESCOPE_VRR_ON", "On") },
        { data: "off", label: t("GAMESCOPE_VRR_OFF", "Off") },
    ];
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGSectionHeader, null, t("GFG_ENGINE_TUNING", "Engine Tuning")),
        window.SP_REACT.createElement(CollapseControl, { containerClassName: "GFG_EngineTuningCollapseButton_Container", collapsed: collapsed, onToggle: () => setCollapsed(!collapsed) }),
        !collapsed && (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: window.SP_REACT.createElement(GFGRestartLabel, { label: t("GFG_ENGINE_PRESET", "Renderer Preset (Restart)") }), description: t("GFG_ENGINE_PRESET_DESC", "Standard leaves quality controls independent. Ultra Performance applies the existing low-GPU-cost preset as one choice instead of several switches."), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: renderPresetOptions, selectedOption: config.ultra_performance ? "ultra" : "standard", onChange: (option) => onConfigUpdate(ultraPerformanceChanges(option.data === "ultra")) }))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: t("GFG_FG_MODEL", "Frame Generation Model"), description: t("CONFIG_PERFORMANCE_MODE_DESC", "The lighter model lowers GPU cost at the expense of more artifacts."), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: modelOptions, selectedOption: (config.ultra_performance || config.performance_mode) ? "light" : "quality", disabled: config.ultra_performance, onChange: (option) => onConfigChange(PERFORMANCE_MODE, option.data === "light") }))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.SliderField, { label: `${t("CONFIG_FLOW_SCALE", "Motion Analysis")} (${Math.round((config.ultra_performance ? ULTRA_PERFORMANCE_FLOW_SCALE : config.flow_scale) * 100)}%)`, description: t("CONFIG_FLOW_SCALE_DESC", "Lower values reduce GPU work; higher values favor motion quality."), value: config.ultra_performance ? ULTRA_PERFORMANCE_FLOW_SCALE : config.flow_scale, min: FLOW_SCALE_MIN, max: FLOW_SCALE_MAX, step: 0.01, disabled: config.ultra_performance, onChange: (value) => onConfigChange(FLOW_SCALE, value) })),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: window.SP_REACT.createElement(GFGRestartLabel, { label: t("GFG_PRECISION", "Precision (Restart)") }), description: t("GFG_PRECISION_DESC", "FP16 is faster on supported GPUs. FP32 is the compatibility path for hardware that dislikes FP16."), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: precisionOptions, selectedOption: (config.ultra_performance || config.allow_fp16) ? "fp16" : "fp32", disabled: config.ultra_performance, onChange: (option) => onConfigChange(ALLOW_FP16, option.data === "fp16") }))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: t("GFG_PACING", "Frame Pacing"), description: t("GFG_PACING_DESC", "Smooth cadence favors even presentation. Responsive keeps more freedom for real frames and latency."), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: pacingOptions, selectedOption: (config.adaptive_stable_cadence ?? DEFAULT_CONFIGURATION.adaptive_stable_cadence) ? "smooth" : "responsive", onChange: (option) => onConfigChange(ADAPTIVE_STABLE_CADENCE, option.data === "smooth") }))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: t("GAMESCOPE_VRR_MODE", "Gamescope VRR"), description: t("GAMESCOPE_VRR_MODE_DESC", "Follow Steam is the safe default; force On or Off only for a profile that benefits from it."), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: vrrOptions, selectedOption: config.gamescope_vrr_mode ?? "follow-steam", onChange: (option) => onConfigChange(GAMESCOPE_VRR_MODE, option.data) })))))));
}
/** Find the nearest vertical scroller that owns a focused settings control. */
function findFocusScrollContainer(element) {
    const view = element.ownerDocument.defaultView;
    for (let parent = element.parentElement; parent; parent = parent.parentElement) {
        if (parent.scrollHeight > parent.clientHeight &&
            /auto|scroll|overlay/.test(view?.getComputedStyle(parent).overflowY ?? "")) {
            return parent;
        }
    }
    return element.ownerDocument.scrollingElement;
}

const EFFECTS_PER_PAGE = 5;
const EFFECT_ROW_HEIGHT = 38;
const EFFECT_ROW_GAP = 2;
function EffectsChecklist({ options, initialSelection, onChange, }) {
    const [selected, setSelected] = SP_REACT.useState(initialSelection);
    const [expanded, setExpanded] = SP_REACT.useState(false);
    const [page, setPage] = SP_REACT.useState(0);
    const [focusedEffect, setFocusedEffect] = SP_REACT.useState(null);
    const [hoveredEffect, setHoveredEffect] = SP_REACT.useState(null);
    const [focusedAction, setFocusedAction] = SP_REACT.useState(null);
    const [hoveredAction, setHoveredAction] = SP_REACT.useState(null);
    const checklistRef = SP_REACT.useRef(null);
    const focusAnchor = SP_REACT.useRef();
    const pendingPageFocusRow = SP_REACT.useRef();
    const pendingSave = SP_REACT.useRef(Promise.resolve());
    const selectionValue = initialSelection.join(":");
    const effects = options.filter((option) => option.data !== VKBASALT_SHADER_NONE);
    const pageCount = Math.max(1, Math.ceil(effects.length / EFFECTS_PER_PAGE));
    SP_REACT.useEffect(() => {
        setSelected(initialSelection);
    }, [selectionValue]);
    SP_REACT.useLayoutEffect(() => {
        if (expanded)
            return;
        const anchor = focusAnchor.current;
        if (!anchor)
            return;
        if (anchor.target.isConnected) {
            anchor.target.focus({ preventScroll: true });
            if (anchor.scroller) {
                anchor.scroller.scrollTop +=
                    anchor.target.getBoundingClientRect().top - anchor.top;
            }
        }
        focusAnchor.current = undefined;
    }, [expanded]);
    SP_REACT.useLayoutEffect(() => {
        const requestedRow = pendingPageFocusRow.current;
        if (requestedRow === undefined)
            return;
        const effectCount = Math.min(EFFECTS_PER_PAGE, Math.max(0, effects.length - page * EFFECTS_PER_PAGE));
        if (effectCount === 0) {
            pendingPageFocusRow.current = undefined;
            return;
        }
        const targetRow = Math.min(requestedRow, effectCount - 1);
        const target = checklistRef.current?.querySelector(`[data-gfg-effect-row="${targetRow}"]`);
        target?.focus({ preventScroll: true });
        pendingPageFocusRow.current = undefined;
    }, [effects.length, page]);
    const updateSelection = (next) => {
        setSelected(next);
        const value = next.join(":") || VKBASALT_SHADER_NONE;
        pendingSave.current = pendingSave.current
            .catch(() => { })
            .then(() => onChange(value));
    };
    const closeAfterFocusLeaves = () => {
        if (!expanded)
            return;
        window.setTimeout(() => {
            const checklist = checklistRef.current;
            const activeElement = checklist?.ownerDocument
                .activeElement;
            if (checklist &&
                !checklist.contains(activeElement) &&
                !checklist.querySelector(".gfg-effects-focus-within")) {
                if (activeElement && activeElement !== checklist.ownerDocument.body) {
                    focusAnchor.current = {
                        target: activeElement,
                        top: activeElement.getBoundingClientRect().top,
                        scroller: findFocusScrollContainer(activeElement),
                    };
                }
                setExpanded(false);
                setFocusedEffect(null);
                setFocusedAction(null);
            }
        }, 0);
    };
    const actionStyle = (action, disabled = false) => {
        const highlighted = focusedAction === action || hoveredAction === action;
        return {
            boxSizing: "border-box",
            display: "grid",
            placeItems: "center",
            height: "34px",
            minHeight: "34px",
            padding: "0 9px",
            border: "1px solid rgba(255, 81, 61, 0.24)",
            borderRadius: "5px",
            background: highlighted
                ? "rgba(255, 81, 61, 0.42)"
                : "rgba(37, 19, 21, 0.46)",
            outline: highlighted ? "2px solid #ff745f" : "2px solid transparent",
            outlineOffset: "-2px",
            color: "#f5f7fa",
            textAlign: "center",
            lineHeight: 1,
            opacity: disabled ? 0.45 : 1,
        };
    };
    const actionFocusProps = (action) => ({
        onFocus: () => setFocusedAction(action),
        onBlur: () => setFocusedAction(null),
        onGamepadFocus: () => setFocusedAction(action),
        onGamepadBlur: () => setFocusedAction(null),
        onMouseEnter: () => setHoveredAction(action),
        onMouseLeave: () => setHoveredAction(null),
    });
    const changePage = (direction) => {
        setPage((current) => Math.min(pageCount - 1, Math.max(0, current + direction)));
    };
    const onPageButtonDown = (event) => {
        if (event.detail.button !== DFL.GamepadButton.DIR_LEFT &&
            event.detail.button !== DFL.GamepadButton.DIR_RIGHT) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        changePage(event.detail.button === DFL.GamepadButton.DIR_LEFT ? -1 : 1);
    };
    const changePageFromEffect = (direction, row) => {
        const nextPage = Math.min(pageCount - 1, Math.max(0, page + direction));
        if (nextPage === page)
            return;
        const nextPageEffectCount = Math.min(EFFECTS_PER_PAGE, Math.max(0, effects.length - nextPage * EFFECTS_PER_PAGE));
        const targetRow = Math.min(row, Math.max(0, nextPageEffectCount - 1));
        const targetEffect = effects[nextPage * EFFECTS_PER_PAGE + targetRow];
        if (!targetEffect)
            return;
        if (targetRow !== row) {
            pendingPageFocusRow.current = targetRow;
        }
        setFocusedEffect(targetEffect.data);
        setHoveredEffect(null);
        setPage(nextPage);
    };
    const onEffectPageButtonDown = (event, row) => {
        if (event.detail.button !== DFL.GamepadButton.DIR_LEFT &&
            event.detail.button !== DFL.GamepadButton.DIR_RIGHT) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        changePageFromEffect(event.detail.button === DFL.GamepadButton.DIR_LEFT ? -1 : 1, row);
    };
    const summaryHighlighted = focusedAction === "summary" || hoveredAction === "summary";
    const collapseToSummary = () => {
        checklistRef.current
            ?.querySelector('[data-gfg-effects-summary="true"]')
            ?.focus({ preventScroll: true });
        setExpanded(false);
        setFocusedEffect(null);
        setFocusedAction("summary");
    };
    const handleExpandedCancel = (event) => {
        event.preventDefault();
        event.stopPropagation();
        collapseToSummary();
    };
    return (window.SP_REACT.createElement("div", { ref: checklistRef, "data-testid": "gfg-effects-selector", style: {
            boxSizing: "border-box",
            width: "100%",
            marginTop: "8px",
            paddingBottom: expanded ? "8px" : "0px",
        } },
        window.SP_REACT.createElement(GFGFocusable, { "flow-children": "column", focusWithinClassName: "gfg-effects-focus-within", onBlur: closeAfterFocusLeaves, onGamepadBlur: closeAfterFocusLeaves, ...(expanded ? { onCancel: handleExpandedCancel } : {}), style: { width: "100%" } },
            window.SP_REACT.createElement(GFGFocusable, { "data-gfg-effects-summary": "true", role: "button", tabIndex: 0, "aria-expanded": expanded, onClick: () => setExpanded(!expanded), onActivate: () => setExpanded(!expanded), ...actionFocusProps("summary"), style: {
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    boxSizing: "border-box",
                    width: "100%",
                    minHeight: "40px",
                    padding: "7px 12px",
                    border: summaryHighlighted
                        ? "1px solid rgba(255, 116, 95, 0.80)"
                        : "1px solid rgba(255, 81, 61, 0.26)",
                    borderRadius: "7px",
                    background: summaryHighlighted
                        ? "rgba(255, 81, 61, 0.42)"
                        : "rgba(37, 19, 21, 0.72)",
                    outline: summaryHighlighted
                        ? "2px solid #ff745f"
                        : "2px solid transparent",
                    outlineOffset: "-2px",
                    color: "#f5f7fa",
                    fontSize: "14px",
                } },
                window.SP_REACT.createElement("span", { style: {
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        width: "100%",
                    } },
                    window.SP_REACT.createElement("span", null, expanded
                        ? t("CONFIG_VKBASALT_EFFECTS_DONE", "Done")
                        : t("CONFIG_VKBASALT_EFFECTS_SELECTED", "Choose effects ({value} selected)", {
                            value: selected.length,
                        })),
                    expanded ? (window.SP_REACT.createElement(RiArrowUpSFill, { "aria-hidden": "true" })) : (window.SP_REACT.createElement(RiArrowDownSFill, { "aria-hidden": "true" })))),
            expanded && (window.SP_REACT.createElement("div", { "data-testid": "gfg-effects-list", style: {
                    width: "100%",
                    boxSizing: "border-box",
                    marginTop: "6px",
                    padding: "4px",
                    border: "1px solid rgba(255, 81, 61, 0.18)",
                    borderRadius: "7px",
                    background: "rgba(14, 15, 19, 0.48)",
                } },
                window.SP_REACT.createElement(GFGFocusable, { "flow-children": "column", style: { display: "flex", flexDirection: "column", gap: "2px" } },
                    window.SP_REACT.createElement("div", { "data-testid": "gfg-effects-page", style: {
                            display: "flex",
                            flexDirection: "column",
                            gap: `${EFFECT_ROW_GAP}px`,
                            height: `${EFFECTS_PER_PAGE * EFFECT_ROW_HEIGHT +
                                (EFFECTS_PER_PAGE - 1) * EFFECT_ROW_GAP}px`,
                        } }, effects
                        .slice(page * EFFECTS_PER_PAGE, (page + 1) * EFFECTS_PER_PAGE)
                        .map((option, row) => {
                        const order = selected.indexOf(option.data);
                        const enabled = order !== -1;
                        const highlighted = focusedEffect === option.data ||
                            hoveredEffect === option.data;
                        const toggleEffect = () => updateSelection(enabled
                            ? selected.filter((effect) => effect !== option.data)
                            : [...selected, option.data]);
                        return (window.SP_REACT.createElement(GFGFocusable, { key: row, role: "checkbox", tabIndex: 0, "data-gfg-effect-row": row, "aria-checked": enabled, "aria-label": enabled
                                ? `${order + 1}. ${option.label}`
                                : option.label, onClick: toggleEffect, onActivate: toggleEffect, onButtonDown: (event) => onEffectPageButtonDown(event, row), onKeyDown: (event) => {
                                if (event.key !== "ArrowLeft" &&
                                    event.key !== "ArrowRight") {
                                    return;
                                }
                                event.preventDefault();
                                event.stopPropagation();
                                changePageFromEffect(event.key === "ArrowLeft" ? -1 : 1, row);
                            }, onFocus: () => setFocusedEffect(option.data), onBlur: () => setFocusedEffect(null), onGamepadFocus: () => setFocusedEffect(option.data), onGamepadBlur: () => setFocusedEffect(null), onMouseEnter: () => setHoveredEffect(option.data), onMouseLeave: () => setHoveredEffect(null), style: {
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                boxSizing: "border-box",
                                width: "100%",
                                height: `${EFFECT_ROW_HEIGHT}px`,
                                minHeight: `${EFFECT_ROW_HEIGHT}px`,
                                flex: `0 0 ${EFFECT_ROW_HEIGHT}px`,
                                padding: "6px 9px",
                                borderRadius: "5px",
                                background: highlighted
                                    ? "rgba(255, 81, 61, 0.42)"
                                    : enabled
                                        ? "rgba(255, 81, 61, 0.20)"
                                        : "transparent",
                                outline: highlighted
                                    ? "2px solid #ff745f"
                                    : "2px solid transparent",
                                outlineOffset: "-2px",
                                color: "#f5f7fa",
                                fontSize: "13px",
                            } },
                            window.SP_REACT.createElement("span", { style: {
                                    minWidth: 0,
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                } }, enabled
                                ? `${order + 1}. ${option.label}`
                                : option.label),
                            window.SP_REACT.createElement("span", { "aria-hidden": "true", style: {
                                    display: "grid",
                                    placeItems: "center",
                                    width: "18px",
                                    height: "18px",
                                    flex: "0 0 18px",
                                    marginLeft: "8px",
                                    border: `1px solid ${enabled ? "#ff745f" : "rgba(255, 197, 188, 0.50)"}`,
                                    borderRadius: "4px",
                                    background: enabled ? "#ff513d" : "transparent",
                                    fontSize: "12px",
                                    fontWeight: 700,
                                } }, enabled ? "✓" : "")));
                    })),
                    window.SP_REACT.createElement(GFGFocusable, { role: "button", tabIndex: 0, "aria-label": t("CONFIG_VKBASALT_SHADER", "Effects"), "aria-description": `${page + 1} / ${pageCount}`, onActivate: () => changePage(1), onButtonDown: onPageButtonDown, onKeyDown: (event) => {
                            if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") {
                                return;
                            }
                            event.preventDefault();
                            event.stopPropagation();
                            changePage(event.key === "ArrowLeft" ? -1 : 1);
                        }, ...actionFocusProps("pager"), style: {
                            ...actionStyle("pager"),
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            gap: "6px",
                            width: "100%",
                            marginTop: "5px",
                            padding: 0,
                        } },
                        window.SP_REACT.createElement("span", { "aria-hidden": "true", "data-testid": "gfg-effects-previous-page", title: t("CONFIG_VKBASALT_EFFECTS_PREVIOUS_PAGE", "Previous effects page"), onClick: () => changePage(-1), style: {
                                display: "grid",
                                placeItems: "center",
                                alignSelf: "stretch",
                                width: "42px",
                                cursor: page === 0 ? "default" : "pointer",
                                opacity: page === 0 ? 0.45 : 1,
                            } }, "\u2039"),
                        window.SP_REACT.createElement("span", { "aria-live": "polite", style: { fontSize: "12px", opacity: 0.75 } },
                            page + 1,
                            " / ",
                            pageCount),
                        window.SP_REACT.createElement("span", { "aria-hidden": "true", "data-testid": "gfg-effects-next-page", title: t("CONFIG_VKBASALT_EFFECTS_NEXT_PAGE", "Next effects page"), onClick: () => changePage(1), style: {
                                display: "grid",
                                placeItems: "center",
                                alignSelf: "stretch",
                                width: "42px",
                                cursor: page === pageCount - 1 ? "default" : "pointer",
                                opacity: page === pageCount - 1 ? 0.45 : 1,
                            } }, "\u203A")),
                    window.SP_REACT.createElement(GFGFocusable, { role: "button", tabIndex: 0, "aria-disabled": selected.length === 0, onClick: () => selected.length > 0 && updateSelection([]), onActivate: () => selected.length > 0 && updateSelection([]), ...actionFocusProps("clear"), style: {
                            ...actionStyle("clear", selected.length === 0),
                            alignSelf: "stretch",
                            width: "100%",
                            marginTop: "8px",
                            fontSize: "12px",
                        } }, t("CONFIG_VKBASALT_EFFECTS_CLEAR", "Clear all"))))))));
}

function ShadersConfigurationGroup({ config, isDefaultProfile, profileName, vkBasaltConfigPath, onConfigChange, }) {
    const vkBasaltEnabled = config.external_vulkan_layer === EXTERNAL_VULKAN_LAYER_VKBASALT;
    const sharpeningEnabled = config.vkbasalt_sharpening !== VKBASALT_SHARPENING_NONE;
    const displayedConfigPath = vkBasaltConfigPath ||
        (isDefaultProfile
            ? "~/.config/vkBasalt/vkBasalt.conf"
            : "~/.config/mako-render/vkbasalt/<profile>.conf");
    const selectedEffects = config.vkbasalt_shader === VKBASALT_SHADER_NONE
        ? []
        : config.vkbasalt_shader.split(":");
    const sharpeningOptions = [
        {
            data: VKBASALT_SHARPENING_NONE,
            label: t("CONFIG_VKBASALT_EFFECT_NONE", "Off"),
        },
        {
            data: VKBASALT_SHARPENING_CAS,
            label: t("CONFIG_VKBASALT_SHARPENING_CAS", "CAS"),
        },
        {
            data: VKBASALT_SHARPENING_DLS,
            label: t("CONFIG_VKBASALT_SHARPENING_DLS", "DLS"),
        },
    ];
    const antialiasingOptions = [
        {
            data: VKBASALT_ANTIALIASING_NONE,
            label: t("CONFIG_VKBASALT_EFFECT_NONE", "Off"),
        },
        {
            data: VKBASALT_ANTIALIASING_FXAA,
            label: t("CONFIG_VKBASALT_ANTIALIASING_FXAA", "FXAA"),
        },
        {
            data: VKBASALT_ANTIALIASING_SMAA,
            label: t("CONFIG_VKBASALT_ANTIALIASING_SMAA", "SMAA"),
        },
    ];
    const shaderOptions = [
        {
            data: VKBASALT_SHADER_NONE,
            label: t("CONFIG_VKBASALT_EFFECT_NONE", "Off"),
        },
        {
            data: VKBASALT_SHADER_HDR_LOOK,
            label: t("CONFIG_VKBASALT_SHADER_HDR_LOOK", "HDR Look (SDR)"),
        },
        {
            data: VKBASALT_SHADER_CLARITY,
            label: t("CONFIG_VKBASALT_SHADER_CLARITY", "Clarity"),
        },
        {
            data: VKBASALT_SHADER_LEVELS_PLUS,
            label: t("CONFIG_VKBASALT_SHADER_LEVELS_PLUS", "Levels Plus"),
        },
        {
            data: VKBASALT_SHADER_VIBRANCE,
            label: t("CONFIG_VKBASALT_SHADER_VIBRANCE", "Vibrance"),
        },
        {
            data: VKBASALT_SHADER_COLOURFULNESS,
            label: t("CONFIG_VKBASALT_SHADER_COLOURFULNESS", "Colourfulness"),
        },
        {
            data: VKBASALT_SHADER_CURVES,
            label: t("CONFIG_VKBASALT_SHADER_CURVES", "Curves"),
        },
        {
            data: VKBASALT_SHADER_DEBAND,
            label: t("CONFIG_VKBASALT_SHADER_DEBAND", "Deband"),
        },
        {
            data: VKBASALT_SHADER_TECHNICOLOR2,
            label: t("CONFIG_VKBASALT_SHADER_TECHNICOLOR2", "Technicolor 2"),
        },
        {
            data: VKBASALT_SHADER_DPX,
            label: t("CONFIG_VKBASALT_SHADER_DPX", "DPX / Cineon"),
        },
        {
            data: VKBASALT_SHADER_BLEACH_BYPASS,
            label: t("CONFIG_VKBASALT_SHADER_BLEACH_BYPASS", "Bleach Bypass"),
        },
        {
            data: VKBASALT_SHADER_NOIR,
            label: t("CONFIG_VKBASALT_SHADER_NOIR", "Noir"),
        },
        {
            data: VKBASALT_SHADER_TECHNICOLOR,
            label: t("CONFIG_VKBASALT_SHADER_TECHNICOLOR", "Technicolor"),
        },
        {
            data: VKBASALT_SHADER_MONOCHROME,
            label: t("CONFIG_VKBASALT_SHADER_MONOCHROME", "Monochrome"),
        },
        {
            data: VKBASALT_SHADER_SEPIA,
            label: t("CONFIG_VKBASALT_SHADER_SEPIA", "Sepia"),
        },
        {
            data: VKBASALT_SHADER_FILM_GRAIN,
            label: t("CONFIG_VKBASALT_SHADER_FILM_GRAIN", "Film Grain"),
        },
        {
            data: VKBASALT_SHADER_VIGNETTE,
            label: t("CONFIG_VKBASALT_SHADER_VIGNETTE", "Vignette"),
        },
        {
            data: VKBASALT_SHADER_CARTOON,
            label: t("CONFIG_VKBASALT_SHADER_CARTOON", "Cartoon"),
        },
        {
            data: VKBASALT_SHADER_NOSTALGIA,
            label: t("CONFIG_VKBASALT_SHADER_NOSTALGIA", "Nostalgia"),
        },
        {
            data: VKBASALT_SHADER_CHROMATIC_ABERRATION,
            label: t("CONFIG_VKBASALT_SHADER_CHROMATIC_ABERRATION", "Chromatic Aberration"),
        },
    ];
    const shaderPipelineOptions = [
        { data: "off", label: t("GFG_SHADER_PIPELINE_OFF", "Off") },
        { data: "on", label: t("GFG_SHADER_PIPELINE_ON", "Enabled") },
    ];
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement(DFL.Field, { label: window.SP_REACT.createElement(GFGExperimentalSettingLabel, { label: t("GFG_SHADER_PIPELINE", "Shader Pipeline (Restart)"), badgeLabel: t("EXPERIMENTAL_LABEL", "Experimental") }), description: t("CONFIG_ENABLE_VKBASALT_DESC", "Loads the bundled sharpening, anti-aliasing, and effect pipeline for this profile."), childrenLayout: "below", childrenContainerWidth: "max" },
                window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: shaderPipelineOptions, selectedOption: vkBasaltEnabled ? "on" : "off", onChange: (option) => onConfigChange(EXTERNAL_VULKAN_LAYER, option.data === "on" ? EXTERNAL_VULKAN_LAYER_VKBASALT : EXTERNAL_VULKAN_LAYER_NONE) }))),
        vkBasaltEnabled && (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: t("CONFIG_VKBASALT_SHADER", "Effects"), description: t("CONFIG_VKBASALT_SHADER_DESC", "Effects run in selection order; uncheck and recheck to move one last. Stacking increases GPU load, especially with heavier effects such as HDR Look. Test per game and monitor GPU usage."), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(EffectsChecklist, { key: profileName, options: shaderOptions, initialSelection: selectedEffects, onChange: (value) => onConfigChange(VKBASALT_SHADER, value) }))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: t("CONFIG_VKBASALT_SHARPENING", "Sharpening"), description: t("CONFIG_VKBASALT_SHARPENING_DESC", "CAS is a crisp general-purpose sharpener. DLS can preserve noisy or grainy detail better when paired with denoise."), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: sharpeningOptions, selectedOption: config.vkbasalt_sharpening, onChange: (option) => onConfigChange(VKBASALT_SHARPENING, String(option.data)) }))),
            sharpeningEnabled && (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.SliderField, { label: t("CONFIG_VKBASALT_SHARPNESS", "Sharpness ({value}%)", {
                        value: Math.round(config.vkbasalt_sharpness * 100),
                    }), description: t("CONFIG_VKBASALT_SHARPNESS_DESC", "Higher values produce a stronger effect but can exaggerate grain and create halos around high-contrast edges."), value: config.vkbasalt_sharpness, min: VKBASALT_STRENGTH_MIN, max: VKBASALT_STRENGTH_MAX, step: 0.01, onChange: (value) => onConfigChange(VKBASALT_SHARPNESS, value) }))),
            config.vkbasalt_sharpening === VKBASALT_SHARPENING_DLS && (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.SliderField, { label: t("CONFIG_VKBASALT_DLS_DENOISE", "DLS Denoise ({value}%)", { value: Math.round(config.vkbasalt_dls_denoise * 100) }), description: t("CONFIG_VKBASALT_DLS_DENOISE_DESC", "Limits how strongly DLS sharpens film grain and fine noise."), value: config.vkbasalt_dls_denoise, min: VKBASALT_STRENGTH_MIN, max: VKBASALT_STRENGTH_MAX, step: 0.01, onChange: (value) => onConfigChange(VKBASALT_DLS_DENOISE, value) }))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: t("CONFIG_VKBASALT_ANTIALIASING", "Anti-aliasing"), description: t("CONFIG_VKBASALT_ANTIALIASING_DESC", "Optionally smooth jagged edges before sharpening. FXAA is lighter and softer; SMAA is more selective and may cost more GPU time."), childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: antialiasingOptions, selectedOption: config.vkbasalt_antialiasing, onChange: (option) => onConfigChange(VKBASALT_ANTIALIASING, String(option.data)) }))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(GFGInlineTip, { tone: "info" }, isDefaultProfile
                    ? t("CONFIG_VKBASALT_ADVANCED_GLOBAL_NOTE", "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. The Default profile uses this global file.", { path: displayedConfigPath })
                    : t("CONFIG_VKBASALT_ADVANCED_PROFILE_NOTE", "Advanced options can be edited in {path}. GFG Extreme merges only the controls above and preserves every other setting. Manual advanced changes apply on the next launch. This file belongs to the selected profile and is removed when that profile is deleted.", { path: displayedConfigPath })))))));
}

function modalityButtonStyle(active, revealed) {
    return {
        position: "relative",
        boxSizing: "border-box",
        flex: "1 1 0",
        minWidth: 0,
        height: "46px",
        margin: 0,
        padding: "0 4px",
        overflow: "hidden",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: active ? "#f5f7fa" : revealed ? "#d8d9dd" : "#80858f",
        background: active
            ? "linear-gradient(145deg, rgba(42, 21, 23, 0.98), rgba(20, 13, 15, 0.98) 62%, rgba(75, 27, 24, 0.98))"
            : revealed
                ? "linear-gradient(145deg, rgba(37, 19, 21, 0.94), rgba(16, 18, 23, 0.96))"
                : "linear-gradient(145deg, rgba(17, 13, 15, 0.90), rgba(11, 13, 17, 0.94))",
        border: active
            ? "1px solid rgba(255, 116, 95, 0.78)"
            : revealed
                ? "1px solid rgba(255, 81, 61, 0.44)"
                : "1px solid rgba(255, 81, 61, 0.28)",
        borderRadius: "8px",
        outline: revealed ? "1px solid rgba(255, 116, 95, 0.48)" : "none",
        outlineOffset: "1px",
        boxShadow: active
            ? "inset 0 1px 0 rgba(255, 255, 255, 0.12), inset 0 -12px 24px rgba(20, 10, 11, 0.34), 0 0 14px rgba(255, 81, 61, 0.20)"
            : revealed
                ? "inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 0 9px rgba(255, 81, 61, 0.16)"
                : "inset 0 1px 0 rgba(255, 255, 255, 0.045), 0 2px 5px rgba(0, 0, 0, 0.2)",
        textShadow: "0 1px 2px rgba(0, 0, 0, 0.80)",
        transform: revealed ? "translateY(-1px)" : "translateY(0)",
        transition: "background 140ms ease, border-color 140ms ease, box-shadow 140ms ease, color 140ms ease, transform 140ms ease",
    };
}
function ModalityTabs({ activeModality, onModalityChange, }) {
    const [revealedModality, setRevealedModality] = SP_REACT.useState(null);
    const options = [
        {
            id: "frame-generation",
            label: t("CONTENT_TAB_FRAME_GENERATION", "Frame-gen"),
            ribbonLabel: t("CONTENT_TAB_FRAME_GENERATION", "Frame-gen"),
            icon: FiFastForward,
        },
        {
            id: "spatial",
            label: t("CONTENT_TAB_SCALING", "Scaling"),
            ribbonLabel: t("CONTENT_TAB_SCALING", "Scaling"),
            icon: FiMaximize2,
        },
        {
            id: "shaders",
            label: t("CONTENT_TAB_SHADERS", "Shaders"),
            ribbonLabel: t("CONTENT_TAB_SHADERS", "Shaders"),
            icon: FiLayers,
        },
    ];
    const hideRibbon = (modality) => {
        setRevealedModality((current) => (current === modality ? null : current));
    };
    return (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { "data-gfg-modality-selector": "true", style: {
                width: "100%",
                boxSizing: "border-box",
                margin: "14px 0 12px",
                padding: "7px",
                border: "1px solid rgba(255, 81, 61, 0.22)",
                borderRadius: "11px",
                background: "linear-gradient(155deg, rgba(11, 13, 17, 0.88), rgba(32, 17, 18, 0.48))",
                boxShadow: "inset 0 1px 0 rgba(255, 255, 255, 0.035), 0 4px 12px rgba(0, 0, 0, 0.20)",
            } },
            window.SP_REACT.createElement(GFGFocusable, { role: "tablist", "aria-label": t("CONTENT_IMAGE_PROCESSING", "Image Processing"), "flow-children": "row", noFocusRing: true, style: {
                    width: "100%",
                    display: "flex",
                    alignItems: "stretch",
                    gap: "7px",
                } }, options.map((option) => {
                const active = activeModality === option.id;
                const revealed = revealedModality === option.id;
                const Icon = option.icon;
                return (window.SP_REACT.createElement(GFGFocusable, { key: option.id, role: "tab", id: `gfg-modality-tab-${option.id}`, "aria-label": option.label, "aria-selected": active, "aria-controls": `gfg-modality-panel-${option.id}`, "data-modality": option.id, onClick: () => onModalityChange(option.id), onActivate: () => onModalityChange(option.id), onMouseEnter: () => setRevealedModality(option.id), onMouseLeave: () => hideRibbon(option.id), onFocus: () => setRevealedModality(option.id), onBlur: () => hideRibbon(option.id), onGamepadFocus: () => setRevealedModality(option.id), onGamepadBlur: () => hideRibbon(option.id), noFocusRing: true, style: {
                        ...modalityButtonStyle(active, revealed),
                        flex: "1 1 0",
                        minWidth: 0,
                        width: "100%",
                    } },
                    window.SP_REACT.createElement("span", { style: {
                            position: "absolute",
                            width: "1px",
                            height: "1px",
                            padding: 0,
                            margin: "-1px",
                            overflow: "hidden",
                            clip: "rect(0, 0, 0, 0)",
                            whiteSpace: "nowrap",
                        } }, option.label),
                    window.SP_REACT.createElement("span", { "aria-hidden": "true", style: {
                            position: "absolute",
                            inset: "0 0 auto",
                            height: "2px",
                            opacity: active ? 1 : 0,
                            background: "linear-gradient(90deg, transparent, #ff745f 24%, #fff3f1 50%, #ff745f 76%, transparent)",
                            boxShadow: "0 0 8px rgba(255, 116, 95, 0.72)",
                            transition: "opacity 140ms ease",
                        } }),
                    window.SP_REACT.createElement(Icon, { "aria-hidden": "true", size: 20, style: {
                            filter: active
                                ? "drop-shadow(0 0 5px rgba(255, 116, 95, 0.58))"
                                : "none",
                            transform: revealed
                                ? "translateY(-5px) scale(0.94)"
                                : "translateY(0) scale(1)",
                            transition: "transform 140ms ease, filter 140ms ease",
                        } }),
                    window.SP_REACT.createElement("span", { "aria-hidden": "true", "data-gfg-modality-ribbon": option.id, style: {
                            position: "absolute",
                            left: "4px",
                            right: "4px",
                            bottom: "3px",
                            minWidth: 0,
                            padding: "1px 3px",
                            overflow: "hidden",
                            border: "1px solid rgba(255, 81, 61, 0.28)",
                            borderRadius: "4px",
                            opacity: revealed ? 1 : 0,
                            color: "#f5f7fa",
                            background: "linear-gradient(90deg, rgba(42, 21, 23, 0.90), rgba(75, 27, 24, 0.82), rgba(42, 21, 23, 0.90))",
                            boxShadow: "inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 1px 3px rgba(0, 0, 0, 0.24)",
                            fontSize: "7.5px",
                            fontWeight: 650,
                            lineHeight: 1.15,
                            letterSpacing: "0.1px",
                            textAlign: "center",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            transform: revealed ? "translateY(0)" : "translateY(5px)",
                            transition: "opacity 130ms ease, transform 130ms ease",
                            pointerEvents: "none",
                        } }, option.ribbonLabel)));
            })))));
}

function FeatureSettings({ config, disabled = false, runtimeState, scalingModelCompatible = null, profileName, vkBasaltConfigPath, onConfigChange, onConfigUpdate, }) {
    const [activeModality, setActiveModality] = SP_REACT.useState("frame-generation");
    const activeModalityLabel = activeModality === "frame-generation"
        ? t("CONTENT_FPS_MULTIPLIER", "Frame Generation")
        : activeModality === "spatial"
            ? t("CONTENT_SCALING", "Spatial Settings")
            : t("CONTENT_SHADERS", "Shaders");
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGSectionHeader, null, t("CONTENT_IMAGE_PROCESSING", "Image Processing")),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", { "data-gfg-image-processing-tip": "true", style: { marginTop: "3px" } },
                window.SP_REACT.createElement(GFGInlineTip, { tone: "info" }, t("IMAGE_PROCESSING_PERFORMANCE_INFO", "Combining Frame Generation, Scaling, and Shaders may cost performance. Disable unused features; changing display mode can change input resolution and GPU cost.")))),
        window.SP_REACT.createElement(ModalityTabs, { activeModality: activeModality, onModalityChange: setActiveModality }),
        window.SP_REACT.createElement("div", { key: activeModality, id: `gfg-modality-panel-${activeModality}`, role: "tabpanel", "aria-label": activeModalityLabel, "data-gfg-modality-panel": activeModality, style: {
                marginTop: "4px",
                animation: "gfg-modality-enter 150ms ease-out",
            } },
            activeModality === "frame-generation" && (window.SP_REACT.createElement(FpsMultiplierControl, { config: config, profileName: profileName, onConfigChange: onConfigChange, onConfigUpdate: onConfigUpdate })),
            activeModality === "spatial" && (window.SP_REACT.createElement(ScalingControl, { config: config, disabled: disabled, runtimeActivationSupported: runtimeState.scalingActivationSupported, runtimeInactiveReason: runtimeState.inactiveReason, runtimeFactorCeiling: runtimeState.nonSupersamplingFactorCeiling, modelCompatible: scalingModelCompatible, runtimeRequestedMethod: runtimeState.requestedMethod, runtimeActiveMethod: runtimeState.scalingActive ? runtimeState.activeMethod : null, runtimeGFGFallback: runtimeState.scalingActive &&
                    runtimeState.activeMethod === "mako" &&
                    Boolean(runtimeState.fallbackReason), onConfigChange: onConfigChange, onConfigUpdate: onConfigUpdate })),
            activeModality === "shaders" && (window.SP_REACT.createElement(ShadersConfigurationGroup, { config: config, isDefaultProfile: profileName === DEFAULT_PROFILE_NAME, profileName: profileName, vkBasaltConfigPath: vkBasaltConfigPath, onConfigChange: onConfigChange }))),
        window.SP_REACT.createElement("style", null, `
        @keyframes gfg-modality-enter {
          from { opacity: 0; transform: translateY(3px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `),
        (config.fg_backend ?? FG_BACKEND_GFG) === FG_BACKEND_GFG && window.SP_REACT.createElement(PerformanceConfigurationGroup, { config: config, onConfigChange: onConfigChange, onConfigUpdate: onConfigUpdate }),
        (config.fg_backend ?? FG_BACKEND_GFG) === FG_BACKEND_GFG && window.SP_REACT.createElement(FrameGenerationConfigurationSection, { config: config, onConfigChange: onConfigChange, onConfigUpdate: onConfigUpdate })));
}

function methodLabel(method) {
    switch (method) {
        case "mako":
            return t("SCALING_METHOD_MAKO", "GFG Scaler");
        case "ls1":
            return t("SCALING_METHOD_LS1", "LS1 Quality");
        case "ls1-performance":
            return t("SCALING_METHOD_LS1_PERFORMANCE", "LS1 Performance");
        default:
            return t("SCALING_METHOD_NATIVE", "Native Resolution");
    }
}
function liveMethodLabel(method) {
    switch (method) {
        case "native":
            return t("LIVE_STATUS_NATIVE", "Native");
        case "ls1-performance":
            return t("LIVE_STATUS_LS1_PERFORMANCE", "LS1 Perf");
        default:
            return methodLabel(method);
    }
}
function resolution(width, height) {
    return width > 0 && height > 0 ? `${width} × ${height}` : "—";
}
function scalingInactiveNotice(reason) {
    switch (reason) {
        case "variable-surface-memory-budget":
            return t("LIVE_STATUS_SCALING_MEMORY_LIMIT", "The requested render resolution exceeds this GPU's memory safety limit. Lower the in-game resolution.");
        case "gamescope-presentation-target-no-headroom":
        case "variable-surface-no-headroom":
            return t("LIVE_STATUS_SCALING_NO_HEADROOM", "This input already fills the display target. Try Windowed mode, lower the in-game resolution, or enable Quality Supersampling.");
        default:
            return null;
    }
}
function StatusDetail({ label, value, }) {
    return (window.SP_REACT.createElement("div", { "data-gfg-live-status-detail": "true", style: {
            display: "grid",
            gridTemplateColumns: "minmax(0, 0.8fr) minmax(0, 1.2fr)",
            gap: "5px",
            alignItems: "baseline",
            marginTop: "2px",
        } },
        window.SP_REACT.createElement("span", { style: { color: "#777c85" } }, label),
        window.SP_REACT.createElement("span", { style: {
                color: "#e6e7ea",
                textAlign: "right",
                overflowWrap: "anywhere",
            } }, value)));
}
function StatusRow({ label, active, separated, children, }) {
    return (window.SP_REACT.createElement("div", { style: {
            display: "grid",
            gridTemplateColumns: "8px minmax(0, 1fr)",
            columnGap: "6px",
            padding: "6px 8px",
            borderLeft: separated ? makoPanelDivider : undefined,
        } },
        window.SP_REACT.createElement("span", { "aria-hidden": "true", style: {
                width: "7px",
                height: "7px",
                marginTop: "3px",
                borderRadius: "50%",
                background: active ? "#ff745f" : "#666b74",
                boxShadow: active ? "0 0 7px rgba(255, 81, 61, 0.34)" : "none",
            } }),
        window.SP_REACT.createElement("div", { style: { minWidth: 0 } },
            window.SP_REACT.createElement("div", { style: { color: "#f5f7fa", fontSize: "10px", fontWeight: 650 } }, label),
            window.SP_REACT.createElement("div", { style: {
                    marginTop: "2px",
                    color: "#b8bbc2",
                    fontSize: "9px",
                    lineHeight: 1.3,
                } }, children))));
}
function StatusFooterNotices({ notices }) {
    const noticeContent = (notice) => (window.SP_REACT.createElement("span", { style: { color: notice.color } }, notice.content));
    return (window.SP_REACT.createElement("div", { "data-gfg-live-status-footer": "true", style: {
            display: "grid",
            gap: "4px",
            padding: "6px 10px",
            borderTop: makoPanelDivider,
            color: "#ffc5bc",
            fontSize: "9px",
            lineHeight: 1.35,
        } }, notices.length > 1 ? (window.SP_REACT.createElement("ul", { "data-gfg-live-status-notice-list": "true", style: { margin: 0, paddingLeft: "16px", listStyleType: "disc" } }, notices.map((notice) => (window.SP_REACT.createElement("li", { key: notice.key }, noticeContent(notice)))))) : (noticeContent(notices[0]))));
}
function RuntimeStatusCard({ runtimeState, }) {
    const inactiveNotice = runtimeState.scalingEnabled && !runtimeState.scalingActive
        ? scalingInactiveNotice(runtimeState.inactiveReason)
        : null;
    const memoryConstraintNotice = runtimeState.scalingActive &&
        runtimeState.constraintReason === "variable-surface-memory-budget" &&
        runtimeState.requestedFactor > runtimeState.effectiveFactor + 0.005;
    const pendingNotice = runtimeState.frameGenerationPending || runtimeState.scalingPending;
    const notices = [];
    if (runtimeState.frameGenerationEnabled) {
        notices.push({
            key: "frame-generation-menu-policy",
            content: t("LIVE_STATUS_FG_MENU_SUSPENDED", "Frame Generation is disabled while a Steam or Decky menu is open."),
        });
    }
    if (runtimeState.supersamplingActive) {
        notices.push({
            key: "supersampling",
            color: gfgAccentColor,
            content: t("LIVE_STATUS_SUPERSAMPLING", "Quality Supersampling active."),
        });
    }
    if (memoryConstraintNotice) {
        notices.push({
            key: "memory-constraint",
            content: t("LIVE_STATUS_SCALING_MEMORY_CONSTRAINED", "Requested {requested}×; limited to {effective}× by this GPU's memory safety limit.", {
                requested: runtimeState.requestedFactor.toFixed(2),
                effective: runtimeState.effectiveFactor.toFixed(2),
            }),
        });
    }
    if (inactiveNotice) {
        notices.push({ key: "scaling-inactive", content: inactiveNotice });
    }
    if (runtimeState.fallbackReason) {
        notices.push({
            key: "scaling-fallback",
            content: t("LIVE_STATUS_SCALING_FALLBACK", "You selected {requested}; GFG Extreme is using {active} instead.", {
                requested: methodLabel(runtimeState.requestedMethod),
                active: methodLabel(runtimeState.activeMethod),
            }),
        });
    }
    if (pendingNotice) {
        notices.push({
            key: "pending",
            content: t("LIVE_STATUS_PENDING", "A saved change is still applying or needs a restart."),
        });
    }
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGSectionHeader, null, t("LIVE_STATUS_TITLE", "Live Status")),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement(GFGSectionTail, null,
                window.SP_REACT.createElement("div", { "aria-label": t("LIVE_STATUS_TITLE", "Live Status"), style: { ...makoPanelStyle, width: "100%", marginTop: "8px" } },
                    window.SP_REACT.createElement("div", { style: {
                            padding: "4px 8px",
                            display: "flex",
                            alignItems: "baseline",
                            justifyContent: "flex-end",
                            gap: "8px",
                        } },
                        window.SP_REACT.createElement("span", { style: {
                                color: runtimeState.hasContext ? gfgAccentColor : "#7d828c",
                                fontSize: "8.5px",
                                fontWeight: 600,
                                textTransform: "uppercase",
                            } }, runtimeState.hasContext
                            ? t("LIVE_STATUS_CONNECTED", "GFG Extreme is active")
                            : t("LIVE_STATUS_WAITING", "Waiting for GFG Extreme"))),
                    !runtimeState.hasContext ? (window.SP_REACT.createElement("div", { style: {
                            padding: "8px 10px",
                            borderTop: makoPanelDivider,
                            color: "#b8bbc2",
                            fontSize: "10px",
                            lineHeight: 1.4,
                        } }, t("LIVE_STATUS_WAITING_DESC", "Live metrics unavailable; GFG Extreme may still work. Some games/emulators may not report them. Check Frame Generation or Scaling manually."))) : (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                        window.SP_REACT.createElement("div", { "data-gfg-live-status-grid": "compact-two-column", style: {
                                display: "grid",
                                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                                borderTop: makoPanelDivider,
                            } },
                            window.SP_REACT.createElement(StatusRow, { label: t("CONTENT_FPS_MULTIPLIER", "Frame Generation"), active: runtimeState.frameGenerationActive }, runtimeState.frameGenerationActive ? (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                window.SP_REACT.createElement(StatusDetail, { label: t("LIVE_STATUS_MODE", "Mode"), value: runtimeState.frameGenerationMode === "adaptive"
                                        ? t("ADAPTIVE_VALUE", "Adaptive")
                                        : t("LIVE_STATUS_FIXED_VALUE", "Fixed") }),
                                runtimeState.frameGenerationMode === "adaptive" ? (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                    window.SP_REACT.createElement(StatusDetail, { label: t("LIVE_STATUS_ADAPTIVE_STYLE", "Style"), value: runtimeState.frameGenerationAdaptiveStyle ===
                                            "steady"
                                            ? t("LIVE_STATUS_STEADY_VALUE", "Steady")
                                            : t("LIVE_STATUS_FRACTIONAL_VALUE", "Fractional") }),
                                    window.SP_REACT.createElement(StatusDetail, { label: t("LIVE_STATUS_TARGET", "Target"), value: `${runtimeState.frameGenerationTargetFps ?? "—"} FPS` }),
                                    window.SP_REACT.createElement(StatusDetail, { label: t("LIVE_STATUS_MAX_MULTIPLIER", "Max factor"), value: `${runtimeState.frameGenerationMultiplier ?? "—"}×` }))) : (window.SP_REACT.createElement(StatusDetail, { label: t("LIVE_STATUS_MULTIPLIER", "Factor"), value: `${runtimeState.frameGenerationMultiplier ?? "—"}×` })))) : runtimeState.frameGenerationEnabled ? (t("LIVE_STATUS_FG_INACTIVE", "On in settings, but not currently generating frames.")) : (t("LIVE_STATUS_OFF", "Off"))),
                            window.SP_REACT.createElement(StatusRow, { label: t("FEATURE_UPSCALING_TAB", "Upscaling"), active: runtimeState.scalingActive, separated: true }, runtimeState.scalingActive ? (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                window.SP_REACT.createElement(StatusDetail, { label: t("LIVE_STATUS_MODEL", "Model"), value: liveMethodLabel(runtimeState.activeMethod) }),
                                window.SP_REACT.createElement(StatusDetail, { label: t("LIVE_STATUS_ORIGINAL_RESOLUTION", "Input"), value: resolution(runtimeState.sourceWidth, runtimeState.sourceHeight) }),
                                runtimeState.supersamplingActive ? (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                    window.SP_REACT.createElement(StatusDetail, { label: t("LIVE_STATUS_RENDER_RESOLUTION", "Render"), value: resolution(runtimeState.presentationWidth, runtimeState.presentationHeight) }),
                                    window.SP_REACT.createElement(StatusDetail, { label: t("LIVE_STATUS_DISPLAY_RESOLUTION", "Display"), value: resolution(runtimeState.gamescopeTargetWidth, runtimeState.gamescopeTargetHeight) }))) : (window.SP_REACT.createElement(StatusDetail, { label: t("LIVE_STATUS_SCALED_RESOLUTION", "Output"), value: resolution(runtimeState.presentationWidth, runtimeState.presentationHeight) })),
                                window.SP_REACT.createElement(StatusDetail, { label: t("LIVE_STATUS_MULTIPLIER", "Factor"), value: `${runtimeState.effectiveFactor.toFixed(2)}×` }))) : runtimeState.scalingEnabled ? (runtimeState.scalingActivationSupported === false ? (t("LIVE_STATUS_SCALING_UNAVAILABLE", "Unavailable for this running surface.")) : (t("LIVE_STATUS_SCALING_INACTIVE", "On in settings, but the game image is not being upscaled."))) : (t("LIVE_STATUS_OFF", "Off")))),
                        notices.length > 0 && (window.SP_REACT.createElement(StatusFooterNotices, { notices: notices })))))))));
}

/** Keep confirmed model failures visible even in the controls-only view. */
function ModelWarning({ ls1, lsfg, ls1RuntimeFallback = false, }) {
    const ls1Failed = ls1RuntimeFallback || ls1?.compatible === false;
    const lsfgFailed = lsfg?.compatible === false;
    const missingDll = (ls1Failed && ls1?.reason === "dll-unavailable") ||
        (lsfgFailed && lsfg?.reason === "dll-unavailable");
    // Missing installation is not a model compatibility failure. It also takes
    // precedence over a running game's older LS1 fallback report.
    if (missingDll || (!ls1Failed && !lsfgFailed))
        return null;
    return (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { role: "alert", style: { marginBottom: "8px" } },
            window.SP_REACT.createElement(GFGInlineTip, { tone: "warning", alwaysVisible: true },
                window.SP_REACT.createElement("div", { style: { fontWeight: 700, marginBottom: "6px" } }, t("MODEL_WARNING_TITLE", "Lossless Scaling model warning")),
                window.SP_REACT.createElement("div", null, t("MODEL_WARNING_DESCRIPTION", "Some Lossless Scaling features may be unavailable:")),
                window.SP_REACT.createElement("ul", { style: {
                        margin: "8px 0 0",
                        paddingLeft: "18px",
                        display: "grid",
                        gap: "6px",
                    } },
                    ls1Failed && (window.SP_REACT.createElement("li", null, ls1RuntimeFallback
                        ? t("SCALING_LS1_ACTIVE_FALLBACK", "LS1 is unavailable for this game. GFG Scaler is active. Your LS1 selection is preserved.")
                        : t("MODEL_WARNING_LS1", "LS1 failed its availability check. GFG Scaler is used automatically if LS1 cannot load."))),
                    lsfgFailed && (window.SP_REACT.createElement("li", null, t("MODEL_WARNING_LSFG", "An LSFG model check failed. Frame Generation may be unavailable with the selected precision setting.")))),
                window.SP_REACT.createElement("div", { style: { marginTop: "8px" } }, t("MODEL_WARNING_UPDATE", "Apply available GFG Extreme and Renderer updates, then restart. If unresolved, verify Lossless Scaling files and collect diagnostics."))),
            window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", onClick: () => DFL.Navigation.NavigateToExternalWeb("https://github.com/eugeniosegala/MAKO/releases/latest") }, t("MODEL_WARNING_CHECK_UPDATES", "Open renderer releases")))));
}

const SUPPORTED_FLATPAK_RUNTIME_VERSION_LIST = SUPPORTED_FLATPAK_RUNTIMES.map(({ version }) => version).join(", ");
function UnderlinedWelcomeText({ children }) {
    return (window.SP_REACT.createElement("span", { style: {
            textDecorationLine: "underline",
            textDecorationColor: "rgba(255, 116, 95, 0.80)",
            textUnderlineOffset: "2px",
        } }, children));
}
function WelcomeNotice({ separated }) {
    const [tipsCollapsed, setTipsCollapsed] = usePersistentCollapseState("gfg-welcome-tips-collapsed", false, "welcome tips");
    const expanded = !tipsCollapsed;
    return (window.SP_REACT.createElement(GFGInfo, { as: DFL.PanelSectionRow },
        window.SP_REACT.createElement("div", { role: "note", "data-gfg-info": "true", style: {
                ...makoPanelStyle,
                width: "100%",
                boxSizing: "border-box",
                marginTop: separated ? "8px" : undefined,
                padding: "12px",
            } },
            window.SP_REACT.createElement("div", { style: {
                    color: "#f5f7fa",
                    fontSize: "13px",
                    fontWeight: 700,
                    lineHeight: 1.3,
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "7px",
                } },
                window.SP_REACT.createElement("span", { "aria-hidden": "true", style: { fontSize: "16px", lineHeight: 1 } }, "\uD83E\uDD88"),
                window.SP_REACT.createElement("span", { style: { flex: 1, minWidth: 0 } }, t("WELCOME_TITLE", "Hello from the GFG Extreme Team!"))),
            expanded && (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                window.SP_REACT.createElement("div", { style: {
                        marginTop: "7px",
                        color: "#c6c8ce",
                        fontSize: "11px",
                        lineHeight: 1.42,
                    } },
                    window.SP_REACT.createElement("div", null,
                        t("WELCOME_LIVE_UPDATES", "Many settings apply live."),
                        " ",
                        t("WELCOME_RESTART_REQUIRED", "Options marked Restart require a game restart."),
                        " ",
                        t("WELCOME_PERFORMANCE_NOTE", "Game resolution and scaling changes can affect performance."),
                        " ",
                        t("WELCOME_CLEAN_SESSION_PREFIX", "If anything "),
                        window.SP_REACT.createElement(UnderlinedWelcomeText, null, t("WELCOME_CLEAN_SESSION_WRONG", "looks or feels wrong")),
                        t("WELCOME_CLEAN_SESSION_AFTER", " after "),
                        window.SP_REACT.createElement(UnderlinedWelcomeText, null, t("WELCOME_CLEAN_SESSION_CHANGES", "several changes")),
                        t("WELCOME_CLEAN_SESSION_RESTART_SEPARATOR", ", "),
                        window.SP_REACT.createElement(UnderlinedWelcomeText, null, t("WELCOME_CLEAN_SESSION_RESTART", "restart the game for a clean new session.")))),
                window.SP_REACT.createElement("div", { style: {
                        marginTop: "9px",
                        paddingTop: "8px",
                        borderTop: makoPanelDivider,
                        color: "#9da3ad",
                        fontSize: "10.5px",
                        lineHeight: 1.4,
                    } }, t("WELCOME_ENJOY", "Settings vary by game. Test what works for you; check the release page for GFG Extreme updates.")))),
            window.SP_REACT.createElement("div", { style: {
                    display: "flex",
                    justifyContent: "center",
                    marginTop: expanded ? "9px" : "8px",
                } },
                window.SP_REACT.createElement(DFL.DialogButton, { "aria-expanded": expanded, style: {
                        width: "auto",
                        minWidth: "78px",
                        height: "28px",
                        padding: "4px 10px",
                        fontSize: "11px",
                        flexShrink: 0,
                    }, onClick: () => setTipsCollapsed((current) => !current) }, expanded
                    ? t("WELCOME_TIPS_COLLAPSE", "Hide tips")
                    : t("WELCOME_TIPS_EXPAND", "Show tips"))))));
}
/** Purely visual status notices shown above GFG Extreme's controls. */
function ContentNotices({ developmentBuildInfo, mainRunningApp, showWelcome, engineUpdateRequired, installedEngineVersion, expectedEngineVersion, isInstalling, isInstallCompletionVisible, isUninstalling, onInstall, modelStatus, }) {
    const [showDevelopmentDetails, setShowDevelopmentDetails] = SP_REACT.useState(false);
    const hasDevelopmentNotice = Boolean(developmentBuildInfo);
    const hasRunningAppNotice = Boolean(mainRunningApp);
    const developmentDeployed = t("DEVELOPMENT_DEPLOYED", "deployed");
    const developmentUnchanged = t("DEVELOPMENT_UNCHANGED", "unchanged");
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(ModelWarning, { ...modelStatus }),
        developmentBuildInfo && (window.SP_REACT.createElement(GFGInfo, { as: DFL.PanelSectionRow },
            window.SP_REACT.createElement("div", { "data-gfg-info": "true", style: {
                    padding: "8px 12px",
                    width: "100%",
                    boxSizing: "border-box",
                    backgroundColor: "rgba(255, 81, 61, 0.16)",
                    borderRadius: "4px",
                    border: "1px solid rgba(255, 81, 61, 0.50)",
                    color: "#ffc5bc",
                    fontSize: "13px",
                    overflow: "hidden",
                } },
                window.SP_REACT.createElement("div", { style: {
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        minWidth: 0,
                    } },
                    window.SP_REACT.createElement("div", { style: { flex: 1, minWidth: 0 } },
                        window.SP_REACT.createElement("div", { style: { fontWeight: "bold" } },
                            "\uD83E\uDDEA",
                            " ",
                            t("DEVELOPMENT_DEPLOYMENT_TITLE", "Local development deployment")),
                        window.SP_REACT.createElement("div", { style: {
                                marginTop: "2px",
                                color: "#f0f1f4",
                                fontSize: "11px",
                                whiteSpace: "nowrap",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                            } },
                            "GFG Extreme ",
                            window.SP_REACT.createElement("code", null, developmentBuildInfo.plugin.commit),
                            developmentBuildInfo.plugin.dirty ? "*" : "",
                            " · GFG Engine ",
                            developmentBuildInfo.engine ? (window.SP_REACT.createElement("code", null, developmentBuildInfo.engine.commit)) : (developmentUnchanged),
                            developmentBuildInfo.engine?.dirty ? "*" : "")),
                    window.SP_REACT.createElement(DFL.DialogButton, { "aria-expanded": showDevelopmentDetails, style: {
                            width: "72px",
                            minWidth: "72px",
                            height: "30px",
                            padding: "4px 8px",
                            fontSize: "12px",
                        }, onClick: () => setShowDevelopmentDetails((current) => !current) }, showDevelopmentDetails
                        ? t("DEVELOPMENT_HIDE", "Hide")
                        : t("DEVELOPMENT_DETAILS", "Details"))),
                showDevelopmentDetails && (window.SP_REACT.createElement("div", { style: {
                        display: "flex",
                        flexDirection: "column",
                        gap: "8px",
                        marginTop: "8px",
                        paddingTop: "8px",
                        borderTop: "1px solid rgba(255, 81, 61, 0.35)",
                        overflowWrap: "anywhere",
                    } },
                    window.SP_REACT.createElement("div", { style: { color: "#f0f1f4" } },
                        window.SP_REACT.createElement("span", { style: { color: "#ff745f" } }, t("DEVELOPMENT_DEPLOYED_AT", "Deployed")),
                        " ",
                        new Date(developmentBuildInfo.generatedAt).toLocaleString()),
                    window.SP_REACT.createElement("div", null,
                        window.SP_REACT.createElement("div", { style: { color: "#ff745f", fontWeight: "600" } }, "GFG Extreme"),
                        window.SP_REACT.createElement("div", null,
                            t("DEVELOPMENT_COMMIT", "Commit"),
                            ":",
                            " ",
                            window.SP_REACT.createElement("code", null, developmentBuildInfo.plugin.commit),
                            developmentBuildInfo.plugin.dirty
                                ? ` ${t("DEVELOPMENT_LOCAL_EDITS", "+ local edits")}`
                                : ""),
                        window.SP_REACT.createElement("div", null,
                            t("DEVELOPMENT_FRONTEND", "Frontend"),
                            ":",
                            " ",
                            developmentBuildInfo.plugin.frontendDeployed
                                ? developmentDeployed
                                : developmentUnchanged),
                        window.SP_REACT.createElement("div", null,
                            t("DEVELOPMENT_BACKEND", "Backend"),
                            ":",
                            " ",
                            developmentBuildInfo.plugin.backendDeployed
                                ? developmentDeployed
                                : developmentUnchanged)),
                    window.SP_REACT.createElement("div", null,
                        window.SP_REACT.createElement("div", { style: { color: "#ff745f", fontWeight: "600" } }, "GFG Engine"),
                        developmentBuildInfo.engine ? (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                            window.SP_REACT.createElement("div", null,
                                t("DEVELOPMENT_COMMIT", "Commit"),
                                ":",
                                " ",
                                window.SP_REACT.createElement("code", null, developmentBuildInfo.engine.commit),
                                developmentBuildInfo.engine.dirty
                                    ? ` ${t("DEVELOPMENT_LOCAL_EDITS", "+ local edits")}`
                                    : ""),
                            window.SP_REACT.createElement("div", null,
                                t("DEVELOPMENT_LAYER_64", "64-bit layer"),
                                ":",
                                " ",
                                developmentBuildInfo.engine.layer64Sha256 ? (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                    developmentDeployed,
                                    " \u00B7 SHA-256",
                                    " ",
                                    window.SP_REACT.createElement("code", null, developmentBuildInfo.engine.layer64Sha256.slice(0, 12)))) : (developmentUnchanged)),
                            window.SP_REACT.createElement("div", null,
                                t("DEVELOPMENT_LAYER_32", "32-bit layer"),
                                ":",
                                " ",
                                developmentBuildInfo.engine.layer32Sha256 ? (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                    developmentDeployed,
                                    " \u00B7 SHA-256",
                                    " ",
                                    window.SP_REACT.createElement("code", null, developmentBuildInfo.engine.layer32Sha256.slice(0, 12)))) : (developmentUnchanged)),
                            window.SP_REACT.createElement("div", null,
                                t("DEVELOPMENT_FLATPAK_BUNDLES", "Flatpak bundles"),
                                ":",
                                " ",
                                developmentBuildInfo.engine.flatpakArchiveSha256 ? (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                    SUPPORTED_FLATPAK_RUNTIME_VERSION_LIST,
                                    " ",
                                    developmentDeployed,
                                    " \u00B7 SHA-256",
                                    " ",
                                    window.SP_REACT.createElement("code", null, developmentBuildInfo.engine.flatpakArchiveSha256.slice(0, 12)))) : (developmentUnchanged)))) : (window.SP_REACT.createElement("div", null, t("DEVELOPMENT_UNCHANGED_BY_DEPLOYMENT", "Unchanged by this deployment"))))))))),
        showWelcome && window.SP_REACT.createElement(WelcomeNotice, { separated: hasDevelopmentNotice }),
        mainRunningApp && (window.SP_REACT.createElement(GFGInfo, { as: DFL.PanelSectionRow },
            window.SP_REACT.createElement("div", { "data-gfg-info": "true", style: {
                    marginTop: hasDevelopmentNotice || showWelcome ? "8px" : undefined,
                    padding: "8px 12px",
                    width: "100%",
                    boxSizing: "border-box",
                    backgroundColor: "rgba(255, 81, 61, 0.10)",
                    borderRadius: "4px",
                    border: "1px solid rgba(255, 81, 61, 0.30)",
                    fontSize: "13px",
                    overflowWrap: "anywhere",
                } },
                window.SP_REACT.createElement("strong", null, mainRunningApp.display_name),
                " ",
                t("CONTENT_RUNNING", "running."),
                " ",
                t("PROFILE_CAPTURE_READY", "GFG Extreme selects saved profiles automatically. If this game is new, save it below; restart the game after changing restart-only settings.")))),
        engineUpdateRequired && (window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", { "data-gfg-update-notice": "true", style: {
                    marginTop: hasDevelopmentNotice || showWelcome || hasRunningAppNotice
                        ? "8px"
                        : undefined,
                    padding: "12px",
                    borderRadius: "8px",
                    background: "rgba(255, 116, 95, 0.16)",
                    border: "1px solid rgba(255, 116, 95, 0.70)",
                    color: "#ffc5bc",
                } },
                window.SP_REACT.createElement(GFGInfo, { "data-gfg-info": "true", style: { fontWeight: "bold", marginBottom: "4px" } }, t("CONTENT_ENGINE_UPDATE_REQUIRED", "GFG Engine update required")),
                window.SP_REACT.createElement(GFGInfo, { "data-gfg-info": "true", style: { fontSize: "13px", marginBottom: "10px" } },
                    t("CONTENT_ENGINE_INSTALLED", "Installed:"),
                    " ",
                    installedEngineVersion ||
                        t("CONTENT_ENGINE_NOT_RECORDED", "not recorded"),
                    ". ",
                    t("CONTENT_ENGINE_EXPECTS", "This plugin expects:"),
                    " ",
                    expectedEngineVersion ||
                        t("CONTENT_ENGINE_BUNDLED_VERSION", "the bundled version"),
                    ".",
                    !installedEngineVersion &&
                        ` ${t("CONTENT_ENGINE_PREDATES_TRACKING", "The installed payload predates version tracking.")}`,
                    " ",
                    t("CONTENT_ENGINE_UPDATE_DESC", "Reinstall bundled GFG Engine, then update runtime extensions for prepared Flatpaks.")),
                window.SP_REACT.createElement("div", { className: "GFG_BrandButton" },
                    window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", onClick: onInstall, disabled: isInstalling || isInstallCompletionVisible || isUninstalling }, isInstallCompletionVisible ? (window.SP_REACT.createElement(GFGInstallCompletion, null)) : (window.SP_REACT.createElement("div", { style: {
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "8px",
                        } },
                        isInstalling && window.SP_REACT.createElement(GFGCompactSpinner, null),
                        window.SP_REACT.createElement("span", null, isInstalling
                            ? t("CONTENT_UPDATING_RENDERER", "Updating GFG Engine...")
                            : t("CONTENT_UPDATE_RENDERER", "Update GFG Engine")))))))))));
}

// Use Decky's resolved class, never a hard-coded Steam CSS module name.
const infoSelector = `[data-gfg-info="true"], .${DFL.gamepadDialogClasses.FieldDescription}, .GFG_OptionDescription`;
const ribbonSelector = '[data-gfg-info-toggle="true"]';
function adjacentControl(panel, source) {
    const view = source.ownerDocument.defaultView;
    const controls = Array.from(panel.querySelectorAll("button, input, select, textarea, a[href], [tabindex]")).filter((control) => {
        if (control.tabIndex < 0 ||
            control.contains(source) ||
            control.matches(":disabled") ||
            control.closest(`${infoSelector}, ${ribbonSelector}, [hidden], [inert], [aria-disabled="true"], .disabled`))
            return false;
        for (let element = control; element; element = element.parentElement) {
            const style = view?.getComputedStyle(element);
            if (style?.display === "none" ||
                style?.visibility === "hidden" ||
                style?.visibility === "collapse")
                return false;
            if (element === panel)
                break;
        }
        return true;
    });
    // DOM order follows the panel's column navigation. Prefer continuing down
    // the settings; at the end, stay near the previous surviving control.
    return (controls.find((control) => source.compareDocumentPosition(control) &
        Node.DOCUMENT_POSITION_FOLLOWING) ??
        controls[controls.length - 1] ??
        null);
}
/** Keep help visibility local to the panel, independent of game profiles. */
function InfoVisibility({ children }) {
    const [hidden, setHidden] = usePersistentCollapseState("gfg-info-hidden", false, "GFG Extreme information");
    const [focused, setFocused] = SP_REACT.useState(false);
    const ribbon = SP_REACT.useRef(null);
    const scrollFrame = SP_REACT.useRef();
    const focusAnchor = SP_REACT.useRef();
    const label = hidden
        ? t("CONTENT_SHOW_INFO", "Show info")
        : t("CONTENT_HIDE_INFO", "Hide info");
    const cancelScroll = () => {
        if (scrollFrame.current !== undefined) {
            cancelAnimationFrame(scrollFrame.current);
            scrollFrame.current = undefined;
        }
    };
    SP_REACT.useEffect(() => cancelScroll, []);
    SP_REACT.useLayoutEffect(() => {
        const anchor = focusAnchor.current;
        if (!anchor)
            return;
        const target = anchor.target.isConnected
            ? anchor.target
            : ribbon.current?.querySelector("button");
        // Refocusing a surviving control alone emits no new focus event. Restore
        // its screen position explicitly, after descriptions have changed height.
        target?.focus({ preventScroll: true });
        if (target === anchor.target && anchor.scroller) {
            anchor.scroller.scrollTop +=
                target.getBoundingClientRect().top - anchor.top;
        }
        focusAnchor.current = undefined;
    }, [hidden]);
    const onFocusCapture = (event) => {
        cancelScroll();
        const target = event.target;
        if (focusAnchor.current ||
            !event.currentTarget.contains(target) ||
            target.closest(ribbonSelector))
            return;
        // Keep normal navigation centred, but never let an older request scroll
        // away from a newer control or from the position restored by an R1 toggle.
        scrollFrame.current = requestAnimationFrame(() => {
            scrollFrame.current = undefined;
            if (target.isConnected && target.ownerDocument.activeElement === target) {
                target.scrollIntoView({
                    block: "center",
                    inline: "nearest",
                    behavior: "auto",
                });
            }
        });
    };
    const toggle = (source) => {
        cancelScroll();
        const panel = ribbon.current?.closest(".GFG_InfoVisibility");
        const activeElement = ribbon.current?.ownerDocument
            .activeElement;
        let target = source ?? activeElement;
        const sourceTop = target?.getBoundingClientRect().top;
        if (target &&
            panel?.contains(target) &&
            !hidden &&
            target.closest(infoSelector)) {
            target = adjacentControl(panel, target);
        }
        if (!target || !panel?.contains(target)) {
            target = ribbon.current?.querySelector("button") ?? null;
        }
        if (target) {
            focusAnchor.current = {
                target,
                top: sourceTop ?? target.getBoundingClientRect().top,
                scroller: target.closest(ribbonSelector)
                    ? null
                    : findFocusScrollContainer(target),
            };
            target.focus({ preventScroll: true });
        }
        setHidden((current) => !current);
    };
    const onButtonDown = (event) => {
        if (event.detail.button !== DFL.GamepadButton.BUMPER_RIGHT)
            return;
        event.preventDefault();
        event.stopPropagation();
        if (!event.detail.is_repeat)
            toggle(event.target);
    };
    return (window.SP_REACT.createElement(GFGFocusable, { className: hidden ? "GFG_InfoVisibility GFG_ExtremeRoot GFG_InfoHidden" : "GFG_InfoVisibility GFG_ExtremeRoot", "flow-children": "column", onButtonDown: onButtonDown, onFocusCapture: onFocusCapture },
        window.SP_REACT.createElement("style", null, `

        .GFG_ExtremeRoot {
          --gfg-red: #ff513d;
          --gfg-red-hot: #ff745f;
          --gfg-ink: #08090c;
          --gfg-panel: #101217;
          --gfg-line: rgba(255, 81, 61, 0.36);
          --gfg-text: #f5f7fa;
          position: relative;
          background:
            linear-gradient(115deg, rgba(255, 81, 61, 0.035) 0 1px, transparent 1px 22px),
            linear-gradient(180deg, rgba(5, 6, 8, 0.18), rgba(5, 6, 8, 0.48));
        }
        .GFG_ExtremeRoot::before {
          content: "";
          position: absolute;
          top: 0;
          left: 0;
          width: 3px;
          height: 100%;
          background: linear-gradient(180deg, var(--gfg-red), rgba(255,81,61,0.08) 74%, transparent);
          pointer-events: none;
          z-index: 2;
        }
        .GFG_ExtremeHeader {
          position: relative;
          width: 100%;
          min-height: 66px;
          box-sizing: border-box;
          display: flex;
          align-items: center;
          gap: 10px;
          margin: 2px 0 4px;
          padding: 10px 14px 10px 16px;
          overflow: hidden;
          color: var(--gfg-text);
          background: linear-gradient(112deg, #07090c 0%, #14161c 67%, #251315 100%);
          border: 1px solid rgba(255,81,61,0.52);
          border-left: 4px solid var(--gfg-red);
          clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 14px 100%, 0 calc(100% - 14px));
          box-shadow: inset 0 0 0 1px rgba(255,255,255,0.025), 0 6px 14px rgba(0,0,0,0.28);
        }
        .GFG_ExtremeHeader::after {
          content: "";
          position: absolute;
          right: -20px;
          bottom: -28px;
          width: 145px;
          height: 70px;
          transform: rotate(-17deg);
          background: linear-gradient(90deg, transparent, rgba(255,81,61,0.16));
          pointer-events: none;
        }
        .GFG_ExtremeHeaderEdge {
          position: absolute;
          top: 0;
          right: 14px;
          width: 54px;
          height: 3px;
          background: var(--gfg-red);
          box-shadow: -64px 0 0 rgba(255,81,61,0.38);
        }
        .GFG_ExtremeHeaderIcon {
          position: relative;
          z-index: 1;
          display: grid;
          place-items: center;
          width: 42px;
          height: 42px;
          flex: 0 0 42px;
          color: #090a0c;
          background: linear-gradient(145deg, #ff745f, #ff513d);
          clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
          box-shadow: 0 0 18px rgba(255,81,61,0.18);
        }
        .GFG_ExtremeHeaderText { min-width: 0; position: relative; z-index: 1; }
        .GFG_ExtremeWordmark {
          display: flex;
          align-items: baseline;
          gap: 6px;
          font-size: 18px;
          font-weight: 900;
          line-height: 1;
          letter-spacing: 1.15px;
          text-transform: uppercase;
          text-shadow: 0 1px 0 #000;
        }
        .GFG_ExtremeSlash { color: #6e737c; font-weight: 500; }
        .GFG_ExtremeName { color: var(--gfg-red-hot); }
        .GFG_ExtremeTagline {
          margin-top: 6px;
          color: #9da3ad;
          font-size: 8px;
          font-weight: 800;
          line-height: 1;
          letter-spacing: 1.45px;
          text-transform: uppercase;
        }
        .GFG_ExtremePulse {
          position: absolute;
          z-index: 1;
          right: 14px;
          width: 6px;
          height: 24px;
          background: var(--gfg-red);
          box-shadow: -9px 8px 0 rgba(255,81,61,0.24), -18px 14px 0 rgba(255,81,61,0.09);
          transform: skewX(-16deg);
        }
        .GFG_ExtremeRoot [data-gfg-info-toggle="true"] button,
        .GFG_ExtremeRoot .GFG_DialogButton,
        .GFG_ExtremeRoot .GFG_BrandButton button {
          border-radius: 2px !important;
        }
        .GFG_ExtremeRoot .GFG_BrandButton button {
          border-color: rgba(255,81,61,0.48) !important;
          background: linear-gradient(110deg, #0b0d11 0%, #171319 70%, #2a1517 100%) !important;
          color: #f7f7f8 !important;
          font-weight: 750 !important;
          letter-spacing: .25px !important;
          box-shadow: inset 3px 0 0 rgba(255,81,61,0.72), 0 3px 9px rgba(0,0,0,.24) !important;
        }
        .GFG_ExtremeRoot .GFG_BrandButton button:hover:not(:disabled),
        .GFG_ExtremeRoot .GFG_BrandButton button:focus,
        .GFG_ExtremeRoot .GFG_BrandButton button:focus-visible {
          background: linear-gradient(110deg, #121419 0%, #27171a 62%, #4b1b18 100%) !important;
          outline-color: var(--gfg-red-hot) !important;
          box-shadow: inset 4px 0 0 var(--gfg-red), 0 0 0 2px rgba(255,81,61,.20), 0 0 14px rgba(255,81,61,.17) !important;
        }
        .GFG_ExtremeRoot [data-gfg-experimental-badge="true"] {
          border-radius: 2px !important;
          border-color: rgba(255,81,61,.52) !important;
          background: rgba(84,25,22,.58) !important;
          color: #ffc5bc !important;
        }
        .GFG_ExtremeRoot [data-gfg-section-tail="true"] {
          border-bottom: 1px solid rgba(255,81,61,.10);
        }
        .GFG_ExtremeRoot input[type="range"],
        .GFG_ExtremeRoot input[type="checkbox"],
        .GFG_ExtremeRoot input[type="radio"] { accent-color: var(--gfg-red); }
        .GFG_ExtremeRoot select { border-color: rgba(255,81,61,.42) !important; }

        .GFG_InfoVisibility .${DFL.gamepadDialogClasses.FieldDescription},
        .GFG_InfoVisibility .GFG_OptionDescription,
        .GFG_InfoVisibility .GFG_OptionMessage {
          font-size: 10px !important;
          line-height: 14px !important;
        }
        .GFG_InfoVisibility.DesktopUI .${DFL.gamepadDialogClasses.FieldDescription},
        .GFG_InfoVisibility.DesktopUI .GFG_OptionDescription,
        .GFG_InfoVisibility.DesktopUI .GFG_OptionMessage,
        .DesktopUI .GFG_InfoVisibility .${DFL.gamepadDialogClasses.FieldDescription},
        .DesktopUI .GFG_InfoVisibility .GFG_OptionDescription,
        .DesktopUI .GFG_InfoVisibility .GFG_OptionMessage {
          font-size: 11px !important;
          line-height: 16px !important;
        }
        .GFG_InfoHidden .${DFL.gamepadDialogClasses.FieldDescription},
        .GFG_InfoHidden .GFG_OptionDescription {
          display: none !important;
        }
        .GFG_InfoHidden [data-gfg-update-notice="true"] {
          background: none !important;
          border: none !important;
          padding: 0 !important;
        }
      `),
        window.SP_REACT.createElement(InfoHiddenContext.Provider, { value: hidden }, children),
        window.SP_REACT.createElement("div", { ref: ribbon, "data-gfg-info-toggle": "true", style: {
                position: "sticky",
                bottom: "8px",
                zIndex: 5,
                display: "flex",
                justifyContent: "flex-end",
                margin: "8px 12px",
                pointerEvents: "none",
            } },
            window.SP_REACT.createElement(DFL.DialogButton, { "aria-label": label, "aria-pressed": hidden, onClick: () => toggle(), onGamepadFocus: () => setFocused(true), onGamepadBlur: () => setFocused(false), style: {
                    ...makoDialogButtonStyle(focused),
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    width: "auto",
                    minWidth: 0,
                    height: "28px",
                    padding: "4px 9px",
                    borderRadius: "6px",
                    fontSize: "11px",
                    lineHeight: 1.2,
                    pointerEvents: "auto",
                } },
                window.SP_REACT.createElement("span", { "aria-hidden": "true", style: {
                        border: "1px solid rgba(255, 197, 188, 0.60)",
                        borderRadius: "3px",
                        padding: "1px 4px",
                        fontSize: "10px",
                        fontWeight: 700,
                    } }, "R1"),
                label))));
}

function AdvancedDetailsModal({ closeModal, }) {
    const [installation, setInstallation] = SP_REACT.useState(null);
    const [dll, setDll] = SP_REACT.useState(null);
    const [loading, setLoading] = SP_REACT.useState(true);
    const [error, setError] = SP_REACT.useState(null);
    SP_REACT.useEffect(() => {
        let active = true;
        Promise.all([checkGFGInstalled(), checkLosslessScalingDll()])
            .then(([installationResult, dllResult]) => {
            if (active) {
                setInstallation(installationResult);
                setDll(dllResult);
            }
        })
            .catch((err) => {
            if (active) {
                setError(err instanceof Error
                    ? err.message
                    : t("ADVANCED_DETAILS_FAILED_LOAD_DATA", "Failed to load data"));
            }
        })
            .finally(() => {
            if (active)
                setLoading(false);
        });
        return () => {
            active = false;
        };
    }, []);
    const copyToClipboard = async (value) => {
        try {
            await navigator.clipboard.writeText(value);
        }
        catch (err) {
            console.error("Failed to copy to clipboard:", err);
        }
    };
    const valueStyle = {
        display: "block",
        boxSizing: "border-box",
        minWidth: 0,
        width: "100%",
        maxWidth: "100%",
        padding: "8px 10px",
        overflowWrap: "anywhere",
        wordBreak: "break-word",
        userSelect: "text",
        border: "1px solid rgba(255, 81, 61, 0.16)",
        borderRadius: "4px",
        background: "rgba(0, 0, 0, 0.30)",
        color: "#f5f7fa",
        fontSize: "13px",
        lineHeight: 1.4,
    };
    const labelStyle = {
        marginBottom: "4px",
        color: "#b8bbc2",
        fontSize: "11px",
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.35px",
    };
    const detail = (label, value) => {
        const displayedValue = value || t("ADVANCED_DETAILS_NOT_AVAILABLE", "Not available");
        return (window.SP_REACT.createElement("div", { style: makoPanelItemStyle },
            window.SP_REACT.createElement("div", { style: labelStyle }, label),
            window.SP_REACT.createElement(GFGFocusable, { onClick: () => void copyToClipboard(displayedValue), onActivate: () => void copyToClipboard(displayedValue), style: valueStyle }, displayedValue)));
    };
    const installationSummary = installation?.error
        ? installation.error
        : installation?.host_architecture_supported === false
            ? t("ADVANCED_DETAILS_UNSUPPORTED_HOST", "Unsupported host")
            : installation?.installed
                ? installation.engine_update_required
                    ? t("ADVANCED_DETAILS_UPDATE_REQUIRED", "Bundled update available")
                    : t("STATUS_ENGINE_INSTALLED", "GFG Engine installed")
                : installation &&
                    (installation.lib_exists ||
                        installation.json_exists ||
                        installation.script_exists)
                    ? t("ADVANCED_DETAILS_INCOMPLETE", "Incomplete installation")
                    : t("STATUS_ENGINE_NOT_INSTALLED", "GFG Engine not installed");
    return (window.SP_REACT.createElement(DFL.ModalRoot, { closeModal: closeModal },
        window.SP_REACT.createElement(DFL.DialogHeader, null, t("CONTENT_ADVANCED_DETAILS", "Advanced Details")),
        window.SP_REACT.createElement(DFL.DialogBody, null,
            loading && (window.SP_REACT.createElement("div", { style: { ...makoPanelStyle, margin: "8px 0 18px", padding: "18px" } },
                window.SP_REACT.createElement(GFGCompactSpinner, null),
                " ",
                t("ADVANCED_DETAILS_LOADING", "Loading information..."))),
            error && (window.SP_REACT.createElement("div", { style: {
                    ...makoPanelStyle,
                    margin: "8px 0 18px",
                    padding: "14px",
                    color: "#ffc5bc",
                } },
                t("ADVANCED_DETAILS_ERROR_PREFIX", "Error:"),
                " ",
                error)),
            !loading && !error && installation && dll && (window.SP_REACT.createElement(GFGFocusable, { "flow-children": "column" },
                window.SP_REACT.createElement("div", { style: { ...makoPanelStyle, margin: "8px 0 18px" } },
                    window.SP_REACT.createElement("div", { style: makoPanelSectionHeaderStyle }, t("ADVANCED_DETAILS_RENDERER", "GFG Engine")),
                    detail(t("ADVANCED_DETAILS_INSTALLATION", "Installation"), installationSummary),
                    detail(t("ADVANCED_DETAILS_INSTALLED_VERSION", "Installed version"), installation.installed && installation.engine_version_known
                        ? installation.installed_engine_version
                        : null),
                    detail(t("ADVANCED_DETAILS_BUNDLED_VERSION", "Bundled version"), installation.expected_engine_version),
                    detail(t("ADVANCED_DETAILS_HOST_ARCHITECTURE", "Host architecture"), installation.host_architecture),
                    installation.lib_exists &&
                        detail(t("ADVANCED_DETAILS_LAYER_PATH", "Renderer library"), installation.lib_path),
                    installation.json_exists &&
                        detail(t("ADVANCED_DETAILS_MANIFEST_PATH", "Vulkan manifest"), installation.json_path),
                    installation.script_exists &&
                        detail(t("ADVANCED_DETAILS_LAUNCHER_PATH", "Launch wrapper"), installation.script_path),
                    window.SP_REACT.createElement("div", { style: {
                            ...makoPanelSectionHeaderStyle,
                            borderTop: makoPanelDivider,
                        } }, t("ADVANCED_DETAILS_LIBRARY", "Lossless Scaling Library")),
                    detail(t("ADVANCED_DETAILS_DETECTION", "Detection"), dll.detected
                        ? t("STATUS_LOSSLESS_INSTALLED", "Lossless Scaling installed")
                        : dll.error ||
                            t("ADVANCED_DETAILS_DLL_NOT_DETECTED", "Lossless Scaling not detected")),
                    dll.detected &&
                        detail(t("ADVANCED_DETAILS_DLL_PATH", "DLL Path"), dll.path),
                    dll.detected &&
                        dll.source &&
                        detail(t("ADVANCED_DETAILS_DETECTION_SOURCE", "Detection Source"), dll.source)),
                window.SP_REACT.createElement(DFL.DialogControlsSection, null,
                    window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                        window.SP_REACT.createElement("div", { className: "GFG_BrandButton" },
                            window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", onClick: closeModal }, t("ADVANCED_DETAILS_CLOSE", "Close"))))))))));
}

const MAKO_FLATPAK_GUIDE_URL = "https://github.com/eugeniosegala/MAKO/blob/main/plugin/docs/LAUNCHERS.md";
function translateFlatpakRuntime(version) {
    return t("FLATPAK_RUNTIME_VERSION", "Runtime {version}", { version });
}
const FlatpaksModal = ({ closeModal }) => {
    const [extensionStatus, setExtensionStatus] = SP_REACT.useState(null);
    const [flatpakApps, setFlatpakApps] = SP_REACT.useState(null);
    const [loading, setLoading] = SP_REACT.useState(true);
    const [operationInProgress, setOperationInProgress] = SP_REACT.useState(null);
    const [appErrors, setAppErrors] = SP_REACT.useState({});
    const [wrapperPath, setWrapperPath] = SP_REACT.useState(DEFAULT_MAKO_WRAPPER_PATH);
    const loadData = async () => {
        setLoading(true);
        try {
            const [statusResult, appsResult, launchOptionResult] = await Promise.all([
                checkFlatpakExtensionStatus(),
                getFlatpakApps(),
                getLaunchOption().catch(() => null),
            ]);
            setExtensionStatus(statusResult);
            setFlatpakApps(appsResult);
            if (launchOptionResult?.wrapper_path) {
                setWrapperPath(launchOptionResult.wrapper_path);
            }
        }
        catch (error) {
            console.error("Error loading Flatpak data:", error);
        }
        finally {
            setLoading(false);
        }
    };
    SP_REACT.useEffect(() => {
        loadData();
    }, []);
    const handleExtensionOperation = async (operation, version) => {
        const operationId = `${operation}-${version}`;
        setOperationInProgress(operationId);
        try {
            const result = operation === "install"
                ? await installFlatpakExtension(version)
                : await uninstallFlatpakExtension(version);
            if (result.success) {
                // Reload status after operation
                const newStatus = await checkFlatpakExtensionStatus();
                setExtensionStatus(newStatus);
                showSuccessToast(t("FLATPAK_EXTENSION_UPDATED", "Flatpak extension updated"), result.message ||
                    `${version} ${t("FLATPAK_RUNTIME_EXTENSION_UPDATED", "runtime extension updated")}`);
            }
            else {
                const action = operation === "install"
                    ? t("FLATPAK_INSTALL_ACTION", "install")
                    : t("FLATPAK_UNINSTALL_ACTION", "uninstall");
                showErrorToast(t("FLATPAK_EXTENSION_FAILED", "Flatpak extension failed"), result.error ||
                    result.message ||
                    `${t("FLATPAK_EXTENSION_ACTION_FAILED", "Could not")} ${action} ${version} ${t("FLATPAK_RUNTIME_EXTENSION", "runtime extension")}`);
            }
        }
        catch (error) {
            console.error(`Error ${operation}ing extension:`, error);
            showErrorToast(t("FLATPAK_EXTENSION_FAILED", "Flatpak extension failed"), String(error));
        }
        finally {
            setOperationInProgress(null);
        }
    };
    const handleAppOverrideToggle = async (app) => {
        const hasOverrides = app.has_filesystem_override &&
            app.has_wrapper_override &&
            app.has_required_env_override !== false;
        const operationId = `app-${app.app_id}`;
        setOperationInProgress(operationId);
        setAppErrors((current) => {
            const next = { ...current };
            delete next[app.app_id];
            return next;
        });
        try {
            const result = hasOverrides
                ? await removeFlatpakAppOverride(app.app_id)
                : await setFlatpakAppOverride(app.app_id);
            if (result.success) {
                // Reload apps data after operation
                const newApps = await getFlatpakApps();
                setFlatpakApps(newApps);
                showSuccessToast(t("FLATPAK_APPLICATION_UPDATED", "Flatpak application updated"), result.message ||
                    `${app.app_name || app.app_id} ${t("FLATPAK_UPDATED", "updated")}`);
            }
            else {
                setAppErrors((current) => ({
                    ...current,
                    [app.app_id]: result.error ||
                        result.message ||
                        `${t("FLATPAK_APPLICATION_ACTION_FAILED", "Could not update")} ${app.app_name || app.app_id}`,
                }));
            }
        }
        catch (error) {
            console.error("Error toggling app override:", error);
            setAppErrors((current) => ({ ...current, [app.app_id]: String(error) }));
        }
        finally {
            setOperationInProgress(null);
        }
    };
    const confirmOperation = (operation, title, description) => {
        DFL.showModal(window.SP_REACT.createElement(DFL.ConfirmModal, { strTitle: title, strDescription: description, onOK: operation, onCancel: () => { } }));
    };
    const handleRuntimePrimaryAction = (version, installed) => {
        const operation = installed
            ? "uninstall"
            : "install";
        const action = () => handleExtensionOperation(operation, version);
        if (operation === "uninstall") {
            confirmOperation(action, t("FLATPAK_UNINSTALL_TITLE", "Uninstall Runtime Extension"), `${t("FLATPAK_UNINSTALL_CONFIRM_PREFIX", "Are you sure you want to uninstall the")} ${version} ${t("FLATPAK_UNINSTALL_CONFIRM_SUFFIX", "runtime extension?")}`);
            return;
        }
        action();
    };
    if (loading) {
        return (window.SP_REACT.createElement(DFL.ModalRoot, { closeModal: closeModal },
            window.SP_REACT.createElement(DFL.DialogHeader, null, t("FLATPAK_MODAL_TITLE", "Flatpak Extensions")),
            window.SP_REACT.createElement(DFL.DialogBody, null,
                window.SP_REACT.createElement("div", { style: {
                        display: "flex",
                        justifyContent: "center",
                        padding: "20px",
                    } },
                    window.SP_REACT.createElement(GFGCompactSpinner, { size: 28 })))));
    }
    const instructionSteps = [
        {
            id: "try-first",
            title: t("FLATPAK_STEP_WRAPPER_PATH", "Wrapper installed on this device:"),
            command: wrapperPath,
        },
        {
            id: "final-result",
            title: t("FLATPAK_STEP_FINAL", 'Target for a shortcut that originally used "/usr/bin/flatpak":'),
            command: `"${wrapperPath}" "/usr/bin/flatpak"`,
        },
    ];
    const focusableInstructionStyle = {
        padding: "10px",
        background: "rgba(0, 0, 0, 0.3)",
        borderRadius: "6px",
        marginBottom: "12px",
    };
    const commandStyle = {
        fontFamily: "monospace",
        fontSize: "0.85em",
        background: "rgba(0, 0, 0, 0.45)",
        padding: "8px",
        borderRadius: "4px",
        marginTop: "6px",
        overflowWrap: "anywhere",
    };
    return (window.SP_REACT.createElement(DFL.ModalRoot, { closeModal: closeModal },
        window.SP_REACT.createElement(DFL.DialogHeader, null, t("FLATPAK_MODAL_TITLE", "Flatpak Extensions")),
        window.SP_REACT.createElement(DFL.DialogBody, null,
            window.SP_REACT.createElement(GFGFocusable, { "flow-children": "column" },
                window.SP_REACT.createElement("div", { style: {
                        ...makoPanelStyle,
                        margin: "8px 0 18px",
                    } },
                    window.SP_REACT.createElement("div", { style: makoPanelSectionHeaderStyle }, t("FLATPAK_RUNTIME_INSTALLER", "Runtime Extension Installer")),
                    extensionStatus && extensionStatus.success ? (SUPPORTED_FLATPAK_RUNTIMES.map((runtime) => {
                        const installBusy = operationInProgress === `install-${runtime.version}`;
                        const uninstallBusy = operationInProgress === `uninstall-${runtime.version}`;
                        const isBusy = installBusy || uninstallBusy;
                        const installed = extensionStatus[runtime.statusField];
                        return (window.SP_REACT.createElement("div", { key: runtime.version, style: makoPanelItemStyle },
                            window.SP_REACT.createElement("div", { style: {
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "10px",
                                } },
                                installed ? (window.SP_REACT.createElement(FaCheck, { style: { color: "#ff513d", flex: "0 0 16px" } })) : (window.SP_REACT.createElement(FaTimes, { style: { color: "#ff745f", flex: "0 0 16px" } })),
                                window.SP_REACT.createElement("div", { style: { minWidth: 0 } },
                                    window.SP_REACT.createElement("div", { style: { color: "#f5f7fa", fontWeight: 600 } }, translateFlatpakRuntime(runtime.version)),
                                    window.SP_REACT.createElement("div", { style: {
                                            marginTop: "2px",
                                            color: "#b8bbc2",
                                            fontSize: "12px",
                                        } }, installed
                                        ? t("FLATPAK_INSTALLED", "Installed")
                                        : t("FLATPAK_NOT_INSTALLED", "Not installed")))),
                            window.SP_REACT.createElement("div", { style: { display: "flex", gap: "8px", marginTop: "10px" } },
                                installed && (window.SP_REACT.createElement("div", { className: "GFG_BrandButton", style: { flex: 1, minWidth: 0 } },
                                    window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", onClick: () => handleExtensionOperation("install", runtime.version), disabled: isBusy }, installBusy ? (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                        window.SP_REACT.createElement(GFGCompactSpinner, null),
                                        " ",
                                        t("FLATPAK_UPDATING_BTN", "Updating..."))) : (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                        window.SP_REACT.createElement(FaDownload, null),
                                        " ",
                                        t("FLATPAK_UPDATE_BTN", "Update")))))),
                                window.SP_REACT.createElement("div", { className: `GFG_BrandButton${installed ? " GFG_BrandButton--danger" : ""}`, style: { flex: 1, minWidth: 0 } },
                                    window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", onClick: () => handleRuntimePrimaryAction(runtime.version, installed), disabled: isBusy }, uninstallBusy ? (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                        window.SP_REACT.createElement(GFGCompactSpinner, null),
                                        " ",
                                        t("FLATPAK_UNINSTALLING_BTN", "Uninstalling..."))) : installBusy && !installed ? (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                        window.SP_REACT.createElement(GFGCompactSpinner, null),
                                        " ",
                                        t("FLATPAK_INSTALLING_BTN", "Installing..."))) : installed ? (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                        window.SP_REACT.createElement(FaTrash, null),
                                        " ",
                                        t("FLATPAK_UNINSTALL_BTN", "Uninstall"))) : (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                                        window.SP_REACT.createElement(FaDownload, null),
                                        " ",
                                        t("FLATPAK_INSTALL_BTN", "Install"))))))));
                    })) : (window.SP_REACT.createElement("div", { style: makoPanelItemStyle },
                        window.SP_REACT.createElement("div", { style: {
                                display: "flex",
                                alignItems: "flex-start",
                                gap: "10px",
                            } },
                            window.SP_REACT.createElement(FaTimes, { style: {
                                    color: "#ff745f",
                                    flex: "0 0 16px",
                                    marginTop: "2px",
                                } }),
                            window.SP_REACT.createElement("div", null,
                                window.SP_REACT.createElement("div", { style: { color: "#f5f7fa", fontWeight: 600 } }, t("FLATPAK_ERROR", "Error")),
                                window.SP_REACT.createElement("div", { style: {
                                        marginTop: "3px",
                                        color: "#b8bbc2",
                                        fontSize: "12px",
                                        overflowWrap: "anywhere",
                                    } }, extensionStatus?.error ||
                                    t("FLATPAK_ERROR_STATUS", "Failed to check extension status")))))),
                    window.SP_REACT.createElement("div", { style: {
                            ...makoPanelSectionHeaderStyle,
                            borderTop: makoPanelDivider,
                        } }, t("FLATPAK_APPS_TITLE", "Flatpak Applications")),
                    window.SP_REACT.createElement("div", { style: {
                            ...makoPanelItemStyle,
                            color: "#b8bbc2",
                            fontSize: "12px",
                            lineHeight: 1.4,
                        } },
                        window.SP_REACT.createElement("div", { style: {
                                color: "#f5f7fa",
                                fontSize: "13px",
                                fontWeight: 600,
                                marginBottom: "4px",
                            } }, t("FLATPAK_PREPARE_APPLICATION", "Prepare an application")),
                        t("FLATPAK_PREPARE_APPLICATION_DESC", "Install the matching extension and prepare the app. Heroic/Lutris need a per-game wrapper; emulators apply app-wide. See launcher guide.")),
                    flatpakApps && flatpakApps.success ? (flatpakApps.apps.length > 0 ? (flatpakApps.apps.map((app) => {
                        const hasOverrides = app.has_filesystem_override &&
                            app.has_wrapper_override &&
                            app.has_required_env_override !== false;
                        const partialOverrides = app.has_filesystem_override ||
                            app.has_wrapper_override ||
                            app.has_env_override;
                        const appBusy = operationInProgress === `app-${app.app_id}`;
                        let statusColor = "#ff745f";
                        let statusText = t("FLATPAK_STATUS_NO_OVERRIDES", "No overrides");
                        if (hasOverrides) {
                            statusColor = "#ff513d";
                            statusText = t("FLATPAK_STATUS_CONFIGURED", "Prepared");
                        }
                        else if (partialOverrides) {
                            statusColor = "#ff745f";
                            statusText = t("FLATPAK_STATUS_PARTIAL", "Partial");
                        }
                        const appError = appErrors[app.app_id];
                        const description = PER_GAME_WRAPPER_FLATPAK_APP_IDS.some((appId) => appId === app.app_id)
                            ? t("FLATPAK_PER_GAME_APP_DESC", "{app_id} - {status}. Enable GFG Extreme per game using {wrapper_path}. See the launcher setup guide for the correct field.", {
                                app_id: app.app_id,
                                status: statusText,
                                wrapper_path: app.wrapper_path,
                            })
                            : t("FLATPAK_DIRECT_APP_DESC", "{app_id} - {status}. Preparation applies to this entire Flatpak app. Follow the launcher setup guide for EmuDeck and Steam shortcuts.", {
                                app_id: app.app_id,
                                status: statusText,
                            });
                        return (window.SP_REACT.createElement("div", { key: app.app_id, style: {
                                ...makoPanelItemStyle,
                                display: "flex",
                                alignItems: "center",
                                gap: "10px",
                            } },
                            window.SP_REACT.createElement(FaCog, { style: {
                                    color: appError ? "#ff745f" : statusColor,
                                    flex: "0 0 16px",
                                } }),
                            window.SP_REACT.createElement("div", { style: { flex: 1, minWidth: 0 } },
                                window.SP_REACT.createElement("div", { style: {
                                        color: "#f5f7fa",
                                        fontWeight: 600,
                                        overflowWrap: "anywhere",
                                    } }, app.app_name || app.app_id),
                                window.SP_REACT.createElement("div", { style: {
                                        marginTop: "3px",
                                        color: "#b8bbc2",
                                        fontSize: "12px",
                                        lineHeight: 1.35,
                                        overflowWrap: "anywhere",
                                    } }, description),
                                appError && (window.SP_REACT.createElement("div", { style: {
                                        marginTop: "5px",
                                        color: "#ff745f",
                                        fontSize: "12px",
                                        lineHeight: 1.35,
                                        overflowWrap: "anywhere",
                                    } }, appError))),
                            window.SP_REACT.createElement("div", { "aria-busy": appBusy, style: {
                                    flex: "0 0 auto",
                                    position: "relative",
                                    display: "inline-flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                } },
                                window.SP_REACT.createElement(DFL.Toggle, { value: hasOverrides, onChange: () => {
                                        if (!appBusy)
                                            void handleAppOverrideToggle(app);
                                    } }),
                                appBusy && (window.SP_REACT.createElement("div", { role: "status", style: {
                                        position: "absolute",
                                        inset: "1px 4px 1px 1px",
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        boxSizing: "border-box",
                                        pointerEvents: "none",
                                        overflow: "hidden",
                                        border: "1px solid rgba(255, 81, 61, 0.42)",
                                        borderRadius: "999px",
                                        background: "rgba(18, 14, 16, 0.90)",
                                    } },
                                    window.SP_REACT.createElement(GFGCompactSpinner, { size: 14 }))))));
                    })) : (window.SP_REACT.createElement("div", { style: makoPanelItemStyle },
                        window.SP_REACT.createElement("div", { style: { color: "#f5f7fa", fontWeight: 600 } }, t("FLATPAK_NO_APPS", "No Flatpak Apps Found")),
                        window.SP_REACT.createElement("div", { style: {
                                marginTop: "3px",
                                color: "#b8bbc2",
                                fontSize: "12px",
                            } }, t("FLATPAK_NO_APPS_DESC", "No Flatpak applications are currently installed"))))) : (window.SP_REACT.createElement("div", { style: makoPanelItemStyle },
                        window.SP_REACT.createElement("div", { style: { color: "#f5f7fa", fontWeight: 600 } }, t("FLATPAK_ERROR", "Error")),
                        window.SP_REACT.createElement("div", { style: {
                                marginTop: "3px",
                                color: "#b8bbc2",
                                fontSize: "12px",
                                overflowWrap: "anywhere",
                            } }, flatpakApps?.error ||
                            t("FLATPAK_ERROR_APPS", "Failed to load Flatpak applications")))),
                    window.SP_REACT.createElement("div", { style: {
                            ...makoPanelSectionHeaderStyle,
                            borderTop: makoPanelDivider,
                        } }, t("FLATPAK_STEAM_CONFIG_TITLE", "Manual Steam shortcut reference")),
                    window.SP_REACT.createElement("div", { style: {
                            ...makoPanelItemStyle,
                            display: "flex",
                            flexDirection: "column",
                        } },
                        window.SP_REACT.createElement("div", { style: {
                                fontWeight: "bold",
                                marginBottom: "8px",
                                color: "#fff",
                            } }, t("FLATPAK_STEAM_CONFIG_HEADER", "Target example (does not configure Steam)")),
                        window.SP_REACT.createElement("div", { style: {
                                fontSize: "0.9em",
                                lineHeight: "1.4",
                                marginBottom: "8px",
                            } }, t("FLATPAK_STEAM_CONFIG_DESC", "Only for manual Steam shortcuts originally targeting /usr/bin/flatpak. Prepare the app above; keep Start In and Launch Options. Heroic, Lutris, and EmuDeck use the launcher guide.")),
                        window.SP_REACT.createElement("div", { style: {
                                fontSize: "0.9em",
                                lineHeight: "1.4",
                                marginBottom: "12px",
                                color: "#ff745f",
                            } },
                            window.SP_REACT.createElement("strong", null, t("FLATPAK_IMPORTANT_LABEL", "IMPORTANT:")),
                            " ",
                            t("FLATPAK_STEAM_CONFIG_IMPORTANT", "Replace TARGET only. Do not paste this into Launch Options.")),
                        instructionSteps.map((step) => (window.SP_REACT.createElement(GFGFocusable, { key: step.id, focusWithinClassName: "gpfocuswithin", onActivate: () => { }, style: focusableInstructionStyle },
                            window.SP_REACT.createElement("div", { style: { fontWeight: "bold" } }, step.title),
                            window.SP_REACT.createElement("div", { style: commandStyle }, step.command)))),
                        window.SP_REACT.createElement("div", { className: "GFG_BrandButton" },
                            window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", onClick: () => DFL.Navigation.NavigateToExternalWeb(MAKO_FLATPAK_GUIDE_URL) }, t("FLATPAK_OPEN_README", "Open launcher setup guide"))))),
                window.SP_REACT.createElement(DFL.DialogControlsSection, null,
                    window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                        window.SP_REACT.createElement("div", { className: "GFG_BrandButton" },
                            window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", onClick: closeModal }, t("FLATPAK_CLOSE", "Close")))))))));
};


function inspectorBackendLabel(value) {
    switch (value) {
        case FG_BACKEND_GFG: return t("GFG_BACKEND_GFG", "GFG Engine");
        case FG_BACKEND_OPTISCALER: return t("GFG_BACKEND_OPTISCALER", "OptiScaler");
        case FG_BACKEND_NATIVE: return t("GFG_BACKEND_NATIVE", "Game Native");
        case FG_BACKEND_OFF: return t("GFG_BACKEND_OFF", "Off");
        default: return value || "—";
    }
}
function inspectorOnOff(value) {
    return value ? t("GFG_INSPECTOR_ON", "On") : t("GFG_INSPECTOR_OFF", "Off");
}
function InspectorStage({ title, rows }) {
    return (window.SP_REACT.createElement("div", { style: {
            padding: "9px 10px",
            borderTop: "1px solid rgba(255,81,61,0.12)",
        } },
        window.SP_REACT.createElement("div", { style: {
                color: "#ff745f",
                fontSize: "10px",
                fontWeight: 800,
                letterSpacing: "0.75px",
                textTransform: "uppercase",
                marginBottom: "6px",
            } }, title),
        rows.map(([label, value]) => window.SP_REACT.createElement("div", { key: label, style: {
                display: "flex", justifyContent: "space-between", gap: "12px",
                fontSize: "11px", lineHeight: 1.45, color: "#c6c8ce",
            } },
            window.SP_REACT.createElement("span", { style: { color: "#8f949d" } }, label),
            window.SP_REACT.createElement("span", { style: { color: "#f5f7fa", textAlign: "right", overflowWrap: "anywhere" } }, String(value ?? "—"))))));
}
function PipelineInspectorCard({ profileName = "" }) {
    const [status, setStatus] = SP_REACT.useState(null);
    const [loading, setLoading] = SP_REACT.useState(true);
    SP_REACT.useEffect(() => {
        let active = true;
        const load = async () => {
            try {
                const result = await getPipelineInspector(profileName || "");
                if (active) setStatus(result);
            }
            catch (error) {
                if (active) setStatus({ success: false, error: String(error) });
            }
            finally {
                if (active) setLoading(false);
            }
        };
        void load();
        const timer = setInterval(() => void load(), 3000);
        return () => { active = false; clearInterval(timer); };
    }, [profileName]);
    const actual = status?.actual ?? {};
    const saved = status?.saved ?? {};
    const effective = status?.effective ?? {};
    const proxies = Array.isArray(actual.optiscaler_proxy_hits)
        ? [...new Set(actual.optiscaler_proxy_hits.map((item) => String(item.proxy || "").toUpperCase()).filter(Boolean))]
        : [];
    const actualOwner = actual.state === "running"
        ? (actual.optiscaler_proxy_loaded
            ? `OptiScaler · ${proxies.length ? proxies.join(", ") : "proxy loaded"}`
            : actual.renderer_loaded && effective.frame_generation_enabled
                ? "GFG Engine"
                : saved.fg_backend === FG_BACKEND_NATIVE
                    ? t("GFG_INSPECTOR_NATIVE_UNOBSERVABLE", "Game Native · FG internals not observable")
                    : saved.fg_backend === FG_BACKEND_OFF
                        ? t("GFG_INSPECTOR_FG_OFF", "Frame Generation Off")
                        : t("GFG_INSPECTOR_NO_FG_MAPPING", "No FG mapping detected"))
        : actual.state === "ended"
            ? t("GFG_INSPECTOR_ENDED", "Last launch ended")
            : t("GFG_INSPECTOR_NOT_LAUNCHED", "Not launched yet");
    const reasons = Array.isArray(status?.mismatch_reasons) ? status.mismatch_reasons : [];
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGSectionHeader, null, t("GFG_INSPECTOR_TITLE", "Pipeline Inspector")),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", { style: { ...makoPanelStyle, width: "100%", boxSizing: "border-box", overflow: "hidden" } },
                window.SP_REACT.createElement("div", { style: { padding: "10px", color: "#9da3ad", fontSize: "10.5px", lineHeight: 1.4 } },
                    loading ? t("GFG_INSPECTOR_LOADING", "Reading saved, effective, and live pipeline state…")
                        : t("GFG_INSPECTOR_DESC", "Saved is the profile, Effective is what GFG applies at launch, Actual is what is mapped in the running process.")),
                !loading && status?.success && window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
                    window.SP_REACT.createElement(InspectorStage, { title: t("GFG_INSPECTOR_SAVED", "Saved"), rows: [
                            [t("GFG_INSPECTOR_BACKEND", "Backend"), inspectorBackendLabel(saved.fg_backend)],
                            [t("GFG_INSPECTOR_FG", "Frame Generation"), inspectorOnOff(saved.frame_generation_enabled)],
                            [t("GFG_INSPECTOR_DOCK", "Automatic Dock"), inspectorOnOff(saved.automatic_dock_mode)],
                            [t("GFG_INSPECTOR_SCALING", "Scaling"), inspectorOnOff(saved.scaling_enabled)],
                            [t("GFG_INSPECTOR_SHADERS", "Shaders"), inspectorOnOff(saved.shaders_enabled)],
                        ] }),
                    window.SP_REACT.createElement(InspectorStage, { title: t("GFG_INSPECTOR_EFFECTIVE", "Effective"), rows: [
                            [t("GFG_INSPECTOR_FG", "Frame Generation"), inspectorOnOff(effective.frame_generation_enabled)],
                            [t("GFG_INSPECTOR_DOCK", "Automatic Dock"), inspectorOnOff(effective.automatic_dock_mode)],
                            [t("GFG_INSPECTOR_RENDERER_REQUIRED", "GFG renderer required"), inspectorOnOff(effective.renderer_required)],
                            [t("GFG_INSPECTOR_TARGET", "Target FPS"), effective.target_fps ?? "—"],
                        ] }),
                    window.SP_REACT.createElement(InspectorStage, { title: t("GFG_INSPECTOR_ACTUAL", "Actual"), rows: [
                            [t("GFG_INSPECTOR_OWNER", "Observed FG owner"), actualOwner],
                            [t("GFG_INSPECTOR_RENDERER", "GFG renderer mapped"), inspectorOnOff(actual.renderer_loaded)],
                            [t("GFG_INSPECTOR_OPTISCALER", "OptiScaler proxy mapped"), inspectorOnOff(actual.optiscaler_proxy_loaded)],
                            [t("GFG_INSPECTOR_PROCESSES", "Inspected processes"), Array.isArray(actual.candidate_pids) ? actual.candidate_pids.length : 0],
                        ] }),
                    status.double_fg_warning && window.SP_REACT.createElement("div", { style: { padding: "8px 10px" } },
                        window.SP_REACT.createElement(GFGInlineTip, { tone: "warning", alwaysVisible: true },
                            t("GFG_INSPECTOR_DOUBLE_FG", "Potential double frame generation: GFG is active and an OptiScaler proxy is actually mapped."))),
                    reasons.length > 0 && window.SP_REACT.createElement("div", { style: { padding: "8px 10px", display: "grid", gap: "6px" } },
                        reasons.map((reason, index) => window.SP_REACT.createElement(GFGInlineTip, { key: `${index}-${reason}`, tone: "warning", alwaysVisible: true }, reason)))),
                !loading && (!status || !status.success) && window.SP_REACT.createElement("div", { style: { padding: "10px", color: "#ffc5bc", fontSize: "11px" } },
                    status?.error || t("GFG_INSPECTOR_UNAVAILABLE", "Inspector unavailable"))))));
}
function ConfigJournalCard({ profileName = "", onRestored }) {
    const [entries, setEntries] = SP_REACT.useState([]);
    const [restoring, setRestoring] = SP_REACT.useState(false);
    const load = SP_REACT.useCallback(async () => {
        try {
            const result = await getConfigJournal(profileName || "", 5);
            setEntries(result?.success && Array.isArray(result.entries) ? result.entries : []);
        }
        catch {
            setEntries([]);
        }
    }, [profileName]);
    SP_REACT.useEffect(() => {
        void load();
        const timer = setInterval(() => void load(), 5000);
        return () => clearInterval(timer);
    }, [load]);
    const latest = entries[0];
    const restoreLatest = async () => {
        if (!latest || restoring) return;
        setRestoring(true);
        try {
            const result = await restoreConfigJournalEntry(latest.id);
            if (!result?.success) throw new Error(result?.error || "Restore failed");
            showSuccessToast(t("GFG_JOURNAL_RESTORED", "Configuration restored"), t("GFG_JOURNAL_RESTORED_DESC", "The previous values were restored and recorded as a recovery entry."));
            await load();
            if (onRestored) await onRestored();
        }
        catch (error) {
            showErrorToast(t("GFG_JOURNAL_RESTORE_FAILED", "Restore failed"), String(error));
        }
        finally {
            setRestoring(false);
        }
    };
    return (window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGSectionHeader, null, t("GFG_JOURNAL_TITLE", "Configuration Journal")),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", { style: { ...makoPanelStyle, width: "100%", boxSizing: "border-box", padding: "10px" } },
                entries.length === 0 ? window.SP_REACT.createElement("div", { style: { color: "#9da3ad", fontSize: "11px" } }, t("GFG_JOURNAL_EMPTY", "No configuration changes recorded yet.")) :
                    window.SP_REACT.createElement("div", { style: { display: "grid", gap: "8px" } },
                        entries.slice(0, 3).map((entry) => {
                            const fields = Array.isArray(entry.changed_fields) ? entry.changed_fields.join(", ") : "";
                            const when = Number(entry.timestamp) ? new Date(Number(entry.timestamp) * 1000).toLocaleTimeString() : "";
                            return window.SP_REACT.createElement("div", { key: entry.id, style: { paddingBottom: "7px", borderBottom: "1px solid rgba(255,81,61,0.12)" } },
                                window.SP_REACT.createElement("div", { style: { display: "flex", justifyContent: "space-between", gap: "8px", fontSize: "10px", color: "#ff745f", fontWeight: 700 } },
                                    window.SP_REACT.createElement("span", null, String(entry.actor || "system").toUpperCase()),
                                    window.SP_REACT.createElement("span", { style: { color: "#8f949d", fontWeight: 500 } }, when)),
                                window.SP_REACT.createElement("div", { style: { marginTop: "3px", color: "#f5f7fa", fontSize: "11px", overflowWrap: "anywhere" } }, fields || t("GFG_JOURNAL_CHANGE", "Configuration change")),
                                entry.reason && window.SP_REACT.createElement("div", { style: { marginTop: "2px", color: "#8f949d", fontSize: "10px" } }, entry.reason));
                        })),
                latest && window.SP_REACT.createElement("div", { className: "GFG_BrandButton", style: { marginTop: "10px" } },
                    window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", bottomSeparator: "none", disabled: restoring, onClick: restoreLatest },
                        restoring ? t("GFG_JOURNAL_RESTORING", "Restoring…") : t("GFG_JOURNAL_RESTORE_LATEST", "Restore previous change")))))));
}


function useGovernorView(profileName = "") {
    const [status, setStatus] = SP_REACT.useState(null);
    const [busy, setBusy] = SP_REACT.useState(false);
    const load = SP_REACT.useCallback(async () => {
        try {
            const value = await getGovernorStatus(profileName || "");
            setStatus(value);
        }
        catch (error) {
            setStatus({ success: false, error: String(error), state: "UNAVAILABLE" });
        }
    }, [profileName]);
    SP_REACT.useEffect(() => {
        void load();
        const timer = setInterval(() => void load(), 1500);
        return () => clearInterval(timer);
    }, [load]);
    const setEnabled = async (value) => {
        if (!profileName || busy) return;
        setBusy(true);
        try {
            const result = await setGovernorEnabled(profileName, Boolean(value));
            if (!result?.success) throw new Error(result?.error || "Governor update failed");
            await load();
        }
        catch (error) {
            showErrorToast("GFG Governor", String(error));
        }
        finally { setBusy(false); }
    };
    return { status, busy, setEnabled, reload: load };
}

function GFGPageTitle({ title, subtitle = "", onBack = null }) {
    return window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { style: { width: "100%", marginTop: "4px", marginBottom: "10px" } },
            onBack && window.SP_REACT.createElement("div", { className: "GFG_BrandButton", style: { marginBottom: "8px" } },
                window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", bottomSeparator: "none", onClick: onBack }, "‹ Back")),
            window.SP_REACT.createElement("div", { style: { color: "#f8f8fa", fontSize: "21px", fontWeight: 800, letterSpacing: "-0.4px" } }, title),
            subtitle && window.SP_REACT.createElement("div", { style: { color: "#8b9098", fontSize: "10.5px", lineHeight: 1.4, marginTop: "3px" } }, subtitle)));
}

function GFGNavRow({ label, value = "", description = "", onClick, accent = false }) {
    return window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { className: "GFG_BrandButton", style: { width: "100%" } },
            window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", bottomSeparator: "none", onClick },
                window.SP_REACT.createElement("div", { style: { width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", padding: "2px 0" } },
                    window.SP_REACT.createElement("div", { style: { minWidth: 0 } },
                        window.SP_REACT.createElement("div", { style: { color: accent ? "#ff6652" : "#f5f6f7", fontWeight: 700, fontSize: "13px" } }, label),
                        description && window.SP_REACT.createElement("div", { style: { color: "#747a83", fontSize: "9.5px", marginTop: "2px", whiteSpace: "normal" } }, description)),
                    window.SP_REACT.createElement("div", { style: { display: "flex", alignItems: "center", gap: "8px", flexShrink: 0, color: "#a8adb4", fontSize: "11px" } },
                        value && window.SP_REACT.createElement("span", null, value),
                        window.SP_REACT.createElement("span", { style: { color: "#555b63", fontSize: "18px" } }, "›"))))));
}

function governorReasonLabel(reason) {
    switch (String(reason || "")) {
        case "diagnostics-log-unavailable": return "Diagnostics log unavailable";
        case "diagnostics-path-unavailable": return "Diagnostics path unavailable";
        case "diagnostics-active-no-events": return "Diagnostics active · waiting for renderer events";
        case "diagnostics-events-no-fps-samples": return "Renderer events found · no FPS samples yet";
        case "telemetry-stale": return "Telemetry stopped updating";
        case "collecting-fresh-evidence": return "Collecting fresh performance evidence";
        case "operating-point-recommended-not-yet-applied": return "Operating point ready to apply";
        case "tdp-control-unavailable": return "TDP control unavailable";
        case "power-search-started": return "Finding minimum stable power";
        case "governor-disabled": return "Governor is off";
        default: return String(reason || "Waiting for runtime evidence").replaceAll("-", " ");
    }
}

function GovernorHero({ profileName = "", onOpen }) {
    const { status, busy, setEnabled } = useGovernorView(profileName);
    const summary = status?.telemetry?.summary ?? {};
    const real = summary?.real?.median;
    const output = summary?.output?.median;
    const mult = summary?.multiplier?.median;
    const target = status?.target_output_fps;
    const power = status?.power ?? {};
    const point = status?.recommended_point;
    const enabled = Boolean(status?.enabled);
    const fmt = (value, digits = 0) => Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—";
    const rawState = String(status?.state || "PROBE");
    const activeState = ["LOCKED", "OPTIMIZE_POWER"].includes(rawState);
    return window.SP_REACT.createElement(DFL.PanelSectionRow, null,
        window.SP_REACT.createElement("div", { style: {
            width: "100%", boxSizing: "border-box", padding: "14px", borderRadius: "13px",
            background: "linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.025))",
            border: "1px solid rgba(255,255,255,.08)", boxShadow: "0 10px 25px rgba(0,0,0,.18)"
        } },
            window.SP_REACT.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "10px" } },
                window.SP_REACT.createElement("div", null,
                    window.SP_REACT.createElement("div", { style: { color: activeState ? "#ff6652" : "#f4f5f6", fontSize: "11px", fontWeight: 800, letterSpacing: ".7px", textTransform: "uppercase" } }, rawState.replaceAll("_", " ")),
                    window.SP_REACT.createElement("div", { style: { color: "#7d838c", fontSize: "9.5px", marginTop: "3px", maxWidth: "210px" } }, governorReasonLabel(status?.reason))),
                window.SP_REACT.createElement("div", { style: { textAlign: "right" } },
                    window.SP_REACT.createElement("div", { style: { color: "#fff", fontSize: "27px", lineHeight: 1, fontWeight: 800 } }, target || "—"),
                    window.SP_REACT.createElement("div", { style: { color: "#727780", fontSize: "8.5px", marginTop: "3px", letterSpacing: ".8px" } }, "TARGET FPS"))),
            window.SP_REACT.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr auto 1fr auto 1fr", gap: "8px", alignItems: "center", marginTop: "14px" } },
                [[fmt(real,1),"REAL"],[mult ? `×${fmt(mult,1)}` : "—","GFG"],[fmt(output,1),"OUTPUT"]].flatMap((entry, index) => {
                    const nodes = [window.SP_REACT.createElement("div", { key: `m-${index}`, style: { textAlign: "center", padding: "8px 4px", borderRadius: "8px", background: "rgba(0,0,0,.16)" } },
                        window.SP_REACT.createElement("div", { style: { color: index === 1 ? "#ff6652" : "#f6f7f8", fontSize: "18px", fontWeight: 800 } }, entry[0]),
                        window.SP_REACT.createElement("div", { style: { color: "#666c74", fontSize: "8px", marginTop: "2px" } }, entry[1]))];
                    if (index < 2) nodes.push(window.SP_REACT.createElement("div", { key: `a-${index}`, style: { color: "#444a52" } }, "→"));
                    return nodes;
                })),
            window.SP_REACT.createElement("div", { style: { display: "flex", justifyContent: "space-between", gap: "8px", marginTop: "11px", fontSize: "10px" } },
                window.SP_REACT.createElement("span", { style: { color: "#858a92" } }, point ? `${point.base_target_fps}×${point.multiplier} · ${point.render_scale_pct}%` : "Operating point not proven"),
                window.SP_REACT.createElement("span", { style: { color: "#f1f2f3", fontWeight: 700 } }, power.observed_tdp_w ? `${fmt(power.observed_tdp_w,1)} W` : "TDP —")),
            window.SP_REACT.createElement("div", { style: { marginTop: "10px" } },
                window.SP_REACT.createElement(DFL.ToggleField, { label: "Governor", description: enabled ? "Observe, prove, optimize power, then lock." : "Enable Governor for this profile. Restart the game once to attach renderer diagnostics.", checked: enabled, disabled: busy || !profileName, onChange: setEnabled, bottomSeparator: "none" })),
            onOpen && window.SP_REACT.createElement("div", { className: "GFG_BrandButton", style: { marginTop: "4px" } },
                window.SP_REACT.createElement(DFL.ButtonItem, { layout: "below", bottomSeparator: "none", onClick: onOpen }, "Open Governor"))));
}

function GovernorScreen({ profileName, onBack }) {
    const { status, busy, setEnabled } = useGovernorView(profileName);
    const summary = status?.telemetry?.summary ?? {};
    const snapshot = status?.telemetry?.snapshot ?? {};
    const point = status?.recommended_point;
    const power = status?.power ?? {};
    const search = status?.power_search ?? {};
    const fmt = (value, digits = 1) => Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—";
    return window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGPageTitle, { title: "Governor", subtitle: "One operating point. Minimum stable power. No constant retuning.", onBack }),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement(DFL.ToggleField, { label: "Governor", description: governorReasonLabel(status?.reason), checked: Boolean(status?.enabled), disabled: busy || !profileName, onChange: setEnabled, bottomSeparator: "none" })),
        window.SP_REACT.createElement(GFGSectionHeader, null, "Current state"),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", { style: { width: "100%", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" } },
                [["State", String(status?.state || "—").replaceAll("_"," ")],["Target", status?.target_output_fps ? `${status.target_output_fps} FPS` : "—"],["Operating point", point ? `${point.base_target_fps}×${point.multiplier} · ${point.render_scale_pct}%` : "—"],["TDP", power.observed_tdp_w ? `${fmt(power.observed_tdp_w)} W` : "—"],["P5 real", `${fmt(summary?.real?.p5)} FPS`],["Median real", `${fmt(summary?.real?.median)} FPS`],["Output", `${fmt(summary?.output?.median)} FPS`],["Samples", String(summary?.samples ?? 0)]].map(([label,value]) =>
                    window.SP_REACT.createElement("div", { key: label, style: { padding: "9px", borderRadius: "9px", background: "rgba(255,255,255,.035)", border: "1px solid rgba(255,255,255,.055)" } },
                        window.SP_REACT.createElement("div", { style: { color: "#666c74", fontSize: "8.5px", textTransform: "uppercase", letterSpacing: ".6px" } }, label),
                        window.SP_REACT.createElement("div", { style: { color: label === "State" ? "#ff6652" : "#f3f4f5", marginTop: "3px", fontSize: "12px", fontWeight: 700 } }, value))))),
        window.SP_REACT.createElement(GFGSectionHeader, null, "Telemetry"),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", { style: { width: "100%", padding: "10px", borderRadius: "9px", background: "rgba(255,255,255,.025)", color: "#a3a8af", fontSize: "10px", lineHeight: 1.5 } },
                window.SP_REACT.createElement("div", null, snapshot.available ? "Live FPS samples detected" : governorReasonLabel(status?.reason)),
                window.SP_REACT.createElement("div", { style: { color: "#656b74", marginTop: "4px", overflowWrap: "anywhere" } }, snapshot.path || "No diagnostics path"),
                snapshot.sample_age_ms != null && window.SP_REACT.createElement("div", { style: { color: "#656b74" } }, `Last sample ${fmt(snapshot.sample_age_ms,0)} ms ago`))),
        window.SP_REACT.createElement(GFGSectionHeader, null, "Power search"),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", { style: { width: "100%", color: "#9da2aa", fontSize: "10.5px", lineHeight: 1.5 } },
                window.SP_REACT.createElement("div", null, `State: ${search.state || "idle"}`),
                window.SP_REACT.createElement("div", null, `Known-good: ${search.known_good_tdp_w ? `${fmt(search.known_good_tdp_w)} W` : "—"}`),
                window.SP_REACT.createElement("div", null, `Reason: ${search.reason || "—"}`))));
}

function FrameGenerationScreen({ config, profileName, onConfigChange, onConfigUpdate, onBack, onAdvanced }) {
    const backend = config.fg_backend ?? FG_BACKEND_GFG;
    const [backendStatus, setBackendStatus] = SP_REACT.useState(null);
    SP_REACT.useEffect(() => {
        let active = true;
        if (backend !== FG_BACKEND_OPTISCALER) { setBackendStatus(null); return () => { active = false; }; }
        void getFgBackendStatus(profileName || "").then((result) => { if (active) setBackendStatus(result); }).catch(() => {});
        return () => { active = false; };
    }, [backend, config.optiscaler_proxy, profileName]);
    const backendOptions = [
        { data: FG_BACKEND_GFG, label: "GFG Engine" },
        { data: FG_BACKEND_OPTISCALER, label: "OptiScaler" },
        { data: FG_BACKEND_NATIVE, label: "Game Native" },
        { data: FG_BACKEND_OFF, label: "Off" },
    ];
    const fractional = isFractionalAdaptivePresetEnabled(config);
    const mode = !config.frame_generation_provisioned ? "off" : !config.adaptive ? "fixed" : fractional ? "adaptive-fractional" : "adaptive-smooth";
    const modeOptions = [
        { data: "off", label: "Off" }, { data: "fixed", label: "Fixed" },
        { data: "adaptive-smooth", label: "Adaptive Smooth" }, { data: "adaptive-fractional", label: "Adaptive Fractional" },
    ];
    const setMode = (value) => {
        if (value === "off") return void onConfigUpdate({ frame_generation_provisioned: false, frame_generation_enabled: false });
        if (value === "fixed") return void onConfigUpdate({ frame_generation_provisioned: true, frame_generation_enabled: true, adaptive: false });
        if (value === "adaptive-fractional") return void onConfigUpdate({ frame_generation_provisioned: true, frame_generation_enabled: true, ...fractionalAdaptivePresetChanges(true) });
        return void onConfigUpdate({ frame_generation_provisioned: true, frame_generation_enabled: true, adaptive: true, adaptive_auto_base_fps_cap: true, dynamic_cadence_recovery: false });
    };
    const currentMultiplier = config.adaptive ? (config.adaptive_max_multiplier ?? 2) : (config.multiplier ?? 2);
    const multiplierOptions = [2,3,...([2,3].includes(currentMultiplier) ? [] : [currentMultiplier])].sort().map((v) => ({ data:v, label:`×${v}${v>3 ? " · manual legacy" : ""}` }));
    const proxyOptions = OPTISCALER_PROXY_VALUES.map((proxy) => ({ data: proxy, label: proxy === OPTISCALER_PROXY_AUTO ? "Auto Detect" : `${proxy.toUpperCase()}.dll` }));
    return window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGPageTitle, { title: "Frame Generation", subtitle: "Choose one owner. Only controls relevant to that backend are shown.", onBack }),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement(DFL.Field, { label: "Backend", description: "Who owns frame generation for this profile.", childrenLayout: "below", childrenContainerWidth: "max" },
                window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: backendOptions, selectedOption: backend, onChange: (option) => onConfigChange(FG_BACKEND, String(option.data)) }))),
        backend === FG_BACKEND_GFG && window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: "Mode", childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: modeOptions, selectedOption: mode, onChange: (option) => setMode(String(option.data)) }))),
            mode !== "off" && window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: config.adaptive ? "Maximum multiplier" : "Multiplier", description: "Governor automatic planning uses x1/x2/x3 only.", childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: multiplierOptions, selectedOption: currentMultiplier, onChange: (option) => config.adaptive ? onConfigChange("adaptive_max_multiplier", Number(option.data)) : onConfigChange("multiplier", Number(option.data)) }))),
            window.SP_REACT.createElement(GFGNavRow, { label: "Engine tuning", description: "Quality model, cadence and renderer-specific controls", onClick: onAdvanced })),
        backend === FG_BACKEND_OPTISCALER && window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.Field, { label: "Proxy DLL", childrenLayout: "below", childrenContainerWidth: "max" },
                    window.SP_REACT.createElement(DFL.Dropdown, { rgOptions: proxyOptions, selectedOption: config.optiscaler_proxy ?? OPTISCALER_PROXY_AUTO, onChange: (option) => onConfigChange(OPTISCALER_PROXY, String(option.data)) }))),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement("div", { style: { color: "#a2a7ae", fontSize: "10.5px", lineHeight: 1.5 } },
                    `Status: ${backendStatus?.optiscaler_status || "not evaluated"}`,
                    backendStatus?.optiscaler_proxy_detected && window.SP_REACT.createElement("div", null, `Detected: ${backendStatus.optiscaler_proxy_detected}.dll`)))),
        backend === FG_BACKEND_NATIVE && window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement(GFGInlineTip, { tone: "info", alwaysVisible: true }, "The game owns frame generation. GFG scaling and shaders stay independent.")),
        backend === FG_BACKEND_OFF && window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement(GFGInlineTip, { tone: "info", alwaysVisible: true }, "Frame generation is disabled for this profile.")));
}

function ScalingScreen({ config, disabled, onConfigChange, onConfigUpdate, onBack }) {
    const method = config.scaling_enabled ? effectiveScalingMethod(config) : "off";
    const options = [
        { data:"off", label:"Off" }, { data:SCALING_METHOD_MAKO, label:"GFG Scaler" },
        { data:SCALING_METHOD_LS1, label:"LS1 Quality" }, { data:SCALING_METHOD_LS1_PERFORMANCE, label:"LS1 Performance" },
    ];
    const setMethod = (value) => value === "off" ? onConfigUpdate({ scaling_enabled:false }) : onConfigUpdate({ scaling_enabled:true, scaling_method:value });
    return window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGPageTitle, { title: "Scaling", subtitle: "Scaling is independent from frame generation.", onBack }),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement(DFL.Field, { label:"Scaler", childrenLayout:"below", childrenContainerWidth:"max" },
                window.SP_REACT.createElement(DFL.Dropdown, { rgOptions:options, selectedOption:method, disabled, onChange:(option)=>setMethod(String(option.data)) }))),
        config.scaling_enabled && window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.SliderField, { label:`Scale Factor (${Number(config.scaling_factor || 1).toFixed(1)}x)`, value:Number(config.scaling_factor || 1), min:1, max:2, step:.1, validValues:"steps", minimumDpadGranularity:.1, onChange:(value)=>onConfigChange(SCALING_FACTOR, Number(value.toFixed(1))) })),
            window.SP_REACT.createElement(DFL.PanelSectionRow, null,
                window.SP_REACT.createElement(DFL.SliderField, { label:`Sharpness (${Math.round(Number(config.scaling_sharpness || 0)*100)}%)`, value:Number(config.scaling_sharpness || 0), min:0, max:1, step:.01, onChange:(value)=>onConfigChange(SCALING_SHARPNESS, Number(value.toFixed(2))), bottomSeparator:"none" }))));
}

function AdvancedHub({ onBack, open }) {
    return window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGPageTitle, { title:"Advanced", subtitle:"Diagnostics and specialist controls live here, separated by task.", onBack }),
        window.SP_REACT.createElement(GFGNavRow, { label:"Pipeline Inspector", description:"Saved · Effective · Actual", onClick:()=>open("inspector") }),
        window.SP_REACT.createElement(GFGNavRow, { label:"Activity", description:"Configuration and Governor history", onClick:()=>open("activity") }),
        window.SP_REACT.createElement(GFGNavRow, { label:"Shaders", description:"vkBasalt and post-processing", onClick:()=>open("shaders") }),
        window.SP_REACT.createElement(GFGNavRow, { label:"Engine Tuning", description:"Renderer quality, cadence and expert FG controls", onClick:()=>open("tuning") }),
        window.SP_REACT.createElement(GFGNavRow, { label:"Compatibility", description:"WSI, overrides and manual compatibility options", onClick:()=>open("compatibility") }),
        window.SP_REACT.createElement(GFGNavRow, { label:"System", description:"Flatpak, installation and technical details", onClick:()=>open("system") }));
}

const localDevelopmentBuildInfo = null;


const currentRelease = {"version":"4.0.0-gfg.4 · Governor 0.0.1 β2","codename":"redline"};

function Content() {
    const { isInstalled, installationStatus, engineUpdateRequired, hostArchitectureSupported, installedEngineVersion, expectedEngineVersion, setIsInstalled, setInstallationStatus, checkInstallation, } = useInstallationStatus();
    const { dllDetected, dllDetectionStatus } = useDllDetection();
    const { config, vkBasaltConfigPath, applyConfigPatch, replaceConfig, loadGFGConfig, } = useGFGConfig();
    const { updateProfileConfigFields, syncCurrentProfile } = useProfileManagement();
    const { isInstalling, isUninstalling, isInstallCompletionVisible, handleInstall, handleUninstall, } = useInstallationActions();
    const { mainRunningApp, editingProfile, selectEditingProfile, getEditingProfile, } = useProfileSession({ isInstalled, loadProfileConfig: loadGFGConfig, syncCurrentProfile });
    const scalingRuntimeState = useRuntimeScalingStatus(editingProfile, Boolean(isInstalled && mainRunningApp));
    const modelStatus = useModelStatus(config, isInstalled);
    const [screen, setScreen] = SP_REACT.useState("home");
    const { saveConfigChanges: handleConfigChanges, saveConfigField: handleConfigChange, } = useProfileConfigWriter({ editingProfile, getEditingProfile, updateProfileConfigFields, loadProfileConfig: loadGFGConfig, applyConfigPatch, replaceConfig });
    const onInstall = async () => {
        await handleInstall(setIsInstalled, setInstallationStatus, loadGFGConfig, engineUpdateRequired ? "update" : "install");
        await checkInstallation();
    };
    const onUninstall = () => handleUninstall(setIsInstalled, setInstallationStatus);
    const handleShowAdvancedDetails = () => DFL.showModal(window.SP_REACT.createElement(AdvancedDetailsModal, null));
    const handleShowFlatpaks = () => DFL.showModal(window.SP_REACT.createElement(FlatpaksModal, null));
    const fgBackendLabel = inspectorBackendLabel(config.fg_backend ?? FG_BACKEND_GFG);
    const scaleValue = config.scaling_enabled ? methodLabel(effectiveScalingMethod(config)) : "Off";
    const activeName = mainRunningApp?.display_name || "No game running";
    const home = () => window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", { style: { width:"100%", padding:"7px 2px 4px" } },
                window.SP_REACT.createElement("div", { style: { display:"flex", justifyContent:"space-between", alignItems:"baseline", gap:"10px" } },
                    window.SP_REACT.createElement("div", null,
                        window.SP_REACT.createElement("div", { style: { color:"#fff", fontSize:"20px", fontWeight:900, letterSpacing:"-0.5px" } }, "GFG EXTREME"),
                        window.SP_REACT.createElement("div", { style: { color:"#6f757e", fontSize:"9px", marginTop:"2px" } }, currentRelease.version)),
                    window.SP_REACT.createElement("div", { style: { color:"#ff6652", fontSize:"9px", fontWeight:800, letterSpacing:".8px" } }, "REDLINE")))),
        engineUpdateRequired && window.SP_REACT.createElement(ContentNotices, { developmentBuildInfo:null, mainRunningApp:undefined, showWelcome:false, engineUpdateRequired:true, installedEngineVersion, expectedEngineVersion, isInstalling, isInstallCompletionVisible, isUninstalling, onInstall, modelStatus }),
        window.SP_REACT.createElement(DFL.PanelSectionRow, null,
            window.SP_REACT.createElement("div", { style:{ width:"100%", padding:"9px 10px", borderRadius:"10px", background:"rgba(255,255,255,.025)", border:"1px solid rgba(255,255,255,.05)" } },
                window.SP_REACT.createElement("div", { style:{ color:"#f3f4f5", fontSize:"12px", fontWeight:700, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" } }, activeName),
                window.SP_REACT.createElement("div", { style:{ color:"#737983", fontSize:"9px", marginTop:"3px" } }, `Profile · ${editingProfile || "—"}`))),
        window.SP_REACT.createElement(GovernorHero, { profileName:editingProfile, onOpen:()=>setScreen("governor") }),
        window.SP_REACT.createElement(GFGNavRow, { label:"Frame Generation", value:fgBackendLabel, description:"Backend and generation mode", onClick:()=>setScreen("fg") }),
        window.SP_REACT.createElement(GFGNavRow, { label:"Scaling", value:scaleValue, description:"Independent spatial scaling", onClick:()=>setScreen("scaling") }),
        window.SP_REACT.createElement(GFGNavRow, { label:"Profiles", value:editingProfile || "Default", description:"Games and process profiles", onClick:()=>setScreen("profiles") }),
        window.SP_REACT.createElement(GFGNavRow, { label:"Advanced", description:"Inspector, activity, shaders, compatibility and system", onClick:()=>setScreen("advanced") }));

    let body = null;
    if (!isInstalled) {
        body = window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
            window.SP_REACT.createElement(GfgExtremeHeader, null),
            window.SP_REACT.createElement(GFGReleaseIdentity, { version:currentRelease.version, codename:currentRelease.codename, bottomMargin:"8px" }),
            window.SP_REACT.createElement(ContentNotices, { developmentBuildInfo:null, mainRunningApp:undefined, showWelcome:false, engineUpdateRequired:false, installedEngineVersion, expectedEngineVersion, isInstalling, isInstallCompletionVisible, isUninstalling, onInstall, modelStatus }),
            window.SP_REACT.createElement(InstallationButton, { isInstalled, isInstalling, isInstallCompletionVisible, isUninstalling, hostArchitectureSupported, onInstall, onUninstall }),
            window.SP_REACT.createElement(StatusDisplay, { dllDetected, dllDetectionStatus, isInstalled, installationStatus, topMargin:"16px" }));
    }
    else if (screen === "home") body = home();
    else if (screen === "governor") body = window.SP_REACT.createElement(GovernorScreen, { profileName:editingProfile, onBack:()=>setScreen("home") });
    else if (screen === "fg") body = window.SP_REACT.createElement(FrameGenerationScreen, { config, profileName:editingProfile, onConfigChange:handleConfigChange, onConfigUpdate:handleConfigChanges, onBack:()=>setScreen("home"), onAdvanced:()=>setScreen("tuning") });
    else if (screen === "scaling") body = window.SP_REACT.createElement(ScalingScreen, { config, disabled:engineUpdateRequired, onConfigChange:handleConfigChange, onConfigUpdate:handleConfigChanges, onBack:()=>setScreen("home") });
    else if (screen === "profiles") body = window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGPageTitle, { title:"Profiles", subtitle:"Select what you are editing. Running games stay pinned to their active profile.", onBack:()=>setScreen("home") }),
        window.SP_REACT.createElement(ProfileManagement, { editingProfile, mainRunningApp, topMargin:"2px", onProfileChange:async (profileName)=>{ selectEditingProfile(profileName); await loadGFGConfig(profileName); } }));
    else if (screen === "advanced") body = window.SP_REACT.createElement(AdvancedHub, { onBack:()=>setScreen("home"), open:setScreen });
    else if (screen === "inspector") body = window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGPageTitle, { title:"Pipeline Inspector", subtitle:"Saved intent, effective launch state and actual process mappings.", onBack:()=>setScreen("advanced") }),
        mainRunningApp && window.SP_REACT.createElement(RuntimeStatusCard, { runtimeState:scalingRuntimeState }),
        window.SP_REACT.createElement(PipelineInspectorCard, { profileName:editingProfile }));
    else if (screen === "activity") body = window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGPageTitle, { title:"Activity", subtitle:"Configuration changes and rollback history.", onBack:()=>setScreen("advanced") }),
        window.SP_REACT.createElement(ConfigJournalCard, { profileName:editingProfile, onRestored:async()=>{ await loadGFGConfig(editingProfile); } }));
    else if (screen === "shaders") body = window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGPageTitle, { title:"Shaders", subtitle:"Post-processing stays independent from frame generation and scaling.", onBack:()=>setScreen("advanced") }),
        window.SP_REACT.createElement(ShadersConfigurationGroup, { config, isDefaultProfile:editingProfile===DEFAULT_PROFILE_NAME, profileName:editingProfile, vkBasaltConfigPath, onConfigChange:handleConfigChange }));
    else if (screen === "tuning") body = window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGPageTitle, { title:"Engine Tuning", subtitle:"Expert renderer controls. Normal Governor use should not require this page.", onBack:()=>setScreen("advanced") }),
        window.SP_REACT.createElement(PerformanceConfigurationGroup, { config, onConfigChange:handleConfigChange, onConfigUpdate:handleConfigChanges }),
        window.SP_REACT.createElement(FrameGenerationConfigurationSection, { config, onConfigChange:handleConfigChange, onConfigUpdate:handleConfigChanges, initiallyCollapsed:false }));
    else if (screen === "compatibility") body = window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGPageTitle, { title:"Compatibility", subtitle:"Low-level compatibility and manual overrides only.", onBack:()=>setScreen("advanced") }),
        window.SP_REACT.createElement(ConfigurationSection, { config, onConfigChange:handleConfigChange, onConfigUpdate:handleConfigChanges, includeAdvancedRendering:false }));
    else if (screen === "system") body = window.SP_REACT.createElement(window.SP_REACT.Fragment, null,
        window.SP_REACT.createElement(GFGPageTitle, { title:"System", subtitle:"Installation, Flatpak support and technical package information.", onBack:()=>setScreen("advanced") }),
        window.SP_REACT.createElement(StatusDisplay, { dllDetected, dllDetectionStatus, isInstalled, installationStatus, topMargin:"4px" }),
        window.SP_REACT.createElement(GFGNavRow, { label:"Flatpak Setup", description:"Runtime extensions and application access", onClick:handleShowFlatpaks }),
        window.SP_REACT.createElement(GFGNavRow, { label:"Technical Details", description:"Renderer and package details", onClick:handleShowAdvancedDetails }),
        window.SP_REACT.createElement(InstallationButton, { isInstalled, isInstalling, isInstallCompletionVisible, isUninstalling, hostArchitectureSupported, onInstall, onUninstall, topMargin:"16px" }));
    else body = home();

    return window.SP_REACT.createElement(InfoVisibility, null,
        window.SP_REACT.createElement(GFGButtonTheme, null),
        window.SP_REACT.createElement(DFL.PanelSection, null, body));
}

var index = definePlugin(() => {
    console.log("GFG Extreme initializing");
    return {
        name: "GFG Extreme",
        titleView: window.SP_REACT.createElement("div", { className: DFL.staticClasses.Title }, "GFG // EXTREME"),
        alwaysRender: true,
        content: window.SP_REACT.createElement(Content, null),
        icon: window.SP_REACT.createElement(MdBolt, null),
        onDismount() {
            console.log("GFG Extreme unloading");
        }
    };
});

export { index as default };
