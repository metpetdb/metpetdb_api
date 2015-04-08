from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
# from django.views.generic.simple import direct_to_template
# from django.views.generic.simple import redirect_to
# from django.views.generic import TemplateView


# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

from api.resources import SampleResource, RockTypeResource, \
                               SubsampleResource, SubsampleTypeResource, \
                               ReferenceResource, ChemicalAnalysisResource, \
                               MineralResource, UserResource, RegionResource, \
                               MetamorphicGradeResource, SampleAliasResource, \
                               MetamorphicRegionResource, \
                               MineralRelationshipResource, OxideResource, \
                               ElementResource
from tastypie.api import Api

api_v1 = Api(api_name='v1')
api_v1.register(UserResource())
api_v1.register(SampleResource())
api_v1.register(SampleAliasResource())
api_v1.register(RockTypeResource())
api_v1.register(SubsampleResource())
api_v1.register(SubsampleTypeResource())
api_v1.register(ReferenceResource())
api_v1.register(ChemicalAnalysisResource())
api_v1.register(OxideResource())
api_v1.register(ElementResource())
api_v1.register(MineralResource())
api_v1.register(RegionResource())
api_v1.register(MetamorphicGradeResource())
api_v1.register(MetamorphicRegionResource())
api_v1.register(MineralRelationshipResource())

urlpatterns = patterns('',
  url(r'^api/', include(api_v1.urls)),

  url(r'^register/$', 'api.views.register'),
  url(r'^authenticate/$', 'api.views.authenticate', name="authenticate"),
  url(r'^reset-password/$', 'api.views.reset_password', name="reset_password"),
  url(r'^reset-password/(?P<token>[^/]+)/$', 'api.views.reset_password', name="reset_password"),

  url(r'^confirm/([a-zA-Z0-9]*)/$', 'api.views.confirm'),

  url(r'^request_contributor_access/$',
      'api.views.request_contributor_access'),
  url(r'^grant_contributor_access/([a-zA-Z0-9]*)/$',
      'api.views.grant_contributor_access'),

  url(r'^get-chem-analyses-given-sample-filters/$', 'api.views.chem_analyses_given_sample_filters'),
  # url(r'^chemical_analysis/(\d+)/$', 'webservices.views.chemical_analysis',
  #                                     name='chemical_analysis'),

  # url(r'^api/metpetdb/$','webservices.views.metpetdb'),

  # url(r'^webservices/samples$', 'webservices.views.samples'),
  # url(r'^webservices/chemicalanalyses$', 'webservices.views.chemical_analyses'),

  # Uncomment the admin/doc line below to enable admin documentation:
  # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

  # Uncomment the next line to enable the admin:
  # url(r'^admin/', include(admin.site.urls)),
)
urlpatterns+=staticfiles_urlpatterns()

