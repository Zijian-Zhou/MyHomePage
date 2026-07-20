from django.urls import path
from . import views

urlpatterns = [
    path('', views.Index.as_view(), name='index'),
    path('publication/<int:pk>/', views.publication_detail, name='publication_detail'),
    path('news/<int:pk>/', views.news_detail, name='news_detail'),
    path('research/<int:pk>/', views.research_detail, name='research_detail'),
    path('publication-file/<slug:access_key>/', views.publication_file_download, name='publication_file_download'),
    path('orcid/authorize/', views.orcid_authorize, name='orcid_authorize'),
    path('orcid/callback/', views.orcid_callback, name='orcid_callback'),
    path('admin/user-management/', views.user_management, name='user_management'),
    path('auth/public-key/', views.rsa_public_key, name='rsa_public_key'),
] 
