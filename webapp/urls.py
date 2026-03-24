"""
URL configuration for webapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.homepage, name='homepage'),
    path('callgraph/', views.callgraph, name='callgraph'),
    path('results/<str:package_name>/', views.results, name='results'),
    path('gasket/', views.gasket, name='gasket'),
    #path('results_gasket/<str:package_name>/', views.gasket_results, name='gasket_results'),
    path('results_gasket/<str:package_name>/<str:package_version>/', views.gasket_results, name='gasket_results'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('myacc/', views.myacc, name='myacc'),
    path('logout/', views.logout_view, name='logout'),
    path('workspace/', views.workspace, name='workspace'),
    path('analyses/', views.analyses, name='analyses'),
    path('analysis/<int:analysis_id>/', views.analysis_detail, name='analysis_detail'),
    path('ajax/get-versions/', views.get_package_versions, name='get_package_versions'),
]
