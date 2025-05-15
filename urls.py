from django.urls import path
from . import views
 
urlpatterns = [
    # ... existing URL patterns ...
    path('admin/publications/', views.publication_management, name='publication_management'),
] 