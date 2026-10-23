from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from . import password_reset_views as reset_views


urlpatterns = [
    # =========================
    # HOME PAGE
    # =========================
    path("", views.home, name="home"),

    # =========================
    # USER AUTHENTICATION
    # =========================
    path("register/", views.register, name="register"),
    path("login/", views.RateLimitedLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # =========================
    # PASSWORD RESET USING EMAIL LINK
    # =========================
    path(
        "password-reset/link/",
        auth_views.PasswordResetView.as_view(
            template_name="prediction/password_reset_link_form.html",
            email_template_name="prediction/password_reset_email.txt",
            subject_template_name="prediction/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_link_sent"),
        ),
        name="password_reset_link",
    ),
    path(
        "password-reset/link/sent/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="prediction/password_reset_link_sent.html",
        ),
        name="password_reset_link_sent",
    ),
    path(
        "password-reset/link/confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="prediction/password_reset_link_confirm.html",
            success_url=reverse_lazy("password_reset_link_complete"),
        ),
        name="password_reset_link_confirm",
    ),
    path(
        "password-reset/link/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="prediction/password_reset_link_complete.html",
        ),
        name="password_reset_link_complete",
    ),

    # =========================
    # PASSWORD RESET USING OTP
    # =========================
    path(
        "password-reset/",
        reset_views.password_reset_request,
        name="password_reset_request",
    ),
    path(
        "password-reset/verify/",
        reset_views.password_reset_verify,
        name="password_reset_verify",
    ),
    path(
        "password-reset/new/",
        reset_views.password_reset_new,
        name="password_reset_new",
    ),
    path(
        "password-reset/complete/",
        reset_views.password_reset_complete,
        name="password_reset_complete",
    ),

    # =========================
    # HEART DISEASE PREDICTION
    # =========================
    path("predict/", views.predict, name="predict"),
    path("result/<int:pk>/", views.result, name="result"),
    path(
        "result/<int:pk>/report/",
        views.download_report,
        name="download_report",
    ),
    path(
        "result/<int:pk>/whatif/",
        views.whatif,
        name="whatif",
    ),
    path(
        "result/<int:pk>/delete/",
        views.delete_record,
        name="delete_record",
    ),

    # =========================
    # HISTORY AND BATCH PREDICTIONS
    # =========================
    path("history/", views.history, name="history"),
    path("batch/", views.batch_predict, name="batch"),
    path(
        "batch/template/",
        views.batch_template,
        name="batch_template",
    ),

    # =========================
    # USER PROFILE
    # =========================
    path("profile/", views.profile, name="profile"),
    path(
        "profile/delete/",
        views.delete_account,
        name="delete_account",
    ),

    # =========================
    # MODEL INFORMATION
    # =========================
    path("model/", views.model_details, name="model"),

    # =========================
    # SEARCH, FAQ, CONTACT AND PRIVACY
    # =========================
    path("search/", views.search, name="search"),
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("privacy/", views.privacy, name="privacy"),

    # =========================
    # DOCTOR DASHBOARD
    # =========================
    path(
        "doctor/",
        views.doctor_dashboard,
        name="doctor_dashboard",
    ),
    path(
        "doctor/patient/<int:user_id>/",
        views.doctor_patient,
        name="doctor_patient",
    ),

    # =========================
    # API ENDPOINTS
    # =========================
    path("api/health/", views.api_health, name="api_health"),
    path("api/predict/", views.api_predict, name="api_predict"),
    path("api/whatif/", views.api_whatif, name="api_whatif"),
    path("api/history/", views.api_history, name="api_history"),
]