"""URL configuration for onw_backend project.

nginx strips the site prefix and forwards ``/api/...`` to Django, so the whole
API lives under ``/api/``. All routes the frontend hits are defined in
``room/urls.py`` and mounted here.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/", include("room.urls")),
    path("admin/", admin.site.urls),
]