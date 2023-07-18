from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
# Create your models here.



class Usermanager(BaseUserManager):
    def create_user(self, user_name, password=None,**kwargs):
      
        user = self.model(user_name=user_name, password=password,**kwargs)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, user_name, password=None, **kwargs):
        user = self.create_user(
            user_name=user_name,
            password=password,
            is_superuser=True,
            is_staff=True,
            **kwargs
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

class masUser(AbstractBaseUser, PermissionsMixin):
    user_name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    mobile_number = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    objects = Usermanager()

    REQUIRED_FIELDS = ['password']
    USERNAME_FIELD = 'user_name'

    def __str__(self):
        return self.email