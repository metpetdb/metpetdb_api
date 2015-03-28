from api.models import GroupAccess
from api.models import User, Sample, Subsample, SubsampleType, \
                            RockType

from django.contrib.auth.models import User as AuthUser
from tastypie.test import ResourceTestCase
from tastypie.models import ApiKey
import nose.tools as nt
from .base_class import TestSetUp, client

subsample_data = {
    'user': '/api/v1/user/1/',
    'public_data': 'Y',
    'subsample_type':'/api/v1/subsample_type/1/',
    'grid_id': 1,
    'version': 1,
    'name':'Subby',
    'sample': '/api/v1/sample/1/'
}

class SubSampleReadResourceTest(TestSetUp):
    fixtures = ['users.json', 'rock_types.json',
                'subsample_types.json']

    def setUp(self):
        super(SubSampleReadResourceTest, self).setUp()
        rock_type = RockType.objects.get(pk=16)
        subsample_type = SubsampleType.objects.get(pk=2)
        sample = Sample.objects.create(user = self.user,
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
                                 user=self.user,
                                 grid_id=1,
                                 name="Public Subsample",
                                 subsample_type=subsample_type,
                                 sample=sample
        )
        Subsample.objects.create(version=1,
                                 public_data='N',
                                 user=self.user,
                                 grid_id=1,
                                 name="Private Subsample",
                                 subsample_type=subsample_type,
                                 sample=sample
        )

    def test_finds_an_existing_subsample(self):
        credentials = self.get_credentials()
        nt.assert_equal(Subsample.objects.all().count(), 2)
        resp = client.get('/api/v1/subsample/1/',
                          authentication=credentials, format='json')
        self.assertHttpOK(resp)

    def test_does_not_find_a_non_existent_subsample(self):
        credentials = self.get_credentials()
        resp = client.get('/api/v1/subsample/1000/',
                          authentication=credentials, format='json')
        self.assertHttpNotFound(resp)

    def test_cannot_read_a_subsample_without_an_apikey(self):
        resp = client.get('/api/v1/subsample/1/', format='json')
        self.assertHttpUnauthorized(resp)

    def test_user_can_read_unowned_public_subsample(self):
        credentials = self.get_credentials(user_id=2)
        resp = client.get('/api/v1/subsample/1/',
                          authentication=credentials,
                          format='json')
        self.assertHttpOK(resp)

    def test_user_cannot_read_unowned_private_subsample(self):
        credentials = self.get_credentials(user_id=2)
        resp = client.get('/api/v1/subsample/2/',
                          authentication=credentials,
                          format='json')
        self.assertHttpUnauthorized(resp)

class SubSampleResourceCreateTest(TestSetUp):
    fixtures = ['users.json', 'rock_types.json',
     'subsample_types.json']

    def setUp(self):
        super(SubSampleResourceCreateTest, self).setUp()
        rock_type = RockType.objects.get(pk=16)
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

    def test_authorized_user_can_create_a_subsample(self):
        nt.assert_equal(Subsample.objects.count(), 0)
        credentials = self.get_credentials()
        resp = client.post('/api/v1/subsample/', data=subsample_data,
                           authentication=credentials, format='json')
        self.assertHttpCreated(resp)
        nt.assert_equal(Sample.objects.count(), 1)

    def test_unauthorized_user_cannot_create_a_subsample(self):
        nt.assert_equal(Subsample.objects.count(), 0)
        credentials = self.get_credentials(user_id=3)
        resp = client.post('/api/v1/subsample/', data=subsample_data,
                           authentication=credentials, format='json')
        self.assertHttpUnauthorized(resp)
        nt.assert_equal(Subsample.objects.count(), 0)

class SubsampleResourceUpdateDeleteTest(TestSetUp):
    fixtures = ['users.json', 'rock_types.json',
                'subsample_types.json']

    def setUp(self):
        super(SubsampleResourceUpdateDeleteTest, self).setUp()
        rock_type = RockType.objects.get(pk=16)
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
        credentials = self.get_credentials()
        resp = client.post('/api/v1/subsample/', data=subsample_data,
                           authentication=credentials, format='json')
        self.assertHttpCreated(resp)

    def test_user_can_delete_own_subsample(self):
        credentials = self.get_credentials()
        nt.assert_equal(Subsample.objects.count(), 1)
        nt.assert_equal(GroupAccess.objects.count(), 4)
        resp = client.delete('/api/v1/subsample/1/',
                             authentication=credentials, format='json')
        self.assertHttpAccepted(resp)
        nt.assert_equal(Subsample.objects.count(), 0)
        nt.assert_equal(GroupAccess.objects.count(), 2)

    def test_user_cannot_delete_unowned_subsample(self):
        credentials = self.get_credentials(user_id=2)
        nt.assert_equal(Subsample.objects.count(), 1)
        resp = client.delete('/api/v1/subsample/1/',
                             authentication=credentials, format='json')
        self.assertHttpUnauthorized(resp)
        nt.assert_equal(Subsample.objects.count(), 1)

    def test_user_can_update_own_subsample(self):
        credentials = self.get_credentials()
        nt.assert_equal(Subsample.objects.count(), 1)
        subsample = self.deserialize(client.get('/api/v1/subsample/1/',
                                                authentication=credentials,
                                                format='json'))
        nt.assert_equal("Subby", subsample['name'])
        subsample['name'] = "Subby Wilson"

        resp = client.put('/api/v1/subsample/1/', data=subsample,
                           authentication=credentials, format='json')

        self.assertHttpOK(resp)
        subsample = self.deserialize(client.get('/api/v1/subsample/1/',
                                                authentication=credentials,
                                                format='json'))
        nt.assert_equal("Subby Wilson", subsample['name'])
        nt.assert_equal(Subsample.objects.count(), 1)

    def test_user_cannot_update_unowned_subsample(self):
        credentials = self.get_credentials()
        subsample = self.deserialize(client.get('/api/v1/subsample/1/',
                                                authentication=credentials,
                                                format='json'))
        nt.assert_equal("Subby", subsample['name'])
        subsample['name'] = "Updated by a test case"

        credentials = self.get_credentials(user_id = 2)
        resp = client.put('/api/v1/subsample/1/', data=subsample,
                           authentication=credentials, format='json')
        self.assertHttpUnauthorized(resp)
