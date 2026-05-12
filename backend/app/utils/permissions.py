import app.models.user

class Permissions:
    ADMIN_PANEL = "perm_admin_panel"
    VIEW_INSTANCES = "perm_view_instances"
    EDIT_INSTANCES = "perm_edit_instances"
    VIEW_USERS = "perm_view_users"
    EDIT_USERS = "perm_edit_users"
    VIEW_TIDES = "perm_view_tides"
    EDIT_TIDES = "perm_edit_tides"
    VIEW_REGISTRY = "perm_view_registry"
    EDIT_REGISTRY = "perm_edit_registry"
    VIEW_GROUPS = "perm_view_groups"
    EDIT_GROUPS = "perm_edit_groups"

    @staticmethod
    def check_permission(userid, permission):
        user = app.models.user.User.query.filter_by(id=userid).first()

        for group in user.groups:
            if getattr(group, permission):
                return True
        return False
