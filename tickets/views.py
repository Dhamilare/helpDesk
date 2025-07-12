from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, F
from django.http import JsonResponse, Http404, HttpResponse
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, 
    DeleteView, TemplateView, FormView
)
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from datetime import datetime, timedelta
import json
from django.contrib.auth import authenticate, login as auth_login, logout
from django.views import View
from .models import *
from .forms import *

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')

class CustomLoginView(View):
    template_name = 'accounts/login.html'
    form_class = LoginForm

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                auth_login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                next_url = request.GET.get('next') or 'dashboard'
                return redirect(next_url)
            else:
                messages.error(request, "Invalid username or password.")
        return render(request, self.template_name, {'form': form})


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'tickets/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Base ticket queryset
        tickets = Ticket.objects.select_related('submitter', 'assigned_to', 'priority', 'department')
        
        # Filter based on user role
        if hasattr(user, 'userprofile'):
            if user.userprofile.is_agent or user.userprofile.is_supervisor:
                # Agents see all tickets in their department or assigned to them
                tickets = tickets.filter(
                    Q(assigned_to=user) | 
                    Q(department=user.userprofile.department)
                )
            else:
                # Regular users see only their tickets
                tickets = tickets.filter(submitter=user)
        else:
            tickets = tickets.filter(submitter=user)
        
        # Statistics
        context.update({
            'total_tickets': tickets.count(),
            'open_tickets': tickets.filter(status='open').count(),
            'in_progress_tickets': tickets.filter(status='in_progress').count(),
            'resolved_tickets': tickets.filter(status='resolved').count(),
            'overdue_tickets': tickets.filter(
                due_date__lt=timezone.now(), 
                status__in=['open', 'in_progress', 'pending']
            ).count(),
        })
        
        # Recent tickets
        context['recent_tickets'] = tickets.order_by('-created_at')[:10]
        
        # Priority distribution
        priority_stats = tickets.values('priority__name', 'priority__level').annotate(
            count=Count('id')
        ).order_by('priority__level')
        context['priority_stats'] = priority_stats
        
        # Status distribution
        status_stats = tickets.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        context['status_stats'] = status_stats
        
        # My assigned tickets (for agents)
        if hasattr(user, 'userprofile') and user.userprofile.is_agent:
            context['my_assigned_tickets'] = tickets.filter(
                assigned_to=user
            ).exclude(status__in=['resolved', 'closed']).order_by('-created_at')[:5]
        
        return context


class TicketListView(LoginRequiredMixin, ListView):
    """List all tickets with filtering"""
    model = Ticket
    template_name = 'tickets/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Ticket.objects.select_related(
            'submitter', 'assigned_to', 'priority', 'department', 'category'
        ).prefetch_related('comments')
        
        user = self.request.user
        
        # Filter based on user role
        if hasattr(user, 'userprofile'):
            if user.userprofile.is_supervisor:
                # Supervisors see all tickets
                pass
            elif user.userprofile.is_agent:
                # Agents see tickets in their department or assigned to them
                queryset = queryset.filter(
                    Q(assigned_to=user) | 
                    Q(department=user.userprofile.department)
                )
            else:
                # Regular users see only their tickets
                queryset = queryset.filter(submitter=user)
        else:
            queryset = queryset.filter(submitter=user)
        
        # Apply filters
        form = TicketFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get('status'):
                queryset = queryset.filter(status=form.cleaned_data['status'])
            if form.cleaned_data.get('priority'):
                queryset = queryset.filter(priority=form.cleaned_data['priority'])
            if form.cleaned_data.get('department'):
                queryset = queryset.filter(department=form.cleaned_data['department'])
            if form.cleaned_data.get('category'):
                queryset = queryset.filter(category=form.cleaned_data['category'])
            if form.cleaned_data.get('assigned_to'):
                queryset = queryset.filter(assigned_to=form.cleaned_data['assigned_to'])
            if form.cleaned_data.get('date_from'):
                queryset = queryset.filter(created_at__date__gte=form.cleaned_data['date_from'])
            if form.cleaned_data.get('date_to'):
                queryset = queryset.filter(created_at__date__lte=form.cleaned_data['date_to'])
            if form.cleaned_data.get('search'):
                search_term = form.cleaned_data['search']
                queryset = queryset.filter(
                    Q(title__icontains=search_term) |
                    Q(description__icontains=search_term) |
                    Q(ticket_number__icontains=search_term)
                )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = TicketFilterForm(self.request.GET)
        context['bulk_action_form'] = BulkTicketActionForm()
        return context


class TicketDetailView(LoginRequiredMixin, DetailView):
    """Detailed ticket view"""
    model = Ticket
    template_name = 'tickets/ticket_detail.html'
    context_object_name = 'ticket'
    
    def get_queryset(self):
        queryset = Ticket.objects.select_related(
            'submitter', 'assigned_to', 'priority', 'department', 'category'
        ).prefetch_related(
            'comments__author',
            'attachments__uploaded_by',
            'history__user'
        )
        
        user = self.request.user
        
        # Filter based on user role
        if hasattr(user, 'userprofile'):
            if user.userprofile.is_supervisor:
                return queryset
            elif user.userprofile.is_agent:
                return queryset.filter(
                    Q(assigned_to=user) | 
                    Q(department=user.userprofile.department)
                )
        
        return queryset.filter(submitter=user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Comments (filter internal comments for non-agents)
        comments = self.object.comments.all()
        if not (hasattr(user, 'userprofile') and 
                (user.userprofile.is_agent or user.userprofile.is_supervisor)):
            comments = comments.filter(is_internal=False)
        
        context.update({
            'comments': comments,
            'comment_form': TicketCommentForm(user=user),
            'attachment_form': TicketAttachmentForm(user=user),
            'can_edit': self.can_edit_ticket(user),
            'can_comment': True,
            'ticket_history': self.object.history.all()[:10],
        })
        
        return context
    
    def can_edit_ticket(self, user):
        """Check if user can edit this ticket"""
        if hasattr(user, 'userprofile'):
            if user.userprofile.is_supervisor:
                return True
            elif user.userprofile.is_agent:
                return (self.object.assigned_to == user or 
                       self.object.department == user.userprofile.department)
        return self.object.submitter == user


class TicketCreateView(LoginRequiredMixin, CreateView):
    """Create new ticket"""
    model = Ticket
    form_class = TicketCreateForm
    template_name = 'tickets/ticket_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Ticket created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('ticket_detail', kwargs={'pk': self.object.pk})


class TicketUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update existing ticket"""
    model = Ticket
    form_class = TicketUpdateForm
    template_name = 'tickets/ticket_form.html'
    
    def test_func(self):
        ticket = self.get_object()
        user = self.request.user
        
        if hasattr(user, 'userprofile'):
            if user.userprofile.is_supervisor:
                return True
            elif user.userprofile.is_agent:
                return (ticket.assigned_to == user or 
                       ticket.department == user.userprofile.department)
        
        return ticket.submitter == user
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Ticket updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('ticket_detail', kwargs={'pk': self.object.pk})


@login_required
@require_http_methods(["POST"])
def add_ticket_comment(request, pk):
    """Add comment to ticket via AJAX"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Check permissions
    user = request.user
    can_comment = False
    
    if hasattr(user, 'userprofile'):
        if user.userprofile.is_supervisor:
            can_comment = True
        elif user.userprofile.is_agent:
            can_comment = (ticket.assigned_to == user or 
                          ticket.department == user.userprofile.department)
    
    if not can_comment and ticket.submitter != user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    form = TicketCommentForm(request.POST, user=user)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.ticket = ticket
        comment.save()
        
        # Return JSON response for AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'author': comment.author.get_full_name(),
                    'comment': comment.comment,
                    'is_internal': comment.is_internal,
                    'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
                }
            })
        
        messages.success(request, 'Comment added successfully!')
        return redirect('ticket_detail', pk=pk)
    
    return JsonResponse({'error': 'Invalid form data'}, status=400)


@login_required
@require_http_methods(["POST"])
def upload_ticket_attachment(request, pk):
    """Upload attachment to ticket"""
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # Check permissions (same as comment permissions)
    user = request.user
    can_upload = False
    
    if hasattr(user, 'userprofile'):
        if user.userprofile.is_supervisor:
            can_upload = True
        elif user.userprofile.is_agent:
            can_upload = (ticket.assigned_to == user or 
                         ticket.department == user.userprofile.department)
    
    if not can_upload and ticket.submitter != user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    form = TicketAttachmentForm(request.POST, request.FILES, user=user)
    if form.is_valid():
        attachment = form.save(commit=False)
        attachment.ticket = ticket
        attachment.save()
        
        messages.success(request, 'File uploaded successfully!')
        return redirect('ticket_detail', pk=pk)
    
    messages.error(request, 'Error uploading file. Please check the file type and size.')
    return redirect('ticket_detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def bulk_ticket_actions(request):
    """Handle bulk actions on tickets"""
    user = request.user

    # Permission check
    profile = getattr(user, 'userprofile', None)
    if not profile or not (profile.is_agent or profile.is_supervisor):
        messages.error(request, 'Permission denied.')
        return redirect('ticket_list')

    form = BulkTicketActionForm(request.POST)
    ticket_ids = request.POST.getlist('ticket_ids')

    if not ticket_ids:
        messages.error(request, 'No tickets selected.')
        return redirect('ticket_list')

    if form.is_valid():
        action = form.cleaned_data['action']
        assigned_to = form.cleaned_data.get('assigned_to')
        status = form.cleaned_data.get('status')
        priority = form.cleaned_data.get('priority')

        tickets = Ticket.objects.filter(id__in=ticket_ids)
        # apply permission restrictions
        if not profile.is_supervisor:
            tickets = tickets.filter(Q(assigned_to=user) | Q(department=profile.department))

        with transaction.atomic():
            if action == 'assign' and assigned_to:
                updated = tickets.update(assigned_to=assigned_to)
                messages.success(request, f'Successfully assigned {updated} tickets.')
            elif action == 'status' and status:
                updated = tickets.update(status=status)
                messages.success(request, f'Successfully updated status for {updated} tickets.')
            elif action == 'priority' and priority:
                updated = tickets.update(priority=priority)
                messages.success(request, f'Successfully updated priority for {updated} tickets.')
            elif action == 'close':
                updated = tickets.update(status='closed', closed_at=timezone.now())
                messages.success(request, f'Successfully closed {updated} tickets.')

    return redirect('ticket_list')


@login_required
def get_categories_by_department(request):
    department_id = request.GET.get('department_id')
    ticket_id = request.GET.get('ticket_id')

    categories = []
    if department_id:
        categories_qs = Category.objects.filter(department_id=department_id, is_active=True)

        # Include the current category if it's not in the active list
        if ticket_id:
            try:
                ticket = Ticket.objects.get(pk=ticket_id)
                if ticket.category and ticket.category.department_id == int(department_id):
                    if not categories_qs.filter(pk=ticket.category.pk).exists():
                        categories_qs = categories_qs | Category.objects.filter(pk=ticket.category.pk)
            except Ticket.DoesNotExist:
                pass

        categories = categories_qs.values('id', 'name').order_by('name')

    return JsonResponse({'categories': list(categories)})


class UserProfileView(LoginRequiredMixin, FormView):
    template_name = 'accounts/profile.html'
    form_class = UserProfileForm
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['instance'] = self.get_object()
        return kwargs
    
    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('profile')


class CustomUserRegistrationView(FormView):
    template_name = 'accounts/register.html'
    form_class = CustomUserCreationForm

    def form_valid(self, form):
        user = form.save()
        username = form.cleaned_data.get('username')
        messages.success(self.request, f'Account created for {username}! Please log in.')

        new_user = authenticate(
            self.request,
            username=username,
            password=form.cleaned_data.get('password1')
        )

        return redirect('login')

    def get_success_url(self):
        return reverse('login')


# Knowledge Base Views
class KnowledgeBaseListView(ListView):
    """List all published knowledge base articles"""
    model = KnowledgeBase
    template_name = 'kb/kb_list.html'
    context_object_name = 'articles'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = KnowledgeBase.objects.filter(is_published=True)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(tags__icontains=search)
            )
        
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        return context


class KnowledgeBaseDetailView(DetailView):
    """Knowledge base article detail"""
    model = KnowledgeBase
    template_name = 'kb/kb_detail.html'
    context_object_name = 'article'
    
    def get_queryset(self):
        return KnowledgeBase.objects.filter(is_published=True)
    
    def get_object(self):
        obj = super().get_object()
        # Increment view count
        obj.views = F('views') + 1
        obj.save(update_fields=['views'])
        obj.refresh_from_db()
        return obj


class KnowledgeBaseCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create knowledge base article"""
    model = KnowledgeBase
    form_class = KnowledgeBaseForm
    template_name = 'kb/kb_form.html'
    
    def test_func(self):
        return (hasattr(self.request.user, 'userprofile') and 
                (self.request.user.userprofile.is_agent or 
                 self.request.user.userprofile.is_supervisor))
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Knowledge base article created successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('kb_detail', kwargs={'pk': self.object.pk})


class KnowledgeBaseUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update knowledge base article"""
    model = KnowledgeBase
    form_class = KnowledgeBaseForm
    template_name = 'kb/kb_form.html'
    
    def test_func(self):
        article = self.get_object()
        user = self.request.user
        
        if hasattr(user, 'userprofile'):
            if user.userprofile.is_supervisor:
                return True
            elif user.userprofile.is_agent:
                return article.author == user
        
        return False
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Knowledge base article updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('kb_detail', kwargs={'pk': self.object.pk})


@login_required
@require_http_methods(["POST"])
def kb_article_vote(request, pk):
    """Vote on knowledge base article helpfulness"""
    article = get_object_or_404(KnowledgeBase, pk=pk)
    vote_type = request.POST.get('vote_type')
    
    if vote_type == 'helpful':
        article.helpful_votes = F('helpful_votes') + 1
        article.save(update_fields=['helpful_votes'])
        messages.success(request, 'Thank you for your feedback!')
    elif vote_type == 'not_helpful':
        article.not_helpful_votes = F('not_helpful_votes') + 1
        article.save(update_fields=['not_helpful_votes'])
        messages.success(request, 'Thank you for your feedback!')
    
    return redirect('kb_detail', pk=pk)


# Reports and Analytics Views
class ReportsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Reports dashboard"""
    template_name = 'reports/reports.html'
    
    def test_func(self):
        return (hasattr(self.request.user, 'userprofile') and 
                (self.request.user.userprofile.is_agent or 
                 self.request.user.userprofile.is_supervisor))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Date range from request
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if not date_from:
            date_from = (timezone.now() - timedelta(days=30)).date()
        else:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        
        if not date_to:
            date_to = timezone.now().date()
        else:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        # Base queryset
        tickets = Ticket.objects.filter(
            created_at__date__range=[date_from, date_to]
        )
        
        # Filter by user's department if not supervisor
        user = self.request.user
        if hasattr(user, 'userprofile') and not user.userprofile.is_supervisor:
            tickets = tickets.filter(department=user.userprofile.department)
        
        # Statistics
        total_tickets = tickets.count()
        resolved_tickets = tickets.filter(status='resolved').count()
        closed_tickets = tickets.filter(status='closed').count()
        overdue_tickets = tickets.filter(
            due_date__lt=timezone.now(),
            status__in=['open', 'in_progress', 'pending']
        ).count()
        
        # Resolution rate
        resolution_rate = 0
        if total_tickets > 0:
            resolution_rate = round((resolved_tickets + closed_tickets) / total_tickets * 100, 1)
        
        # Average resolution time
        resolved_ticket_times = tickets.filter(
            status__in=['resolved', 'closed'],
            resolved_at__isnull=False
        ).annotate(
            resolution_time=F('resolved_at') - F('created_at')
        ).values_list('resolution_time', flat=True)
        
        avg_resolution_time = None
        if resolved_ticket_times:
            total_seconds = sum(rt.total_seconds() for rt in resolved_ticket_times)
            avg_seconds = total_seconds / len(resolved_ticket_times)
            avg_resolution_time = round(avg_seconds / 3600, 1)  # Convert to hours
        
        # Tickets by department
        dept_stats = tickets.values('department__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Tickets by priority
        priority_stats = tickets.values('priority__name', 'priority__level').annotate(
            count=Count('id')
        ).order_by('priority__level')
        
        # Tickets by status
        status_stats = tickets.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Top agents by tickets resolved
        agent_stats = tickets.filter(
            status__in=['resolved', 'closed'],
            assigned_to__isnull=False
        ).values('assigned_to__first_name', 'assigned_to__last_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        context.update({
            'date_from': date_from,
            'date_to': date_to,
            'total_tickets': total_tickets,
            'resolved_tickets': resolved_tickets,
            'closed_tickets': closed_tickets,
            'overdue_tickets': overdue_tickets,
            'resolution_rate': resolution_rate,
            'avg_resolution_time': avg_resolution_time,
            'dept_stats': dept_stats,
            'priority_stats': priority_stats,
            'status_stats': status_stats,
            'agent_stats': agent_stats,
        })
        
        return context


@login_required
def export_tickets_csv(request):
    """Export tickets to CSV"""
    import csv
    from django.http import HttpResponse
    
    user = request.user
    
    # Check permissions
    if not (hasattr(user, 'userprofile') and 
            (user.userprofile.is_agent or user.userprofile.is_supervisor)):
        return HttpResponse('Permission denied', status=403)
    
    # Get tickets based on user permissions
    tickets = Ticket.objects.select_related(
        'submitter', 'assigned_to', 'priority', 'department', 'category'
    )
    
    if not user.userprofile.is_supervisor:
        tickets = tickets.filter(department=user.userprofile.department)
    
    # Apply filters from request
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        tickets = tickets.filter(created_at__date__gte=date_from)
    if date_to:
        tickets = tickets.filter(created_at__date__lte=date_to)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tickets_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Ticket Number', 'Title', 'Status', 'Priority', 'Department', 
        'Category', 'Submitter', 'Assigned To', 'Created At', 'Resolved At'
    ])
    
    for ticket in tickets:
        writer.writerow([
            ticket.ticket_number,
            ticket.title,
            ticket.get_status_display(),
            ticket.priority.name,
            ticket.department.name,
            ticket.category.name,
            ticket.submitter.get_full_name(),
            ticket.assigned_to.get_full_name() if ticket.assigned_to else 'Unassigned',
            ticket.created_at.strftime('%Y-%m-%d %H:%M'),
            ticket.resolved_at.strftime('%Y-%m-%d %H:%M') if ticket.resolved_at else '',
        ])
    
    return response


# Error handling views
def handler404(request, exception):
    """Custom 404 page"""
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    """Custom 500 page"""
    return render(request, 'errors/500.html', status=500)


# AJAX utility views
@login_required
def get_ticket_stats(request):
    user = request.user
    
    # Base queryset
    tickets = Ticket.objects.all()
    
    # Filter based on user role
    if hasattr(user, 'userprofile'):
        if user.userprofile.is_supervisor:
            pass  # Supervisors see all
        elif user.userprofile.is_agent:
            tickets = tickets.filter(
                Q(assigned_to=user) | 
                Q(department=user.userprofile.department)
            )
        else:
            tickets = tickets.filter(submitter=user)
    else:
        tickets = tickets.filter(submitter=user)
    
    stats = {
        'total': tickets.count(),
        'open': tickets.filter(status='open').count(),
        'in_progress': tickets.filter(status='in_progress').count(),
        'resolved': tickets.filter(status='resolved').count(),
        'overdue': tickets.filter(
            due_date__lt=timezone.now(),
            status__in=['open', 'in_progress', 'pending']
        ).count(),
    }
    
    return JsonResponse(stats)