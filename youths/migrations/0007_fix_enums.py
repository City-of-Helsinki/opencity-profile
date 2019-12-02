# Generated by Django 2.2.4 on 2019-12-02 20:51

from django.db import migrations
import enumfields.fields
import youths.enums


class Migration(migrations.Migration):

    dependencies = [
        ('youths', '0006_youthprofile_birth_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='youthprofile',
            name='language_at_home',
            field=enumfields.fields.EnumField(default='fi', enum=youths.enums.YouthLanguage, max_length=32),
        ),
    ]
