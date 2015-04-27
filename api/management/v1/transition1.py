#!/usr/bin/env python

import logging
import dotenv

dotenv.read_dotenv('../../api_variables.env')
logger = logging.getLogger(__name__)

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User as AuthUser
from django.db import transaction

from tastypie.models import ApiKey

from api.models import get_public_groups
from api.models import User as MetpetUser
from api.models import Group, GroupAccess
from api.models import Sample, Image
from api.models import Subsample, ChemicalAnalyses, Grid


@transaction.atomic
def main():
    """Imports metpetdb's various tables into Django for auth purposes.

    This function is idempotent, but shouldn't need to be run multiple times.
    """
    for metpet_user in MetpetUser.objects.filter(django_user=None).iterator():
        logger.info("Transitioning %s.", metpet_user.name)
        email = metpet_user.email
        logger.debug("Email = %s", email)
        # Use the email for the username, but strip out disallowed characters
        # and cap total length at 30 characters to comply with Django's
        # requirements:
        username = ''.join(c for c in email if c.isalnum() or c in ['_', '@',
                                                                    '+', '.',
                                                                    '-'])[:30]
        logger.debug("Username = %s", username)

        auth_user = AuthUser(username=username,
                             email=email,
                             is_staff=False,
                             is_active=True,
                             is_superuser=False)
        auth_user.set_unusable_password()
        auth_user.save()

        ApiKey.objects.create(user=auth_user)

        metpet_user.django_user = auth_user
        metpet_user.password = None
        metpet_user.save()

        if metpet_user.enabled.upper() == 'Y':
            # Add user to public group(s), so (s)he can read public things
            logger.info("Adding %s to public group.", metpet_user.name)
            metpet_user.auto_verify(None) # Pass None to skip code check

        if metpet_user.contributor_enabled.upper() == 'Y':
            # Add user to personal group, so (s)he can create things
            logger.info("Adding %s to personal group.", metpet_user.name)
            metpet_user.manual_verify()

        metpet_user.save()

    models_with_owners = [Sample, Image]
    models_with_public_data = [Sample, Image, Subsample, ChemicalAnalyses, Grid]
    public_groups = get_public_groups()

    for Model in models_with_owners:
        ctype = ContentType.objects.get_for_model(Model)

        for item in Model.objects.all().iterator():
            owner = item.user
            owner_django = owner.django_user
            try:
                owner_group = Group.objects.get(groupextra__owner=owner_django,
                                                groupextra__group_type='u_uid')
            except Group.DoesNotExist:
                logger.warning("Skipping item %s, owner %s doesn't have a group.",
                               item, owner)
                continue # skip this item
            if GroupAccess.objects.filter(group=owner_group, content_type=ctype,
                                          object_id=item.pk).exists():
                continue # Already been done, skip it
            GroupAccess(group=owner_group, read_access=True, write_access=True,
                        content_type=ctype, object_id=item.pk).save()

    for Model in models_with_public_data:
        ctype = ContentType.objects.get_for_model(Model)

        for item in Model.objects.filter(public_data__iexact='y').iterator():
            for group in public_groups:
                if GroupAccess.objects.filter(group=group, content_type=ctype,
                                              object_id=item.pk).exists():
                    continue # Object is already in this group
                GroupAccess(group=group, content_type=ctype, object_id=item.pk,
                            read_access=True, write_access=False).save()

if __name__ == "__main__":
    main()
