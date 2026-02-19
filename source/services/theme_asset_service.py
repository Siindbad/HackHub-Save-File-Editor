import os


def resource_base_dir(module_resource_base_dir_fn):
    try:
        return module_resource_base_dir_fn()
    except Exception:
        return os.getcwd()


def siindbad_b_sprite_dir(base_dir):
    return os.path.join(base_dir, "assets", "buttons", "variants", "B", "r5_sprites")
