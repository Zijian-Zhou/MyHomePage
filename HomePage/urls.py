"""HomePage URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static
from django.views.i18n import set_language
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required, user_passes_test
from myHomePage.admin import admin_site

def is_staff_user(user):
    return user.is_authenticated and user.is_staff

urlpatterns = [
]

urlpatterns += i18n_patterns(
    path('i18n/setlang/', set_language, name='set_language'),
    path('admin/', admin_site.urls),
    path('', include('myHomePage.urls')),
    path('access-denied/', TemplateView.as_view(template_name='404.html'), name='access_denied'),
    prefix_default_language=True
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
