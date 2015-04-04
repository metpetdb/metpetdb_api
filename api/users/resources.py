from tastypie.authorization import Authorization
from tastypie.constants import ALL
from tastypie.resources import ModelResource
from api.resources import CustomApiKeyAuth
from apps.users.models import UserV2


class UserV2Resource(ModelResource):
    """
    This resource exists to just let other resources get user data when
    required, so only GET requests are allowed.
    """
    class Meta:
        resource_name = 'user'
        allowed_methods = ['get']
        queryset = UserV2.objects.all()
        authorization = Authorization()
        authentication = CustomApiKeyAuth()
        filtering = {
            'email': ALL
        }
        excludes = ['password']
