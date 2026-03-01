"""Editor runtime state bootstrap helpers."""

from __future__ import annotations

from collections import deque
from typing import Any
import os
import time
import uuid

from core.domain_impl.ui import tree_engine_service
from core.domain_impl.ui import tree_navigation_service
from core.domain_impl.ui.visual_asset_service import VISUALS
from core.exceptions import EXPECTED_ERRORS


def init_input_mode_runtime_state(owner: Any) -> None:
    """Initialize INPUT mode runtime fields."""
    owner._input_mode_container = None
    owner._input_mode_canvas = None
    owner._input_mode_scroll = None
    owner._input_mode_fields_host = None
    owner._input_mode_field_specs = []
    owner._input_mode_current_path = []
    owner._input_mode_no_fields_label = None
    owner._input_mode_last_render_item = None
    owner._input_mode_last_render_path_key = None
    owner._input_mode_force_refresh = True
    owner._input_mode_render_token = 0
    owner._input_mode_router_batch_after_id = None
    owner._input_mode_router_prewarm_after_id = None
    owner._input_mode_router_virtual_after_id = None
    owner._input_mode_router_settle_after_id = None
    owner._input_mode_scroll_drag_after_id = None
    owner._input_mode_scroll_drag_active = False
    owner._input_mode_router_row_pool = []
    owner._input_mode_router_pool_host = None
    owner._input_mode_router_shell = None
    owner._input_mode_router_art_cache = {}
    owner._input_suspicion_phone_photo_cache = {}
    # ROUTER INPUT prewarm defaults:
    # - max rows caps per-render workload
    # - prewarm row limit primes pooled rows for smooth first ROUTER open
    owner._router_input_max_rows = 60
    owner._router_input_prewarm_row_limit = 60
    owner._router_input_prewarm_row_limit_cap = 60
    owner._router_input_prewarm_delay_ms = 180
    owner._input_mode_router_virtual_rows = []
    owner._input_mode_router_virtual_next_index = 0
    owner._input_mode_router_virtual_total_rows = 0
    owner._input_mode_layout_finalize_after_id = None
    owner._input_mode_layout_finalize_reset_scroll = False
    owner._input_mode_refresh_after_id = None
    owner._input_mode_pending_item_id = None


def init_tree_runtime_state(owner: Any) -> None:
    """Initialize tree runtime fields via visual service."""
    VISUALS._init_tree_runtime_state(owner)


def init_chrome_runtime_state(owner: Any) -> None:
    """Initialize window chrome/runtime state used before UI build."""
    owner.logo_image = None
    owner.logo_label = None
    owner.logo_frame = None
    owner._logo_frame_inner = None
    owner._logo_path = None
    owner._logo_photo_cache = {}
    owner._header_frame = None
    owner._header_variant_bar = None
    owner._header_variant_host = None
    owner._header_variant_is_footer = False
    owner._header_variant_labels = {}
    owner._header_variant = "A"
    owner._show_header_variant_controls = False
    owner._editor_mode = "JSON"
    owner._editor_mode_host = None
    owner._editor_mode_parent = None
    owner._editor_mode_labels = {}
    owner._editor_mode_tab_cache = {}
    owner._editor_right_parent = None
    owner._body_panedwindow = None
    owner._body_paned_bindtags_default = ()
    owner._input_mode_paned_sash_x = None
    owner._input_mode_paned_fixed_sash_x = None
    owner._input_mode_paned_recheck_after_id = None
    owner._input_mode_paned_lock_active = False
    owner._text_scroll = None
    init_input_mode_runtime_state(owner)
    init_tree_runtime_state(owner)
    # INPUT mode is now public by default; keep flag for compatibility checks.
    owner._input_mode_public_enabled = True
    owner._app_theme_variant = "SIINDBAD"
    owner._app_theme_labels = {}
    owner._toolbar_style_variant = "B"
    # Toolbar variants are finalized: use Variant-B for all themes.
    owner._toolbar_style_variant_by_theme = {"SIINDBAD": "B", "KAMUE": "B", "GLITCH": "B"}
    # Dev toggle: set HACKHUB_ENABLE_TOOLBAR_VARIANTS=1 to show toolbar variant controls.
    owner._show_toolbar_variant_controls = (
        str(os.environ.get("HACKHUB_ENABLE_TOOLBAR_VARIANTS", "0")).strip().lower()
        in ("1", "true", "yes", "on")
    )
    # Optional forced style lock; keep unset so A/B can be switched from UI.
    owner._siindbad_style_focus = None
    owner._toolbar_button_images = {}
    owner._toolbar_asset_image_cache = {}
    owner._toolbar_theme_shade_cache = {}
    owner._toolbar_buttons = {}
    owner._toolbar_button_text = {}
    owner._toolbar_style_labels = {}
    owner._toolbar_style_title_label = None
    owner._toolbar_center_frame = None
    owner._toolbar_layout_mode = None
    owner._find_host_default_padx = None
    owner._find_button_default_padx = None
    owner._find_entry_width_override = None
    owner._topbar_align_after_id = None
    owner._topbar_align_pending_delay_ms = None
    owner._siindbad_button_icons = {}
    owner._siindbad_button_icon_signature = None


def init_footer_bugreport_runtime_state(owner: Any) -> None:
    """Initialize footer/chips/bug report runtime state."""
    owner._credit_badge_images = []
    owner._credit_badge_sources_cache = None
    owner._credit_github_icon_cache = {}
    owner._credit_discord_icon_cache = {}
    owner._credit_badge_render_signature = None
    owner._credit_discord_badge_render_signature = None
    owner._credit_badge_widget_pool = {}
    owner._credit_badge_active_signature = None
    owner._credit_discord_widget_pool = {}
    owner._credit_discord_active_signature = None
    owner._credit_badge_host = None
    owner._credit_discord_badge_host = None
    owner._credit_bar = None
    owner._credit_left_slot = None
    owner._credit_center_slot = None
    owner._credit_right_slot = None
    owner._credit_content = None
    owner._credit_label = None
    owner._credit_badges_divider = None
    owner._credit_badges_divider_lines = ()
    owner._credit_discord_badge_images = []
    owner._credit_discord_divider = None
    owner._credit_discord_divider_lines = ()
    owner._credit_theme_divider = None
    owner._credit_theme_divider_lines = ()
    owner._theme_selector_host = None
    owner._bug_report_host = None
    owner._bug_report_chip = None
    owner._bug_report_label = None
    owner._bug_report_chip_hovered = False
    owner._bug_report_chip_icon_photo = None
    owner._bug_report_icon_cache = {}
    owner._bug_report_chip_icon_label = None
    owner._bug_report_chip_text_label = None
    owner._bug_report_dialog = None
    owner._bug_report_card_frame = None
    owner._bug_report_header_frame = None
    owner._bug_report_header_icon = None
    owner._bug_report_header_icon_photo = None
    owner._bug_report_header_title = None
    owner._bug_report_close_badge = None
    owner._bug_report_pulse_after_id = None
    owner._bug_report_pulse_tick = 0
    owner._bug_report_follow_root = False
    owner._bug_report_offset_x = 0
    owner._bug_report_offset_y = 0
    owner._bug_report_is_dragging = False
    owner._last_bug_report_submit_monotonic = 0.0
    owner._bug_submit_splash = None
    owner._bug_submit_splash_after_id = None
    owner._theme_footer_refresh_after_id = None
    owner._titlebar_theme_signature_by_hwnd = {}
    owner._font_stepper_label = None
    owner._font_size_value_label = None
    owner._font_control_host = None
    owner._readme_window = None
    owner._find_entry_host = None
    owner._toolbar_host = None
    owner._body_top_separator = None
    owner._body_top_separator_inner = None
    owner.find_entry = None


def init_text_context_runtime_state(owner: Any) -> None:
    """Initialize text-context menu and font-stepper runtime state."""
    owner._text_context_menu = None
    owner._text_context_menu_anchor = None
    owner._text_context_menu_frame = None
    owner._text_context_menu_panel = None
    owner._text_context_menu_body = None
    owner._text_context_menu_separator = None
    owner._text_context_menu_separators = []
    owner._text_context_menu_items = {}
    owner._text_context_menu_widget_actions = {}
    owner._text_context_menu_row_style = None
    owner._text_context_menu_item_states = {}
    owner._text_context_menu_hover_action = None
    owner._text_context_menu_global_bindings = []
    owner._text_context_menu_pulse_after_id = None
    owner._text_context_menu_pulse_tick = 0
    owner._input_context_menu = None
    owner._input_context_target_widget = None
    owner._input_context_target_allow_paste = False
    owner.font_size_combo = None
    owner.font_size_var = None
    owner._font_stepper_source_size = (1028, 253)
    owner._font_stepper_minus_box_src = (395, 43, 648, 174)
    owner._font_stepper_plus_box_src = (676, 43, 929, 174)


def init_theme_update_runtime_state(owner: Any) -> None:
    """Initialize theme prewarm/update/startup-loader runtime fields."""
    owner._theme_prewarm_after_id = None
    owner._theme_prewarm_queue = []
    owner._theme_prewarm_done = set()
    owner._theme_prewarm_tasks = deque()
    owner._theme_prewarm_active_variant = None
    owner._theme_prewarm_budget_ms = 10
    owner._theme_prewarm_loader_budget_ms = 6
    owner._theme_prewarm_idle_tick_ms = 12
    owner._theme_prewarm_loader_tick_ms = 16
    owner._theme_prewarm_total_by_variant = {"SIINDBAD": 0, "KAMUE": 0, "GLITCH": 0}
    owner._theme_prewarm_done_by_variant = {"SIINDBAD": 0, "KAMUE": 0, "GLITCH": 0}
    owner._theme_logo_photo_by_variant = {}
    owner._toolbar_refresh_after_id = None
    owner._updates_auto_after_id = None
    # Saved startup update-check preference: default off unless user enables from update dialogs.
    owner._startup_update_check_enabled = False
    owner._update_overlay_title_after_id = None
    owner._update_overlay_progress_pct = 0.0
    owner._update_overlay_stage = ""
    owner._update_install_stage_hold_ms = 3000
    owner._update_restart_notice_ms = 4200
    owner._shutdown_cleanup_done = False
    owner._theme_perf_logging = (
        # Perf debug toggle: set HACKHUB_THEME_PERF_LOG=1 to print theme switch timings.
        str(os.environ.get("HACKHUB_THEME_PERF_LOG", "0")).strip().lower()
        in ("1", "true", "yes", "on")
    )
    owner._startup_loader_enabled = True
    owner._startup_loader_extra_hold_ms = 1600
    owner._startup_loader_overlay = None
    owner._startup_loader_pct_label = None
    owner._startup_loader_statement_label = None
    owner._startup_loader_top_fill = None
    owner._startup_loader_bottom_fill = None
    owner._startup_loader_started_ts = 0.0
    owner._startup_loader_ready_ts = None
    owner._startup_loader_text_after_id = None
    owner._startup_loader_hide_after_id = None
    owner._startup_loader_progress_after_id = None
    owner._startup_loader_statement_index = 0
    owner._startup_loader_line_pool_loading = []
    owner._startup_loader_line_pool_ready = []
    owner._startup_loader_required_variants = {"SIINDBAD", "KAMUE", "GLITCH"}
    owner._startup_loader_deferred_variants = set()
    owner._startup_loader_title_prefix_label = None
    owner._startup_loader_title_suffix_label = None
    owner._startup_loader_title_variant = "SIINDBAD"
    owner._startup_loader_title_after_id = None
    owner._startup_loader_title_cycle_ms = 4200
    owner._startup_loader_progress_interval_ms = 34
    owner._startup_loader_statement_interval_loading_ms = 1450
    owner._startup_loader_statement_interval_ready_ms = 1150
    owner._startup_loader_complete_dwell_ms = 260
    owner._startup_loader_finish_visible_hold_ms = 140
    owner._startup_loader_display_pct = 0.0
    owner._startup_loader_last_progress_ts = 0.0
    owner._startup_loader_smooth_rate_pct_per_sec = 30.0
    owner._startup_loader_finishing = False
    owner._startup_loader_finish_started_ts = 0.0
    owner._startup_loader_finish_start_pct = 0.0
    owner._startup_loader_finish_reached_100_ts = 0.0
    owner._startup_loader_window_mode = bool(
        getattr(owner.root, "_hh_use_startup_loader_window", False)
    )
    owner._startup_loader_title_cache = {}
    owner._startup_loader_fill_photo_cache = {}
    owner._startup_loader_panel_photo_cache = {}
    owner._theme_rgba_image_cache = {}
    owner._display_scale = 1.0
    owner._auto_display_profile_name = "default"
    owner._window_layout = None


def init_editor_session_runtime_state(owner: Any) -> None:
    """Initialize editor/session diagnostics and interaction runtime fields."""
    # Diagnostics file toggle:
    # - False disables `sins_json_diagnostics` file writes/rotation.
    owner.DIAG_LOG_ENABLED = False
    owner.network_types = ["ROUTER", "DEVICE", "FIREWALL", "SPLITTER"]
    owner.network_types_set = set(owner.network_types)
    owner.find_matches = []
    owner.find_index = 0
    owner.last_find_query = ""
    owner._find_search_entries = []
    owner._json_find_path_token_cache = {}
    owner._json_find_tag_widget = None
    owner.error_overlay = None
    owner.error_pin = None
    owner._mono_family = None
    owner._font_family_lookup_cache = None
    owner._font_size = 10
    owner._auto_apply_pending = False
    owner._auto_apply_in_progress = False
    owner._live_feedback_after_id = None
    owner._live_feedback_delay_ms = int(owner.LIVE_FEEDBACK_DELAY_MS_DEFAULT)
    owner._pending_insert_restore_index = ""
    owner._diag_event_seq = 0
    owner._diag_action = "startup:0"
    owner._error_visual_mode = "guide"
    owner._last_edit_was_deletion = False
    owner._error_focus_index = None
    owner._last_error_highlight_note = ""
    owner._last_error_insertion_only = False
    owner._last_error_overlay_message = ""
    owner._error_overlay_actions = None
    owner._allow_highlight_key_change_once = False
    owner._last_tree_selected_item = None
    owner._json_lock_apply_after_id = None
    owner._json_render_seq = 0
    owner._last_json_error_diag = None
    owner._error_hooks_installed = False
    owner._crash_notice_shown = False
    owner._prev_sys_excepthook = None
    owner._prev_threading_excepthook = None
    owner._session_id = uuid.uuid4().hex[:12]
    owner._session_started_monotonic = time.monotonic()
    owner._last_callback_origin = ""
    owner._crash_report_offer_after_id = None
    owner._document_load_depth = 0
    owner._document_load_in_progress = False
    owner._document_load_request_seq = 0
    owner._active_document_load_request_id = 0
    owner._document_load_async_after_id = None
    owner._document_load_async_result = None
    owner._document_load_last_completed_ts = 0.0
    owner._document_load_quiet_window_ms = 220
    owner._list_labelers = tree_engine_service.default_list_labelers(owner)
    owner._list_labelers[("Database",)] = owner._database_root_entry_label


def bootstrap(owner: Any) -> None:
    """Seed all grouped runtime state buckets for editor startup."""
    owner.TREE_NAV = tree_navigation_service.bind(
        owner,
        expected_errors=EXPECTED_ERRORS,
    )
    init_chrome_runtime_state(owner)
    init_footer_bugreport_runtime_state(owner)
    init_text_context_runtime_state(owner)
    init_theme_update_runtime_state(owner)
    init_editor_session_runtime_state(owner)


class EditorLifecycleFacade:
    """Facade entry points for runtime lifecycle seeding."""

    @staticmethod
    def bootstrap(owner: Any) -> None:
        bootstrap(owner)

    @staticmethod
    def init_chrome_runtime_state(owner: Any) -> None:
        init_chrome_runtime_state(owner)

    @staticmethod
    def init_footer_bugreport_runtime_state(owner: Any) -> None:
        init_footer_bugreport_runtime_state(owner)

    @staticmethod
    def init_text_context_runtime_state(owner: Any) -> None:
        init_text_context_runtime_state(owner)

    @staticmethod
    def init_theme_update_runtime_state(owner: Any) -> None:
        init_theme_update_runtime_state(owner)

    @staticmethod
    def init_editor_session_runtime_state(owner: Any) -> None:
        init_editor_session_runtime_state(owner)

    @staticmethod
    def init_input_mode_runtime_state(owner: Any) -> None:
        init_input_mode_runtime_state(owner)

    @staticmethod
    def init_tree_runtime_state(owner: Any) -> None:
        init_tree_runtime_state(owner)


LIFECYCLE = EditorLifecycleFacade()
