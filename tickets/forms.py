from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Ticket, TicketComment, TicketAttachment, Department,
    Category, Priority, UserProfile, KnowledgeBase
)

class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Apply Bootstrap form-control class directly to widgets
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password'].widget.attrs.update({'class': 'form-control'})


class TicketCreateForm(forms.ModelForm):

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'department', 'category', 'priority']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6, 'class': 'form-control'}),
            'title': forms.TextInput(attrs={
                'placeholder': 'Brief description of the issue',
                'class': 'form-control'
            }),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        department_id = None

        if self.is_bound and 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['category'].queryset = Category.objects.filter(
                    department_id=department_id, is_active=True
                ).order_by('name')
            except (ValueError, TypeError):
                self.fields['category'].queryset = Category.objects.none()

        elif self.instance.pk and self.instance.department:
            department_id = self.instance.department_id
            qs = Category.objects.filter(department_id=department_id, is_active=True)
            if self.instance.category and self.instance.category not in qs:
                qs = qs | Category.objects.filter(pk=self.instance.category.pk)
            self.fields['category'].queryset = qs.order_by('name')
        else:
            self.fields['category'].queryset = Category.objects.none()

    def save(self, commit=True):
        ticket = super().save(commit=False)
        if self.user:
            ticket.submitter = self.user
        if commit:
            ticket.save()
        return ticket


class TicketUpdateForm(forms.ModelForm):
    """Form for updating existing tickets"""

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'department', 'category', 'priority',
                  'assigned_to', 'status', 'resolution', 'tags']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6, 'class': 'form-control'}),
            'resolution': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'tags': forms.TextInput(attrs={'placeholder': 'Comma-separated tags', 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        

        # Filter assigned_to to only agents and supervisors
        agent_users = User.objects.filter(
            userprofile__is_agent=True
        ).select_related('userprofile')
        self.fields['assigned_to'].queryset = agent_users
        self.fields['assigned_to'].empty_label = "Unassigned"

        # Filter categories based on department
        if self.instance and self.instance.department:
            self.fields['category'].queryset = Category.objects.filter(
                department=self.instance.department, is_active=True
            )


class TicketCommentForm(forms.ModelForm):
    """Form for adding comments to tickets"""

    class Meta:
        model = TicketComment
        fields = ['comment', 'is_internal']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Add your comment...', 'class': 'form-control'}),
            'is_internal': forms.CheckboxInput(attrs={'class': 'form-check-input'}) # Add Bootstrap class for checkbox
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        

        # Only show internal option to agents/supervisors
        if self.user and not (hasattr(self.user, 'userprofile') and
                              (self.user.userprofile.is_agent or self.user.userprofile.is_supervisor)):
            self.fields.pop('is_internal')

    def save(self, commit=True):
        comment = super().save(commit=False)
        if self.user:
            comment.author = self.user
        if commit:
            comment.save()
        return comment


class TicketAttachmentForm(forms.ModelForm):
    """Form for uploading ticket attachments"""

    class Meta:
        model = TicketAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'accept': '.pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif,.zip', 'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (5MB limit)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError('File size cannot exceed 5MB.')

            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.zip']
            file_extension = '.' + file.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise ValidationError(f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}')

        return file

    def save(self, commit=True):
        attachment = super().save(commit=False)
        if self.user:
            attachment.uploaded_by = self.user
        if commit:
            attachment.save()
        return attachment


class TicketFilterForm(forms.Form):
    """Form for filtering tickets"""

    STATUS_CHOICES = [('', 'All Statuses')] + Ticket.STATUS_CHOICES

    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    priority = forms.ModelChoiceField(
        queryset=Priority.objects.all(),
        empty_label="All Priorities",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        empty_label="All Departments",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        empty_label="All Categories",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(userprofile__is_agent=True),
        empty_label="All Agents",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search tickets...', 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class UserProfileForm(forms.ModelForm):

    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = UserProfile
        fields = ['department', 'phone', 'job_title']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user



class KnowledgeBaseForm(forms.ModelForm):

    class Meta:
        model = KnowledgeBase
        fields = ['title', 'content', 'category', 'tags', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'rows': 10, 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={'placeholder': 'Comma-separated tags', 'class': 'form-control'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        

    def save(self, commit=True):
        article = super().save(commit=False)
        if self.user:
            article.author = self.user
        if commit:
            article.save()
        return article


class BulkTicketActionForm(forms.Form):
    """Form for bulk actions on tickets"""

    ACTION_CHOICES = [
        ('', 'Select Action'),
        ('assign', 'Assign to Agent'),
        ('status', 'Change Status'),
        ('priority', 'Change Priority'),
        ('close', 'Close Tickets'),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES, required=True, widget=forms.Select(attrs={'class': 'form-select'}))
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(userprofile__is_agent=True),
        required=False,
        empty_label="Select Agent",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(choices=Ticket.STATUS_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    priority = forms.ModelChoiceField(
        queryset=Priority.objects.all(),
        required=False,
        empty_label="Select Priority",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)