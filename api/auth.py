from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission, Group, User, AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist


class DACBackend(ModelBackend):
    """Backend for Django's auth system.

    Provides row-level permissions based on ownership, groups, and the public
    attribute.
    """
    def has_perm(self, user_obj, perm, obj=None):
        """Determine if user_obj has perm (with respect to obj, if present)."""
        # Build up the full list of permissions and check if it includes perm
        return perm in self.get_all_permissions(user_obj, obj)
    def get_group_permissions(self, user_obj, obj=None):
        """Determine all the permissions user_obj inherits from groups.

        With respect to obj, if present.
        """
        results = set()
        if obj is not None:
            # Look up the permissions applicable to obj
            ctype = ContentType.objects.get_for_model(obj)
            all_perms = Permission.objects.filter(content_type=ctype)
            try:
                read_perm = all_perms.get(codename__startswith='read')
                write_perm = all_perms.get(codename__startswith='change')
            except ObjectDoesNotExist:
                # No permissions applicable, bail.
                # This can happen if the object does not provide a read perm.
                # Such objects don't get row-level perms, so skip 'em.
                return super(DACBackend, self).get_group_permissions(user_obj, obj)
            if hasattr(obj, "group_access"):
                # If the object has group-based access control at all, then
                # Find all the groups by which this user might have access
                # NB: this queryset returns GroupAccess's, not Groups

                # API key authentication is disabled for GET requests to allow
                # anybody to access resources with public_data == 'Y'
                if type(user_obj) == AnonymousUser:
                    can_read, can_write = None, None
                else:
                    groupset = obj.group_access.filter(group__user=user_obj)
                    can_read = groupset.filter(read_access=True).exists()
                    can_write = groupset.filter(write_access=True).exists()

                if hasattr(obj, 'public_data') and obj.public_data == "Y":
                    can_read = True

                if can_read:
                    results.add("%s.%s" % (read_perm.content_type.app_label,
                                           read_perm.codename))
                if can_write:
                    results.add("%s.%s" % (write_perm.content_type.app_label,
                                           write_perm.codename))
        else:
            # Check whether the user should have add permissions
            create_perms = Permission.objects.filter(codename__startswith='add')
            personal_group = Group.objects.filter(groupextra__group_type='u_uid',
                                                  groupextra__owner=user_obj)
            if personal_group.exists():
                # The user has add permissions,
                results.update(set("%s.%s" % (create_perm.content_type.app_label,
                                              create_perm.codename)
                                   for create_perm in create_perms))
        # Call the superclass in case obj is None
        results.update(super(DACBackend, self).get_group_permissions(user_obj, obj))
        return results
    def get_all_permissions(self, user_obj, obj=None):
        """Determine all the permissions user_obj has.

        With respect to obj, if present.
        """
        results = set()
        if obj is not None:
            # look up the permissions applicable to obj
            ctype = ContentType.objects.get_for_model(obj)
            all_perms = Permission.objects.filter(content_type=ctype)
            if user_obj.is_superuser:
                # If the user is the superuser, just give them all permissions.
                # NB: Permissions need to be translated into a string format
                #     for some bizarre reason
                perms = (["%s.%s" % (p.content_type.app_label, p.codename) for
                          p in all_perms])
                results.update(perms)
        # delegate to get_group_permissions to handle groups
        results.update(self.get_group_permissions(user_obj, obj))
        # delegate to the superclass, in case obj is None
        results.update(super(DACBackend, self).get_all_permissions(user_obj, obj))
        return results


def get_read_queryset(user, prefix=None):
    """Returns a Q object matching all instances which user may read.

    Typical usage:

        query = get_read_queryset(user)
        qs = Foo.objects.filter(query)

    Now qs has only those Foo objects which user may read.

    The backend is written in Python, and can only determine permissions on a
    case-by-case basis.  We need a way to produce database queries for
    "everything John Doe can read," since the alternative is manually checking
    each object in the table.

    This also accepts a prefix argument, which creates indirect filters for
    related objects instead of the current object.

    Typical usage:

        query = get_read_queryset(user, 'bar')
        qs = Foo.objects.filter(query)

    Now qs has only those Foo objects whose bar attribute is readable.

    This function does not perform any db access, and only creates
    Q objects.
    """
    if user.is_superuser:
        return Q()
    if prefix: # NB: if prefix == "", go to else
        # Prepend a prefix
        #Review lines 129 and 130 for removing the prefix from the two strings
        result_dict = {"group_access__read_access": True,
                       "group_access__group__user": user}
        return Q(**result_dict)
    else:
        return (Q(group_access__read_access=True,
                  group_access__group__user=user) | \
                Q(public_data='Y'))

