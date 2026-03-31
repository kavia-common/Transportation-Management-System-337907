"""
Transportation Management System - Customer Website Blueprint.

Serves the public-facing customer website with landing page
and parcel tracking functionality.

Flow name: CustomerWebsiteFlow
Entrypoint: landing Blueprint registered at /home
"""

from flask import Blueprint, render_template

landing = Blueprint('landing', __name__, template_folder='templates', static_folder='static')


# PUBLIC_INTERFACE
@landing.route("/")
def landing_page():
    """
    Render the customer-facing landing page.

    Returns:
        Rendered index.html template with tracking, services, and contact sections.
    """
    return render_template('index.html')
