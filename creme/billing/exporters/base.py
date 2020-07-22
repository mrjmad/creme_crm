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

import logging

from django.conf import settings

from creme.creme_core.utils.imports import safe_import_object

logger = logging.getLogger(__name__)


class BillingExporter:
    id = ''
    verbose_name = ''
    compatible_models = ()

    def __init__(self, model):
        self.model = model
        self.entity = None
        self.user = None

    def export(self, *, entity, user):
        self.entity = entity
        self.user = user
        # TODO: assert entity's type is <model>

        return self._generate_file_ref()

    def _generate_file_ref(self):
        raise NotImplementedError()


class BillingExporterManager:
    def __init__(self, exporter_paths=None):
        if exporter_paths is None:
            exporter_paths = settings.BILLING_EXPORTERS

        self.exporter_paths = [*exporter_paths]

    @property
    def exporter_classes(self):
        for path in self.exporter_paths:
            cls = safe_import_object(path)

            # TODO: + better exception ?
            # if not issubclass(BackendClass, base_cls):
            #     raise self.InvalidClass(
            #         f'Backend: {BackendClass} is invalid, it is not a sub-class of {base_cls}.'
            #     )
            # TODO: check duplicated ID (in apps.py ??)

            yield cls

    def exporter(self, *, exporter_id, model):
        for cls in self.exporter_classes:
            if cls.id == exporter_id:
                if model not in cls.compatible_models:
                    logger.warning(
                        'The exporter %s is not compatible with the model <%s>',
                        cls, model.__name__,
                    )
                    return None

                return cls(model)

        return None
