# Generated by Django 2.2.10 on 2020-02-06 18:19

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('creme_core', '0064_v2_2__remove_rtype_object_m2m'),
    ]

    operations = [
        migrations.RenameField(
            model_name='entityfiltercondition',
            old_name='value',
            new_name='raw_value',
        ),
    ]
