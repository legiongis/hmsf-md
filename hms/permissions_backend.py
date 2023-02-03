import logging

logger = logging.getLogger(__name__)

def user_is_anonymous(user):
    return user.username == 'anonymous'

def user_is_land_manager(user):
    return hasattr(user, "landmanager")

def user_is_scout(user):
    return hasattr(user, "scout")

def generate_site_access_html(user):

    FULL_ACCESS_HTML = "<p>Your account has full access to <strong>all</strong> archaeological sites.</p>"
    NO_ACCESS_HTML = "<p>Your account does not have access to any archaeological sites.</p>"

    if user.is_superuser:
        return FULL_ACCESS_HTML
    if user_is_anonymous(user):
        return NO_ACCESS_HTML

    if user_is_scout(user):

        if user.scout.scoutprofile.site_access_mode == "FULL":
            return FULL_ACCESS_HTML
        elif user.scout.scoutprofile.site_access_mode == "USERNAME=ASSIGNEDTO":
            return "<p>You have access to any archaeological sites to which you have been individually assigned.</p>"
        else:
            return NO_ACCESS_HTML

    if user_is_land_manager(user):

        if user.landmanager.site_access_mode == "FULL":
            html = FULL_ACCESS_HTML
        elif user.landmanager.site_access_mode == "AREA":
            html = "<p>You can access any archaeological sites that are located in the following Management Areas:</p>"
            if len(user.landmanager.all_areas) == 0:
                html += "<p><em>No Management Areas have been added to your Land Manager profile.</em></p>"
            else:
                html += "<ul style='list-style:none; padding-left:0px; font-weight:bold;'>"
                for group in user.landmanager.grouped_areas.all():
                    html += f"<li>{group.name} (grouped area)</li>"
                for area in user.landmanager.individual_areas.all():
                    html += f"<li>{area.name}</li>"
                html += "</ul>"
        elif user.landmanager.site_access_mode == "AGENCY":
            html = f"<p>You can access any archaeological sites that are managed by your agency: <strong>{user.landmanager.management_agency}</strong></p>"
        else:
            html = NO_ACCESS_HTML

        return html
