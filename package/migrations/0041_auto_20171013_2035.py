# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-10-13 20:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0040_project_contributors'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teammembership',
            name='role_confirmed',
            field=models.NullBooleanField(default=None, verbose_name='Role confirmed by team mate'),
        ),
    ]
