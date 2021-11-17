# Generated by Django 2.2.10 on 2020-05-06 11:46


from django.db import migrations


def fix_primary_emails(apps, schema_editor):
    """
    Goes through all the profiles:
    1) Tries to set first matching email with primary=True as a primary email
    2) Tries to set first email as a primary email
    3) If no emails found, profile gets deleted with a message
    4) If profiles has more than one primary email, first will remain as the primary and primary=False will be set for
       the rest
    """
    Profile = apps.get_model("profiles", "Profile")
    for profile in Profile.objects.all():
        primary_emails = profile.emails.filter(primary=True)
        primary_email = primary_emails.first()
        if not primary_email:
            if profile.emails.count() > 0:
                primary_email = profile.emails.first()
            else:
                print(f"Removing profile of {profile.first_name} {profile.last_name}\n")
                profile.delete()
                continue
            primary_email.primary = True
            primary_email.save()
        elif primary_emails.count() > 1:
            primary_emails.exclude(pk=primary_email.pk).update(primary=False)


class Migration(migrations.Migration):

    dependencies = [("profiles", "0024_order_emails")]

    operations = [migrations.RunPython(fix_primary_emails, migrations.RunPython.noop)]
