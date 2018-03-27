# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial

    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from creme.documents import get_document_model, get_folder_model

    from .base import _ProductsTestCase, skipIfCustomService
    from .. import get_service_model
    from ..models import Category, SubCategory
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


Document = get_document_model()
Service = get_service_model()


@skipIfCustomService
class ServiceTestCase(_ProductsTestCase):
    def test_createview(self):
        self.login()
        self.assertEqual(0, Service.objects.count())

        url = reverse('products__create_service')
        self.assertGET200(url)

        name = 'Eva washing'
        description = 'Your Eva is washed by pretty girls'
        reference = '42'
        cat = Category.objects.all()[0]
        sub_cat = SubCategory.objects.filter(category=cat)[0]
        unit = 'A wash'
        unit_price = '1.23'
        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         name,
                                          'reference':    reference,
                                          'description':  description,
                                          'unit':         unit,
                                          'unit_price':   unit_price,
                                          'sub_category': self._cat_field(cat, sub_cat),
                                         }
                                   )
        self.assertNoFormError(response)

        services = Service.objects.all()
        self.assertEqual(1, len(services))

        service = services[0]
        self.assertEqual(name,                service.name)
        self.assertEqual(reference,           service.reference)
        self.assertEqual(description,         service.description)
        self.assertEqual(unit,                service.unit)
        self.assertEqual(Decimal(unit_price), service.unit_price)
        self.assertEqual(cat,                 service.category)
        self.assertEqual(sub_cat,             service.sub_category)

        self.assertRedirects(response, service.get_absolute_url())

    def test_editview(self):
        user = self.login()

        name = 'Eva washing'
        sub_cat = SubCategory.objects.all()[0]
        cat = sub_cat.category
        service = Service.objects.create(user=user, name=name, description='Blabla',
                                         unit_price=Decimal('1.23'), reference='42',
                                         category=cat, sub_category=sub_cat, unit='A wash',
                                        )

        url = service.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        unit_price = '4.53'
        response = self.client.post(url, follow=True,
                                    data={'user':         user.pk,
                                          'name':         name,
                                          'reference':    service.reference,
                                          'description':  service.description,
                                          'unit_price':   unit_price,
                                          'sub_category': self._cat_field(service.category,
                                                                          service.sub_category,
                                                                         ),
                                          'unit':         service.unit,
                                         }
                                   )
        self.assertNoFormError(response)

        service = self.refresh(service)
        self.assertEqual(name,                service.name)
        self.assertEqual(Decimal(unit_price), service.unit_price)

    def test_listview(self):
        user = self.login()

        cat = Category.objects.all()[0]
        create_serv = partial(Service.objects.create, user=user, unit='unit',
                              category=cat, sub_category=SubCategory.objects.all()[0],
                             )
        services = [create_serv(name='Eva00', description='description#1',
                                unit_price=Decimal('1.23'), reference='42',
                               ),
                    create_serv(name='Eva01', description='description#2',
                                unit_price=Decimal('6.58'), reference='43',
                               ),
                   ]

        response = self.assertGET200(Service.get_lv_absolute_url())

        with self.assertNoException():
            services_page = response.context['entities']

        self.assertEqual(2, services_page.paginator.count)
        self.assertEqual(set(services), set(services_page.object_list))

    def _build_service_cat_subcat(self):
        cat = Category.objects.create(name='Mecha', description='Mechanical devices')
        sub_cat = SubCategory.objects.create(name='Eva', description='Fake gods', category=cat)
        service = Service.objects.create(user=self.user, name='Eva00', description='description#1',
                                         unit_price=Decimal('1.23'), reference='42',
                                         category=cat, sub_category=sub_cat, unit='unit'
                                        )
        return service, cat, sub_cat

    def test_delete_subcategory(self):
        self.login()

        service, cat, sub_cat = self._build_service_cat_subcat()

        self.assertPOST404(reverse('creme_config__delete_instance', args=('products', 'subcategory')),
                           data={'id': sub_cat.pk}
                          )
        self.get_object_or_fail(SubCategory, pk=sub_cat.pk)

        service = self.assertStillExists(service)
        self.assertEqual(sub_cat, service.sub_category)

    def test_delete_category(self):
        self.login()

        service, cat, sub_cat = self._build_service_cat_subcat()

        self.assertPOST404(reverse('creme_config__delete_instance', args=('products', 'category')),
                           data={'id': cat.pk}
                          )
        self.get_object_or_fail(SubCategory, pk=sub_cat.pk)
        self.get_object_or_fail(Category, pk=cat.pk)

        service = self.assertStillExists(service)
        self.assertEqual(sub_cat, service.sub_category)
        self.assertEqual(cat,     service.category)

    def test_add_images(self):
        user = self.login_as_basic_user(Service)

        create_image = partial(self._create_image, user=user,
                               folder=get_folder_model().objects.create(user=user, title=_('My Images')),
                              )
        img_1 = create_image(ident=1)
        img_2 = create_image(ident=2)
        img_3 = create_image(ident=3)
        img_4 = create_image(ident=4, user=self.other_user)
        self.assertTrue(user.has_perm_to_link(img_1))
        self.assertFalse(user.has_perm_to_link(img_4))

        sub_cat = SubCategory.objects.all()[0]
        service = Service.objects.create(user=user, name='Eva00', description='A fake god',
                                         unit_price=Decimal('1.23'),
                                         category=sub_cat.category,
                                         sub_category=sub_cat,
                                        )
        service.images.set([img_3])

        url = reverse('products__add_images_to_service', args=(service.id,))
        self.assertGET200(url)

        def post(*images):
            return self.client.post(url, follow=True,
                                    data={'images': '[%s]' % ','.join(str(img.id) for img in images)}
                                   )

        response = post(img_1, img_4)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'images', _(u'Some entities are not linkable: %s') % img_4)

        response = post(img_1, img_2)
        self.assertNoFormError(response)
        self.assertEqual({img_1, img_2, img_3}, set(service.images.all()))

    def test_remove_image(self):
        user = self.login()

        create_image = self._create_image
        img_1 = create_image(ident=1, user=user)
        img_2 = create_image(ident=2, user=user)

        sub_cat = SubCategory.objects.all()[0]
        service = Service.objects.create(user=user, name='Eva00', description='A fake god',
                                         unit_price=Decimal('1.23'),
                                         category=sub_cat.category,
                                         sub_category=sub_cat,
                                        )
        service.images.set([img_1, img_2])

        url = reverse('products__remove_image', args=(service.id,))
        data = {'id': img_1.id}
        self.assertGET404(url, data=data)

        self.assertPOST200(url, data=data, follow=True)
        self.assertEqual([img_2], list(service.images.all()))

    def test_csv_import(self):
        "Categories in CSV ; creation of Category/SubCategory"
        user = self.login()
        count = Service.objects.count()

        cat1 = Category.objects.create(name='(Test) Shipping')
        sub_cat11 = SubCategory.objects.create(name='Air shipping', category=cat1)

        cat2 = Category.objects.create(name='(Test) Cooking')
        sub_cat21 = SubCategory.objects.create(name='Cakes', category=cat2)
        sub_cat22_name = 'Vegetables'

        cat3_name = 'Books'
        sub_cat31_name = 'Sci-Fi'

        names = ['Service %2i' % i for i in xrange(1, 5)]

        lines = [(names[0], '', ''),
                 (names[1], cat2.name, sub_cat21.name),
                 (names[2], cat2.name, sub_cat22_name),
                 (names[3], cat3_name, sub_cat31_name),
                ]

        doc = self._build_csv_doc(lines)
        url = self._build_import_url(Service)
        self.assertGET200(url)

        description = 'Service imported from CSV'
        price = '39'
        reference = '489'
        response = self.client.post(url, follow=True,
                                    data={'step': 1,
                                          'document': doc.id,
                                          # has_header
                                          'user': user.id,

                                          'name_colselect': 1,

                                          'description_colselect': 0,
                                          'description_defval': description,

                                          'unit_price_colselect': 0,
                                          'unit_price_defval': price,

                                          'reference_colselect': 0,
                                          'reference_defval': reference,

                                          'categories_cat_colselect': 2,
                                          'categories_subcat_colselect': 3,
                                          'categories_subcat_defval': sub_cat11.pk,
                                          'categories_create': 'on',  # <==

                                          'unit_colselect': 0,
                                          'quantity_per_unit_colselect': 0,
                                          'countable_colselect': 0,
                                          'web_site_colselect': 0,

                                          # 'property_types',
                                          # 'fixed_relations',
                                          # 'dyn_relations',
                                         }
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(count + len(lines), Service.objects.count())

        def get_service(i):
            service = self.get_object_or_fail(Service, name=names[i])
            self.assertEqual(description, service.description)
            self.assertEqual(Decimal(price), service.unit_price)
            self.assertEqual(reference, service.reference)

            self.assertFalse(service.countable)
            self.assertFalse(service.web_site)

            return service

        service1 = get_service(0)
        self.assertEqual(cat1,      service1.category)
        self.assertEqual(sub_cat11, service1.sub_category)

        service2 = get_service(1)
        self.assertEqual(cat2,      service2.category)
        self.assertEqual(sub_cat21, service2.sub_category)

        service3 = get_service(2)
        self.assertEqual(cat2,           service3.category)
        self.assertEqual(sub_cat22_name, service3.sub_category.name)

        service4 = get_service(3)
        self.assertEqual(cat3_name,      service4.category.name)
        self.assertEqual(sub_cat31_name, service4.sub_category.name)

        results = self._get_job_results(job)
        self.assertEqual(len(lines), len(results))
        self._assertNoResultError(results)
