# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2020  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from django.forms import ChoiceField
from django.utils.translation import gettext_lazy as _

from creme.creme_core.forms import CremeModelForm

from ..exporters import BillingExporterManager
from ..models import ExporterConfigItem


class ExporterConfigurationForm(CremeModelForm):
    exporter_id = ChoiceField(label=_('Exporter'))

    class Meta(CremeModelForm.Meta):
        model = ExporterConfigItem
        exclude = ('content_type',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO: filter exporter compatible w/ ctype
        self.fields['exporter_id'].choices = [
            (cls.id, cls.verbose_name)
            for cls in BillingExporterManager().exporter_classes
        ]
        # TODO: initial ??
