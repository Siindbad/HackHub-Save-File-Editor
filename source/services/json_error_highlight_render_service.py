"""JSON highlight renderer service."""


# Rendering helpers keep Tk-tag application out of decision code.
def apply_json_error_highlight(owner, exc, line, start_index, end_index, note=None):
    return owner._apply_json_error_highlight(exc, line, start_index, end_index, note=note)


def log_json_error(owner, exc, target_line, note=""):
    return owner._log_json_error(exc, target_line, note=note)
