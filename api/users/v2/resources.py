from tastypie.authorization import Authorization
from tastypie.constants import ALL
from tastypie.resources import ModelResource

from api.resources import CustomApiKeyAuth
from apps.users.v2.models import User


class UserResource(ModelResource):
    """
    This resource exists to just let other resources get user data when
    required, so only GET requests are allowed.
    """
    class Meta:
        resource_name = 'user'
        allowed_methods = ['get']
        queryset = User.objects.all()
        authorization = Authorization()
        authentication = CustomApiKeyAuth()
        filtering = {
            'email': ALL
        }
        excludes = ['password']
