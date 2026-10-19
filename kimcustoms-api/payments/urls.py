from django.urls import path

from .views import MpesaCallbackView, MpesaStkPushView


urlpatterns = [
    path("mpesa/stk-push/", MpesaStkPushView.as_view(), name="mpesa-stk-push"),
    path("mpesa/callback/", MpesaCallbackView.as_view(), name="mpesa-callback"),
]
