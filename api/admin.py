from django.contrib import admin
from . import models
from django.contrib.gis.admin import GeoModelAdmin
from django import forms

def clean_version_closure(model):
    def clean_version(self):
        try:
            prev = model.objects.select_for_update().get(pk=self.instance.pk)
        except model.DoesNotExist:
            return 0
        if self.cleaned_data['version'] == prev.version:
            return prev.version + 1
        else:
            raise forms.ValidationError("Edit conflict detected (someone"+
                                        " changed the object since you loaded"+
                                        " the page; you'll probably have to"+
                                        " start over)")
    return clean_version


class SampleAdminForm(forms.ModelForm):
    clean_version = clean_version_closure(models.Sample)
    class Meta:
        model = models.Sample

class SubsampleAdminForm(forms.ModelForm):
    clean_version = clean_version_closure(models.Subsample)
    class Meta:
        model = models.Subsample

class ChemicalAnalysisAdminForm(forms.ModelForm):
    clean_version = clean_version_closure(models.ChemicalAnalysis)
    class Meta:
        model = models.ChemicalAnalysis

class UserAdminForm(forms.ModelForm):
    clean_version = clean_version_closure(models.User)
    class Meta:
        model = models.User

def is_public(obj):
    return obj.public_data == u'Y'

is_public.boolean = True
is_public.admin_order_field = 'public_data'

class SampleAdmin(GeoModelAdmin):
    form = SampleAdminForm
    def latitude(self, sample):
        return sample.location.x
    def longitude(self, sample):
        return sample.location.y
    list_display = ('id', 'number', 'rock_type', 'owner',
                    is_public, 'latitude', 'longitude')
    list_filter = ('public_data', 'collection_date', 'rock_type', 'owner',
                   'collector', 'regions')

class SubsampleAdmin(admin.ModelAdmin):
    form = SubsampleAdminForm
    list_display = ('subsample_id', 'name', 'sample', is_public, 'user',
                    'subsample_type')
    list_filter = ('public_data', 'user', 'subsample_type')

class ChemicalAnalysisAdmin(admin.ModelAdmin):
    form = ChemicalAnalysisAdminForm
    list_display = ('chemical_analysis_id', 'subsample', is_public, 'user')
    list_filter = ('public_data', 'analysis_method', 'analysis_date',
                   'mineral', 'user')

class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm
    exclude = ('password',)
    list_display = ('name', 'email', 'is_enabled', 'institution')
    def is_enabled(self, user):
        return user.enabled == u'Y'
    is_enabled.boolean = True
    is_enabled.admin_order_field = 'enabled'

admin.site.register(models.Sample, SampleAdmin)
admin.site.register(models.RockType)
admin.site.register(models.Subsample, SubsampleAdmin)
admin.site.register(models.SubsampleType)
admin.site.register(models.ChemicalAnalysis, ChemicalAnalysisAdmin)
admin.site.register(models.Mineral)
admin.site.register(models.User, UserAdmin)
