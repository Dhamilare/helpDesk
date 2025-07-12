from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class Category(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='categories')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.department.name} - {self.name}"
    
    class Meta:
        ordering = ['department', 'name']
        verbose_name_plural = 'Categories'
        unique_together = ['name', 'department']


class Priority(models.Model):
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
        (5, 'Emergency'),
    ]
    
    name = models.CharField(max_length=50, unique=True)
    level = models.IntegerField(choices=PRIORITY_CHOICES, unique=True)
    response_time = models.IntegerField(help_text="Response time in hours")
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['level']
        verbose_name_plural = 'Priorities'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    is_agent = models.BooleanField(default=False)
    is_supervisor = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.job_title}"


class Ticket(models.Model):
    """Main ticket model"""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic ticket information
    title = models.CharField(max_length=200)
    description = models.TextField()
    ticket_number = models.CharField(max_length=20, unique=True, blank=True)
    
    # Relationships
    submitter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_tickets')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    priority = models.ForeignKey(Priority, on_delete=models.CASCADE)
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional fields
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    resolution = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        # Generate ticket number if not exists
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
        
        # Set due date based on priority
        if not self.due_date and self.priority:
            self.due_date = timezone.now() + timezone.timedelta(hours=self.priority.response_time)
        
        # Set resolved/closed timestamps
        if self.status == 'resolved' and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status == 'closed' and not self.closed_at:
            self.closed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def generate_ticket_number(self):
        from django.utils.crypto import get_random_string
        import string
        
        while True:
            ticket_num = f"TK{get_random_string(8, string.digits)}"
            if not Ticket.objects.filter(ticket_number=ticket_num).exists():
                return ticket_num
    
    def get_absolute_url(self):
        return reverse('ticket_detail', kwargs={'pk': self.pk})
    
    def is_overdue(self):
        """Check if ticket is overdue"""
        if self.due_date and self.status not in ['resolved', 'closed']:
            return timezone.now() > self.due_date
        return False
    
    def time_since_created(self):
        """Calculate time since ticket was created"""
        return timezone.now() - self.created_at
    
    def __str__(self):
        return f"{self.ticket_number} - {self.title}"
    
    class Meta:
        ordering = ['-created_at']


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="Internal notes not visible to submitter")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Comment on {self.ticket.ticket_number} by {self.author.username}"
    
    class Meta:
        ordering = ['created_at']


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='ticket_attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField()
    
    def save(self, *args, **kwargs):
        if self.file and not self.filename:
            self.filename = self.file.name
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.filename} - {self.ticket.ticket_number}"
    
    class Meta:
        ordering = ['-uploaded_at']


class TicketHistory(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    field_changed = models.CharField(max_length=50, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.action} on {self.ticket.ticket_number} by {self.user.username}"
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Ticket Histories'


class KnowledgeBase(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    tags = models.CharField(max_length=200, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)
    views = models.IntegerField(default=0)
    helpful_votes = models.IntegerField(default=0)
    not_helpful_votes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('kb_article', kwargs={'pk': self.pk})
    
    class Meta:
        ordering = ['-created_at']


class SLA(models.Model):
    name = models.CharField(max_length=100, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    priority = models.ForeignKey(Priority, on_delete=models.CASCADE)
    response_time = models.IntegerField(help_text="Response time in hours")
    resolution_time = models.IntegerField(help_text="Resolution time in hours")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - {self.department.name}"
    
    class Meta:
        ordering = ['department', 'priority__level']
        verbose_name = 'SLA'
        verbose_name_plural = 'SLAs'