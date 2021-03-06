# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

# import warnings
#
# from .. import get_service_model
# from .base import _BaseEditForm, _BaseForm
#
# Service = get_service_model()
#
#
# class ServiceCreateForm(_BaseForm):
#     class Meta(_BaseForm.Meta):
#         model = Service
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('ServiceCreateForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
#
#
# class ServiceEditForm(_BaseEditForm):
#     class Meta(_BaseEditForm.Meta):
#         model = Service
#
#     def __init__(self, *args, **kwargs):
#         warnings.warn('ServiceEditForm is deprecated.', DeprecationWarning)
#         super().__init__(*args, **kwargs)
