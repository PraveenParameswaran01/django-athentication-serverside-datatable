from learnApp.views import dashboard
from django.urls import path

urlpatterns = [
    path("dashboard/", dashboard.dashboard, name="dashboard"),
]
