from django.db import migrations, models


class Migration(migrations.Migration):
    """Two-factor login (TOTP) fields on the profile."""

    dependencies = [
        ("prediction", "0004_share_with_doctors_default_off"),
    ]

    operations = [
        migrations.AddField(model_name="profile", name="totp_secret", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="profile", name="totp_enabled", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="profile", name="totp_last_step", field=models.BigIntegerField(default=0)),
        migrations.AddField(model_name="profile", name="recovery_hashes", field=models.JSONField(blank=True, default=list)),
    ]
