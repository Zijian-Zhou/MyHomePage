from django.urls import path
from . import views

app_name = 'publications'
 
urlpatterns = [
    # ... existing URL patterns ...
    path('admin/publications/import-bibtex/', views.import_bibtex, name='import_bibtex'),
] 