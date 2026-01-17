from django.contrib import admin

# Customize Django Admin Site
admin.site.site_header = "🚗 AutoNews Admin Panel"
admin.site.site_title = "AutoNews Admin"
admin.site.index_title = "Welcome to AutoNews Management"

# Add custom CSS
class AdminCustomization:
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
