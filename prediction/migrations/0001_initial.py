import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("patient", "Patient"), ("doctor", "Doctor")], default="patient", max_length=10)),
                ("share_with_doctors", models.BooleanField(default=True)),
                ("api_token_hash", models.CharField(blank=True, db_index=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="PredictionRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("patient_label", models.CharField(blank=True, max_length=100)),
                ("age", models.PositiveSmallIntegerField()),
                ("sex", models.PositiveSmallIntegerField()),
                ("cp", models.PositiveSmallIntegerField()),
                ("trestbps", models.PositiveSmallIntegerField()),
                ("chol", models.PositiveSmallIntegerField()),
                ("fbs", models.PositiveSmallIntegerField()),
                ("restecg", models.PositiveSmallIntegerField()),
                ("thalach", models.PositiveSmallIntegerField()),
                ("exang", models.PositiveSmallIntegerField()),
                ("oldpeak", models.FloatField()),
                ("slope", models.PositiveSmallIntegerField()),
                ("ca", models.PositiveSmallIntegerField()),
                ("thal", models.PositiveSmallIntegerField()),
                ("probability", models.FloatField()),
                ("risk_level", models.CharField(max_length=10)),
                ("explanation", models.JSONField(blank=True, default=list)),
                ("model_name", models.CharField(blank=True, max_length=60)),
                ("source", models.CharField(default="form", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="predictions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
