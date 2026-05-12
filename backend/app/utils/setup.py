# import json
import os

# def get_setting(key, default=None):
#     """Read a value from data/settings.json."""
#     path = "data/settings.json"
#     if os.path.exists(path):
#         try:
#             with open(path, 'r', encoding="utf-8") as f:
#                 return json.load(f).get(key, default)
#         except Exception:
#             pass
#     return default


# def set_setting(key, value):
#     """Write a value to data/settings.json."""
#     path = "data/settings.json"
#     settings = {}
#     if os.path.exists(path):
#         try:
#             with open(path, 'r', encoding="utf-8") as f:
#                 settings = json.load(f)
#         except Exception:
#             pass
#     settings[key] = value
#     with open(path, 'w', encoding="utf-8") as f:
#         json.dump(settings, f, indent=2)

def get_join_token():
    token_path = "data/join_token"
    if os.path.exists(token_path):
        with open(token_path, 'r', encoding="utf-8") as f:
            return f.read().strip()
    return None
