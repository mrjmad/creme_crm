from django.db import migrations, models
from django.db.models.deletion import CASCADE

import creme.creme_core.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('billing', '0021_v2_2__line_vat_not_null2'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExporterConfigItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('exporter_id', models.CharField(max_length=80)),
                ('content_type', creme.creme_core.models.fields.CTypeOneToOneField(on_delete=CASCADE, to='contenttypes.ContentType')),
            ],
        ),
    ]
