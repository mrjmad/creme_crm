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

# import logging
from creme import billing
from creme.creme_core.models import FileRef

from .base import BillingExporter

# logger = logging.getLogger(__name__)


class XLSExporter(BillingExporter):
    id = 'billing-xls'
    verbose_name = 'XLS'

    # TEMPLATE_PATHS = {
    #     billing.get_invoice_model():        'billing/templates/invoice.tex',
    #     billing.get_credit_note_model():    'billing/templates/billings.tex',
    #     billing.get_quote_model():          'billing/templates/billings.tex',
    #     billing.get_sales_order_model():    'billing/templates/billings.tex',
    #     billing.get_template_base_model():  'billing/templates/billings.tex',
    # }

    compatible_models = (
        billing.get_invoice_model(),
        billing.get_credit_note_model(),
        billing.get_quote_model(),
        billing.get_sales_order_model(),
        # billing.get_template_base_model(),
    )

    # def __init__(self, **kwargs):
    #     super().__init__(**kwargs)
    #
    #     template_path = self.TEMPLATE_PATHS.get(self.entity.__class__)
    #     if template_path is None:
    #         raise ConflictError('This type of entity cannot be exported as PDF')
    #
    #     self.template_path = template_path

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #
    #     entity = self.entity
    #     has_perm = self.user.has_perm_to_view_or_die
    #
    #     source = entity.get_source().get_real_entity()
    #     has_perm(source)
    #
    #     target = entity.get_target().get_real_entity()
    #     has_perm(target)
    #
    #     context['plines'] = entity.get_lines(billing.get_product_line_model())
    #     context['slines'] = entity.get_lines(billing.get_service_line_model())
    #     context['source'] = source
    #     context['target'] = target
    #     context['object'] = entity
    #     context['document_name'] = str(entity._meta.verbose_name)
    #
    #     return context
    #
    # def generate_pdf(self, *, content, dir_path, basename):
    #     latex_file_path = path.join(dir_path, f'{basename}.tex')
    #
    #     # NB: we precise the encoding or it oddly crashes on some systems...
    #     with open(latex_file_path, 'w', encoding='utf-8') as f:
    #         f.write(smart_str(content))
    #
    #     # NB: return code seems always 1 even when there is no error...
    #     subprocess.call(
    #         [
    #             'pdflatex',
    #             '-interaction=batchmode',
    #             '-output-directory', dir_path,
    #             latex_file_path,
    #         ]
    #     )
    #
    #     pdf_basename = f'{basename}.pdf'
    #     temp_pdf_file_path = path.join(dir_path, pdf_basename)
    #
    #     if not path.exists(temp_pdf_file_path):
    #         logger.critical(
    #             'It seems the PDF generation has failed. '
    #             'The temporary directory has not been removed, '
    #             'so you can inspect the *.log file in "%s"',
    #             dir_path,
    #         )
    #         # TODO: use a better exception class ?
    #         raise ConflictError(_(
    #             'The generation of the PDF file has failed ; '
    #             'please contact your administrator.'
    #         ))
    #
    #     final_path = FileCreator(
    #         dir_path=path.join(settings.MEDIA_ROOT, 'upload', 'billing'),
    #         name=pdf_basename,
    #     ).create()
    #     copy(temp_pdf_file_path, final_path)
    #
    #     return final_path, pdf_basename

    # def export(self):
    def _generate_file_ref(self):
        entity = self.entity
        # template = loader.get_template(self.template_path)
        # context = self.get_context_data()
        # tmp_dir_path = mkdtemp(prefix='creme_billing_latex')
        #
        # final_path, pdf_basename = self.generate_pdf(
        #     content=template.render(context),
        #     dir_path=tmp_dir_path,
        #     basename=secure_filename(f'{entity._meta.verbose_name}_{entity.id}'),
        # )
        #
        # rmtree(tmp_dir_path)

        return FileRef.objects.create(
            user=self.user,
            # filedata='upload/billing/' + path.basename(final_path),
            filedata='upload/billing/' + 'path.basename(final_path)',
            # basename=xls_basename,
            basename='xls_basename',
        )
