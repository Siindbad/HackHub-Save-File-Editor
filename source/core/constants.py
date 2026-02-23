APP_VERSION = "1.3.7"

GITHUB_OWNER = "Siindbad"
GITHUB_REPO = "HackHub-Save-File-Editor"
GITHUB_ASSET_NAME = "sins_editor-onedir.zip"
DIST_BRANCH = "main"
DIST_VERSION_FILE = "version.txt"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
UPDATE_TOKEN_ENV = "GITHUB_UPDATE_TOKEN"
BUG_REPORT_TOKEN_ENV = "GITHUB_BUGREPORT_TOKEN"

BUG_REPORT_GITHUB_OWNER = "Siindbad"
BUG_REPORT_GITHUB_REPO = "HackHub-Save-File-Editor"
BUG_REPORT_LABELS = ("bug", "in-app-report")
BUG_REPORT_USE_CUSTOM_CHROME = True
BUG_REPORT_UPLOAD_BRANCH = "main"
BUG_REPORT_UPLOADS_DIR = "bug-uploads"
BUG_REPORT_SCREENSHOT_ALLOWED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
BUG_REPORT_SCREENSHOT_MAX_BYTES = 5 * 1024 * 1024
BUG_REPORT_SCREENSHOT_MAX_DIMENSION = 4096
BUG_REPORT_SCREENSHOT_RETENTION_DAYS = 90
BUG_REPORT_SUBMIT_COOLDOWN_SECONDS = 45
# Optional Discord Forum mirror for in-app bug reports.
# - Set webhook env var to enable forum posting.
# - Set forum tag IDs env var as comma/space-separated numeric IDs (optional).
BUG_REPORT_DISCORD_WEBHOOK_ENV = "DISCORD_BUGREPORT_WEBHOOK"
BUG_REPORT_DISCORD_FORUM_TAG_IDS_ENV = "DISCORD_BUGREPORT_FORUM_TAG_IDS"

DIAG_LOG_MAX_BYTES = 512 * 1024
DIAG_LOG_KEEP_BYTES = 256 * 1024
DIAG_LOG_FILENAME = "sins_json_diagnostics.log"
LEGACY_DIAG_LOG_FILENAMES = ("sins_json_diagnostics.txt",)
LEGACY_SETTINGS_FILENAME = ".sins_editor_settings.json"
RUNTIME_DIR_NAME = "HackHubSaveEditor"
SETTINGS_FILENAME = "sins_editor_settings.json"
CRASH_LOG_FILENAME = "sins_editor_crash.log"
CRASH_STATE_FILENAME = "crash_prompt_state.json"
CRASH_LOG_TAIL_MAX_CHARS = 12000

LIVE_FEEDBACK_DELAY_MS_DEFAULT = 140
STATUS_LOADED = "Loaded"
STATUS_SAVED = "Saved"
STATUS_EXPORTED_HHSAV = "Exported .hhsav"
EXPORT_HHSAV_DIALOG_TITLE = "Export As .hhsav (gzip)"

DIST_ASSET_SHA256_CANDIDATES = ("sins_editor-onedir.zip.sha256", "sha256.txt", "checksums.txt")
UPDATE_REQUIRE_SHA256 = True
UPDATE_VERIFY_AUTHENTICODE = True
UPDATE_REQUIRE_AUTHENTICODE = False
UPDATE_AUTHENTICODE_ALLOWED_SUBJECTS = ()

HIDDEN_ROOT_TREE_CATEGORIES = (
    "_persist",
    "Objective State",
    "ObjectiveState",
    "Surfaces",
    "GameMode",
    "Dialog",
    "Ftp",
)

# Mode-scoped root tree hide lists:
# - JSON keeps the baseline hidden categories.
# - INPUT can diverge without affecting JSON behavior.
HIDDEN_ROOT_TREE_CATEGORIES_INPUT = tuple(HIDDEN_ROOT_TREE_CATEGORIES) + (
    "App.Store",
    "AppStore",
    "BCC.News",
    "BCCNews",
    "Bookmarks",
    "Browser.Session",
    "BrowserSession",
    "Computer",
    "Files",
    "Global.Store",
    "GlobalStore",
    "Esc.Menu",
    "EscMenu",
    "Global.Variables",
    "GlobalVariables",
    "Hacked",
    "Hackhub",
    "Installed.Apps",
    "InstalledApps",
    "Kisscord",
    "Mail.Accounts",
    "MailAccounts",
    "Mails",
    "Personal.Info",
    "PersonalInfo",
    "Phone.Call",
    "PhoneCall",
    "Phone.Messages",
    "PhoneMessages",
    "Process",
    "Program.Sizes",
    "ProgramSizes",
    "Quests",
    "Save",
    "Scoutify",
    "Skills",
    "stats",
    "Taskbar",
    "Terminal",
    "Twotter",
    "Typewriter",
    "Website.Templates",
    "WebsiteTemplates",
)
HIDDEN_ROOT_TREE_KEYS_JSON = {str(name).strip().casefold() for name in HIDDEN_ROOT_TREE_CATEGORIES}
HIDDEN_ROOT_TREE_KEYS_INPUT = {str(name).strip().casefold() for name in HIDDEN_ROOT_TREE_CATEGORIES_INPUT}

# Add root category names here to disable INPUT-mode editing for that branch.
INPUT_MODE_DISABLED_ROOT_CATEGORIES = (
    "Phone",
    "Skypersky",
)
INPUT_MODE_DISABLED_ROOT_KEYS = {
    str(name).strip().casefold() for name in INPUT_MODE_DISABLED_ROOT_CATEGORIES
}

# INPUT tree expand-block policy:
# Root categories listed here stay collapsed in INPUT mode (JSON mode unaffected).
INPUT_MODE_NO_EXPAND_ROOT_CATEGORIES = (
    "Bank",
    "Phone",
    "Skypersky",
    "Database",
    "Mail.Accounts",
    "MailAccounts",
)
INPUT_MODE_NO_EXPAND_ROOT_KEYS = {
    str(name).strip().casefold() for name in INPUT_MODE_NO_EXPAND_ROOT_CATEGORIES
}

# INPUT Network subgroup policy:
# Keep these Network type buckets collapsed in INPUT mode while still showing them.
INPUT_MODE_NETWORK_NO_EXPAND_GROUPS = (
    "ROUTER",
    "DEVICE",
    "FIREWALL",
    "SPLITTER",
)
INPUT_MODE_NETWORK_NO_EXPAND_GROUP_KEYS = {
    str(name).strip().casefold() for name in INPUT_MODE_NETWORK_NO_EXPAND_GROUPS
}

# INPUT Network subgroup hide policy:
# Hide these Network type buckets in INPUT mode while keeping JSON mode unchanged.
INPUT_MODE_NETWORK_HIDDEN_GROUPS = (
    "SPLITTER",
)
INPUT_MODE_NETWORK_HIDDEN_GROUP_KEYS = {
    str(name).strip().casefold() for name in INPUT_MODE_NETWORK_HIDDEN_GROUPS
}

# INPUT marker override policy:
# Render red main arrows for selected root categories in INPUT mode only.
INPUT_MODE_RED_ARROW_ROOT_CATEGORIES = (
    "Bank",
    "Phone",
    "Suspicion",
    "Skypersky",
    "Database",
    "Mail.Accounts",
    "MailAccounts",
)
INPUT_MODE_RED_ARROW_ROOT_KEYS = {
    str(name).strip().casefold() for name in INPUT_MODE_RED_ARROW_ROOT_CATEGORIES
}

# INPUT marker override for Network subgroup buckets.
INPUT_MODE_RED_ARROW_NETWORK_GROUPS = tuple(INPUT_MODE_NETWORK_NO_EXPAND_GROUPS)
INPUT_MODE_RED_ARROW_NETWORK_GROUP_KEYS = {
    str(name).strip().casefold() for name in INPUT_MODE_RED_ARROW_NETWORK_GROUPS
}

TREE_B_SAFE_DISPLAY_LABELS = {
    "GlobalStore": "Global.Store",
    "ProgramSizes": "Program.Sizes",
    "GlobalVariables": "Global.Variables",
    "MailAccounts": "Mail.Accounts",
    "PhoneMessages": "Phone.Messages",
    "PersonalInfo": "Personal.Info",
    "BrowserSession": "Browser.Session",
    "InstalledApps": "Installed.Apps",
    "PhoneCall": "Phone.Call",
    "AppStore": "App.Store",
    "EscMenu": "Esc.Menu",
    "WebsiteTemplates": "Website.Templates",
    "BCCNews": "BCC.News",
}

HEADER_VARIANT_RESTORE_SPEC = {
    "variants": ("A", "B"),
    "default": "A",
    "show_title_default": False,
    "host_pack_footer": {"side": "left", "padx": (4, 0)},
    "host_pack_header": {"anchor": "center"},
    "title_text": "VARIANT :",
    "title_font_size": 9,
    "title_font_weight": "bold",
    "title_padx": (0, 6),
    "chip_padx_footer": 5,
    "chip_padx_header": 7,
    "chip_pady": 1,
    "chip_gap": 3,
    "chip_bg": "#0f1b29",
    "chip_fg": "#8aa9bf",
    "chip_border": "#2f4a61",
}

TREE_MAIN_MARKER_FILES = {
    "SIINDBAD": "tree-main-square-siindbad.png",
    "KAMUE": "tree-main-square-kamue.png",
}

TREE_MAIN_MARKER_SHA256 = {
    "SIINDBAD": "53aa1864bbc6d874305647f5a382c0d409e538e65801e142c6095ed40d0c6945",
    "KAMUE": "3956b9ba11fb162eaac89a7da41e70344091098505a84308a9a6ca0cd347c107",
}

TREE_B2_MARKER_SHA256 = {
    "b2-main-collapsed-kamue.png": "89fdc57d09fd3cc8dcefa9ec0e3302f4d64cfe8ac7c1f8cdf70c3928cb95164d",
    "b2-main-collapsed-siindbad.png": "f1f1d3f3701a9ddd7817120e4a102ccb534cd579b1b3f6a6b145bf33ce94ca67",
    "b2-main-expanded-kamue.png": "32ee23fb634f63aea679a00acef2ae796e905039408e6a3e88c0a0f16f6e5b37",
    "b2-main-expanded-siindbad.png": "adacd167bd2b8da7985c04212e37e1b6545347216a13f763c537c3c3359769a6",
    "b2-main-leaf-kamue.png": "67d2dde60239c36236d6c5a1983c7c8d4391c7a5858a5f1aa1e01344af5efa4a",
    "b2-main-leaf-siindbad.png": "1ffe673d782b407023caf429ce6cb5e61b05d1b2bc7c36b2c7ad0a07d10f3f57",
    "b2-sub-off-collapsed-kamue.png": "0c2dd3aac759a6df29a689334a39a2680ec59d8a215dc6b5551e414085fde212",
    "b2-sub-off-collapsed-siindbad.png": "6ff59203b4fb4c2c9df26aeb82fcf384d7822d3ee404e18a543bbcdd223c6981",
    "b2-sub-off-expanded-kamue.png": "19ccbc62fd0128cdfb0528cf2a08d848dd7169daf5afd17e9139405ff0fb5bad",
    "b2-sub-off-expanded-siindbad.png": "06983ca691ce5131bd0d57d403718c7533e5a095ff7986704ac8138d036c7085",
    "b2-sub-off-leaf-kamue.png": "bc0ae0223b052fddcdf3c8dd7d86cd54d624880c1e11def496cfd979da92d958",
    "b2-sub-off-leaf-siindbad.png": "e050f1fe0e4b76c40c933d889bd68294afc06f8bb6e9dbc9fb2178e4f67af4c5",
    "b2-sub-on-collapsed-kamue.png": "1244f70a5dba68046718dc251bf5472fdf76c891974f3a8c17b2e2388c0498cf",
    "b2-sub-on-collapsed-siindbad.png": "b09fee6243a21012c8426cf6c16954b918067b61d8c454728d11c457d3f951b3",
    "b2-sub-on-expanded-kamue.png": "410e76751beacd227717b7644f0cddd406d5b59eb6074f5643e32ec6451aa2e9",
    "b2-sub-on-expanded-siindbad.png": "30ecb656d585e438d57b3818314a443c0834d1f4d0c3415bd7030b5c443124de",
    "b2-sub-on-leaf-kamue.png": "646df2efb3680b16c9f24f4aab3edb36299e2712d24ad758221f938d19fd7837",
    "b2-sub-on-leaf-siindbad.png": "ff99396f98d06c7939a92a547191d7d64c3791600498d0ea25b6f365d2018a50",
}
