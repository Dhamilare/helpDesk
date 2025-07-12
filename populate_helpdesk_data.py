from django.utils import timezone
from django.contrib.auth.models import User
from tickets.models import (
    Department, Category, Priority, SLA, UserProfile,
    Ticket, TicketComment, TicketAttachment, TicketHistory, KnowledgeBase
)
from django.core.files.base import ContentFile
import random
import io


# === Create Departments ===
departments = {
    "IT Support": {"description": "Handles IT issues", "email": "it@demo.com"},
    "HR": {"description": "HR department", "email": "hr@demo.com"},
    "Facilities": {"description": "Facility-related tasks", "email": "facilities@demo.com"},
}
dept_objs = {}
for name, data in departments.items():
    dept, _ = Department.objects.get_or_create(name=name, defaults=data)
    dept_objs[name] = dept


# === Create Priorities ===
priority_levels = [
    {"name": "Low", "level": 1, "response_time": 72},
    {"name": "Medium", "level": 2, "response_time": 24},
    {"name": "High", "level": 3, "response_time": 12},
    {"name": "Critical", "level": 4, "response_time": 6},
    {"name": "Emergency", "level": 5, "response_time": 2},
]
priority_objs = {}
for p in priority_levels:
    obj, _ = Priority.objects.get_or_create(name=p["name"], level=p["level"], defaults={"response_time": p["response_time"]})
    priority_objs[p["name"]] = obj


# === Create Categories ===
categories = [
    {"name": "Software", "department": "IT Support"},
    {"name": "Hardware", "department": "IT Support"},
    {"name": "Leave Request", "department": "HR"},
    {"name": "Recruitment", "department": "HR"},
    {"name": "Cleaning", "department": "Facilities"},
    {"name": "Repair", "department": "Facilities"},
]
for cat in categories:
    Category.objects.get_or_create(
        name=cat["name"],
        department=dept_objs[cat["department"]],
    )


# === Create Users and UserProfiles ===
users = [
    {"username": "agent1", "email": "agent1@example.com", "is_agent": True},
    {"username": "supervisor1", "email": "supervisor1@example.com", "is_supervisor": True},
    {"username": "staff1", "email": "staff1@example.com"},
]
user_objs = {}
for u in users:
    user, _ = User.objects.get_or_create(username=u["username"], defaults={"email": u["email"]})
    user.set_password("pass1234")
    user.save()
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "department": random.choice(list(dept_objs.values())),
            "job_title": "Support Staff",
            "is_agent": u.get("is_agent", False),
            "is_supervisor": u.get("is_supervisor", False),
        }
    )
    user_objs[u["username"]] = user


# === Create SLAs ===
slas = [
    {"name": "IT-Critical", "department": "IT Support", "priority": "Critical", "response_time": 4, "resolution_time": 8},
    {"name": "HR-Standard", "department": "HR", "priority": "Medium", "response_time": 24, "resolution_time": 48},
]
for s in slas:
    SLA.objects.get_or_create(
        name=s["name"],
        department=dept_objs[s["department"]],
        priority=priority_objs[s["priority"]],
        defaults={"response_time": s["response_time"], "resolution_time": s["resolution_time"]}
    )


# === Create Tickets ===
for i in range(1, 4):
    ticket = Ticket.objects.create(
        title=f"Test Ticket #{i}",
        description="This is a test ticket created by a script.",
        submitter=user_objs["staff1"],
        department=random.choice(list(dept_objs.values())),
        category=Category.objects.order_by('?').first(),
        priority=random.choice(list(priority_objs.values())),
        status=random.choice(['open', 'in_progress', 'resolved']),
    )
    print(f"✅ Created Ticket: {ticket.ticket_number}")


# === Add Comments to Tickets ===
for ticket in Ticket.objects.all():
    TicketComment.objects.create(
        ticket=ticket,
        author=user_objs["agent1"],
        comment="This is a support agent comment.",
        is_internal=False
    )


# === Add Attachment to Ticket ===
for ticket in Ticket.objects.all():
    fake_file = ContentFile(b"Example file content", name="example.txt")
    TicketAttachment.objects.create(
        ticket=ticket,
        file=fake_file,
        filename="example.txt",
        uploaded_by=user_objs["agent1"],
        file_size=fake_file.size
    )


# === Add Ticket History ===
for ticket in Ticket.objects.all():
    TicketHistory.objects.create(
        ticket=ticket,
        user=user_objs["agent1"],
        action="Status Changed",
        field_changed="status",
        old_value="open",
        new_value="in_progress"
    )


# === Create Knowledge Base Articles ===
for i in range(1, 4):
    KnowledgeBase.objects.create(
        title=f"KB Article #{i}",
        content="This is a knowledge base article.",
        category=Category.objects.order_by('?').first(),
        tags="how-to, faq",
        author=user_objs["supervisor1"],
        is_published=True
    )

print("🎉 All helpdesk models populated successfully.")
