from django.urls import path
from .views import StructuredExtractorAPIView

urlpatterns = [
    path('extract/', StructuredExtractorAPIView.as_view(),name='structured-extract'),
]


