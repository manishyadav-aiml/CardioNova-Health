from django.db import migrations, models


class Migration(migrations.Migration):
    """Doctor sharing becomes opt-in: new patients are NOT shared until they switch it on.

    Existing profiles keep their stored value. To make every existing patient private as well, run once:
        python manage.py shell -c "from prediction.models import Profile; Profile.objects.filter(role='patient').update(share_with_doctors=False)"
    """

    dependencies = [
        ("prediction", "0003_merge_0002_utm_accesslog_contact_0002_v2_features"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="share_with_doctors",
            field=models.BooleanField(default=False),
        ),
    ]
