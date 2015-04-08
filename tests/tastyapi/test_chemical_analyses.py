from api.models import User, Sample, Subsample, SubsampleType, \
                            RockType, ChemicalAnalyses, Subsample, Reference, \
                            Mineral, GroupAccess

from django.contrib.auth.models import User as AuthUser
from tastypie.test import ResourceTestCase
from tastypie.models import ApiKey
import nose.tools as nt
from .base_class import TestSetUp, client


class ChemAnalysesTestSetUp(TestSetUp):
    fixtures = ['users.json', 'regions.json',
                'references.json', 'minerals.json', 'rock_types.json',
                'subsample_types.json']

    def setUp(self):
        super(ChemAnalysesTestSetUp, self).setUp()
        rock_type = RockType.objects.get(pk = 16)
        user = User.objects.get(pk=1)
        subsample_type = SubsampleType.objects.get(pk=2)
        sample = Sample.objects.create(user=self.user,
                                       version=1,
                                       sesar_number=14342,
                                       public_data='Y',
                                       date_precision='1',
                                       number='NL-67:2005-06290',
                                       rock_type=rock_type,
                                       description='Created by a test case',
                                       location_error=2000,
                                       country='Brazil',
                                       location_text='anfdaf',
                                       location='POINT(-49.3400382995604971 \
                                                       -16.5187797546387003)')
        Subsample.objects.create(version=1,
                                 public_data='Y',
                                 sample=sample,
                                 user=user,
                                 grid_id=10,
                                 name='Subsample 1',
                                 subsample_type=subsample_type)

class ChemAnalysesCreateTest(ChemAnalysesTestSetUp):

    def test_authorized_user_can_create_a_chemical_analysis(self):
        credentials = self.get_credentials()

        valid_post_data = {
            'user': '/api/v1/user/1/',
            'reference': '/api/v1/reference/2/',
            'subsample': '/api/v1/subsample/1/',
            'mineral': '/api/v1/mineral/5/',
            'public_data': 'Y',
            'large_rock': 'Y',
            'spot_id': '11',
        }

        resp = client.post('/api/v1/chemical_analysis/',
                           data=valid_post_data,
                           authentication=credentials,
                           format='json')
        self.assertHttpCreated(resp)
        nt.assert_equal(ChemicalAnalyses.objects.count(), 1)

        chem_a = ChemicalAnalyses.objects.get(pk=1)
        nt.assert_equal(chem_a.user, User.objects.get(pk=1))
        nt.assert_equal(chem_a.reference, Reference.objects.get(pk=2))
        nt.assert_equal(chem_a.mineral, Mineral.objects.get(pk=5))
        nt.assert_equal(chem_a.subsample, Subsample.objects.get(pk=1))

class ChemAnalysesReadUpdateDeleteTest(ChemAnalysesTestSetUp):
    def setUp(self):
        super(ChemAnalysesReadUpdateDeleteTest, self).setUp()
        rock_type = RockType.objects.get(pk = 16)
        user = User.objects.get(pk=1)
        subsample_type = SubsampleType.objects.get(pk=2)
        subsample = Subsample.objects.get(pk=1)
        # Public chemical analysis
        ChemicalAnalyses.objects.create(version=1,
                                        subsample=subsample,
                                        user=user,
                                        large_rock='Y',
                                        total=1232.10,
                                        spot_id=18,
                                        public_data='Y')

        # Private chemical analysis
        ChemicalAnalyses.objects.create(version=1,
                                        subsample=subsample,
                                        user=user,
                                        large_rock='Y',
                                        total=1232.10,
                                        spot_id=20,
                                        public_data='N')

    def test_authorized_user_can_read_own_chem_analysis(self):
        credentials = self.get_credentials()
        resp = client.get('/api/v1/chemical_analysis/1/',
                          authentication=credentials,
                          format='json')
        self.assertHttpOK(resp)

    def test_user_can_read_unowned_public_chemical_analysis(self):
        credentials = self.get_credentials(user_id=2)
        resp = client.get('/api/v1/chemical_analysis/1/',
                          authentication=credentials,
                          format='json')
        self.assertHttpOK(resp)

    def test_user_can_read_public_chemical_analysis_without_an_apikey(self):
        credentials = self.get_credentials(user_id=2)
        resp = client.get('/api/v1/chemical_analysis/1/',
                          format='json')
        self.assertHttpOK(resp)

    def test_user_cannot_read_private_chemical_analysis_without_an_apikey(self):
        credentials = self.get_credentials(user_id=2)
        resp = client.get('/api/v1/chemical_analysis/2/',
                          format='json')
        self.assertHttpUnauthorized(resp)

    def test_user_cannot_read_unowned_private_chemical_analysis(self):
        credentials = self.get_credentials(user_id=2)
        resp = client.get('/api/v1/chemical_analysis/2/',
                          authentication=credentials,
                          format='json')
        self.assertHttpUnauthorized(resp)

    def test_user_can_update_own_chemical_analysis(self):
        credentials = self.get_credentials()
        chem_a = self.deserialize(client.get(
                                           '/api/v1/chemical_analysis/1/',
                                           authentication=credentials,
                                           format='json'))
        nt.assert_equal(chem_a['spot_id'], '18')
        chem_a['spot_id'] = 25
        chem_a['mineral'] = '/api/v1/mineral/8/'
        resp = client.put('/api/v1/chemical_analysis/1/',
                          data=chem_a,
                          authentication=credentials,
                          format='json')

        chem_a = ChemicalAnalyses.objects.get(pk=1)
        self.assertHttpOK(resp)
        nt.assert_equal(chem_a.spot_id, 25L)
        nt.assert_equal(chem_a.mineral, Mineral.objects.get(pk=8))

    def test_user_can_delete_own_chemical_analysis(self):
        credentials = self.get_credentials()
        nt.assert_equal(ChemicalAnalyses.objects.count(), 2)
        nt.assert_equal(GroupAccess.objects.count(), 7)
        resp = client.delete('/api/v1/chemical_analysis/1/',
                              authentication=credentials,
                              format='json')
        self.assertHttpAccepted(resp)
        nt.assert_equal(ChemicalAnalyses.objects.count(), 1)
        nt.assert_equal(GroupAccess.objects.count(), 5)

    def test_user_cannot_delete_unowned_chemical_analysis(self):
        credentials = self.get_credentials(user_id=2)
        nt.assert_equal(ChemicalAnalyses.objects.count(), 2)
        resp = client.delete('/api/v1/chemical_analysis/1/',
                              authentication=credentials,
                              format='json')
        self.assertHttpUnauthorized(resp)
        nt.assert_equal(ChemicalAnalyses.objects.count(), 2)
