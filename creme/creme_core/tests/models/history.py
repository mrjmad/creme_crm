 # -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType

from creme_core.models import HistoryLine, HistoryConfigItem, RelationType, Relation
from creme_core.tests.views.base import ViewsTestCase

from persons.models import Contact, Organisation, Sector


__all__ = ('HistoryTestCase',)


class HistoryTestCase(ViewsTestCase):
    def setUp(self):
        self.populate('creme_core')

    def _build_organisation(self, name, extra_args=None, **kwargs):
        data = {'name': name}
        data.update(kwargs)

        if extra_args:
            data.update(extra_args)

        response = self.client.post('/persons/organisation/add', follow=True, data=data)
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        try:
            orga = Organisation.objects.get(name=name)
        except Organisation.DoesNotExist, e:
            self.fail(str(e))

        return orga

    def _build_contact(self, first_name, last_name, extra_args=None, **kwargs):
        data = {'first_name': first_name, 'last_name': last_name}
        data.update(kwargs)

        if extra_args:
            data.update(extra_args)

        response = self.client.post('/persons/contact/add', follow=True, data=data)
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        try:
            contact = Contact.objects.get(first_name=first_name, last_name=last_name)
        except Organisation.DoesNotExist, e:
            self.fail(str(e))

        return contact

    def test_creation01(self):
        self.login()

        old_count = HistoryLine.objects.count()
        gainax = self._build_organisation(user=self.other_user.id, name='Gainax')
        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,                 hline.entity.id)
        self.assertEqual(gainax.entity_type,        hline.entity_ctype)
        self.assertEqual(self.other_user,           hline.entity_owner)
        self.assertEqual(self.user.username,        hline.username)
        self.assertEqual(HistoryLine.TYPE_CREATION, hline.type)
        self.assertEqual([],                        hline.modifications)
        self.assert_((datetime.now() - hline.date) < timedelta(seconds=1))

    def test_creation02(self): #double save() beacuse of addresses caused problems
        self.login()

        old_count = HistoryLine.objects.count()

        country = 'Japan'
        gainax = self._build_organisation(user=self.other_user.id, name='Gainax',
                                          extra_args={'billing_address-country': country}
                                         )
        self.assert_(gainax.billing_address is not None)
        self.assertEqual(country, gainax.billing_address.country)

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,                 hline.entity.id)
        self.assertEqual(gainax.entity_type,        hline.entity_ctype)
        self.assertEqual(self.other_user,           hline.entity_owner)
        self.assertEqual(HistoryLine.TYPE_CREATION, hline.type)
        self.assertEqual([],                        hline.modifications)
        self.assert_((datetime.now() - hline.date) < timedelta(seconds=1))

    def test_edition01(self):
        self.login()

        old_count = HistoryLine.objects.count()

        name = 'gainax'
        old_capital = 12000
        gainax = self._build_organisation(user=self.user.id, name=name, capital=old_capital)

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        capital = old_capital * 2
        response = self.client.post('/persons/organisation/edit/%s' % gainax.id, follow=True,
                                    data={
                                            'user':    self.user.id,
                                            'name':    name,
                                            'capital': capital,
                                         }
                                   )
        self.assertNoFormError(response)

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-1]
        self.assertEqual(gainax.id,                hline.entity.id)
        self.assertEqual(HistoryLine.TYPE_EDITION, hline.type)
        self.assertEqual([['capital', old_capital, capital]], hline.modifications)

    #TODO: change 'name' but keep the old unicode() ???
    def test_edition02(self):
        self.login()

        old_count = HistoryLine.objects.count()

        sector01 = Sector.objects.create(title='Studio')
        sector02 = Sector.objects.create(title='Animation studio')

        name = 'Gainax'
        old_phone = '7070707'
        description = """Oh this is an long description
text that takes several lines
about this fantastic animation studio."""
        gainax = self._build_organisation(user=self.user.id, name=name, phone=old_phone,
                                          description=description, sector=sector01.id,
                                          subject_to_vat=False,
                                         )

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        phone = old_phone + '07'
        email = 'contact@gainax.jp'
        description += 'In this studio were created lots of excellent animes like "Evangelion" or "Fushigi no umi no Nadia".'
        response = self.client.post('/persons/organisation/edit/%s' % gainax.id, follow=True,
                                    data={
                                            'user':          self.user.id,
                                            'name':          name,
                                            'phone':         phone,
                                            'email':         email,
                                            'description':   description,
                                            'sector':        sector02.id,
                                            'creation_date': '1984-12-24',
                                            'subject_to_vat': True,
                                         }
                                   )
        self.assertNoFormError(response)

        hline = HistoryLine.objects.latest('date')
        modifs = hline.modifications
        self.assert_(isinstance(modifs, list))
        self.assertEqual(6, len(modifs))
        self.assert_(['phone', old_phone, phone] in modifs)
        self.assert_(['email', email] in modifs)
        self.assert_(['description'] in modifs)
        self.assert_(['sector', sector01.id, sector02.id] in modifs)
        self.assert_(['creation_date'] in modifs)
        self.assert_(['subject_to_vat', True] in modifs, modifs)

        vmodifs = hline.verbose_modifications
        self.assertEqual(6, len(vmodifs))
        #print 'VMODIFS:', vmodifs

        msg = _(u'Set field "%(field)s" from "%(oldvalue)s" to "%(value)s"') % {
                            'field':    _(u'Phone number'),
                            'oldvalue': old_phone,
                            'value':    phone,
                        }
        self.assert_(msg in vmodifs, msg)

        msg = _(u'Set field "%(field)s" to "%(value)s"') % { 'field': _(u'Email'),
                                                             'value': email,
                                                           }
        self.assert_(msg in vmodifs, msg)

        msg = _(u'Set field "%(field)s"') % {'field': _(u'Description')}
        self.assert_(msg in vmodifs, msg)

        msg = _(u'Set field "%(field)s" from "%(oldvalue)s" to "%(value)s"') % {
                        'field':    _(u'Sector'),
                        'oldvalue': sector01,
                        'value':    sector02,
                    }
        self.assert_(msg in vmodifs, msg)

        msg = _(u'Set field "%(field)s"') % {'field': _(u'Date of creation of the organisation')}
        self.assert_(msg in vmodifs, msg)

        msg = _(u'Set field "%(field)s" to "%(value)s"') % {
                            'field': _(u'Subject to VAT'),
                            'value': _('True'),
                        }
        self.assert_(msg in vmodifs, msg)

    def test_edition03(self): #no change
        self.login()

        name = 'gainax'
        capital = 12000
        gainax = self._build_organisation(user=self.user.id, name=name, capital=capital)

        old_count = HistoryLine.objects.count()

        response = self.client.post('/persons/organisation/edit/%s' % gainax.id, follow=True,
                                    data={
                                            'user':    self.user.id,
                                            'name':    name,
                                            'capital': capital,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(old_count, HistoryLine.objects.count())

    def test_deletion(self):
        self.login()

        old_count = HistoryLine.objects.count()
        gainax = Organisation.objects.create(user=self.other_user, name='Gainax')
        entity_repr = unicode(gainax)

        self.assertEqual(old_count + 1, HistoryLine.objects.count())

        creation_line = HistoryLine.objects.get(entity=gainax)

        self.assertEqual(200, self.client.post('/creme_core/entity/delete/%s' % gainax.id, follow=True).status_code)
        self.assertFalse(Organisation.objects.filter(pk=gainax.id).count())

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 2, len(hlines))

        hline = hlines[-1]
        self.assert_(hline.entity is None, hline.entity)
        self.assertEqual(entity_repr,               hline.entity_repr)
        self.assertEqual(self.other_user,           hline.entity_owner)
        self.assertEqual(self.user.username,        hline.username)
        self.assertEqual(HistoryLine.TYPE_DELETION, hline.type)
        self.assert_((datetime.now() - hline.date) < timedelta(seconds=1))
        self.assertEqual([],                        hline.modifications)

        creation_line = HistoryLine.objects.get(pk=creation_line.id) #refresh
        self.assert_(hline.entity is None)
        self.assertEqual(entity_repr, hline.entity_repr)

    def test_related_edition01(self):
        self.login()

        ghibli = self._build_organisation(user=self.user.id, name='Ghibli')

        first_name = 'Hayao'
        last_name  = 'Miyazaki'
        hayao  = self._build_contact(user=self.user.id, first_name=first_name, last_name=last_name)

        rtype, srtype = RelationType.create(('test-subject_employed', 'is employed'), ('test-object_employed', 'employs'))
        Relation.objects.create(user=self.user, subject_entity=hayao, object_entity=ghibli, type=rtype)

        old_count = HistoryLine.objects.count()
        response = self.client.post('/persons/contact/edit/%s' % hayao.id, follow=True,
                                    data={
                                            'user':        self.user.id,
                                            'first_name':  first_name,
                                            'last_name':   last_name,
                                            'description': 'A great animation movie maker'
                                         }
                                   )
        self.assertNoFormError(response)

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 1, len(hlines))

        hline = hlines[-1]
        self.assertEqual(HistoryLine.TYPE_EDITION, hline.type)
        self.assert_(hline.related_line is None)

    def test_related_edition02(self):
        self.login()

        ghibli = self._build_organisation(user=self.user.id, name='Ghibli')

        first_name = 'Hayao'
        last_name  = 'Miyazaki'
        hayao  = self._build_contact(user=self.user.id, first_name=first_name, last_name=last_name)

        rtype, srtype = RelationType.create(('test-subject_employed', 'is employed'), ('test-object_employed', 'employs'))
        Relation.objects.create(user=self.user, subject_entity=hayao, object_entity=ghibli, type=rtype)

        HistoryConfigItem.objects.create(relation_type=rtype)

        old_count = HistoryLine.objects.count()
        response = self.client.post('/persons/contact/edit/%s' % hayao.id, follow=True,
                                    data={
                                            'user':        self.user.id,
                                            'first_name':  first_name,
                                            'last_name':   last_name,
                                            'description': 'A great animation movie maker',
                                         }
                                   )
        self.assertNoFormError(response)

        hlines = list(HistoryLine.objects.order_by('id'))
        self.assertEqual(old_count + 2, len(hlines))

        edition_hline = hlines[-2]
        self.assertEqual(HistoryLine.TYPE_EDITION, edition_hline.type)

        hline = hlines[-1]
        self.assertEqual(ghibli.id,                hline.entity.id)
        self.assertEqual(ghibli.entity_type,       hline.entity_ctype)
        self.assertEqual(self.user,                hline.entity_owner)
        self.assertEqual(HistoryLine.TYPE_RELATED, hline.type)
        self.assertEqual(unicode(ghibli),          hline.entity_repr)
        self.assertEqual([],                       hline.modifications)
        self.assertEqual(edition_hline.id,         hline.related_line.id)

        self.assert_((datetime.now() - hline.date) < timedelta(seconds=1))
        self.assert_(hline.date != ghibli.modified)
