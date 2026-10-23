from django.contrib import admin

from .models import ContactMessage, DoctorAccessLog, PredictionRecord, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Doctors are made here: change the role of a user to 'Doctor'."""
    list_display = ("user", "role", "share_with_doctors", "utm_source", "utm_campaign", "created_at")
    list_editable = ("role",)
    list_filter = ("role", "share_with_doctors", "utm_source")
    search_fields = ("user__username", "user__email")
    exclude = ("api_token_hash",)            # never show or edit token hashes


@admin.register(PredictionRecord)
class PredictionRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "patient_label", "risk_level", "probability", "source", "created_at")
    list_filter = ("risk_level", "source", "created_at")
    search_fields = ("user__username", "patient_label")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)


@admin.register(DoctorAccessLog)
class DoctorAccessLogAdmin(admin.ModelAdmin):
    """Audit trail: read-only so that nobody can erase it from the admin site."""
    list_display = ("viewed_at", "doctor", "patient", "record")
    list_filter = ("viewed_at",)
    search_fields = ("doctor__username", "patient__username")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "email", "handled")
    list_filter = ("handled", "created_at")
    search_fields = ("name", "email", "message")
    readonly_fields = ("name", "email", "message", "ip_hash", "created_at")
