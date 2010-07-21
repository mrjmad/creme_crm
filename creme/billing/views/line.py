# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from decimal import Decimal
from logging import debug

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required

from creme_core.utils import jsonify

from creme_core.models.entity import CremeEntity
from creme_core.entities_access.functions_for_permissions import edit_object_or_die, get_view_or_die
from creme_core.views.generic import add_entity, inner_popup

from billing.models import Line, ProductLine, ServiceLine
from billing.forms.line import ProductLineCreateForm, ProductLineOnTheFlyCreateForm, ServiceLineCreateForm, ServiceLineOnTheFlyCreateForm
from billing.constants import DEFAULT_VAT
from billing.blocks import product_lines_block, service_lines_block,total_block


default_decimal = Decimal()

@login_required
@get_view_or_die('billing')
def _add_line(request, form_class, document_id):
    document = get_object_or_404(CremeEntity, pk=document_id)

    die_status = edit_object_or_die(request, document)
    if die_status:
        return die_status

    if request.POST :
        line_form = form_class(request.POST)

        if line_form.is_valid():
            line_form.save()
    else:
        line_form = form_class(initial={
                                        'document_id':    document_id,
                                        'quantity':       0,
                                        'unit_price':     default_decimal,
                                        'credit':         default_decimal,
                                        'discount':       default_decimal,
                                        'total_discount': False,
                                        'vat':            DEFAULT_VAT,
                                       })

    return inner_popup(request, 'creme_core/generics/blockform/add_popup2.html',
                              {
                                'form':   line_form,
                                'object': document,
                                'title':  u"Ajout d'une ligne de commande dans le document <%s>" % document,
                              },
                              is_valid=line_form.is_valid(),
                              reload=False,
                              delegate_reload=True,
                              context_instance=RequestContext(request))

def add_product_line(request, document_id):
    return _add_line(request, ProductLineCreateForm, document_id)

def add_product_line_on_the_fly(request, document_id):
    return _add_line(request, ProductLineOnTheFlyCreateForm, document_id)

def add_service_line(request, document_id):
    return _add_line(request, ServiceLineCreateForm, document_id)

def add_service_line_on_the_fly(request, document_id):
    return _add_line(request, ServiceLineOnTheFlyCreateForm, document_id)

@login_required
@get_view_or_die('billing')
def _edit_line(request, line_model, line_id):
    line     = get_object_or_404(line_model, pk=line_id)
    document = line.document

    die_status = edit_object_or_die(request, document, app_name='billing')
    if die_status:
        return die_status

    form_class = line.get_edit_form()

    if request.POST:
        line_form = form_class(request.POST, instance=line)

        if line_form.is_valid():
            line_form.save()
    else:
        line_form = form_class(initial={'document_id': document.id}, instance=line)

    return inner_popup(request, 'creme_core/generics/blockform/edit_popup.html',
                       {
                        'form':   line_form,
                        'object': document,
                        'title':  u"Édition d'une ligne dans le document <%s>" % document,
                       },
                       is_valid=line_form.is_valid(),
                       reload=False,
                       delegate_reload=True,
                       context_instance=RequestContext(request))

def edit_productline(request, line_id):
    return _edit_line(request, ProductLine, line_id)

def edit_serviceline(request, line_id):
    return _edit_line(request, ServiceLine, line_id)

@login_required
@get_view_or_die('billing')
def delete(request):
    line      = get_object_or_404(Line, pk=request.POST.get('id'))
    document  = line.document

    die_status = edit_object_or_die(request, document, app_name='billing')
    if die_status:
        return die_status

    line.delete()

#    return HttpResponseRedirect(document.get_absolute_url())
    return HttpResponse()

@login_required
@get_view_or_die('billing')
def update(request, line_id):
    line     = get_object_or_404(Line, pk=line_id)
    document = line.document

    die_status = edit_object_or_die(request, document, app_name='billing')
    if die_status:
        return die_status

    line.is_paid = request.POST.has_key('paid')
    line.save()

    return HttpResponseRedirect(document.get_absolute_url())

@login_required
@jsonify 
def reload_product_lines(request, document_id):
    context = {'request': request, 'object': CremeEntity.objects.get(id=document_id).get_real_entity()}
    return [
            (product_lines_block.id_, product_lines_block.detailview_display(context)),
            (total_block.id_,         total_block.detailview_display(context)),
           ]

    #return product_lines_block.detailview_ajax(request, document_id)

@login_required
@jsonify 
def reload_service_lines(request, document_id):
    context = {'request': request, 'object': CremeEntity.objects.get(id=document_id).get_real_entity() }
    return [
            (service_lines_block.id_, service_lines_block.detailview_display(context)),
            (total_block.id_, total_block.detailview_display(context)),
           ]    
#    return service_lines_block.detailview_ajax(request, document_id)
