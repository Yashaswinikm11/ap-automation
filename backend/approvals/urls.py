from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ApprovalMatrixViewSet, ApprovalRequestViewSet

app_name = 'approvals'

router = DefaultRouter()
router.register(r'matrices', ApprovalMatrixViewSet, basename='approval-matrix')
router.register(r'requests', ApprovalRequestViewSet, basename='approval-request')

urlpatterns = [
    path('', include(router.urls)),
]
