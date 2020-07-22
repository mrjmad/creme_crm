# -*- coding: utf-8 -*-

from decimal import Decimal
from functools import partial
from os.path import basename, dirname, exists, join
from shutil import which
from unittest import skipIf

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.billing.bricks import BillingExportersBrick
from creme.billing.exporters import BillingExporterManager
from creme.billing.exporters.latex import LatexExporter
from creme.billing.exporters.xls import XLSExporter
from creme.billing.models import ExporterConfigItem
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import FileRef, SetCredentials
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import skipIfCustomOrganisation

from .base import (
    CreditNote,
    Invoice,
    Organisation,
    ProductLine,
    Quote,
    SalesOrder,
    ServiceLine,
    TemplateBase,
    _BillingTestCase,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
    skipIfCustomQuote,
    skipIfCustomServiceLine,
)
from .fake_exporters import OnlyInvoiceExporter


@skipIfCustomOrganisation
# class ExportTestCase(_BillingTestCase):
class ExportTestCase(BrickTestCaseMixin, _BillingTestCase):
    def _build_export_url(self, entity):
        return reverse('billing__export', args=(entity.id,))

    def test_exporter_manager01(self):
        "Empty."
        manager = BillingExporterManager([])
        self.assertIsNone(manager.exporter(exporter_id='billing-latex', model=Invoice))
        self.assertIsNone(manager.exporter(exporter_id='billing-xls',   model=Invoice))

    def test_exporter_manager02(self):
        "Pass class directly."
        manager = BillingExporterManager([
            'creme.billing.exporters.latex.LatexExporter',
            'creme.billing.exporters.xls.XLSExporter',
            'creme.billing.tests.fake_exporters.OnlyInvoiceExporter',
        ])

        exporter1 = manager.exporter(exporter_id='billing-latex', model=Invoice)
        self.assertIsInstance(exporter1, LatexExporter)
        self.assertEqual(Invoice, exporter1.model)

        exporter2 = manager.exporter(exporter_id='billing-xls', model=Quote)
        self.assertIsInstance(exporter2, XLSExporter)
        self.assertEqual(Quote, exporter2.model)

        self.assertIsInstance(
            manager.exporter(exporter_id=OnlyInvoiceExporter.id, model=Invoice),
            OnlyInvoiceExporter
        )
        self.assertIsNone(
            manager.exporter(exporter_id=OnlyInvoiceExporter.id, model=Quote),
        )

    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.latex.LatexExporter',
        'creme.billing.exporters.xls.XLSExporter',
    ])
    def test_exporter_manager03(self):
        "Default argument => use settings."
        manager = BillingExporterManager()

        exporter1 = manager.exporter(exporter_id='billing-latex', model=Invoice)
        self.assertIsInstance(exporter1, LatexExporter)
        self.assertEqual(Invoice, exporter1.model)

        exporter2 = manager.exporter(exporter_id='billing-xls', model=Quote)
        self.assertIsInstance(exporter2, XLSExporter)
        self.assertEqual(Quote, exporter2.model)

    def test_configuration_populate(self):
        get_ct = ContentType.objects.get_for_model
        self.get_object_or_fail(
            ExporterConfigItem,
            content_type=get_ct(Invoice), exporter_id='',
        )
        self.get_object_or_fail(
            ExporterConfigItem,
            content_type=get_ct(Quote), exporter_id='',
        )
        self.get_object_or_fail(
            ExporterConfigItem,
            content_type=get_ct(SalesOrder), exporter_id='',
        )
        self.get_object_or_fail(
            ExporterConfigItem,
            content_type=get_ct(CreditNote), exporter_id='',
        )
        self.get_object_or_fail(
            ExporterConfigItem,
            content_type=get_ct(TemplateBase), exporter_id='',
        )

    def test_configuration_portal(self):
        self.login()

        response = self.assertGET200(
            reverse('creme_config__app_portal', args=('billing',))
        )
        self.get_brick_node(
            self.get_html_tree(response.content), BillingExportersBrick.id_,
        )

        # TODO: complete

    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.exporters.latex.LatexExporter',
        'creme.billing.exporters.xls.XLSExporter',
    ])
    def test_configuration_edition01(self):
        self.login(is_superuser=False, admin_4_apps=['billing'])

        ct = ContentType.objects.get_for_model(Invoice)
        url = reverse('billing__edit_exporter_config', args=(ct.id,))
        response1 = self.assertGET200(url)

        with self.assertNoException():
            choices = response1.context['form'].fields['exporter_id'].choices

        exporter_id = 'billing-latex'
        self.assertInChoices(
            value=exporter_id,
            label='Latex',
            choices=choices,
        )
        self.assertInChoices(
            value='billing-xls',
            label='XLS',
            choices=choices,
        )

        # --
        response2 = self.assertPOST200(url, data={'exporter_id': exporter_id})
        self.assertNoFormError(response2)

        conf_item = self.get_object_or_fail(ExporterConfigItem, content_type=ct)
        self.assertEqual(exporter_id, conf_item.exporter_id)

    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExporter'])
    def test_configuration_edition02(self):
        "Not admin credentials."
        self.login(is_superuser=False)  # Not admin_4_apps=['billing']

        ct = ContentType.objects.get_for_model(Invoice)
        self.assertGET403(reverse('billing__edit_exporter_config', args=(ct.id,)))

    def test_export_error01(self):
        "Bad CT."
        user = self.login()
        orga = Organisation.objects.create(user=user, name='Laputa')
        # self.assertGET409(self._build_export_url(orga))
        self.assertGET404(self._build_export_url(orga))

        # TODO: test with a billing model but not managed

    @skipIfCustomQuote
    def test_export_error02(self):
        "Empty configuration."
        self.login()
        quote = self.create_quote_n_orgas('My Quote')[0]

        # ExporterConfigItem.objects.filter(
        #     content_type=quote.entity_type,
        # ).update(exporter_id='billing-latex')
        item = self.get_object_or_fail(ExporterConfigItem, content_type=quote.entity_type)
        self.assertEqual('', item.exporter_id)

        url = self._build_export_url(quote)
        response = self.client.get(url, follow=True)
        self.assertContains(
            response,
            _(
                'The exporter is not configured ; '
                'go to the configuration of the app «Billing».'
            ),
            status_code=409,
        )

    @skipIfCustomQuote
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.xls.XLSExporter'])
    def test_export_error03(self):
        "Invalid configuration."
        self.login()
        quote = self.create_quote_n_orgas('My Quote')[0]

        ExporterConfigItem.objects.filter(
            content_type=quote.entity_type,
        ).update(exporter_id=LatexExporter.id)

        url = self._build_export_url(quote)
        response = self.client.get(url, follow=True)
        self.assertContains(
            response,
            _(
                'The configured exporter is invalid ; '
                'go to the configuration of the app «Billing».'
            ),
            status_code=409,
        )

    @skipIfCustomQuote
    @override_settings(BILLING_EXPORTERS=[
        'creme.billing.tests.fake_exporters.OnlyInvoiceExporter',
    ])
    def test_export_error04(self):
        "Incompatible CT."
        self.login()
        quote = self.create_quote_n_orgas('My Quote')[0]

        ExporterConfigItem.objects.filter(
            content_type=quote.entity_type,
        ).update(exporter_id=LatexExporter.id)

        url = self._build_export_url(quote)
        response = self.client.get(url, follow=True)
        self.assertContains(
            response,
            _(
                'The configured exporter is invalid ; '
                'go to the configuration of the app «Billing».'
            ),
            status_code=409,
        )

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    @skipIf(which('pdflatex') is None, '"pdflatex" is not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExporter'])
    def test_export_invoice_latex(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('My Invoice', discount=0)[0]

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(exporter_id='billing-latex')

        create_line = partial(
            ProductLine.objects.create,
            user=user, related_document=invoice,
        )
        for price in ('10', '20'):
            create_line(on_the_fly_item='Fly ' + price, unit_price=Decimal(price))

        existing_fileref_ids = [*FileRef.objects.values_list('id', flat=True)]

        response = self.assertGET200(self._build_export_url(invoice), follow=True)
        self.assertEqual('application/pdf', response['Content-Type'])

        filerefs = FileRef.objects.exclude(id__in=existing_fileref_ids)
        self.assertEqual(1, len(filerefs))

        fileref = filerefs[0]
        self.assertTrue(fileref.temporary)
        self.assertEqual('{}_{}.pdf'.format(_('Invoice'), invoice.id), fileref.basename)
        self.assertEqual(user, fileref.user)

        fullpath = fileref.filedata.path
        self.assertTrue(exists(fullpath), f'<{fullpath}> does not exists?!')
        self.assertEqual(join(settings.MEDIA_ROOT, 'upload', 'billing'), dirname(fullpath))
        self.assertEqual(
            # f'attachment; filename={basename(fullpath)}',
            f'attachment; filename="{basename(fullpath)}"',
            response['Content-Disposition']
        )
        __ = b''.join(response.streaming_content)  # Consume stream to avoid ResourceWarning

    @skipIfCustomQuote
    @skipIfCustomServiceLine
    @skipIf(which('pdflatex') is None, '"pdflatex" is not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExporter'])
    def test_export_quote_latex(self):
        user = self.login()
        quote = self.create_quote_n_orgas('My Quote')[0]

        ExporterConfigItem.objects.filter(
            content_type=quote.entity_type,
        ).update(exporter_id='billing-latex')

        create_line = partial(
            ServiceLine.objects.create,
            user=user, related_document=quote,
        )

        for price in ('10', '20'):
            create_line(on_the_fly_item='Fly ' + price, unit_price=Decimal(price))

        response = self.assertGET200(self._build_export_url(quote), follow=True)
        self.assertEqual('application/pdf', response['Content-Type'])

    @skipIfCustomInvoice
    def test_export_credentials(self):
        "Billing entity credentials."
        user = self.login(
            is_superuser=False, allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK | EntityCredentials.UNLINK,
            set_type=SetCredentials.ESET_OWN,
        )

        invoice, source, target = self.create_invoice_n_orgas('My Invoice', discount=0)
        invoice.user = self.other_user
        invoice.save()

        self.assertFalse(user.has_perm_to_view(invoice))
        self.assertTrue(user.has_perm_to_view(source))
        self.assertTrue(user.has_perm_to_view(target))

        self.assertGET403(self._build_export_url(invoice))

    @skipIf(which('pdflatex') is None, '"pdflatex" is not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExporter'])
    @skipIfCustomInvoice
    def test_export_latex_credentials01(self):
        "Source credentials."
        user = self.login(
            is_superuser=False, allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK | EntityCredentials.UNLINK,
            set_type=SetCredentials.ESET_OWN,
        )

        invoice, source, target = self.create_invoice_n_orgas('My Invoice', discount=0)
        source.user = self.other_user
        source.save()

        self.assertTrue(user.has_perm_to_view(invoice))
        self.assertFalse(user.has_perm_to_view(source))
        self.assertTrue(user.has_perm_to_view(target))

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(exporter_id=LatexExporter.id)
        self.assertGET403(self._build_export_url(invoice))

    @skipIf(which('pdflatex') is None, '"pdflatex" is not installed.')
    @override_settings(BILLING_EXPORTERS=['creme.billing.exporters.latex.LatexExporter'])
    @skipIfCustomInvoice
    def test_export_latex_credentials02(self):
        "Target credentials."
        user = self.login(
            is_superuser=False, allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK | EntityCredentials.UNLINK,
            set_type=SetCredentials.ESET_OWN,
        )

        invoice, source, target = self.create_invoice_n_orgas('My Invoice', discount=0)
        target.user = self.other_user
        target.save()

        self.assertTrue(user.has_perm_to_view(invoice))
        self.assertTrue(user.has_perm_to_view(source))
        self.assertFalse(user.has_perm_to_view(target))

        ExporterConfigItem.objects.filter(
            content_type=invoice.entity_type,
        ).update(exporter_id=LatexExporter.id)
        self.assertGET403(self._build_export_url(invoice))
