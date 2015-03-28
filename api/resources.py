from django.db import transaction, IntegrityError
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from django.contrib.gis.geos.polygon import Polygon
from django.core.exceptions import ObjectDoesNotExist
from tastypie.resources import ModelResource
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie import fields
from tastypie.validation import Validation
from tastypie.authorization import Authorization
from tastypie.authentication import ApiKeyAuthentication
from tastypie.exceptions import Unauthorized, InvalidFilterError, ImmediateHttpResponse

from .models import User, Sample, MetamorphicGrade, MetamorphicRegion, Region,\
                    RockType, Subsample, SubsampleType, Mineral, Reference, \
                    ChemicalAnalyses, SampleRegion, SampleReference, \
                    SampleMineral, SampleMetamorphicGrade, SampleAliase, \
                    SampleMetamorphicRegion, Oxide, ChemicalAnalysisOxide, \
                    MineralRelationship, Element

from .specified_fields import SpecifiedFields
from . import auth
from . import utils
import logging

logging.basicConfig()
logger = logging.getLogger(__name__)

PREFIX_STRING = '_extra_filter_prefixes'

CLASS_MAPPING = {'regions': SampleRegion,
                 'region_class': Region,
                 'references': SampleReference,
                 'reference_class': Reference,
                 'minerals': SampleMineral,
                 'metamorphic_grades': SampleMetamorphicGrade,
                 'metamorphic_regions': SampleMetamorphicRegion}


class BaseResource(SpecifiedFields):
    @transaction.commit_manually
    def dispatch(self, *args, **kwargs):
        # Transaction begins immediately, before we get here
        try:
            response = super(SpecifiedFields, self).dispatch(*args, **kwargs)
            keep = (200 <= response.status_code < 400)
        except:
            transaction.rollback()
            raise
        else:
            if keep:
                transaction.commit()
            else:
                transaction.rollback()
            return response


class VersionedResource(BaseResource):
    def hydrate_version(self, bundle):
        if 'version' in bundle.data:
            bundle.data['version'] += 1
        else:
            bundle.data['version'] = 1
        return bundle


class VersionValidation(Validation):
    def __init__(self, queryset, pk_field):
        self.queryset = queryset
        self.pk_field = pk_field
    def is_valid(self, bundle, request=None):
        if not bundle.data:
            return {'__all__': 'No data.'}
        if self.pk_field in bundle.data:
            try:
                # Verify if using select_for_update() is important below
                previous = (self.queryset.
                            get(pk=bundle.data[self.pk_field]))
            except ObjectDoesNotExist:
                previous = None
        else:
            previous = None
        if previous is None:
            if request is not None and request.method == 'PUT':
                return {'__all__': 'Cannot find previous version (use POST to create).'}
            elif 'version' in bundle.data and bundle.data['version'] != 0:
                # A version of 0 will be incremented to 1 during hydration
                # FIXME: Is this needed? Version is already set to 1 by the
                # time we come here.
                # return {'version': 'This should be 0 or absent.'}
                pass
        else:
            if request is not None and request.method == 'POST':
                return {'__all__': 'That object already exists (use PUT to update).'}
            elif 'version' not in bundle.data:
                return {'__all__': 'Data corrupted (version number missing).'}
            elif bundle.data['version'] != previous.version + 1:
                return {'version': 'Edit conflict (object has changed since last GET).'}
        return {}

def _filter_by_permission_closure(permission_lambda):
    """Simple closure to deduplicate code."""
    def closure(self, object_list, bundle):
        """Filter object_list for objects to which we have the given permission."""
        permission = permission_lambda(self)
        result = []
        for item in object_list:
            if bundle.request.user.has_perm(permission, bundle.obj):
                result.append(bundle.obj)
        return result
    return closure

def _check_perm_closure(permission_lambda):
    """Simple closure to deduplicate code."""
    def closure(self, object_list, bundle):
        """Check whether we have permission to access bundle.obj."""
        permission = permission_lambda(self)
        if bundle.request.user.has_perm(permission, bundle.obj):
            return True
        else:
            raise Unauthorized("User {} lacks permission {}."
                               .format(bundle.request.user, permission))
    return closure


class ObjectAuthorization(Authorization):
    """Tastypie custom Authorization class.

    Provides row-level CRUD permissions."""
    def __init__(self, app_name, model_name, *args, **kwargs):
        """Store some information which we'll need later."""
        self.read_perm = "{}.read_{}".format(app_name, model_name)
        self.add_perm = "{}.add_{}".format(app_name, model_name)
        self.change_perm = "{}.change_{}".format(app_name, model_name)
        self.del_perm = "{}.delete_{}".format(app_name, model_name)
        super(ObjectAuthorization, self).__init__(*args, **kwargs)
    def read_list(self, object_list, bundle):
        """Make a queryset of all the objects we can read."""

        # Let anonymous users access all public data
        if type(bundle.request.user) == AnonymousUser:
            filters = Q(public_data='Y')
        else:
            filters = auth.get_read_queryset(bundle.request.user)
        qs = object_list.filter(filters)
        return qs
    read_detail = _check_perm_closure(lambda self: self.read_perm)
    def create_list(self, object_list, bundle):
        """Check object_list to make sure new objects are owned by us."""
        logger.info("Received list of objects to create")
        if not bundle.request.user.has_perm(self.add_perm):
            logger.warning("User is not verified.")
            raise Unauthorized("User {} is not manually verified."
                               .format(bundle.request.user))
        result = []
        for item in object_list:
            if item.owner == bundle.request.user:
                result.append(item)
            else:
                logger.warning("User must own created object.")
        return result
    def create_detail(self, object_list, bundle):
        """Check bundle.obj to make sure it is owned by us."""
        user = bundle.request.user
        logger.info("Received single object to create")
        if bundle.obj.user.django_user == user and user.has_perm(self.add_perm):
            return True
        else:
            logger.warning("User must own created object.")
            raise Unauthorized("User must own created object.")
    update_list = _filter_by_permission_closure(lambda self: self.change_perm)
    update_detail = _check_perm_closure(lambda self: self.change_perm)
    delete_list = _filter_by_permission_closure(lambda self: self.change_perm)
    delete_detail = _check_perm_closure(lambda self: self.change_perm)


class CustomApiKeyAuth(ApiKeyAuthentication):
    """Disable API key authentication for GET requests

    Let anybody access resources with public_data == 'Y'
    """

    def is_authenticated(self, request, **kwargs):
        if request.method == 'GET':
            try:
                # If authorization header is present, authenticate the request
                if request.META['HTTP_AUTHORIZATION']:
                    return super(CustomApiKeyAuth, self).is_authenticated(
                                                            request, **kwargs)
            except KeyError:
                # else just set the current user to AnonymousUser and continue
                # handling the request
                request.user = AnonymousUser()
                return True
        else:
            return super(CustomApiKeyAuth, self).is_authenticated(request,
                         **kwargs)


class FirstOrderResource(SpecifiedFields):
    """Resource that can only be filtered with "first-order" filters.

    This prevents users from chaining filters through many relationship fields.

    It also applies read permissions to any related objects we filter by, so
    the user cannot deduce information not explicitly available to them.
    """
    def build_filters(self, filters=None):
        """Convert GET parameters into ORM filters.

        This makes a list of all filters which involve related fields and
        attaches that list to the set of ORM filters.  It will then be used
        by apply_filters to
        """
        extra_filter_prefixes = []
        if filters is None:
            filters = {}
        for filter_expr, value in filters.iterlists():
            # For each filter, break it apart by double underscores...
            filter_bits = filter_expr.split("__")
            if len(filter_bits) == 0:
                # can't happen, but fail gracefully anyway
                continue
            # get the first part of the filter
            field_name = filter_bits[0]
            if field_name not in self.fields:
                # It's not a field, abort
                continue
            # Get the field object
            field = self.fields[field_name]
            # Figure out if it's a relationship field
            try:
                is_related = field.is_related
            except AttributeError:
                is_related = False
            if is_related:
                # Field.attribute is the name of the relationship
                extra_filter_prefixes.append(field.attribute)
        result = super(FirstOrderResource, self).build_filters(filters)
        # We can't apply our restrictions at this point, and it would be
        # unwise to attach this to object-wide state since there's only one
        # instance of each resource, so attach it to the result instead.
        # XXX: There's probably a better way to do this.
        result[PREFIX_STRING] = extra_filter_prefixes
        return result
    def apply_filters(self, request, applicable_filters):
        """Applies the given filters.

        Additionally attaches read restrictions to any tables that are joined
        in.  This ensures no information is exposed to the user that they
        aren't explicitly allowed to see.
        """
        auth_read_limit = Q()
        if PREFIX_STRING in applicable_filters:
            # Extract the result we hid during build_filters()
            extra_filter_prefixes = applicable_filters[PREFIX_STRING]
            # Make sure it doesn't interfere with the ORM
            del applicable_filters[PREFIX_STRING]
            for prefix in extra_filter_prefixes:
                # Attach some read limits to the query
                if type(request.user) == AnonymousUser:
                    auth_read_limit &= Q(public_data='Y')
                else:
                    auth_read_limit &= auth.get_read_queryset(request.user, prefix)
        return self.get_object_list(request).filter(auth_read_limit,
                                                    **applicable_filters)
    def check_filtering(self, field_name, filter_type='exact', filter_bits=None):
        """Verify that filter_bits does not begin with a related field lookup.

        This allows the user to make filters that begin with a related lookup,
        but not filters that involve multiple related lookups ("second-order"
        lookups).
        """
        # We want to call the super method right before we return, so wrap it
        # in a lambda expression -- that way we know it's always called right
        result = lambda: (super(FirstOrderResource, self).
                          check_filtering(field_name, filter_type, filter_bits))
        if filter_bits and field_name in self.fields:
            # NB: filter_bits must be non-empty in addition to not being None
            # get the field object
            target_field = self.fields[field_name]
            # Figure out if it's a relationship field
            try:
                is_related = target_field.is_related
            except AttributeError:
                is_related = False
            if not is_related:
                # It isn't, so we don't have to do anything
                return result()
            # get the resource at the "other end" of this relationship
            target_resource = target_field.get_related_resource(None)
            # get the next part of the filter
            next_filter = filter_bits[0]
            if next_filter not in target_resource.fields:
                # the filter doesn't refer to a field on the resource
                return result()
            next_field = target_resource.fields[next_filter]
            try:
                is_second_order = next_field.is_related
            except AttributeError:
                is_second_order = False
            if is_second_order:
                # The filter refers to a relationship field on the resource,
                # so we need to abort since we can't handle those correctly
                raise InvalidFilterError("Second-order relationship traversal"+
                                         " is not allowed.")
        return result()
    def dehydrate(self, bundle):
        """Remove references to inaccessible objects."""
        bundle = super(FirstOrderResource, self).dehydrate(bundle)

        for field_name in bundle.data:
            # For every field
            if field_name not in self.fields:
                # Don't know what it is, abort
                continue
            # Get the corresponding field object
            target_field = self.fields[field_name]
            # Figure out whether it's a relationship field
            try:
                is_related = target_field.is_related
            except AttributeError:
                # it isn't; abort
                continue
            if not is_related:
                # it isn't; abort
                continue
            # Get the value we're providing for this field
            value = bundle.data[field_name]
            # Many-to-many fields will produce a list here, but a foreign key
            # won't
            if not isinstance(value, list):
                value = [value]
                # NB: Now value is not bundle.data[field_name], so we'll need
                # to re-unify them afterwards
            for item in value[:]:
                try:
                    # Check whether we have permission to access item
                    target_resource = target_field.get_related_resource(None)
                    target_resource.get_via_uri(item, bundle.request)
                except ImmediateHttpResponse:
                    # We don't have permission, remove it
                    value.remove(item)
                except AttributeError:
                    # ToOne field is empty; abort
                    continue
            if value is not bundle.data[field_name] and not value:
                # For ToOne fields: value was a singleton, and now it's empty,
                # so null out the corresponding entry in bundle.data
                bundle.data[field_name] = None

        return bundle


# TODO: Finalize authorization settings for the User resource
class UserResource(BaseResource):
    class Meta:
        resource_name = 'user'
        allowed_methods = ['get']
        queryset = User.objects.all()
        authorization = Authorization()
        authentication = CustomApiKeyAuth()
        filtering = {
            'email': ALL
        }
        excludes = ['password', 'confirmation_code']


class SampleResource(VersionedResource, FirstOrderResource):
    user = fields.ToOneField("tastyapi.resources.UserResource", "user", full=True)
    rock_type = fields.ToOneField("tastyapi.resources.RockTypeResource",
                                  "rock_type", full=True)
    minerals = fields.ToManyField("tastyapi.resources.MineralResource",
                                  "minerals", full=True)
    metamorphic_grades = fields.ToManyField(
                                "tastyapi.resources.MetamorphicGradeResource",
                                "metamorphic_grades", full=True)
    metamorphic_regions = fields.ToManyField(
                                "tastyapi.resources.MetamorphicRegionResource",
                                "metamorphic_regions", full=True)
    regions = fields.ToManyField("tastyapi.resources.RegionResource",
                                 "regions", null=True, full=True)
    references = fields.ToManyField("tastyapi.resources.ReferenceResource",
                                    "references", null=True, full=True)

    class Meta:
        queryset = Sample.objects.all().distinct('sample_id')
        allowed_methods = ['get', 'post', 'put', 'delete']
        always_return_data = True
        authentication = CustomApiKeyAuth()
        authorization = ObjectAuthorization('tastyapi', 'sample')
        ordering = ['collector']
        excludes = ['user']
        filtering = {
                'version': ALL,
                'number': ALL,
                'public_data': ALL,
                'collection_date': ALL,
                'rock_type': ALL_WITH_RELATIONS,
                'regions': ALL_WITH_RELATIONS,
                'minerals': ALL_WITH_RELATIONS,
                'metamorphic_grades': ALL_WITH_RELATIONS,
                'metamorphic_regions': ALL_WITH_RELATIONS,
                'collector': ALL,
                'number': ALL,
                'references': ALL_WITH_RELATIONS,
                'sample_id': ALL,
                'user': ALL,
                'country': ALL,
                'location': ALL
                }
        validation = VersionValidation(queryset, 'sample_id')

    def obj_create(self, bundle, **kwargs):
        """ Save free-text fields: regions and references.

        Regions and references are free-text fields so when you get either of
        these in the request, check if a particular region/reference exists in
        the database, create a new object if it doesn't exist yet, and then
        create a record in the intermediate "through" table.
        """

        """ Remove free-text fields "regions" and "references" from the bundle
        and save them for later, so that Tastypie doesn't try to save them
        on its own and fail
        """
        free_text_fields = {'regions': bundle.data.pop('regions'),
                           'references': bundle.data.pop('references')}
        super(SampleResource, self).obj_create(bundle, **kwargs)
        sample = Sample.objects.get(pk=bundle.obj.sample_id)

        for field_name, entries in free_text_fields.iteritems():
            for entry in entries:
                obj_class = CLASS_MAPPING[field_name[:-1] + "_class"]

                try:
                    obj = obj_class.objects.get(name=entry)
                except ObjectDoesNotExist:
                    id = utils.get_next_id(CLASS_MAPPING[field_name[:-1] +
                                                                     "_class"])
                    obj_args = {field_name[:-1] + "_id": id, 'name': entry}
                    obj = obj_class.objects.create( **obj_args )

                obj_args = {'id': utils.get_next_id(CLASS_MAPPING[field_name]),
                            'sample': sample,
                            field_name[:-1]: obj}

                try: CLASS_MAPPING[field_name].objects.get_or_create(**obj_args)
                except IntegrityError: continue

    def save_m2m(self, bundle):
        for field_name, field_object in self.fields.iteritems():
            if not getattr(field_object, 'is_m2m', False):
                continue

            if not field_object.attribute:
                continue

            if field_object.readonly:
                continue

            """This will get or create a new record for each M2M record passed
               in the request. The CLASS_MAPPING global variable defined at
               the top specifies which classes are currently accepted."""
            for field in bundle.data[field_name]:
                sample = Sample.objects.get(pk=bundle.obj.sample_id)

                obj_args = {'id': utils.get_next_id(CLASS_MAPPING[field_name]),
                            'sample': sample,
                            field_name[:-1]: field.obj}

                try: CLASS_MAPPING[field_name].objects.get_or_create(**obj_args)
                except IntegrityError: continue

    def build_filters(self, filters=None):
        """Build additional filters"""

        orm_filters = super(SampleResource, self).build_filters(filters)

        """
        Coordinates are supposed to be in the format:
        top_lat, top_long, bot_lat, bot_long
        """
        if 'location__contained' in filters:
            points = filters['location__contained']
            points = [float(p.strip()) for p in points.split(',')]
            orm_filters['location__contained'] = points

        return orm_filters

    def apply_filters(self, request, applicable_filters):
        """Apply the filters"""
        if 'location__contained' in applicable_filters:
            area = applicable_filters.pop('location__contained')
            poly = Polygon.from_bbox(area)
            applicable_filters['location__contained'] = poly

        return super(SampleResource, self).apply_filters(request, applicable_filters)


class SampleAliasResource(BaseResource):
    sample = fields.ToOneField("tastyapi.resources.SampleResource",
                                  "sample")
    class Meta:
        queryset = SampleAliase.objects.all()
        resource_name = "sample_alias"
        authorization = Authorization()
        authentication = CustomApiKeyAuth()
        allowed_methods = ['get']
        filtering = { 'sample': ALL_WITH_RELATIONS,
                      'alias': ALL }


class RegionResource(BaseResource):
    class Meta:
        queryset = Region.objects.all()
        authentication = CustomApiKeyAuth()
        ordering = ['name']
        allowed_methods = ['get']
        resource_name = "region"
        filtering = { 'region': ALL,
                      'name': ALL }


class RockTypeResource(BaseResource):
    class Meta:
        queryset = RockType.objects.all()
        resource_name = "rock_type"
        authorization = Authorization()
        authentication = CustomApiKeyAuth()
        ordering = ['rock_type']
        allowed_methods = ['get']
        filtering = { 'rock_type': ALL }


class MineralResource(BaseResource):
    real_mineral = fields.ToOneField('tastyapi.resources.MineralResource',
                                     'real_mineral')
    class Meta:
        resource_name = 'mineral'
        queryset = Mineral.objects.all()
        authentication = ApiKeyAuthentication()
        allowed_methods = ['get']
        filtering = {
                'name': ALL,
                'real_mineral': ALL_WITH_RELATIONS,
                }


class MineralRelationshipResource(BaseResource):
    parent_mineral = fields.ToOneField('tastyapi.resources.MineralResource',
                                          'parent_mineral', full=True)
    child_mineral = fields.ToOneField('tastyapi.resources.MineralResource',
                                         'child_mineral', full=True)

    class Meta:
        resource_name = 'mineral_relationship'
        queryset = MineralRelationship.objects.all()
        allowed_methods = ['get']


class RegionResource(BaseResource):
    class Meta:
        queryset = Region.objects.all()
        authentication = CustomApiKeyAuth()
        ordering = ['name']
        allowed_methods = ['get']
        resource_name = "region"
        filtering = { 'region': ALL,
                      'name': ALL }


class MetamorphicGradeResource(BaseResource):
    class Meta:
        resource_name = "metamorphic_grade"
        authentication = CustomApiKeyAuth()
        queryset = MetamorphicGrade.objects.all()
        ordering = ['name']
        allowed_methods = ['get']
        filtering = { 'name': ALL }


class MetamorphicRegionResource(BaseResource):
    class Meta:
        resource_name = "metamorphic_region"
        authentication = CustomApiKeyAuth()
        queryset = MetamorphicRegion.objects.all()
        ordering = ['name']
        allowed_methods = ['get']
        filtering = { 'name': ALL }


class SubsampleTypeResource(BaseResource):
    class Meta:
        resource_name = 'subsample_type'
        allowed_methods = ['get']
        queryset = SubsampleType.objects.all().distinct('subsample_type_id')
        authentication = CustomApiKeyAuth()
        filtering = {'subsample_type': ALL}


class SubsampleResource(VersionedResource, FirstOrderResource):
    user = fields.ToOneField("tastyapi.resources.UserResource", "user",
                             full=True)
    sample = fields.ToOneField(SampleResource, "sample")
    subsample_type = fields.ToOneField(SubsampleTypeResource,
                                       "subsample_type", full=True)
    class Meta:
        queryset = Subsample.objects.all().distinct('subsample_id')
        excludes = ['user']
        allowed_methods = ['get', 'post', 'put', 'delete']
        always_return_data = True
        authorization = ObjectAuthorization('tastyapi', 'subsample')
        authentication = CustomApiKeyAuth()
        filtering = {
                'subsample_id': ALL,
                'public_data': ALL,
                'grid_id': ALL,
                'name': ALL,
                'subsample_type': ALL_WITH_RELATIONS,
                'sample': ALL_WITH_RELATIONS
                }
        validation = VersionValidation(queryset, 'subsample_id')


class ReferenceResource(BaseResource):
    class Meta:
        resource_name = 'reference'
        queryset = Reference.objects.all()
        allowed_methods = ['get']
        authorization = Authorization()
        authentication = CustomApiKeyAuth()
        ordering = ['name']
        filtering = {'name': ALL}


class OxideResource(BaseResource):
    class Meta:
        queryset = Oxide.objects.all()
        resource_name = "oxide"
        authorization = Authorization()
        authentication = CustomApiKeyAuth()
        allowed_methods = ['get']
        filtering = {
            'oxide_id': ALL
        }


class ElementResource(BaseResource):
    class Meta:
        queryset = Element.objects.all()
        resource_name = "element"
        authorization = Authorization()
        authentication = CustomApiKeyAuth()
        allowed_methods = ['get']
        filtering = {
            'element_id': ALL
        }


class ChemicalAnalysisResource(VersionedResource):
    user = fields.ToOneField("tastyapi.resources.UserResource", "user")
    subsample = fields.ToOneField(SubsampleResource, "subsample")
    reference = fields.ToOneField(ReferenceResource, "reference", null=True)
    minerals = fields.ToOneField(MineralResource, "mineral", null=True, full=True)
    oxides = fields.ToManyField("tastyapi.resources.OxideResource",
                                 "oxides", null=True)
    elements = fields.ToManyField("tastyapi.resources.ElementResource",
                                 "elements", null=True)
    # oxides = fields.ToManyField(ChemicalAnalysisOxideResource,
    #     attribute = lambda bundle: bundle.obj.oxides.through.objects.filter(
    #         chemical_analysis=bundle.obj) or bundle.obj.oxides, full=True)

    class Meta:
        queryset = ChemicalAnalyses.objects.all().distinct('chemical_analysis_id')
        resource_name = 'chemical_analysis'
        allowed_methods = ['get', 'post', 'put', 'delete']
        always_return_data = True
        excludes = ['image', 'user']
        authorization = ObjectAuthorization('tastyapi', 'chemicalanalyses')
        authentication = CustomApiKeyAuth()
        filtering = {
                'chemical_analysis_id': ALL,
                'subsample': ALL_WITH_RELATIONS,
                'reference': ALL_WITH_RELATIONS,
                'public_data': ALL,
                'reference_x': ALL,
                'reference_y': ALL,
                'stage_x': ALL,
                'stage_y': ALL,
                'analysis_method': ALL,
                'where_done': ALL,
                'analyst': ALL,
                'analysis_date': ALL,
                'large_rock': ALL,
                'total': ALL,
                'oxides': ALL_WITH_RELATIONS,
                'minerals': ALL_WITH_RELATIONS,
                'elements': ALL_WITH_RELATIONS
                }
        validation = VersionValidation(queryset, 'chemical_analysis_id')
