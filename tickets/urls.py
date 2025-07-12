from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .forms import LoginForm

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # User Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.CustomUserRegistrationView.as_view(), name='register'),

    # Tickets
    path('tickets/', views.TicketListView.as_view(), name='ticket_list'),
    path('tickets/create/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),
    path('tickets/<int:pk>/update/', views.TicketUpdateView.as_view(), name='ticket_update'),
    path('tickets/<int:pk>/comment/', views.add_ticket_comment, name='add_ticket_comment'),
    path('tickets/<int:pk>/upload/', views.upload_ticket_attachment, name='upload_ticket_attachment'),
    path('tickets/bulk/', views.bulk_ticket_actions, name='bulk_ticket_actions'),
    path('ajax/get-categories/', views.get_categories_by_department, name='get_categories_by_department'),

    # Knowledge Base
    path('kb/', views.KnowledgeBaseListView.as_view(), name='kb_list'),
    path('kb/create/', views.KnowledgeBaseCreateView.as_view(), name='kb_create'),
    path('kb/<int:pk>/', views.KnowledgeBaseDetailView.as_view(), name='kb_detail'),
    path('kb/<int:pk>/edit/', views.KnowledgeBaseUpdateView.as_view(), name='kb_update'),
    path('kb/<int:pk>/vote/', views.kb_article_vote, name='kb_vote'),

    # Reports & Analytics
    path('reports/', views.ReportsView.as_view(), name='reports'),
    path('reports/export/', views.export_tickets_csv, name='export_tickets_csv'),

    # Profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),

    # AJAX / Utilities
    path('ajax/stats/', views.get_ticket_stats, name='get_ticket_stats'),
]
