from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('uploads/', views.uploads, name='uploads'),
    path('auth/register/', views.register, name='registeration'),
    path('auth/login/', views.login, name='login'),
    path('auth/verify/', views.verify, name='verify'),
    path('success/', views.success, name='success'),
    path('documents/', views.documents, name='documents'),
    path('documents/<int:file_id>/', views.download, name='download'),
    path('auth/logout/', views.logout_view, name='logout'),
]
