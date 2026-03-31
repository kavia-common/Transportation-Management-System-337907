"""
Transportation Management System - Admin Panel Blueprint.

Provides the admin web interface for managing the TMS database,
including login, dashboard, and CRUD operations via the panel.

Flow name: AdminPanelFlow
Entrypoint: admin_panel Blueprint registered at /admin
"""

import sys
import os
import logging
import datetime

from flask import (
    Blueprint, render_template, request, redirect,
    session, make_response, jsonify
)

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from extensions import db

logger = logging.getLogger(__name__)

admin_panel = Blueprint(
    'admin_panel', __name__,
    template_folder='templates',
    static_folder='static'
)


# PUBLIC_INTERFACE
@admin_panel.route("/", methods=['GET', 'POST'])
def login_page():
    """
    Admin login page - handles both rendering the login form and processing login.

    GET: Renders login form (redirects to main if already logged in).
    POST: Validates credentials against the Admins table.

    Returns:
        Rendered login template or redirect to main dashboard.
    """
    if request.method == 'GET':
        if 'username' in session:
            return redirect("main")
        else:
            return render_template('login.html', error_message='')
    elif request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        try:
            conn = db.connection
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM Admins WHERE Username=? AND Password=?",
                (username, password)
            )
            row = cur.fetchone()
            if not row:
                conn.close()
                error_message = 'Invalid username or password'
                return render_template('login.html', error_message=error_message)
            else:
                session['username'] = username
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cur.execute(
                    "UPDATE Admins SET LastConnected=? WHERE Username=?",
                    (now, username)
                )
                conn.commit()
                conn.close()
                return redirect("main")
        except Exception as e:
            logger.error("AdminPanelFlow: login error: %s", str(e))
            return render_template('login.html', error_message='System error during login')


# PUBLIC_INTERFACE
@admin_panel.route("/main")
def main_page():
    """
    Admin dashboard main page.

    Requires active session. Redirects to login if not authenticated.

    Returns:
        Rendered main dashboard template.
    """
    if 'username' in session:
        return render_template('main.html', user_name=session['username'])
    else:
        return redirect("../admin")


# PUBLIC_INTERFACE
@admin_panel.route('/logout')
def logout():
    """
    Log out the current admin user.

    Clears the session and redirects to login page.
    """
    session.pop('username', None)
    return redirect("../admin")


# PUBLIC_INTERFACE
@admin_panel.route('/changepassword', methods=['PUT'])
def change_password():
    """
    Change the admin user's password.

    Request params:
        oldPassowrd: Current password (note: preserving original typo for compatibility).
        newPassword: New password.

    Returns:
        JSON with status and message.
    """
    if 'username' in session:
        if request.method == 'PUT':
            data = request.args.to_dict()
            if request.is_json:
                data.update(request.get_json(silent=True) or {})

            old_pas = data.get('oldPassowrd', '')
            new_pas = data.get('newPassword', '')

            try:
                conn = db.connection
                cur = conn.cursor()
                cur.execute(
                    "SELECT * FROM Admins WHERE Username=? AND Password=?",
                    (session['username'], old_pas)
                )
                if not cur.fetchone():
                    conn.close()
                    return make_response(jsonify({
                        "Status": "Error",
                        "Message": "Old password invalid"
                    }))
                else:
                    cur.execute(
                        "UPDATE Admins SET Password=? WHERE Username=?",
                        (new_pas, session['username'])
                    )
                    conn.commit()
                    conn.close()
                    return make_response(jsonify({
                        "Status": "Success",
                        "Message": "Password changed!"
                    }))
            except Exception as e:
                logger.error("AdminPanelFlow: change password error: %s", str(e))
                return make_response(jsonify({
                    "Status": "Error",
                    "Message": "System error"
                }))
    else:
        return redirect("../admin")
