# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _, ugettext, ngettext

from creme.creme_core.gui.bricks import QuerysetBrick
from creme.creme_core.models import SettingValue

from .constants import SETTING_CRUDITY_SANDBOX_BY_USER
from .models import WaitingAction, History


class CrudityQuerysetBrick(QuerysetBrick):
    def __init__(self, *args, **kwargs):
        super(CrudityQuerysetBrick, self).__init__()

    def detailview_display(self, context):
        if not context['user'].has_perm('crudity'):
            raise PermissionDenied(ugettext(u'Error: you are not allowed to view this block: %s' % self.id_))

    # TODO: staticmethod
    @property
    def is_sandbox_by_user(self):
        # No cache need sub-blocks are created on the fly
        return SettingValue.objects.get(key_id=SETTING_CRUDITY_SANDBOX_BY_USER, user=None).value


class WaitingActionsBrick(CrudityQuerysetBrick):
    # dependencies  = ()
    verbose_name  = _(u'Waiting actions')
    template_name = 'crudity/bricks/waiting-actions.html'

    def __init__(self, backend):
        super(WaitingActionsBrick, self).__init__()
        self.backend = backend
        self.id_     = self.generate_id()

    def generate_id(self):
        return CrudityQuerysetBrick.generate_id('crudity', 'waiting_actions-' + self.backend.get_id())

    def _iter_dependencies_info(self):
        yield 'crudity.waitingaction.' + self.backend.get_id()

    def detailview_display(self, context):
        # Credentials are OK: block is not registered in block registry,
        # so reloading is necessarily done with the custom view
        super(WaitingActionsBrick, self).detailview_display(context)
        backend = self.backend
        ct = ContentType.objects.get_for_model(backend.model)

        waiting_actions = WaitingAction.objects.filter(ct=ct, source=backend.source, subject=backend.subject)

        if self.is_sandbox_by_user:
            waiting_actions = waiting_actions.filter(user=context['user'])

        crud_input = backend.crud_input
        btc = self.get_template_context(
                    context,
                    waiting_actions,
                    waiting_ct=ct,
                    backend=backend,
                    extra_header_actions=(action.render(backend=backend) for action in crud_input.brickheader_actions)
                                         if crud_input else
                                         (),
        )
        count = btc['page'].paginator.count

        # TODO: we need a {% blocktrans as %} feature
        if count:
            title = ngettext(u'{count} Waiting action - {ctype} - {source}',
                             u'{count} Waiting actions - {ctype} - {source}',
                             count
                            ).format(count=count,
                                     ctype=ct,
                                     source=backend.verbose_source,
                                    )
        else:
            title = ugettext(u'Waiting actions - {ctype} - {source}').format(ctype=ct, source=backend.verbose_source)

        btc['title'] = title

        return self._render(btc)


class CrudityHistoryBrick(CrudityQuerysetBrick):
    # dependencies  = ()
    verbose_name  = _(u'History')
    template_name = 'crudity/bricks/history.html'

    def __init__(self, ct):
        super(CrudityHistoryBrick, self).__init__()
        self.ct = ct
        self.id_ = self.generate_id()

    def generate_id(self):
        return 'block_crudity-%s' % self.ct.id

    def detailview_display(self, context):
        # Credentials are OK: block is not registered in block registry,
        # so reloading is necessarily done with the custom view
        super(CrudityHistoryBrick, self).detailview_display(context)
        ct = self.ct

        histories = History.objects.filter(entity__entity_type=ct)
        if self.is_sandbox_by_user:
            histories = histories.filter(user=context['user'])

        btc = self.get_template_context(context, histories, ct=ct)
        count = btc['page'].paginator.count

        # TODO: we need a {% blocktrans as %} feature
        if count:
            title = ngettext(u'{count} History item - {ctype}',
                             u'{count} History items - {ctype}',
                             count
                            ).format(count=count, ctype=ct)
        else:
            title = ugettext(u'History items - {ctype}').format(ctype=ct)

        btc['title'] = title

        return self._render(btc)