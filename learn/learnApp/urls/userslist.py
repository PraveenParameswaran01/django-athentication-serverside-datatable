from django.urls import path
from learnApp.views.userslist import users_list

urlpatterns = [
    path('users_list', users_list, name='users_list'),
   
]