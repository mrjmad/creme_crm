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

from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required, permission_required

from creme_core.views.generic import add_to_entity, view_entity, edit_entity
from creme_core.utils import get_from_POST_or_404
from creme_core.views.generic.edit import edit_model_with_popup

from projects.models import Project, ProjectTask
from projects.forms.task import TaskCreateForm, TaskEditForm


@login_required
@permission_required('projects.add_projecttask')
def add(request, project_id):
    return add_to_entity(request, project_id, TaskCreateForm,
                         _(u'Add a task to <%s>'), entity_class=Project)

@login_required
@permission_required('projects')
def detailview(request, object_id):
    return view_entity(request, object_id, ProjectTask, '/projects/task', 'projects/view_task.html')

@login_required
@permission_required('projects')
def edit(request, task_id):
    return edit_entity(request, task_id, ProjectTask, TaskEditForm)

@login_required
@permission_required('projects')
def edit_popup(request, task_id):#TODO: Merge with edit ?
    return edit_model_with_popup(request, {'pk': task_id}, ProjectTask, TaskEditForm)

@login_required
@permission_required('projects')
def delete(request, task_id=None):
    task = get_object_or_404(ProjectTask, pk=request.POST.get('id', task_id))
    project = task.project
    user = request.user

    project.can_change_or_die(user)
    task.can_delete_or_die(user)

    task.delete()

    if request.is_ajax():
        return HttpResponse()

    return HttpResponseRedirect(project.get_absolute_url())

@login_required
@permission_required('projects')
def delete_parent(request):
    POST = request.POST
    parent_id = get_from_POST_or_404(POST, 'parent_id')
    task = get_object_or_404(ProjectTask, pk=get_from_POST_or_404(POST, 'id'))
    user = request.user

    #task.project.can_change_or_die(user) #beware: modify block_tasks.html template if uncommented....
    task.can_change_or_die(user)

    task.parents_task.remove(parent_id)

    return HttpResponse("")
