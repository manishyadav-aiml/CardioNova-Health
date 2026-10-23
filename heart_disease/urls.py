from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),          # the admin address can be changed with DJANGO_ADMIN_URL
    path("", include("prediction.urls")),
]

# Friendly error pages that never show technical details
handler400 = "prediction.views.error_400"
handler403 = "prediction.views.error_403"
handler404 = "prediction.views.error_404"
handler500 = "prediction.views.error_500"
