from creme.billing import get_invoice_model
from creme.billing.exporters import BillingExporter
from creme.creme_core.models import FileRef


class OnlyInvoiceExporter(BillingExporter):
    id = 'billing-test_only_invoice'
    verbose_name = 'Only invoice'
    compatible_models = (
        get_invoice_model(),
    )

    def _generate_file_ref(self):
        return FileRef()
