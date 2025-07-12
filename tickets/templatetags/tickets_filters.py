from django import template

register = template.Library()

@register.filter
def can_edit_ticket(ticket, user):
    if not user.is_authenticated:
        return False
    
    # NEW CONDITION: User must be staff to edit any ticket
    if not user.is_staff:
        return False

    if user.is_superuser:
        return True # Superusers can always edit

    if hasattr(user, 'userprofile'):
        if user.userprofile.is_supervisor:
            return True # Supervisors can always edit
        
        if user.userprofile.is_agent:
            # Agents can edit tickets assigned to them or in their department
            if ticket.assigned_to == user or ticket.department == user.userprofile.department:
                return True

    # If the user is neither supervisor/agent but is staff and the submitter
    if ticket.submitter == user:
        return True 
        
    return False
