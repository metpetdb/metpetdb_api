from api.models import GroupAccess
from api.models import User, Sample, RockType
from django.contrib.auth.models import User as AuthUser
from tastypie.test import ResourceTestCase
import nose.tools as nt
from .base_class import TestSetUp, client


valid_post_data = {
    'user': '/api/v1/user/1/',
    'sesar_number': '14342',
    'public_data': 'Y',
    'date_precision': '1',
    'number': 'NL-67:2005-06290',
    'rock_type': '/api/v1/rock_type/16/',
    'regions': ['Pune', 'Mumbai', 'Pune', 'Hyderabad'],
    'references': ['2004-061314',
                   '2004-065494',
                   '2004-065494'],
    'metamorphic_grades': ['/api/v1/metamorphic_grade/1/',
                           '/api/v1/metamorphic_grade/2/',
                           '/api/v1/metamorphic_grade/3/',
                           '/api/v1/metamorphic_grade/4/'],
    'metamorphic_regions': ['/api/v1/metamorphic_region/427/',
                           '/api/v1/metamorphic_region/428/',
                           '/api/v1/metamorphic_region/429/',
                           '/api/v1/metamorphic_region/430/'],
    'minerals': ['/api/v1/mineral/1/',
                 '/api/v1/mineral/2/',
                 '/api/v1/mineral/3/',
                 '/api/v1/mineral/4/'],
    'description': 'Created by a test case',
    'location_error': '2000',
    'country': 'Brazil',
    'location_text': 'amfadf',
    'location': 'POINT (-49.3400382995604971 -16.5187797546387003)'
}

class SampleResourceCreateTest(TestSetUp):
    fixtures = ['users.json', 'regions.json',
                'references.json', 'metamorphic_grades.json', 'minerals.json',
                'rock_types.json', 'metamorphic_regions.json']

    def test_authorized_user_can_create_a_sample(self):
        nt.assert_equal(Sample.objects.count(), 0)
        credentials = self.get_credentials()
        resp = client.post('/api/v1/sample/', data = valid_post_data,
                           authentication = credentials, format = 'json')
        self.assertHttpCreated(resp)

        nt.assert_equal(Sample.objects.count(), 1)

        sample = Sample.objects.get(pk=1)
        nt.assert_equal(sample.metamorphic_regions.all().count(), 4)
        nt.assert_equal(sample.metamorphic_grades.all().count(), 4)
        nt.assert_equal(sample.references.all().count(), 2)
        nt.assert_equal(sample.minerals.all().count(), 4)
        nt.assert_equal(sample.regions.all().count(), 3)

    def test_unauthorized_user_cannot_create_a_sample(self):
        nt.assert_equal(Sample.objects.count(), 0)
        credentials = self.get_credentials(user_id = 3)
        resp = client.post('/api/v1/sample/', data = valid_post_data,
                           authentication = credentials, format = 'json')
        self.assertHttpUnauthorized(resp)
        nt.assert_equal(Sample.objects.count(), 0)


class SampleResourceReadUpdateDeleteTest(TestSetUp):
    fixtures = ['users.json', 'rock_types.json']

    def setUp(self):
        super(SampleResourceReadUpdateDeleteTest, self).setUp()
        rock_type = RockType.objects.get(pk = 16)
        Sample.objects.create(user = self.user,
                              version = 1,
                              sesar_number = 14342,
                              public_data = 'Y',
                              date_precision = '1',
                              number = 'NL-67:2005-06290',
                              rock_type = rock_type,
                              description = 'Created by a test case',
                              location_error = 2000,
                              country = 'Brazil',
                              location_text = 'anfdaf',
                              location = 'POINT(-49.3400382995604971 \
                                                -16.5187797546387003)')
        Sample.objects.create(user = self.user,
                              version = 1,
                              sesar_number = 14343,
                              public_data = 'N',
                              date_precision = '1',
                              number = 'NL-67:2005-06291',
                              rock_type = rock_type,
                              description = 'Created by a test case',
                              location_error = 2000,
                              country = 'Brazil',
                              location_text = 'anfdaf',
                              location = 'POINT(-49.3400382995604971 \
                                                -16.5187797546387003)')


    def test_finds_an_existing_sample(self):
        credentials = self.get_credentials()
        resp = client.get('/api/v1/sample/1/',
                          authentication = credentials, format = 'json')
        self.assertHttpOK(resp)

    def test_user_can_read_unowned_public_sample(self):
        credentials = self.get_credentials(user_id=2)
        resp = client.get('/api/v1/sample/1/',
                          authentication = credentials, format = 'json')
        self.assertHttpOK(resp)

    def test_does_not_find_a_non_existent_sample(self):
        credentials = self.get_credentials()
        resp = client.get('/api/v1/sample/1000/',
                          authentication = credentials, format = 'json')
        self.assertHttpNotFound(resp)

    def test_can_read_a_public_sample_without_an_apikey(self):
        resp = client.get('/api/v1/sample/1/', format = 'json')
        self.assertHttpOK(resp)

    def test_cannot_read_a_private_sample_without_an_apikey(self):
        resp = client.get('/api/v1/sample/2/', format = 'json')
        self.assertHttpUnauthorized(resp)

    def test_user_can_delete_own_sample(self):
        credentials = self.get_credentials()
        nt.assert_equal(Sample.objects.count(), 2)
        nt.assert_equal(GroupAccess.objects.count(), 3)
        resp = client.delete('/api/v1/sample/1/',
                             authentication = credentials, format = 'json')
        self.assertHttpAccepted(resp)
        nt.assert_equal(Sample.objects.count(), 1)
        nt.assert_equal(GroupAccess.objects.count(), 1)

    def test_user_cannot_delete_unowned_sample(self):
        credentials = self.get_credentials(user_id = 2)
        nt.assert_equal(Sample.objects.count(), 2)
        resp = client.delete('/api/v1/sample/1/',
                             authentication = credentials, format = 'json')
        self.assertHttpUnauthorized(resp)
        nt.assert_equal(Sample.objects.count(), 2)


    def test_user_can_update_own_sample(self):
        credentials = self.get_credentials()
        nt.assert_equal(Sample.objects.count(), 2)
        sample = self.deserialize(client.get('/api/v1/sample/1/',
                                  authentication = credentials, format='json'))
        nt.assert_equal("Created by a test case", sample['description'])
        sample['description'] = "Updated by a test case"

        resp = client.put('/api/v1/sample/1/', data=sample,
                           authentication=credentials, format='json')

        self.assertHttpOK(resp)
        sample = self.deserialize(client.get('/api/v1/sample/1/',
                                  authentication = credentials, format='json'))
        nt.assert_equal("Updated by a test case", sample['description'])
        nt.assert_equal(Sample.objects.count(), 2)


    def test_user_cannot_update_unowned_sample(self):
        credentials = self.get_credentials()
        sample = self.deserialize(client.get('/api/v1/sample/1/',
                                  authentication = credentials, format='json'))
        nt.assert_equal("Created by a test case", sample['description'])
        sample['description'] = "Updated by a test case"

        credentials = self.get_credentials(user_id = 2)
        resp = client.put('/api/v1/sample/1/', data=sample,
                           authentication=credentials, format='json')

        self.assertHttpUnauthorized(resp)

