from time import timezone
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)

class UserManager(BaseUserManager):

    def _create_user(self, email, password,
                     is_staff, is_superuser, **extra_fields):
        """
        Creates and saves a User with the given username, email and password.
        """
        now = timezone.now()
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email,
                          is_staff=is_staff,
                          is_active=False,
                          is_superuser=is_superuser,
                          last_login=now,
                          date_joined=now,
                          **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        return self._create_user(email,
                                 password,
                                 is_staff=False,
                                 is_superuser=False,
                                 **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        return self._create_user(email,
                                 password,
                                 is_staff=True,
                                 is_superuser=True,
                                 **extra_fields)


class UserV2(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=50, blank=True)
    province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=15, blank=True)
    institution = models.CharField(max_length=300, blank=True)
    reference_email = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=False)
    is_contributor = models.BooleanField(default=False)
    professional_url = models.CharField(max_length=255, blank=True)
    research_interests = models.CharField(max_length=1024, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['email', 'name']

    def get_full_name(self):
        """
        Returns the name
        """
        return self.name.strip()

    def get_short_name(self):
        """
        Returns the name
        """
        return self.get_full_name()
