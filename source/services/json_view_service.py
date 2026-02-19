NO_FILE_LOADED_MESSAGE = "No File Loaded. Open A .HHSAV File Before Continuing."


def show_json_no_file_message(text_widget):
    try:
        text_widget.delete("1.0", "end")
        text_widget.insert("1.0", NO_FILE_LOADED_MESSAGE)
        text_widget.edit_modified(False)
    except Exception:
        return
