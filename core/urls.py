
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    # Hook up the new API endpoint
    path('api/v1/', include('extractor.urls')),
]


