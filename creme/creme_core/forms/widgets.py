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

import copy
from datetime import datetime
from functools import partial
from itertools import chain
from json import dumps as json_dump
from types import GeneratorType
# import warnings

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db.models.query import Q
from django.forms import widgets
from django.forms.utils import flatatt
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape, escape
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime, is_naive
from django.utils.translation import ugettext as _, ugettext_lazy, pgettext_lazy, pgettext

from ..templatetags.creme_widgets import get_icon_size_px, get_icon_by_name
from ..utils.date_range import date_range_registry
from ..utils.media import get_current_theme  # creme_media_themed_url as media_url
from ..utils.url import TemplateURLBuilder


def widget_render_input(renderer, widget, name, value, context, **kwargs):
    input_attrs = {'class':  ' '.join(['ui-creme-input', context.get('css', '')]),
                   'widget': context.get('typename', None),
                  }
    input_attrs.update(kwargs)

    return renderer(widget, name, value, input_attrs)


def widget_render_hidden_input(widget, name, value, context):
    input_attrs = {'class': ' '.join(['ui-creme-input', context.get('typename')]),
                   'type':  'hidden',
                  }

    return widgets.Input.render(widget, name, value, input_attrs)


def widget_render_context(typename, attrs, css='', **kwargs):
    # TODO: other atts are not used ?! (eg: ColorPickerWidget which only passes 'attrs' to widget_render_context())
    id   = attrs.get('id')
    auto = attrs.pop('auto', True)
    css = ' '.join((css, 'ui-creme-widget widget-auto' if auto else 'ui-creme-widget', typename)).strip()
    context = {'style':      '',
               'typename':   typename,
               'css':        css,
               'auto':       auto,
               'id':         id,
              }

    context.update(kwargs)

    return context


# TODO: to be improved....
class DynamicInput(widgets.TextInput):
    def __init__(self, type='text', attrs=None):
        super(DynamicInput, self).__init__(attrs)
        self.input_type = type

    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name)
        context = widget_render_context('ui-creme-dinput', attrs)

        return mark_safe(widget_render_input(widgets.TextInput.render, self, name, value, context)) #, url=self.url

# TODO ??? DynamicHiddenInput
# class HiddenInput(Input): #from django
#     input_type = 'hidden'
#     is_hidden = True


class EnhancedSelectOptions(object):
    class Choice(object):
        def __init__(self, value, disabled=False, help=u''):
            self.value = value
            self.disabled = disabled
            self.help = help

    def _set_options(self, options):
        if options is None:
            self.options = ()
        elif isinstance(options, GeneratorType):
            self.options = list(options)
        else:
            self.options = options

    def _get_options(self):
        return list(self.options()) if callable(self.options) else self.options

    @property
    def choices(self):
        return self._get_options()

    @choices.setter
    def choices(self, choices):
        self._set_options(choices)

    def render_label(self, output, label):
        if not self.label:
            return output

        return u'<span class="ui-creme-dselectlabel">%s</span>%s' % (self.label, output)

    def render_enchanced_option(self, selected_choices, option_value, option_label):
        if isinstance(option_value, self.Choice):
            value = force_unicode(option_value.value)
            selected = self.is_choice_selected(selected_choices, value)
            return self.render_enchanced_choice(option_value, value, option_label, selected)

        return super(self.__class__, self).render_option(selected_choices, option_value, option_label)

    def is_choice_selected(self, selected_choices, choice_value):
        selected = False

        if choice_value in selected_choices:
            selected = True
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(choice_value)

        return selected

    def render_enchanced_choice(self, choice, value, label, selected):
        selected_html = u' selected="selected"' if selected else u''
        disabled_html = u' disabled' if choice.disabled else u''

        help_html = u' help="%s"' % escape(choice.help) if choice.help else u''

        return u'<option value="%s"%s%s%s>%s</option>' % (escape(value),
                                                          disabled_html,
                                                          selected_html,
                                                          help_html,
                                                          conditional_escape(force_unicode(label)),
                                                         )


class DynamicSelect(widgets.Select, EnhancedSelectOptions):
    def __init__(self, attrs=None, options=None, url='', label=None):
        super(DynamicSelect, self).__init__(attrs, ())  # TODO: options or ()
        self.url = url
        self.label = label
        self.from_python = None
        self.choices = options

    def render_option(self, selected_choices, option_value, option_label):
        return self.render_enchanced_option(selected_choices, option_value, option_label)

    def render(self, name, value, attrs=None, choices=()):
        attrs = self.build_attrs(attrs, name=name)
        context = widget_render_context('ui-creme-dselect', attrs)

        value = self.from_python(value) if self.from_python is not None else value
        output = widget_render_input(widgets.Select.render, self, name, value, context, url=self.url)

        return mark_safe(self.render_label(output, self.label))


class DynamicSelectMultiple(widgets.SelectMultiple, EnhancedSelectOptions):
    def __init__(self, attrs=None, options=None, url='', label=None):
        super(DynamicSelectMultiple, self).__init__(attrs, ())  # TODO: options or ()
        self.url = url
        self.label = label
        self.from_python = None
        self.choices = options

    def render_option(self, selected_choices, option_value, option_label):
        return self.render_enchanced_option(selected_choices, option_value, option_label)

    def render(self, name, value, attrs=None, choices=()):
        attrs = self.build_attrs(attrs, name=name)
        context = widget_render_context('ui-creme-dselect', attrs)

        value = self.from_python(value) if self.from_python is not None else value
        output = widget_render_input(widgets.SelectMultiple.render, self, name, value, context, url=self.url)

        return mark_safe(self.render_label(output, self.label))


class ActionButtonList(widgets.Widget):
    def __init__(self, delegate, attrs=None, actions=()):
        super(ActionButtonList, self).__init__(attrs)
        self.delegate = delegate
        self.actions = list(actions)
        self.from_python = None

    def __deepcopy__(self, memo):
        obj = super(ActionButtonList, self).__deepcopy__(memo)
        obj.actions = copy.deepcopy(self.actions)
        return obj

    def add_action(self, name, label, enabled=True, **kwargs):
        self.actions.append((name, label, enabled, kwargs))
        return self

    def clear_actions(self):
        self.actions[:] = ()
        return self

    def render(self, name, value, attrs=None):
        value = self.from_python(value) if self.from_python is not None else value
        attrs = attrs or {}

        context = widget_render_context('ui-creme-actionbuttonlist', attrs)
        context['delegate'] = self.delegate.render(name, value, attrs)
        context['buttons'] = self._render_actions()

        return mark_safe('<ul class="ui-layout hbox %(css)s" style="%(style)s" widget="%(typename)s">'
                            '<li class="delegate">%(delegate)s</li>'
                            '%(buttons)s'
                         '</ul>' % context
                        )

    def _render_actions(self):
        return '\n'.join(self._render_action(name, label, enabled, **attrs)
                            for name, label, enabled, attrs in self.actions
                        )

    def _render_action(self, name, label, enabled, **kwargs):
        if enabled is not None:
            if enabled is False or (callable(enabled) and not enabled()):
                kwargs['disabled'] = u''

        title = kwargs.pop('title', label)

        return ('<li>'
                    '<button class="ui-creme-actionbutton" name="%(name)s" title="%(title)s" alt="%(title)s" type="button" %(attr)s>'
                       '%(label)s'
                    '</button>'
                '</li>' % {'name':  name,
                           'attr':  flatatt(kwargs),
                           'label': label,
                           'title': title,
                          }
               )


class PolymorphicInput(widgets.TextInput):
    def __init__(self, attrs=None, key='', *args):
        super(PolymorphicInput, self).__init__(attrs)
        self.key = key
        self.inputs = []
        self.default_input = None
        self.set_inputs(*args)
        self.from_python = None  # TODO: wait for django 1.2 and new widget api to remove this hack

    def render(self, name, value, attrs=None):
        # TODO: wait for django 1.2 and new widget api to remove this hack
        value = self.from_python(value) if self.from_python is not None else value
        attrs = self.build_attrs(attrs, name=name, type='hidden')

        context = widget_render_context('ui-creme-polymorphicselect', attrs,
                                        style=attrs.pop('style', ''),
                                        selectors=self._render_inputs(attrs),
                                        key=self.key,
                                       )
        context['input'] = widget_render_hidden_input(self, name, value, context)

        return mark_safe('<span class="%(css)s" style="%(style)s" widget="%(typename)s" key="%(key)s">'
                             '%(input)s'
                             '%(selectors)s'
                         '</span>' % context
                        )

    def set_inputs(self, *args):
        for input in args:
            self.add_input(input.name, input.widget, input.attrs, **input.kwargs)

    def add_dselect(self, name, options=None, attrs=None, **kwargs):
        if isinstance(options, basestring):
            self.add_input(name, widget=DynamicSelect, attrs=attrs, url=options, **kwargs)
        else:
            self.add_input(name, widget=DynamicSelect, attrs=attrs, options=options, **kwargs)

    def add_input(self, name, widget, attrs=None, **kwargs):
        self.inputs.append((name, widget(attrs=attrs, **kwargs) if isinstance(widget, type) else widget))

    def set_default_input(self, widget, attrs=None, **kwargs):
        self.default_input = widget(attrs=attrs, **kwargs) if isinstance(widget, type) else widget

    def _render_inputs(self, attrs):
        output = ['<script selector-key="%s" type="text/template">%s</script>' % (name, input.render('', ''))
                      for name, input in self.inputs
                 ]

        if self.default_input:
            output.append('<script selector-key="*" type="text/template">%s</script>' %
                                self.default_input.render('', '')
                         )

        return '\n'.join(output)


class DateRangeSelect(widgets.TextInput):
    def __init__(self, attrs=None, choices=None):
        super(DateRangeSelect, self).__init__(attrs)
        self.choices = choices

    def range_choices(self):
        choices = [('', pgettext_lazy('creme_core-date_range', u'Customized'))]
        choices.extend(date_range_registry.choices())
        return choices

    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name, type='hidden')
        context = widget_render_context('ui-creme-daterange-selector', attrs)

        choices = self.range_choices() if self.choices is None else self.choices
        date_range = ['<select class="daterange-input range-type">']
        date_range.extend(u'<option value="%s">%s</option>' % (name, verb_name)
                            for name, verb_name in choices
                         )
        date_range.append('</select>')

        context['input'] = widget_render_hidden_input(self, name, value, context)
        context['select'] = '\n'.join(date_range)
        context['from'] = _(u'From')
        context['to'] = _(u'To')
        context['date_format'] = settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT)

        return mark_safe('<span class="%(css)s" style="%(style)s" widget="%(typename)s" date_format="%(date_format)s">'
                            '%(input)s%(select)s'
                            '<span class="daterange-inputs">'
                                ' %(from)s<input type="text" class="daterange-input date-start" />'
                                '&nbsp;%(to)s<input type="text" class="daterange-input date-end" />'
                            '</span>'
                         '</span>' % context
                        )


class NullableDateRangeSelect(DateRangeSelect):
    def range_choices(self):
        choices = [('', pgettext_lazy('creme_core-date_range', u'Customized'))]
        choices.extend(date_range_registry.choices(exclude_empty=False))
        return choices


class ChainedInput(widgets.TextInput):
    HORIZONTAL = 'hbox'
    VERTICAL = 'vbox'

    def __init__(self, attrs=None, *args):
        super(ChainedInput, self).__init__(attrs)
        self.inputs = []
        self.set_inputs(*args)
        self.from_python = None  # TODO : wait for django 1.2 and new widget api to remove this hack

    def __deepcopy__(self, memo):
        obj = super(ChainedInput, self).__deepcopy__(memo)
        obj.inputs = copy.deepcopy(self.inputs)
        return obj

    def render(self, name, value, attrs=None):
        # TODO: wait for django 1.2 and new widget api to remove this hack
        value = self.from_python(value) if self.from_python is not None else value
        attrs = self.build_attrs(attrs, name=name, type='hidden')

        context = widget_render_context('ui-creme-chainedselect', attrs,
                                        style=attrs.pop('style', ''),
                                        selects=self._render_inputs(attrs),
                                       )

        context['input'] = widget_render_hidden_input(self, name, value, context)

        return mark_safe(u'<div class="%(css)s" style="%(style)s" widget="%(typename)s">'
                            u'%(input)s'
                            u'%(selects)s'
                         u'</div>' % context
                        )

    def set_inputs(self, *args):
        for input in args:
            self.add_input(input.name, input.widget, input.attrs, **input.kwargs)

    def add_dselect(self, name, options=None, attrs=None, **kwargs):
        if isinstance(options, basestring):
            self.add_input(name, widget=DynamicSelect, attrs=attrs, url=options, **kwargs)
        else:
            self.add_input(name, widget=DynamicSelect, attrs=attrs, options=options, **kwargs)

    def add_input(self, name, widget, attrs=None, **kwargs):
        self.inputs.append((name, widget(attrs=attrs or {}, **kwargs) if callable(widget) else widget))

    # TODO ?
    # def clear(self):
    #     self.inputs[:] = ()

    def _render_inputs(self, attrs):
        direction = attrs.get('direction', ChainedInput.HORIZONTAL)
        output = [u'<ul class="ui-layout %s">' % direction]

        output.extend(u'<li chained-name="%s" class="ui-creme-chainedselect-item">%s</li>' % (
                            name, input.render('', '')
                        ) for name, input in self.inputs
                     )

        if attrs.pop('reset', True):
            # output.append(u'<li>'
            #                   u'<img class="reset" src="%(url)s" alt="%(title)s" title="%(title)s" />'
            #               u'</li>' % {'url':   media_url('images/delete_22_button.png'),
            #                           'title': _(u'Reset'),
            #                          }
            #              )
            theme = get_current_theme()
            output.append(u'<li>{}</li>'.format(get_icon_by_name('delete', theme=theme, label=_(u'Reset'),
                                                                 size_px=get_icon_size_px(theme, size='form-widget'),
                                                                ).render(css_class='reset')
                                               )
                         )

        output.append(u'</ul>')

        return u'\n'.join(output)


class SelectorList(widgets.TextInput):
    class Action(object):
        def __init__(self, name, label, enabled=True, **kwargs):
            self.name = name
            self.label = label
            self.enabled = enabled
            self.attrs = kwargs or {}

        @property
        def enabled(self):
            return self._enabled if callable(self._enabled) else self._enabled is True

        @enabled.setter
        def enabled(self, enabled):
            self._enabled = enabled

    def __init__(self, selector, attrs=None, enabled=True):
        super(SelectorList, self).__init__(attrs)
        self.selector = selector
        self.enabled = enabled
        self.actions = [self.Action('add', ugettext_lazy(u'Add'))]
        # TODO : wait for django 1.2 and new widget api to remove this hack
        self.from_python = None

    def add_action(self, name, label, enabled=True, **kwargs):
        self.actions.append(self.Action(name, label, enabled, **kwargs))
        return self

    def clear_actions(self):
        self.actions[:] = ()
        return self

    def _render_actions(self):
        return '\n'.join(self._render_action(action) for action in self.actions)

    def _render_action(self, action):
        attrs = dict(action.attrs)

        if not action.enabled:
            attrs['disabled'] = u''

        title = attrs.pop('title', action.label)
        context = {'name':  action.name,
                   'attr':  flatatt(attrs),
                   'label': action.label,
                   'title': title,
                  }

        return (u'<li>'
                  u'<button class="ui-creme-actionbutton selectorlist-%(name)s" '
                          u'title="%(title)s" alt="%(title)s" type="button" %(attr)s>'
                    u'%(label)s'
                  u'</button>'
                u'</li>' % context)

    def render(self, name, value, attrs=None):
        value = self.from_python(value) if self.from_python is not None else value
        attrs = self.build_attrs(attrs, name=name, type='hidden')
        clonelast = 'cloneLast' if attrs.pop('clonelast', True) else ''
        disabled = 'disabled' if not self.enabled else ''

        context = widget_render_context('ui-creme-selectorlist', attrs,
                                        add=_(u'Add'),
                                        clonelast=clonelast,
                                        disabled=disabled,
                                        selector=self.selector.render('', '', {'auto': False, 'reset': False}),
                                       )

        context['input'] = widget_render_hidden_input(self, name, value, context)
        # context['img_url'] = media_url('images/add_16.png')
        context['actions'] = self._render_actions()

        return mark_safe('<div class="%(css)s" style="%(style)s" widget="%(typename)s" %(clonelast)s %(disabled)s>'
                         '    %(input)s'
                         '    <div class="inner-selector-model" style="display:none;">%(selector)s</div>'
                         '    <ul class="selectors ui-layout"></ul>'
                         '    <ul class="ui-layout hbox">%(actions)s</ul>'
                         '</div>' % context)


class EntitySelector(widgets.TextInput):
    def __init__(self, content_type=None, attrs=None):
        """ Constructor.
        @param content_type: Template variable which represent the ContentType ID in the URL. Default is '${ctype}'.
        @param attrs: see Widget.
        """
        super(EntitySelector, self).__init__(attrs)
        self.url = self._build_listview_url(content_type)
        self.text_url = self._build_text_url()
        self.from_python = None

    def _build_listview_url(self, content_type):
        return '%s?ct_id=%s&selection=${selection}&q_filter=${qfilter}' % (
            reverse('creme_core__listview_popup'),
            content_type or '${ctype}',
        )

    def _build_text_url(self):
        # TODO: use a GET parameter instead of using a TemplateURLBuilder ?
        return TemplateURLBuilder(entity_id=(TemplateURLBuilder.Int, '${id}'))\
                                 .resolve('creme_core__entity_as_json')

    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name, type='hidden')
        # selection_mode = '0' if attrs.pop('multiple', False) else '1'
        selection_mode = 'multiple' if attrs.pop('multiple', False) else 'single'
        autoselect_mode = 'popupAuto' if attrs.pop('autoselect', False) else ''

        context = widget_render_context('ui-creme-entityselector', attrs,
                                        url=self.url,
                                        text_url=self.text_url,
                                        selection=selection_mode,
                                        autoselect=autoselect_mode,
                                        style=attrs.pop('style', ''),
                                        label=_(u'Select…'),
                                       )

        context['disabled'] = 'disabled' if attrs.pop('disabled', False) else ''

        value = self.from_python(value) if self.from_python is not None else value
        context['input'] = widget_render_hidden_input(self, name, value, context)

        # TODO: manage Q instance (not managed in field yet).
        qfilter = attrs.pop('qfilter', None)
        if callable(qfilter):
            qfilter = qfilter()
        if isinstance(qfilter, Q):
            raise TypeError('<%s>: "Q" instance for qfilter is not (yet) supported (notice that it '
                            'can be generated from the "limit_choices_to" in a field related '
                            'to CremeEntity of one of your models).\n'
                            ' -> Use a dict (or a callable which returns a dict)' %
                                self.__class__.__name__
                           )
        context['qfilter'] = escape(json_dump(qfilter)) if qfilter else ''

        return mark_safe('<span class="%(css)s" style="%(style)s" widget="%(typename)s" '
                               'labelURL="%(text_url)s" label="%(label)s" '
                               'popupURL="%(url)s" popupSelection="%(selection)s" %(autoselect)s '
                               'qfilter="%(qfilter)s">'
                            '%(input)s'
                            '<button type="button" %(disabled)s>%(label)s</button>'
                         '</span>' % context
                        )


class CTEntitySelector(ChainedInput):
    def __init__(self, content_types=(), attrs=None, multiple=False, autocomplete=False, creator=False):
        super(CTEntitySelector, self).__init__(attrs)
        self.content_types = content_types
        self.multiple = multiple
        self.autocomplete = autocomplete
        self.creator = creator

    def render(self, name, value, attrs=None):
        field_attrs = {'auto': False, 'datatype': 'json'}
        if self.autocomplete:
            field_attrs['autocomplete'] = True

        self.add_dselect('ctype', options=self.content_types, attrs=field_attrs)

        multiple = self.multiple
        actions = ActionButtonList(delegate=EntitySelector(content_type='${ctype.id}',
                                                           attrs={'auto': False,
                                                                  'multiple': multiple,
                                                                 },
                                                          ),
                                  )

        if not self.is_required and not multiple:
            clear_label = _(u'Clear')
            actions.add_action('reset', clear_label, title=clear_label,
                               action='reset', value='',
                              )

        if self.creator:
            actions.add_action('create', _(u'Add'), popupUrl='${ctype.create}', popupTitle='${ctype.create_label}')

        self.add_input('entity', widget=actions)

        return super(CTEntitySelector, self).render(name, value, attrs)


class MultiCTEntitySelector(SelectorList):
    def __init__(self, content_types=(), attrs=None, autocomplete=False, creator=False):
        super(MultiCTEntitySelector, self).__init__(None, attrs=attrs)
        self.content_types = content_types
        self.autocomplete = autocomplete
        self.creator = creator

    def render(self, name, value, attrs=None):
        self.selector = CTEntitySelector(content_types=self.content_types,
                                         multiple=True,
                                         autocomplete=self.autocomplete,
                                         creator=self.creator,
                                         attrs={'reset': False},
                                        )

        return super(MultiCTEntitySelector, self).render(name, value, attrs)


class RelationSelector(ChainedInput):
    # _CTYPES_URL_FMT = '/creme_core/relation/type/${rtype}/content_types/json'

    # def __init__(self, relation_types=(), content_types=_CTYPES_URL_FMT,
    def __init__(self, relation_types=(), content_types=None,  # TODO: rename 'ctypes_url' ?
                 attrs=None, multiple=False, autocomplete=False,
                ):
        super(RelationSelector, self).__init__(attrs)
        self.relation_types = relation_types
        self.content_types = content_types
        self.multiple = multiple
        self.autocomplete = autocomplete

    def _build_ctypes_url(self):
        return TemplateURLBuilder(rtype_id=(TemplateURLBuilder.Word, '${rtype}'))\
                                 .resolve('creme_core__ctypes_compatible_with_rtype')

    def render(self, name, value, attrs=None):
        dselect_attrs = {'auto': False, 'autocomplete': True} if self.autocomplete else \
                        {'auto': False}

        self.add_dselect('rtype', options=self.relation_types, attrs=dselect_attrs)
        # self.add_dselect('ctype', options=self.content_types,  attrs=dselect_attrs)
        self.add_dselect('ctype', options=self.content_types or self._build_ctypes_url(), attrs=dselect_attrs)
        self.add_input('entity', widget=EntitySelector,
                       attrs={'auto': False, 'multiple': self.multiple},
                      )

        return super(RelationSelector, self).render(name, value, attrs)


class MultiRelationSelector(SelectorList):
    # def __init__(self, relation_types=(), content_types=RelationSelector._CTYPES_URL_FMT,
    def __init__(self, relation_types=(), content_types=None,
                 attrs=None, autocomplete=False,
                ):
        super(MultiRelationSelector, self).__init__(None, attrs=attrs)
        self.relation_types = relation_types
        self.content_types = content_types
        self.autocomplete = autocomplete

    def render(self, name, value, attrs=None):
        self.selector = RelationSelector(relation_types=self.relation_types,
                                         content_types=self.content_types,
                                         multiple=True,
                                         autocomplete=self.autocomplete,
                                        )

        return super(MultiRelationSelector, self).render(name, value, attrs)


class EntityCreatorWidget(ActionButtonList):
    def __init__(self, model=None, q_filter=None, attrs=None, creation_url='', creation_allowed=False):
        super(EntityCreatorWidget, self).__init__(delegate=None, attrs=attrs)
        self.model = model
        self.q_filter = q_filter
        self.creation_url = creation_url
        self.creation_allowed = creation_allowed

    def _is_disabled(self, attrs):
        if attrs is not None:
            return 'disabled' in attrs or 'readonly' in attrs

        return False

    def _build_actions(self, model, attrs):
        is_disabled = self._is_disabled(attrs)

        self.clear_actions()

        if not is_disabled:
            if not self.is_required:
                clear_label = _(u'Clear')
                self.add_action('reset', clear_label, title=clear_label, action='reset', value='')

            url = self.creation_url

            if url:
                allowed = self.creation_allowed
                self.add_action('create', model.creation_label, enabled=allowed, popupUrl=url,
                                title=_(u'Create') if allowed else _(u"Can't create"),
                               )

    def render(self, name, value, attrs=None):
        model = self.model

        if model is None:
            self.delegate = Label(empty_label='Model is not set')
        else:
            selector_attrs = {'auto': False, 'disabled': self._is_disabled(attrs)}

            if self.q_filter is not None:
                selector_attrs['qfilter'] = self.q_filter

            self.delegate = EntitySelector(unicode(ContentType.objects.get_for_model(model).id),
                                           selector_attrs
                                          )

            self._build_actions(model, attrs)

        return super(EntityCreatorWidget, self).render(name, value, attrs)


# TODO: factorise with EntityCreatorWidget ?
class MultiEntityCreatorWidget(SelectorList):
    def __init__(self, model=None, q_filter=None, attrs=None, creation_url='', creation_allowed=False):
        attrs = attrs or {'clonelast': False}
        super(MultiEntityCreatorWidget, self).__init__(None, attrs=attrs)
        self.model = model
        self.q_filter = q_filter
        self.creation_url = creation_url
        self.creation_allowed = creation_allowed

    def render(self, name, value, attrs=None):
        model = self.model
        self.selector = button_list = ActionButtonList(delegate=None)

        if model is None:
            delegate = Label(empty_label=u'Model is not set')
        else:
            self.clear_actions()  # TODO: indicate that we do not want actions in __init__
            self.add_action('add', getattr(model, 'selection_label', pgettext('creme_core-verb', u'Select')))

            delegate = EntitySelector(unicode(ContentType.objects.get_for_model(model).id),
                                      {'auto':       False,
                                       'qfilter':    self.q_filter,
                                       'multiple':   True,
                                       'autoselect': True,
                                      },
                                     )

            def add_action(name, label, enabled=True, **kwargs):
                button_list.add_action(name, label, enabled=False, hidden=True, **kwargs)
                self.add_action(name, label, enabled)

            url = self.creation_url
            if url:
                allowed = self.creation_allowed
                add_action('create', model.creation_label, enabled=allowed, popupUrl=url,
                            title=_(u'Create') if allowed else _(u"Can't create")
                           )

        button_list.delegate = delegate
        return super(MultiEntityCreatorWidget, self).render(name, value, attrs)


class FilteredEntityTypeWidget(ChainedInput):
    def __init__(self, content_types=(), attrs=None, autocomplete=True):
        super(FilteredEntityTypeWidget, self).__init__(attrs)
        self.content_types = content_types
        self.autocomplete = autocomplete

    def render(self, name, value, attrs=None):
        add_dselect = partial(self.add_dselect,
                              attrs={'auto': False, 'autocomplete': self.autocomplete},
                             )
        ctype_name = 'ctype'
        add_dselect(ctype_name, options=self.content_types)

        # TODO: allow to omit the 'All' filter ??
        # TODO: do not make a request for ContentType ID == '0'
        add_dselect('efilter',
                    # options='/creme_core/entity_filter/get_for_ctype/${%s}/all' % ctype_name,
                    options=reverse('creme_core__efilters') + '?ct_id=${%s}&all=true' % ctype_name,
                   )

        return super(FilteredEntityTypeWidget, self).render(name, value, attrs)


class DateTimeWidget(widgets.DateTimeInput):
    is_localized = True

    def __init__(self, attrs=None):
        super(DateTimeWidget, self).__init__(attrs=attrs, format='%d-%m-%Y %H:%M')

    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name, type='hidden')
        # value = localtime(value) if value is not None else value

        if isinstance(value, datetime) and not is_naive(value):
            value = localtime(value)

        context = widget_render_context('ui-creme-datetimepicker', attrs,
                                        date_format=settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT),
                                        date_label=_(u'On'),
                                        time_label=_(u'at'),
                                        hour_label=_(u'h'),  # TODO: improve i18n
                                        minute_label='',     # TODO: improve i18n
                                        clear_label=_(u'Clean'),
                                        now_label=_(u'Now'),
                                        readonly_attr='readonly' if attrs.get('readonly') is not None else '',
                                        disabled_attr='disabled' if attrs.get('disabled') is not None else '',
                                        input=super(DateTimeWidget, self).render(name, value, attrs),
                                       )

        return mark_safe(
"""<ul class="%(css)s" style="%(style)s" widget="%(typename)s" format="%(date_format)s" %(readonly_attr)s %(disabled_attr)s>
    %(input)s
    <li>%(date_label)s</li>
    <li class="date"><input class="ui-corner-all" type="text" maxlength="12"/></li>
    <li>%(time_label)s</li>
    <li class="hour"><input class="ui-corner-all" type="text" maxlength="2"/></li>
    <li>%(hour_label)s</li>
    <li class="minute"><input class="ui-corner-all" type="text" maxlength="2"/></li>
    <li>%(minute_label)s</li>
    <li class="clear"><button type="button">%(clear_label)s</button></li>
    <li class="now"><button type="button">%(now_label)s</button></li>
</ul>
""" % context)


class TimeWidget(widgets.TextInput):
    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name, type='hidden')

        return mark_safe(
"""<ul id="%(id)s_timepicker" class="ui-creme-timepicker">
    %(input)s
    <li class="hour"><input class="ui-corner-all" type="text" maxlength="2"/></li>
    <li>%(hour_label)s</li>
    <li class="minute"><input class="ui-corner-all" type="text" maxlength="2"/></li>
    <li>%(minute_label)s</li>
    <li><button type="button">%(now_label)s</button></li>
</ul>
<script type="text/javascript">
    $('.ui-creme-timepicker#%(id)s_timepicker').each(function() {creme.forms.TimePicker.init($(this));});
</script>""" % {'input':        super(TimeWidget, self).render(name, value, attrs),
                'hour_label':   _(u'h'),
                'minute_label': '',
                'id':           attrs['id'],
                'now_label':    _(u'Now'),
              })

    def value_from_datadict(self, data, files, name):
        value = data.get(name, '')

        if value.strip() == ':':
            value = ''

        return value


class CalendarWidget(widgets.TextInput):
    is_localized = True
    default_help_text = settings.DATE_FORMAT_VERBOSE

    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name)
        context = widget_render_context('ui-creme-datepicker', attrs)
        dateformat = settings.DATE_FORMAT_JS.get(settings.DATE_FORMAT)

        return mark_safe(u"""<div>%(help_text)s</div>%(input)s""" % {
                                  'help_text': self.default_help_text,
                                  'input': widget_render_input(widgets.TextInput.render, self, name, value, context,
                                                               format=dateformat,
                                                               readonly=attrs.get('readonly', False)),
                              })


# TODO: Only used in reports for now. Kept until *Selector widgets accept optgroup
class DependentSelect(widgets.Select):
    def __init__(self, target_id, attrs=None, choices=()):
        self.target_id = target_id
        self.target_url = None
        # self._source_val = self._target_val = None
        self.target_val = None
        super(DependentSelect, self).__init__(attrs, choices)

#    def _set_target(self, target):
#        self._target_val = target
#    target_val = property(lambda self: self._target_val, _set_target); del _set_target
#
#    def _set_source(self, source):
#        self._source_val = source
#    source_val = property(lambda self: self._source_val, _set_source); del _set_source

    def render(self, name, value, attrs=None, choices=()):
        final_attrs = self.build_attrs(attrs, name=name)
        id = final_attrs['id']
        final_attrs['onchange'] = """(function() {
    var source = $('#%(id)s');
    if (!source || typeof(source) === undefined) return;

    var target = $('#%(target_id)s');
    if (!target || typeof(target) === undefined) return;

    $.post('%(target_url)s',
           {record_id: source.val()},
           function(data) {
               var data = creme.forms.Select.optionsFromData(data.result, 'text', 'id');
               creme.forms.Select.fill(target, data, '%(target_val)s');
           }, 'json');
}());""" % {
            'id': id,
            'target_id': self.target_id,
            'target_url': self.target_url,
            'target_val': self.target_val,
        }

        return mark_safe('<script type="text/javascript">'
                            '$("#%(id)s").change();'
                         '</script>'
                         '%(input)s' % {'input': super(DependentSelect, self).render(name, value, final_attrs, choices),
                                        'id': id,
                                       }
                        )


class OptionalWidget(widgets.MultiWidget):
    def __init__(self, sub_widget=widgets.TextInput, attrs=None, sub_label=''):
        super(OptionalWidget, self).__init__(
                widgets=(widgets.CheckboxInput(attrs={'onchange': 'creme.forms.optionalWidgetHandler(this)'}),
                         sub_widget,
                        ),
                attrs=attrs,
            )
        self.sub_label = sub_label

    def decompress(self, value):
        return (value[0], value[1]) if value else (None, None)

    # TODO: true JS widget ?
    def format_output(self, rendered_widgets):
        return (
'''<ul class="optional-widget">
    <li>%(check)s</li>
    <li>%(label)s&nbsp;%(sub_widget)s</li>
    <script type="text/javascript">
        creme.forms.optionalWidgetHandler = function(check_box) {
            var jq_check_box = $(check_box);
            jq_check_box.parent().siblings('li').css('display', jq_check_box.is(':checked')? '': 'none');
        }
        $(document).ready(function() {
            $('ul.optional-widget li input').each(function() {creme.forms.optionalWidgetHandler(this);});
        });
    </script>
</ul>''' % {'check':      rendered_widgets[0],
            'sub_widget': rendered_widgets[1],
            'label':      self.sub_label,
           })

    @property
    def sub_widget(self):
        return self.widgets[1]


class OptionalSelect(OptionalWidget):
    def __init__(self, choices=(), *args, **kwargs):
        super(OptionalSelect, self).__init__(widgets.Select(choices=choices), *args, **kwargs)


class TinyMCEEditor(widgets.Textarea):
    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name)
        context = widget_render_context('ui-creme-jqueryplugin', attrs)

        plugin_options = json_dump({
            "mode": "textareas",
            "script_url": '%stiny_mce/tiny_mce.js' % settings.MEDIA_URL,
            "convert_urls": False,
            "theme": "advanced",
            "height": 300,
            "plugins": "spellchecker,pagebreak,style,layer,table,save,advhr,advimage,advlink,emotions,iespell,inlinepopups,insertdatetime,preview,media,searchreplace,print,contextmenu,paste,directionality,fullscreen,noneditable,visualchars,nonbreaking,xhtmlxtras,template, fullpage",
            "theme_advanced_buttons1": "save,newdocument,|,bold,italic,underline,strikethrough,|,justifyleft,justifycenter,justifyright,justifyfull,|,styleselect,formatselect,fontselect,fontsizeselect",
            "theme_advanced_buttons2": "cut,copy,paste,pastetext,pasteword,|,search,replace,|,bullist,numlist,|,outdent,indent,blockquote,|,undo,redo,|,link,unlink,anchor,image,cleanup,code,|,insertdate,inserttime,preview,|,forecolor,backcolor",
            "theme_advanced_buttons3": "tablecontrols,|,hr,removeformat,visualaid,|,sub,sup,|,charmap,emotions,iespell,media,advhr,|,print,|,ltr,rtl,|,fullscreen",
            "theme_advanced_buttons4": "insertlayer,moveforward,movebackward,absolute,|,styleprops,spellchecker,|,cite,abbr,acronym,del,ins,attribs,|,visualchars,nonbreaking,blockquote,pagebreak,|,insertfile,insertimage",
            "theme_advanced_toolbar_location": "top",
            "theme_advanced_toolbar_align": "left",
            "theme_advanced_path_location": "bottom",
            "theme_advanced_resizing": True,
        })

        return mark_safe(widget_render_input(widgets.Textarea.render, self, name, value, context,
                                             plugin='tinymce', 
                                             plugin_options=plugin_options))


class ColorPickerWidget(widgets.TextInput):
    def render(self, name, value, attrs=None):
        attrs = self.build_attrs(attrs, name=name)
        context = widget_render_context('ui-creme-jqueryplugin', attrs)

        return mark_safe(widget_render_input(widgets.TextInput.render, self, name, value, context, plugin='gccolor'))


class UnorderedMultipleChoiceWidget(widgets.SelectMultiple, EnhancedSelectOptions):
    MIN_SEARCH_COUNT = 10
    MIN_FILTER_COUNT = 30
    MIN_CHECKALL_COUNT = 3

    def __init__(self, attrs=None, choices=(),
                 columntype='', filtertype=None, viewless=None,
                 creation_url='', creation_allowed=False, creation_label=ugettext_lazy(u'Create')):
        super(UnorderedMultipleChoiceWidget, self).__init__(attrs, choices)
        self.columntype = columntype
        self.filtertype = filtertype
        self.viewless = viewless
        self.creation_url = creation_url
        self.creation_allowed = creation_allowed
        self.creation_label = creation_label

    def render_option(self, selected_choices, option_value, option_label):
        return self.render_enchanced_option(selected_choices, option_value, option_label)

    def render(self, name, value, attrs=None, choices=()):
        if not self.choices and not self.creation_allowed:
            return _(u'No choice available.')

        count = self._choice_count()
        attrs = self.build_attrs(attrs, name=name)
        filtertype = self._build_filtertype(count)
        input = widgets.SelectMultiple.render(self, name, value, {'class': 'ui-creme-input'}, choices)

        context = widget_render_context('ui-creme-checklistselect', attrs,
                                        body=self._render_body(attrs, filtertype),
                                        header=self._render_header(attrs, filtertype, count),
                                        counter=self._render_counter(attrs, filtertype),
                                        viewless=self._render_viewless(attrs, self.viewless),
                                        footer=self._render_footer(attrs, self.viewless),
                                        input=input,
                                       )

        return mark_safe(
u"""<div class="%(css)s" style="%(style)s" widget="%(typename)s" %(viewless)s>
    %(input)s
    %(counter)s
    %(header)s
    %(body)s
    %(footer)s
</div>""" % context)

    def _choice_count(self):
        return sum(len(c[1]) if isinstance(c[1], (list, tuple)) else 1 for c in self.choices)

    def _build_filtertype(self, count):
        if self.filtertype:
            return self.filtertype

        if count < self.MIN_SEARCH_COUNT:
            return None
        elif count < self.MIN_FILTER_COUNT:
            return 'search'
        else:
            return 'filter'

    def _render_viewless(self, attrs, viewless):
        if not viewless:
            return ''

        return 'less' if viewless is True else 'less="%s"' % viewless

    def _render_counter(self, attrs, filtertype):
        return '<span class="checklist-counter"></span>'

    def _render_footer(self, attrs, viewless):
        if not viewless:
            return ''

        return u'<div class="checklist-footer">'\
               '    <a class="checklist-toggle-less">%s</a>'\
               '</div>' % _(u'More')

    def _render_header_filter(self, filtertype):
        if not filtertype:
            return ''

        filtername = pgettext('creme_core-noun', u'Filter') if filtertype == 'filter' else \
                     pgettext('creme_core-noun', u'Search')
        return u'<input type="search" class="checklist-filter" placeholder="%s">' % filtername.upper()

    def _render_header(self, attrs, filtertype, count):
        has_checkall = attrs.get('checkall', True)
        checkall_hidden = ' hidden' if count < self.MIN_CHECKALL_COUNT else ''
        url = self.creation_url

        filter = self._render_header_filter(filtertype)
        buttons = []

        if has_checkall:
            buttons.extend([u'<a type="button" class="checklist-check-all%s">%s</a>' % (checkall_hidden, _(u'Check all')),
                            u'<a type="button" class="checklist-check-none%s">%s</a>' % (checkall_hidden, _(u'Check none'))])

        if url:
            disabled = 'disabled' if not self.creation_allowed else ''
            buttons.append(u'<a type="button" class="checklist-create" href="%s" %s>%s</a>' % (url, disabled, self.creation_label))

        return u'<div class="checklist-header">%(buttons)s%(filter)s</div>' % {
                   'filter': filter, 
                   'buttons': u''.join(buttons),
               }

    def _render_body(self, attrs, filtertype):
        return u'<div class="checklist-body"><ul class="checklist-content %s %s"></ul></div>' % (
                    filtertype or '', self.columntype,
                )


class OrderedMultipleChoiceWidget(widgets.SelectMultiple):
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = ()
        value_dict = {opt_value: order + 1 for order, opt_value in enumerate(value)}
        attrs = self.build_attrs(attrs, name=name)

        reduced = attrs.get('reduced', 'false')
        assert reduced in ('true', 'false')

        output = [u'<table %s><tbody>' % flatatt(attrs)]

        for i, (opt_value, opt_label) in enumerate(chain(self.choices, choices)):
            order = value_dict.get(opt_value, '')

            output.append(
u"""<tr name="oms_row_%(i)s">
    <td><input class="oms_check" type="checkbox" name="%(name)s_check_%(i)s" %(checked)s/></td>
    <td class="oms_value">%(label)s<input type="hidden" name="%(name)s_value_%(i)s" value="%(value)s" /></td>
    <td><input class="oms_order" type="text" name="%(name)s_order_%(i)s" value="%(order)s"/></td>
</tr>""" % {'i':        i,
            'label':    escape(opt_label),
            'name':     name,
            'value':    opt_value,
            'checked':  'checked' if order else '',
            'order':    order,
           })

        output.append(
u"""</tbody></table>
<script type="text/javascript">
    $(document).ready(function() {
        creme.forms.toOrderedMultiSelect('%(id)s', %(reduced)s);
    });
</script>""" % {'id':      attrs['id'],
                'reduced': reduced,
               })

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        prefix_check = '%s_check_' % name
        prefix_order = '%s_order_' % name
        prefix_value = '%s_value_' % name

        selected = []
        for key, value in data.iteritems():
            if key.startswith(prefix_check):
                index = key[len(prefix_check):]  # In fact not an int...
                order = int(data.get(prefix_order + index) or 0)
                value = data[prefix_value + index]
                selected.append((order, value))

        selected.sort(key=lambda i: i[0])

        return [val for _order, val in selected]


class Label(widgets.TextInput):
    empty_label = None

    def __init__(self, attrs=None, empty_label=None):
        super(Label, self).__init__(attrs=attrs)
        self.empty_label = empty_label

    def render(self, name, value, attrs=None):
        return mark_safe(u'%(input)s<span %(attrs)s>%(content)s</span>' % {
                'input':   super(Label, self).render(name, value, {'style': 'display:none;'}),
                'attrs':   flatatt(self.build_attrs(attrs, name=name)),
                'content': conditional_escape(force_unicode(value or self.empty_label)),
            })


class ListEditionWidget(widgets.Widget):
    content = ()
    only_delete = False

    def render(self, name, value, attrs=None, choices=()):
        output = [u'<table %s><tbody>' % flatatt(self.build_attrs(attrs, name=name))]
        row = (u'<tr>'
                    '<td><input type="checkbox" name="%(name)s_check_%(i)s" %(checked)s/></td>'
                    '<td><input type="text" name="%(name)s_value_%(i)s" value="%(label)s" style="display:none;"/><span>%(label)s</span></td>'
                '</tr>' if self.only_delete else
                u'<tr>'
                    '<td><input type="checkbox" name="%(name)s_check_%(i)s" %(checked)s/></td>'
                    '<td><input type="text" name="%(name)s_value_%(i)s" value="%(label)s"/></td>'
                 '</tr>')

        for i, label in enumerate(self.content):
            checked = 'checked'

            if value:
                new_label = value[i]

                if new_label is None:
                    checked = ''
                else:
                    label = new_label

            output.append(row % {'i':        i,
                                 'name':     name,
                                 'label':    escape(label),
                                 'checked':  checked,
                                }
                         )

        output.append(u'</tbody></table>')

        return mark_safe(u'\n'.join(output))

    def value_from_datadict(self, data, files, name):
        prefix_check = name + '_check_%i'
        prefix_value = name + '_value_%i'
        get     = data.get
        has_key = data.has_key

        return [get(prefix_value % i) if has_key(prefix_check % i) else None
                    for i in xrange(len(self.content))
               ]


# class AdaptiveWidget(Select):
#     def __init__(self, ct_id, object_id="", attrs=None, choices=()):
#         super(AdaptiveWidget, self).__init__(attrs, choices)
#         self.ct_id = ct_id
#         self.object_id = object_id
#         self.url = "/creme_core/entity/get_widget/%s" % ct_id
#         warnings.warn("AdaptiveWidget is deprecated and will be removed in 1.7",
#                       DeprecationWarning
#                      )
#
#     def render(self, name, value, attrs=None, choices=()):
#         attrs = self.build_attrs(attrs, name=name)
#         context = widget_render_context('ui-creme-adaptive-widget', attrs,
#                                         url=self.url,
#                                         object_id=self.object_id,
#                                         style=attrs.pop('style', ''),
#                                        )
#         context['input'] = super(AdaptiveWidget, self).render(name, value, attrs, choices)
#
#         return mark_safe('<span class="%(css)s" style="%(style)s" widget="%(typename)s" '
#                                'url="%(url)s" object_id="%(object_id)s">'
#                             '%(input)s'
#                          '</span>' % context
#                         )


class DatePeriodWidget(widgets.MultiWidget):
    def __init__(self, choices=(), attrs=None):
        super(DatePeriodWidget, self).__init__(
                    widgets=(widgets.Select(choices=choices, attrs={'class': 'dperiod-type'}),
                             widgets.TextInput(attrs={'class': 'dperiod-value'}),  # TODO: min_value
                            ),
                    attrs=attrs,
        )

    @property
    def choices(self):
        return self.widgets[0].choices

    @choices.setter
    def choices(self, choices):
        self.widgets[0].choices = choices

    def decompress(self, value):
        if value:
            d = value.as_dict()
            return d['type'], d['value']

        return None, None

    def format_output(self, rendered_widgets):
        return u'<ul class="ui-layout hbox">%s</ul>' % (
                    _(u'%(dateperiod_value)s%(dateperiod_type)s') % {
                            'dateperiod_type':  u'<li>%s</li>' % rendered_widgets[0],
                            'dateperiod_value': u'<li>%s</li>' % rendered_widgets[1],
                        }
                )


class DateRangeWidget(widgets.MultiWidget):
    def __init__(self, choices=(), attrs=None):
        self.render_as = attrs.pop('render_as', 'table') if attrs else 'table'

        super(DateRangeWidget, self).__init__(
            widgets=(widgets.Select(choices=choices, attrs={'class': 'range-type'}),
                     CalendarWidget(attrs={'class': 'date-start'}),
                     CalendarWidget(attrs={'class': 'date-end'}),
                    ),
            attrs=attrs,
        )

    @property
    def choices(self):
        return self.widgets[0].choices

    @choices.setter
    def choices(self, choices):
        self.widgets[0].choices = choices

    def decompress(self, value):
        if value:
            return value[0], value[1], value[2]
        return None, None, None

    def format_output(self, rendered_widgets):
        typename = 'ui-creme-daterange'
        context = widget_render_context(typename, {})

        if self.render_as == 'table':
            return u"".join([u'<table class="%(css)s" style="%(style)s" widget="%(typename)s"><tbody><tr>' % context,
                             u''.join(u'<td>%s</td>' % w for w in rendered_widgets),
                             u'</tr></tbody></table>'
                            ])
        elif self.render_as == 'ul':
            return u"".join([u'<ul class="%(css)s" style="%(style)s" widget="%(typename)s">' % context,
                             u''.join(u'<li>%s</li>' % w for w in rendered_widgets),
                             u'</ul>'
                            ])

        return u'<div class="%s">%s</div>' % (
                        typename,
                        u''.join(u'<div>%s</div>' % w for w in rendered_widgets),
                    )


class DurationWidget(widgets.MultiWidget):
    def __init__(self, attrs=None):
        TextInput = widgets.TextInput
        super(DurationWidget, self).__init__(widgets=(TextInput(), TextInput(), TextInput()),
                                             attrs=attrs,
                                            )

    def decompress(self, value):
        if value:
            return value.split(':')
        return None, None, None

    def format_output(self, rendered_widgets):
        hours_widget, minutes_widget, seconds_widget = rendered_widgets
        return (u'<span>%(hours)s&nbsp;%(hours_label)s&nbsp;'
                        '%(minutes)s&nbsp;%(minutes_label)s&nbsp;'
                        '%(seconds)s&nbsp;%(seconds_label)s&nbsp;'
                 '</span>' % {'hours':   hours_widget,   'hours_label':   _(u'Hour(s)'),
                              'minutes': minutes_widget, 'minutes_label': _(u'Minute(s)'),
                              'seconds': seconds_widget, 'seconds_label': _(u'Second(s)'),
                             })


class ChoiceOrCharWidget(widgets.MultiWidget):
    def __init__(self, attrs=None, choices=()):
        # self.select_widget = select = widgets.Select(choices=choices)
        # super(ChoiceOrCharWidget, self).__init__(widgets=(select, widgets.TextInput()), attrs=attrs)
        super(ChoiceOrCharWidget, self).__init__(widgets=(widgets.Select(choices=choices),
                                                          widgets.TextInput(),
                                                         ),
                                                 attrs=attrs,
                                                )

    @property
    def choices(self):
        # return self.select_widget.choices
        return self.widgets[0].choices

    @choices.setter
    def choices(self, choices):
        # self.select_widget.choices = choices
        self.widgets[0].choices = choices

    def decompress(self, value):
        if value:
            return value[0], value[1]

        return None, None


class CremeRadioFieldRenderer(widgets.RadioFieldRenderer):
    def render(self):
        return mark_safe(u'<ul class="radio_select">\n%s\n</ul>' %
                            u'\n'.join(u'<li>%s</li>' % force_unicode(w) for w in self)
                        )


class CremeRadioSelect(widgets.RadioSelect):
    renderer = CremeRadioFieldRenderer

