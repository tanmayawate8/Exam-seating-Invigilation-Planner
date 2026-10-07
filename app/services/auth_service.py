"""
Authentication Service Module.
Encapsulates user authentication, session binding, password verification, and audit integration.
"""

from typing import Tuple, Optional
from flask import has_request_context
from flask_login import login_user, logout_user
from sqlalchemy import or_

from app.extensions import db
from app.models.user import User
from app.models.student import Student
from app.utils.audit import log_audit


class AuthService:
    """Service layer managing authentication business logic."""

    @staticmethod
    def authenticate(
        identifier: str,
        password: str,
        remember: bool = False,
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, Optional[User], str]:
        """
        Authenticates a user via username, email, or Student Name + Enrollment Number against hashed password.
        Manages Flask-Login session and generates audit records.
        """
        ident_clean = identifier.strip()
        pwd_clean = password.strip()
        user: Optional[User] = None

        # 1. Official Polytechnic Student Authentication: Name + Enrollment Number (as initial password)
        # Find student identity using Enrollment Number (unique in institution)
        student_candidate = Student.query.filter(Student.enrollment_number == pwd_clean).first()
        if student_candidate and student_candidate.user:
            # Verify student name matches identifier (case-insensitive)
            expected_names = [
                (student_candidate.name or "").strip().lower(),
                student_candidate.full_name.strip().lower(),
            ]
            if student_candidate.first_name and student_candidate.last_name:
                expected_names.append(f"{student_candidate.first_name} {student_candidate.last_name}".strip().lower())
                expected_names.append(f"{student_candidate.last_name} {student_candidate.first_name}".strip().lower())

            if ident_clean.lower() in expected_names:
                # Student name matches! Now verify password hash against Enrollment Number
                if student_candidate.user.check_password(pwd_clean):
                    user = student_candidate.user
                else:
                    log_audit(
                        action="LOGIN_FAILED",
                        entity_type="User",
                        entity_id=str(student_candidate.user_id),
                        user_id=student_candidate.user_id,
                        details=f"Password hash check failed for student '{student_candidate.roll_number}'.",
                        ip_address=ip_address,
                    )
                    return False, None, "Invalid username/email or password."
            # If name did NOT match, do not reveal enrollment exists. Fall through to generic checks.

        # 2. Standard user credentials lookup by Username or Email
        if not user:
            user = User.query.filter(
                or_(
                    User.username.ilike(ident_clean),
                    User.email.ilike(ident_clean),
                )
            ).first()

        # 3. Lookup by Student Enrollment Number as the identifier
        if not user:
            st = Student.query.filter(
                Student.enrollment_number.ilike(ident_clean),
            ).first()
            if st and st.user:
                user = st.user

        if not user:
            log_audit(
                action="LOGIN_FAILED",
                entity_type="User",
                details=f"Login attempt with non-existent identifier: {identifier}",
                ip_address=ip_address,
            )
            return False, None, "Invalid username/email or password."

        if not user.is_active:
            log_audit(
                action="LOGIN_DISABLED_ATTEMPT",
                entity_type="User",
                entity_id=str(user.id),
                user_id=user.id,
                details=f"Disabled account '{user.username}' attempted login.",
                ip_address=ip_address,
            )
            return False, None, "Account is disabled. Please contact the administrator."

        if not user.check_password(password):
            log_audit(
                action="LOGIN_FAILED",
                entity_type="User",
                entity_id=str(user.id),
                user_id=user.id,
                details=f"Incorrect password for user '{user.username}'.",
                ip_address=ip_address,
            )
            return False, None, "Invalid username/email or password."

        # Establish secure Flask-Login session if inside an HTTP request
        if has_request_context():
            login_user(user, remember=remember)

        # Audit successful login
        log_audit(
            action="LOGIN_SUCCESS",
            entity_type="User",
            entity_id=str(user.id),
            user_id=user.id,
            details=f"User '{user.username}' logged in successfully as role {user.role}.",
            ip_address=ip_address,
        )

        return True, user, "Login successful."

    @staticmethod
    def logout(user: Optional[User], ip_address: Optional[str] = None) -> Tuple[bool, str]:
        """
        Terminates the user's active session and logs the event.
        """
        if user and user.is_authenticated:
            log_audit(
                action="LOGOUT",
                entity_type="User",
                entity_id=str(user.id),
                user_id=user.id,
                details=f"User '{user.username}' logged out.",
                ip_address=ip_address,
            )
        if has_request_context():
            logout_user()
        return True, "Logged out successfully."

    @staticmethod
    def change_password(
        user: User,
        current_password: str,
        new_password: str,
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Changes a user's password after verifying the existing password.
        """
        if not user.check_password(current_password):
            log_audit(
                action="PASSWORD_CHANGE_FAILED",
                entity_type="User",
                entity_id=str(user.id),
                user_id=user.id,
                details="Failed attempt: incorrect current password.",
                ip_address=ip_address,
            )
            return False, "Current password does not match."

        user.set_password(new_password)
        db.session.commit()

        log_audit(
            action="PASSWORD_CHANGED",
            entity_type="User",
            entity_id=str(user.id),
            user_id=user.id,
            details="Password updated successfully.",
            ip_address=ip_address,
        )

        return True, "Password changed successfully."

    @staticmethod
    def create_user(
        username: str,
        email: str,
        password: str,
        role: str = "STUDENT",
        is_active: bool = True,
        created_by_user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, Optional[User], str]:
        """
        Creates and persists a new user with hashed credentials.
        """
        normalized_username = username.strip()
        normalized_email = email.strip().lower()

        if User.query.filter(User.username.ilike(normalized_username)).first():
            return False, None, f"Username '{normalized_username}' is already in use."

        if User.query.filter(User.email.ilike(normalized_email)).first():
            return False, None, f"Email '{normalized_email}' is already registered."

        user = User(
            username=normalized_username,
            email=normalized_email,
            role=role.upper(),
            is_active=is_active,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        log_audit(
            action="USER_CREATED",
            entity_type="User",
            entity_id=str(user.id),
            user_id=created_by_user_id,
            details=f"User '{user.username}' created with role '{user.role}'.",
            ip_address=ip_address,
        )

        return True, user, "User created successfully."
