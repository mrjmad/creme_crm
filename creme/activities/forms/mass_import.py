# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2018  Hybird
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

from collections import OrderedDict
from datetime import datetime, time
from functools import partial
from itertools import chain
import logging

from django.contrib.auth import get_user_model
from django.db.models.query_utils import Q
from django.forms import Field, ModelMultipleChoiceField, ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _, ugettext_lazy

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.forms.mass_import import ImportForm4CremeEntity, ExtractorWidget
from creme.creme_core.forms.validators import validate_linkable_entities
from creme.creme_core.models import Relation, RelationType
from creme.creme_core.utils.dates import make_aware_dt

from creme import persons
from creme.persons.models import Civility

from .. import constants
from ..models import ActivityType, Calendar
from .activity_type import ActivityTypeField
from .fields import UserParticipationField


logger = logging.getLogger(__name__)
Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()

MODE_MULTICOLUMNS   = 1
MODE_SPLITTEDCOLUMN = 2

# Maximum of CremeEntities that can be retrieved in _one_ search for Participants/Subjects
# (more means that there is a big problem with the file, & no CremeEntity is created)
MAX_RELATIONSHIPS = 5


# TODO: in creme_core ?
def as_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class RelatedExtractor(object):
    def __init__(self, create_if_unfound=False):
        self._create = create_if_unfound

    def extract_value(self, line, user):
        return (), ()

    def _searched_contact(self, first_name, last_name):
        return Contact(first_name=first_name, last_name=last_name),

    def _search_n_create_contacts(self, user, civility, first_name, last_name):
        extracted = ()
        err_msg = None
        query_dict = {'last_name__iexact': last_name}

        if first_name:
            query_dict['first_name__iexact'] = first_name

        # TODO: filter with link credentials too (because here we limit _before_ filtering unlinkable...)
        contacts = EntityCredentials.filter(user,
                                            Contact.objects.filter(**query_dict),
                                           )[:MAX_RELATIONSHIPS + 1]

        if contacts:
            has_perm = user.has_perm_to_link
            contacts = [c for c in contacts if has_perm(c)]

            if contacts:
                length = len(contacts)

                if length > MAX_RELATIONSHIPS:
                    err_msg = _(u'Too many contacts were found for the search «%s»') % \
                                self._searched_contact(first_name, last_name)
                else:
                    if length > 1:
                        err_msg = _(u'Several contacts were found for the search «%s»') % \
                                    self._searched_contact(first_name, last_name)

                    extracted = contacts
            else:
                err_msg = _(u'No linkable contact found for the search «%s»') % \
                            self._searched_contact(first_name, last_name)
        elif self._create:
            extracted = [Contact.objects.create(user=user,
                                                first_name=first_name,
                                                last_name=last_name,
                                                civility=Civility.objects
                                                                 .filter(Q(title=civility) |
                                                                         Q(shortcut=civility)
                                                                        )
                                                                 .first()
                                                         if civility else None,
                                               )
                        ]
        else:
            err_msg = _(u'The participant «%s» is unfoundable') % \
                        self._searched_contact(first_name, last_name)

        return extracted, (err_msg,) if err_msg else ()


# Participants -----------------------------------------------------------------
def _contact_pattern(verbose_name):
    def _aux(fun):
        fun.verbose_name = verbose_name
        return fun

    return _aux


# NB: 'C' means Civility
#     'F' means First name
#     'L' means Last name
@_contact_pattern(ugettext_lazy('Civility FirstName LastName'))
def _pattern_CFL(contact_as_str):
    names     = contact_as_str.split(None, 2)
    last_name =  names[-1].strip()
    length    = len(names)

    if length > 1:
        civ        = names[0] if length > 2 else None
        first_name = names[-2]
    else:
        civ = first_name = None

    return civ, first_name, last_name


@_contact_pattern(ugettext_lazy('Civility LastName FirstName'))
def _pattern_CLF(contact_as_str):
    names = contact_as_str.split()
    length = len(names)

    if length > 1:
        first_name = names[-1].strip()

        if length > 2:
            civ = names[0]
            last_name = ' '.join(names[1:-1])
        else:
            civ = None
            last_name = names[0]
    else:
        civ = first_name = None
        last_name = names[0]

    return civ, first_name, last_name


@_contact_pattern(ugettext_lazy('FirstName LastName'))
def _pattern_FL(contact_as_str):
    names      = contact_as_str.split(None, 1)
    last_name  = names[-1].strip()
    first_name = names[0] if len(names) > 1 else None

    return None, first_name, last_name


@_contact_pattern(ugettext_lazy('LastName FirstName'))
def _pattern_LF(contact_as_str):
    names      = contact_as_str.rsplit(None, 1)
    last_name  = names[0].strip()
    first_name = names[1] if len(names) == 2 else None

    return None, first_name, last_name


_PATTERNS = OrderedDict([('1', _pattern_CFL),
                         ('2', _pattern_CLF),
                         ('3', _pattern_FL),
                         ('4', _pattern_LF),
                        ]
                       )


class MultiColumnsParticipantsExtractor(RelatedExtractor):
    def __init__(self, first_name_index, last_name_index, create_if_unfound=False):
        super(MultiColumnsParticipantsExtractor, self).__init__(create_if_unfound)
        self._first_name_index = first_name_index - 1 if first_name_index else None
        self._last_name_index = last_name_index - 1

    def extract_value(self, line, user):
        first_name = None
        last_name = line[self._last_name_index]
        first_name_index = self._first_name_index

        if first_name_index is not None:  # None -> not in CSV
            first_name = line[first_name_index]

        return self._search_n_create_contacts(user, None, first_name, last_name)


class SplitColumnParticipantsExtractor(RelatedExtractor):
    def __init__(self, column_index, separator, pattern_func, create_if_unfound=False):
        super(SplitColumnParticipantsExtractor, self).__init__(create_if_unfound)
        self._column_index = column_index - 1
        self._separator = separator
        self._pattern_func = pattern_func

    def extract_value(self, line, user):
        extracted = []
        global_err_msg = []
        search = partial(self._search_n_create_contacts, user)
        func = self._pattern_func

        for contact_as_str in line[self._column_index].split(self._separator):
            if contact_as_str:
                contacts, err_msg = search(*func(contact_as_str))

                extracted.extend(contacts)
                global_err_msg.extend(err_msg)

        return extracted, global_err_msg


class ParticipantsExtractorWidget(ExtractorWidget):
    def render(self, name, value, attrs=None, choices=()):
        get = (value or {}).get

        # TODO: factorise
        firstname_id = '%s_first_name_colselect' % name
        lastname_id = '%s_last_name_colselect' % name
        colselect_id = '%s_colselect' % name
        separator_id = '%s_separator' % name
        pattern_select_id = '%s_pattern' % name

        render_sel = self._render_select
        col_choices = list(chain(self.choices, choices))
        render_colsel = lambda name, sel_val: render_sel(name, choices=col_choices, sel_val=sel_val,
                                                         attrs={'id': name, 'class': 'csv_col_select'},
                                                        )

        checked = 'checked'
        mode = get('mode', 0)

        return mark_safe(
u"""%(create_check)s
<ul class="multi-select">
    <li>
        <label for="%(name)s_mode1">
            <input id="%(name)s_mode1" type="radio" name="%(name)s_mode" value="%(MULTICOLUMNS)s" %(mode_1_checked)s>%(mode_1_label)s<br/>
            <label for="%(firstname_id)s">%(firstname_label)s:%(firstname_select)s</label>
            <label for="%(lastname_id)s">%(lastname_label)s:%(lastname_select)s</label>
        </label>
    </li>
    <li>
        <label for="%(name)s_mode2">
            <input id="%(name)s_mode2" type="radio" name="%(name)s_mode" value="%(SPLITTEDCOLUMN)s" %(mode_2_checked)s>%(mode_2_label)s<br/>
            <label for="%(colselect_id)s">%(colselect)s</label>
            <label for="%(separator_id)s">%(separator_label)s:<input id="%(separator_id)s" type="text" name="%(separator_id)s" value="%(separator_value)s"></label>
            <label for="%(pattern_select_id)s">%(pattern_label)s:%(pattern_select)s</label>
        </label>
    </li>
</ul>
""" % {'name': name,

       'create_check': '' if not self.propose_creation else
                       '<label for="%(id)s"><input id="%(id)s" type="checkbox" name="%(id)s" %(checked)s />%(label)s</label>' % {
                                'id':      '%s_create' % name,
                                'checked': checked if get('create') else '',
                                'label':   _('Create the Contacts who are not found?'),
                            },

       'MULTICOLUMNS':   MODE_MULTICOLUMNS,
       'SPLITTEDCOLUMN': MODE_SPLITTEDCOLUMN,

       'mode_1_checked': checked if mode == MODE_MULTICOLUMNS else '',
       'mode_1_label':   _('Method #1: first name & last name are in separated cells (first name is optional)'),

       'firstname_id':     firstname_id,
       'firstname_label':  _('First name'),
       'firstname_select': render_colsel(firstname_id, get('first_name_column_index')),

       'lastname_id':     lastname_id,
       'lastname_label':  _('Last name'),
       'lastname_select': render_colsel(lastname_id, sel_val=get('last_name_column_index')),

       'mode_2_checked': checked if mode == MODE_SPLITTEDCOLUMN else '',
       'mode_2_label':   _('Method #2: several contacts in one cell (in all patterns the last name is the only required element)'),

       'separator_id':    separator_id,
       'separator_label': _('Separator'),
       'separator_value': get('separator', '/'),

       'colselect_id': colselect_id,
       'colselect':    render_colsel(colselect_id, sel_val=get('column_index', 0)),

       'pattern_label':     _('Contact pattern'),
       'pattern_select_id': pattern_select_id,
       'pattern_select':    render_sel(pattern_select_id, sel_val=get('pattern_id'),
                                       choices=[(pattern_id, unicode(pattern.verbose_name))
                                                    for pattern_id, pattern in _PATTERNS.iteritems()
                                               ],
                                       attrs={'id': pattern_select_id, 'class': 'csv_pattern_select'},
                                      ),
      })

    def value_from_datadict(self, data, files, name):
        get = data.get

        return {'mode': as_int(get('%s_mode' % name), 1),

                'first_name_column_index': as_int(get('%s_first_name_colselect' % name)),
                'last_name_column_index':  as_int(get('%s_last_name_colselect' % name)),

                'column_index':  as_int(get('%s_colselect' % name)),
                'separator':     get('%s_separator' % name, '/'),
                'pattern_id':    get('%s_pattern' % name),
                'create':        get('%s_create' % name, False),
               }


class ParticipantsExtractorField(Field):
    def __init__(self, choices, *args, **kwargs):
        super(ParticipantsExtractorField, self).__init__(widget=ParticipantsExtractorWidget, *args, **kwargs)
        self._user = None
        self._can_create = False
        self._allowed_indexes = {c[0] for c in choices}

        self.widget.choices = choices

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self.widget.propose_creation = self._can_create = user.has_perm_to_create(Contact) 

    def _clean_index(self, value, key):
        try:
            index = int(value[key])
        except TypeError:
            raise ValidationError('Invalid value for index "%s"' % key)

        if index not in self._allowed_indexes:
            raise ValidationError('Invalid index')

        return index

    def _clean_mode(self, value):  # TODO: factorise
        try:
            mode = int(value['mode'])
        except TypeError:
            raise ValidationError('Invalid value for mode')

        return mode

    def _manage_empty(self):
        if self.required:
            raise ValidationError(self.error_messages['required'])

        return RelatedExtractor()  # Empty extractor

    def clean(self, value):
        mode = self._clean_mode(value)
        clean_index = partial(self._clean_index, value)
        create_if_unfound = value['create'] and self._can_create

        if mode == MODE_MULTICOLUMNS:
            first_name_index = clean_index('first_name_column_index')
            last_name_index  = clean_index('last_name_column_index')

            if not last_name_index:
                return self._manage_empty()

            return MultiColumnsParticipantsExtractor(first_name_index,
                                                     last_name_index,
                                                     create_if_unfound,
                                                    )
        elif mode == MODE_SPLITTEDCOLUMN:
            index = clean_index('column_index')

            if not index:  # TODO test
                return self._manage_empty()

            pattern_func = _PATTERNS.get(value['pattern_id'])
            if not pattern_func:
                raise ValidationError('Invalid pattern')

            return SplitColumnParticipantsExtractor(index, value['separator'],
                                                    pattern_func, create_if_unfound,
                                                   )
        else:
            raise ValidationError('Invalid mode')


# Subjects ---------------------------------------------------------------------

class SubjectsExtractor(RelatedExtractor):
    def __init__(self, column_index, separator, create_if_unfound=False):
        super(SubjectsExtractor, self).__init__(create_if_unfound)
        self._column_index = column_index - 1
        self._separator = separator
        self._models = [ct.model_class() for ct in RelationType.objects
                                                               .get(pk=constants.REL_SUB_ACTIVITY_SUBJECT)
                                                               .subject_ctypes.all()
                       ]

    def extract_value(self, line, user):
        extracted = []
        err_msg   = []

        for search in line[self._column_index].split(self._separator):
            search = search.strip()

            if not search:
                continue

            # TODO: it seems this line does not work ; but it would be cool to make less queries...
            #... EntityCredentials.filter(user, CremeEntity.objects.filter(header_filter_search_field__icontains=search))

            has_perm = user.has_perm_to_link
            unlinkable_found = False

            for model in self._models:
                # TODO: filter with link credentials too (because here we limit _before_ filtering unlinkable...)
                instances = EntityCredentials.filter(user,
                                                     model.objects.filter(header_filter_search_field__icontains=search),
                                                    )[:MAX_RELATIONSHIPS + 1]
                linkable_extracted = [e for e in instances if has_perm(e)]

                if linkable_extracted:
                    length = len(linkable_extracted)

                    if length > MAX_RELATIONSHIPS:
                        err_msg.append(_(u'Too many «%(type)s» were found for the search «%(search)s»') % {
                                            'type':   model._meta.verbose_name_plural,
                                            'search': search,
                                        }
                                      )
                    else:
                        if length > 1:
                            err_msg.append(_(u'Several «%(type)s» were found for the search «%(search)s»') % {
                                                'type':   model._meta.verbose_name_plural,
                                                'search': search,
                                            }
                                          )

                        extracted.extend(linkable_extracted)

                    break

                if instances:
                    unlinkable_found = True
            else:
                if self._create:
                    extracted.append(Organisation.objects.create(user=user, name=search))
                elif unlinkable_found:
                    err_msg.append(_(u'No linkable entity found for the search «%s»') % search)
                else:
                    err_msg.append(_(u'The subject «%s» is unfoundable') % search)

        return extracted, err_msg


class SubjectsExtractorWidget(ExtractorWidget):
    def render(self, name, value, attrs=None, choices=()):
        get = (value or {}).get

        # TODO: help_text that indicates what CTypes are used ?
        return mark_safe(
"""%(colselect)s
<label for="%(separator_id)s">
    %(separator_label)s:<input id="%(separator_id)s" type="text" name="%(separator_id)s" value="%(separator_value)s" />
</label>
%(create_check)s
""" % {'colselect': self._render_select('%s_colselect' % name,
                                        choices=chain(self.choices, choices),
                                        sel_val=get('column_index', 0),
                                        attrs={'class': 'csv_col_select'},
                                       ),

       'separator_id':    '%s_separator' % name,
       'separator_label': _('Separator'),
       'separator_value': get('separator', '/'),

        'create_check': '' if not self.propose_creation else
                        '<label for="%(id)s"><input id="%(id)s" type="checkbox" name="%(id)s" %(checked)s />%(label)s</label>' % {
                            'id':      '%s_create' % name,
                            'checked': 'checked' if get('create') else '',
                            'label':   _('Create the Organisations which are not found?'),
                         }

      })

    def value_from_datadict(self, data, files, name):
        get = data.get

        return {'column_index': as_int(get('%s_colselect' % name)),
                'create':       get('%s_create' % name, False),
                'separator':    get('%s_separator' % name, '/'),
               }


class SubjectsExtractorField(Field):
    def __init__(self, choices, *args, **kwargs):
        super(SubjectsExtractorField, self).__init__(widget=SubjectsExtractorWidget, *args, **kwargs)
        self._user = None
        self._can_create = False
        self._allowed_indexes = {c[0] for c in choices}
        self.widget.choices = choices

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, user):
        self._user = user
        self.widget.propose_creation = self._can_create = user.has_perm_to_create(Organisation)

    # TODO: factorise (in ExtractorField) (need _allowed_indexes)
    def _clean_index(self, value, key):
        try:
            index = int(value[key])
        except TypeError:
            raise ValidationError('Invalid value for index "%s"' % key)

        if index not in self._allowed_indexes:
            raise ValidationError('Invalid index')

        return index

    def clean(self, value):
        index = self._clean_index(value, 'column_index')

        if not index:
            if self.required:
                raise ValidationError(self.error_messages['required'])

            return RelatedExtractor()  # Empty extractor

        return SubjectsExtractor(index, value['separator'],
                                 value['create'] and self._can_create
                                )


# Main -------------------------------------------------------------------------
def get_massimport_form_builder(header_dict, choices):
    class ActivityMassImportForm(ImportForm4CremeEntity):
        type_selector = ActivityTypeField(label=_(u'Type'),
                                          types=ActivityType.objects.exclude(pk=constants.ACTIVITYTYPE_INDISPO),
                                         )

        my_participation    = UserParticipationField(label=_(u'Do I participate to this activity?'), empty_label=None)

        participating_users = ModelMultipleChoiceField(label=_(u'Other participating users'),
                                                       queryset=get_user_model().objects.filter(is_staff=False),
                                                       required=False,
                                                      )
        participants        = ParticipantsExtractorField(choices, label=_(u'Participants'), required=False)

        subjects = SubjectsExtractorField(choices, label=_(u'Subjects (organisations only)'), required=False)

        class Meta:
            exclude = ('type', 'sub_type', 'busy')

        blocks = ImportForm4CremeEntity.blocks.new(
                            ('participants',   _(u'Participants & subjects'),
                             ['my_participation',  # 'my_calendar',
                              'participating_users', 'participants', 'subjects']
                            ),
                        )

        def __init__(self, *args, **kwargs):
            super(ActivityMassImportForm, self).__init__(*args, **kwargs)
            self.fields['my_participation'].initial = (True, Calendar.get_user_default_calendar(self.user))

            self.user_participants = []

        def clean_participating_users(self):
            users = self.cleaned_data['participating_users']
            self.user_participants.extend(
                validate_linkable_entities(Contact.objects.filter(is_user__in=users), self.user)
            )
            return users

        def _pre_instance_save(self, instance, line):
            instance.type, instance.sub_type = self.cleaned_data['type_selector']
            instance.floating_type = constants.NARROW
            start = instance.start
            end = instance.end

            if start:
                if not start.time() and (not end or not end.time()):
                    instance.end = make_aware_dt(datetime.combine(start, time(hour=23, minute=59)))
                    instance.floating_type = constants.FLOATING_TIME
                elif not end:
                    instance.end = start + instance.type.as_timedelta()
                elif start > instance.end:
                    instance.end = start + instance.type.as_timedelta()
                    # self.append_error(line, _(u'End time is before start time'), instance)
                    self.append_error(_(u'End time is before start time'))
            else:
                instance.floating_type = constants.FLOATING

        def _post_instance_creation(self, instance, line, updated):
            super(ActivityMassImportForm, self)._post_instance_creation(instance, line, updated)

            cdata = self.cleaned_data
            user = instance.user
            participant_ids = set()

            if updated:
                # TODO: improve get_participant_relations() (not retrieve real entities)
                participant_ids.update(Relation.objects.filter(type=constants.REL_SUB_PART_2_ACTIVITY,
                                                               object_entity=instance.id,
                                                              )
                                                       .values_list('subject_entity', flat=True)
                                      )
                create_sub_rel = partial(Relation.objects.get_or_create, object_entity=instance,
                                         type_id=constants.REL_SUB_ACTIVITY_SUBJECT,
                                         defaults={'user': user},
                                        )
            else:
                create_sub_rel = partial(Relation.objects.create, object_entity=instance,
                                         type_id=constants.REL_SUB_ACTIVITY_SUBJECT, user=user,
                                        )

            def add_participant(participant):
                if participant.id not in participant_ids:
                    Relation.objects.create(subject_entity=participant,
                                            type_id=constants.REL_SUB_PART_2_ACTIVITY,
                                            object_entity=instance, user=user,
                                           )
                    participant_ids.add(participant.id)

            # We could create a cache in self (or even put a cache-per-request in Calendar.get_user_default_calendar()
            # but the import can take a long time, & the default Calendar could change => TODO: use a time based cache ?
            default_calendars_cache = {}

            def add_to_default_calendar(part_user):
                calendar = default_calendars_cache.get(part_user.id)

                if calendar is None:
                    default_calendars_cache[part_user.id] = calendar = \
                        Calendar.get_user_default_calendar(part_user)

                instance.calendars.add(calendar)

            i_participate, my_calendar = cdata['my_participation']
            if i_participate:
                add_participant(user.linked_contact)
                instance.calendars.add(my_calendar)

            for participant in self.user_participants:
                add_participant(participant)
                add_to_default_calendar(participant.is_user)

            dyn_participants, err_messages = cdata['participants'].extract_value(line, self.user)

            for err_msg in err_messages:
                # self.append_error(line, err_msg, instance)
                self.append_error(err_msg)

            for participant in dyn_participants:
                add_participant(participant)

                part_user = participant.is_user
                if part_user is not None:
                    instance.calendars.add(Calendar.get_user_default_calendar(part_user))

            subjects, err_messages = cdata['subjects'].extract_value(line, self.user)

            for err_msg in err_messages:
                # self.append_error(line, err_msg, instance)
                self.append_error(err_msg)

            for subject in subjects:
                create_sub_rel(subject_entity=subject)

    return ActivityMassImportForm
