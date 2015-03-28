import base64
import logging
import dotenv
dotenv.read_dotenv('../../api_variables.env')
logger = logging.getLogger(__name__)

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.models import Group
from django.db import transaction

from tastyapi.models import ApiKey
from tastyapi.models import get_public_groups
from tastyapi.models import User as MetpetUser
from tastyapi.models import Group, GroupExtra, GroupAccess
from tastyapi.models import Sample, Image
from tastyapi.models import Subsample, ChemicalAnalyses, Grid

def translate(raw_crypt):
    """Translates a metpetdb salted password into a Django salted password."""
    logger.debug("Re-crypting %s.", repr(raw_crypt))
    if len(raw_crypt) == 0:
        return 'sha1$$' # Unusuable password
    salt_length = raw_crypt[0]
    raw_salt = raw_crypt[1:salt_length+1]
    raw_hash = raw_crypt[salt_length+1:]
    cooked_salt = base64.b64encode(raw_salt)
    cooked_hash = base64.b16encode(raw_hash).lower() # NB: Base16 = hex
    # XXX: 'sha1-b64-salt' is nonstandard, but there's no obvious alternative.
    cooked_crypt = 'sha1-b64-salt${}${}'.format(cooked_salt, cooked_hash)
    return cooked_crypt


@transaction.commit_on_success
def main():
    """Imports metpetdb's various tables into Django for auth purposes.

    BEFORE RUNNING THIS SCRIPT, execute the following SQL:

        ALTER TABLE users ADD COLUMN django_user_id int UNIQUE REFERENCES
        auth_user(id);

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
        password = translate(bytearray(metpet_user.password))
        if password == 'sha1$$':
            logger.warning("%s (%s) has an unusable password and won't be "+
                           "able to log in.", metpet_user.name, email)
        logger.debug("Password hash = %s", password)
        result = AuthUser(username=username, password=password, email=email,
                          is_staff=False, is_active=True, is_superuser=False)
        result.save()
        ApiKey.objects.create(user=result)
        metpet_user.django_user = result
        metpet_user.password = password
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
