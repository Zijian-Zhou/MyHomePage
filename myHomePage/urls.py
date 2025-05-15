from django.urls import path
from . import views

urlpatterns = [
    path('', views.Index.as_view(), name='index'),
    path('orcid/authorize/', views.orcid_authorize, name='orcid_authorize'),
    path('orcid/callback/', views.orcid_callback, name='orcid_callback'),
    path('admin/user-management/', views.user_management, name='user_management'),
] 