from django.urls import path
from . import views

app_name = 'bills'

urlpatterns = [
    path('', views.index, name='index'),
    path(
        'confirm-send-bills/',
        views.confirm_send_bills,
        name='confirm_send_bills'
    ),
    path('persons/', views.manage_persons, name='manage_persons'),
    path(
        'persons/<int:person_id>/edit/',
        views.edit_person,
        name='edit_person'
    ),
    path(
        'persons/<int:person_id>/delete/',
        views.delete_person,
        name='delete_person'
    ),
    path('bills/', views.manage_bills, name='manage_bills'),
    path(
        'bills/folder/<str:folder_name>/delete/',
        views.delete_folder,
        name='delete_folder'
    ),
    path(
        'bills/folder/<str:folder_name>/bill/<str:bill_name>/delete/',
        views.delete_bill,
        name='delete_bill'
    ),
]
