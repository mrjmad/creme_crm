# Generated by Django 2.2.13 on 2020-06-29 18:02

from django.db import migrations, models
from django.db.models.deletion import PROTECT


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0020_v2_2__line_vat_not_null1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productline',
            name='vat_value',
            field=models.ForeignKey(default=1, on_delete=PROTECT, to='creme_core.Vat', verbose_name='VAT'),
        ),
        migrations.AlterField(
            model_name='serviceline',
            name='vat_value',
            field=models.ForeignKey(default=1, on_delete=PROTECT, to='creme_core.Vat', verbose_name='VAT'),
        ),
    ]
