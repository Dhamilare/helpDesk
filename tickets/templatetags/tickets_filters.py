from django import template

register = template.Library()

@register.filter
def can_edit_ticket(ticket, user):
    """
    Checks if the given user has permission to edit the specific ticket.
    This logic mirrors the can_edit_ticket method in TicketDetailView.
    """
    if not user.is_authenticated:
        return False

    if hasattr(user, 'userprofile'):
        if user.userprofile.is_supervisor:
            return True
        elif user.userprofile.is_agent:
            return (ticket.assigned_to == user or
                    ticket.department == user.userprofile.department)

    return ticket.submitter == user