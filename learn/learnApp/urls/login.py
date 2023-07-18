from django.urls import path
from learnApp.views.login import  home, user_register, user_login, log_out


urlpatterns = [
    path('', home, name='login'),
    path('userregister/', user_register, name='userregister'),
    path('user_login/', user_login, name='user_login'),
    path('log_out/', log_out, name='log_out'),
]