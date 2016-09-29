# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2016  Hybird
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

from django.db.models import ForeignKey, ManyToManyField, BooleanField, DateField
from django.template import Library
from django.template.loader import get_template
from django.utils.translation import ugettext as _

from ..core.entity_cell import (EntityCellRegularField, EntityCellCustomField,
        EntityCellFunctionField, EntityCellRelation)
from ..core.paginator import FlowPaginator
from ..gui.listview import NULL_FK
from ..gui.mass_import import import_form_registry
from ..models import CustomField
from ..models.fields import EntityCTypeForeignKey
from ..utils import creme_entity_content_types, build_ct_choices


logger = logging.getLogger(__name__)
register = Library()


@register.inclusion_tag('creme_core/templatetags/listview_entityfilters.html', takes_context=True)
def get_listview_entity_filters(context):
    efilter = context['entity_filters'].selected

    if efilter:
        efilter_id = efilter.id
        user = context['user']
        can_edit   = efilter.can_edit(user)[0]
        can_delete = efilter.can_delete(user)[0]
    else:
        efilter_id = 0
        can_edit = can_delete = False

    context['efilter_id'] = efilter_id
    context['can_edit'] = can_edit
    context['can_delete'] = can_delete

    return context


@register.inclusion_tag('creme_core/templatetags/listview_headerfilters.html', takes_context=True)
def get_listview_headerfilters(context):
    hfilter = context['header_filters'].selected
    user = context['user']

    context['hfilter_id'] = hfilter.id
    context['can_edit']   = hfilter.can_edit(user)[0]
    context['can_delete'] = hfilter.can_delete(user)[0]

    return context


DEFAULT_PAGINATOR_TEMPLATE = 'creme_core/templatetags/listview_paginator_slow.html'
PAGINATOR_TEMPLATES = {
    FlowPaginator: 'creme_core/templatetags/listview_paginator_fast.html',
}


@register.simple_tag
def get_listview_pagination(page):
    return get_template(PAGINATOR_TEMPLATES.get(page.paginator.__class__, DEFAULT_PAGINATOR_TEMPLATE))\
                       .render({'page': page})


# get_listview_columns_header --------------------------------------------------

def _build_bool_search_widget(widget_ctx, search_value):
    # TODO : Hack or not ? / Remember selected value ?
    selected_value = search_value[0] if search_value else None
    widget_ctx['type'] = 'checkbox'
    widget_ctx['values'] = [{'value':    '1',
                             'text':     _("Yes"),
                             'selected': 'selected' if selected_value == '1' else ''
                            },
                            {'value':    '0',
                             'text':     _("No"),
                             'selected': 'selected' if selected_value == '0' else ''
                            }
                           ]


def _build_date_search_widget(widget_ctx, search_value):
    # TODO: Needs datetime validation
    widget_ctx['type'] = 'datefield'
    if search_value:
        widget_ctx['values'] = {'start': search_value[0], 'end': search_value[-1]}


def _build_select_search_widget(widget_ctx, search_value, choices):
    selected_value = unicode(search_value[0].decode('utf-8')) if search_value else None  # meh
    widget_ctx['type'] = 'select'
    widget_ctx['values'] = [{'value':    key,
                             'text':     unicode(val),
                             'selected': 'selected' if selected_value == unicode(key) else ''
                            } for key, val in choices
                           ]


# TODO: add methods to EntityCells ? -> map of behaviours instead
@register.inclusion_tag('creme_core/templatetags/listview_columns_header.html', takes_context=True)
def get_listview_columns_header(context):
    header_searches = dict(context['list_view_state'].research)

    for cell in context['cells']:
        if not cell.has_a_filter:
            continue

        search_value = header_searches.get(cell.key, '')
        widget_ctx = {'value': search_value, 'type': 'text'}

        if isinstance(cell, EntityCellRegularField):
            field = cell.field_info[-1]

            if isinstance(field, (ForeignKey, ManyToManyField)):  # TODO: hasattr(field, 'rel') ?
                if cell.filter_string.endswith('__header_filter_search_field__icontains'):
                    if search_value:
                        widget_ctx['value'] = search_value[0]
                else:
                    if isinstance(field, EntityCTypeForeignKey):
                        choices = build_ct_choices(creme_entity_content_types())
                    elif not field.get_tag('enumerable'):
                        # TODO: generalise the system of 'header_filter_search_field' ??
                        continue
                    else:
                        choices = []

                        if field.null or field.many_to_many:
                            choices.append((NULL_FK, _('* is empty *')))

                        choices.extend((o.id, o) for o in field.rel.to.objects.distinct())

                    _build_select_search_widget(widget_ctx, search_value, choices)
            elif field.choices:
                # NB: not tested with grouped choices
                _build_select_search_widget(widget_ctx, search_value, field.choices)
            elif isinstance(field, BooleanField):
                _build_bool_search_widget(widget_ctx, search_value)
            elif isinstance(field, DateField):
                _build_date_search_widget(widget_ctx, search_value)
            elif search_value:
                widget_ctx['value'] = search_value[0]
        elif isinstance(cell, EntityCellFunctionField):
            choices = cell.function_field.choices
            if choices is not None:
                _build_select_search_widget(widget_ctx, search_value, choices)
            elif search_value:
                widget_ctx['value'] = search_value[0]
        elif isinstance(cell, EntityCellRelation):
            if search_value:
                widget_ctx['value'] = search_value[0]
        elif isinstance(cell, EntityCellCustomField):
            cf = cell.custom_field
            field_type = cf.field_type

            if field_type in (CustomField.ENUM, CustomField.MULTI_ENUM):
                choices = [(NULL_FK, _('* is empty *'))]
                choices.extend(cf.customfieldenumvalue_set.values_list('id', 'value'))

                _build_select_search_widget(widget_ctx, search_value, choices)
            elif field_type == CustomField.DATETIME:
                _build_date_search_widget(widget_ctx, search_value)
            elif field_type == CustomField.BOOL:
                _build_bool_search_widget(widget_ctx, search_value)
            elif search_value:
                widget_ctx['value'] = search_value[0]

        cell.widget_ctx = widget_ctx

    context['NULL_FK'] = NULL_FK

    return context

# ------------------------------------------------------------------------------


@register.simple_tag
def get_listview_cell(cell, entity, user):
    try:
        return cell.render_html(entity, user)
    except Exception as e:
        logger.critical('Templatetag "get_listview_cell": %s', e)

    return u''


@register.assignment_tag
def ctype_is_registered_for_import(ctype):
    return import_form_registry.is_registered(ctype)


@register.assignment_tag
def listview_header_colspan(cells, is_readonly, is_single_select):
    if is_readonly:
        colspan = len(cells)
    else:
        colspan = sum(2 if cell.type_id != 'actions' else 1 for cell in cells)

    if not is_single_select:
        colspan += 1

    return colspan


@register.filter('listview_column_colspan')
def get_column_colspan(cell, is_readonly):
    return 2 if cell.type_id != 'actions' and not is_readonly else 1
