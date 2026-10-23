import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("prediction", "0001_initial"),
    ]

    operations = [
        migrations.AddField(model_name="profile", name="utm_source", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="profile", name="utm_medium", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="profile", name="utm_campaign", field=models.CharField(blank=True, max_length=100)),
        migrations.CreateModel(
            name="ContactMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("email", models.EmailField(max_length=254)),
                ("message", models.TextField(max_length=2000)),
                ("ip_hash", models.CharField(blank=True, max_length=16)),
                ("handled", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DoctorAccessLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("viewed_at", models.DateTimeField(auto_now_add=True)),
                ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="access_given", to=settings.AUTH_USER_MODEL)),
                ("patient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="access_log", to=settings.AUTH_USER_MODEL)),
                ("record", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="prediction.predictionrecord")),
            ],
            options={"ordering": ["-viewed_at"]},
        ),
    ]
