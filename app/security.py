"""Access-control helpers."""
from functools import wraps

from flask import abort
from flask_login import current_user


def admin_required(view):
    """Allow moderators AND shop-owners (admin role)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def moderator_required(view):
    """Only system moderators."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_moderator:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def owner_required(view):
    """Shop owners (admin) or moderators — identical rule to admin_required."""
    return admin_required(view)


def scoped_query(model):
    """Return a query filtered to the current user's shop.

    Moderators see everything.  Shop owners / workers see only their shop.
    """
    q = model.query
    if not current_user.is_moderator and current_user.shop_id:
        q = q.filter_by(shop_id=current_user.shop_id)
    return q
