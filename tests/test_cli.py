"""Tests for Flask CLI commands (create-admin, seed-reference-data)."""

import pytest

from app.models import User


class TestCreateAdminCommand:
    def test_create_admin_success(self, runner):
        # click.prompt reads from stdin; the test runner feeds it via input.
        result = runner.invoke(args=["create-admin", "newadmin"], input="strongpass123\nstrongpass123\n")
        assert result.exit_code == 0, result.output
        assert "Administrator 'newadmin' created." in result.output
        user = User.query.filter_by(username="newadmin").first()
        assert user is not None
        assert user.is_admin is True
        assert user.password != "strongpass123"  # hashed, not plaintext

    def test_create_admin_rejects_duplicate_without_promote(self, runner, create_user):
        create_user(username="taken")
        result = runner.invoke(args=["create-admin", "taken"], input="strongpass123\nstrongpass123\n")
        assert result.exit_code == 0
        assert "already exists" in result.output
        # The existing user must NOT have been turned into an admin silently.
        user = User.query.filter_by(username="taken").first()
        assert user.is_admin is False

    def test_create_admin_rejects_weak_password(self, runner):
        result = runner.invoke(args=["create-admin", "weakuser"], input="short\nshort\n")
        assert result.exit_code == 0
        assert "at least 8 characters" in result.output
        assert User.query.filter_by(username="weakuser").first() is None

    def test_create_admin_rejects_invalid_username(self, runner):
        result = runner.invoke(args=["create-admin", "ab"], input="strongpass123\nstrongpass123\n")
        assert result.exit_code == 0
        assert "3–80 letters" in result.output
        assert User.query.filter_by(username="ab").first() is None

    def test_create_admin_password_mismatch_aborts(self, runner):
        # confirmation_prompt re-asks once on mismatch, then aborts.
        result = runner.invoke(args=["create-admin", "mismatch"],
                               input="strongpass123\ndifferent123\ndifferent123\n")
        # Mismatch triggers a retry; second pair still differs from first → abort.
        assert "Administrator" not in result.output

    def test_promote_existing_user(self, runner, create_user):
        user = create_user(username="regularuser")
        assert user.is_admin is False
        result = runner.invoke(args=["create-admin", "regularuser", "--promote"])
        assert result.exit_code == 0, result.output
        assert "Promoted" in result.output
        assert User.query.filter_by(username="regularuser").first().is_admin is True

    def test_promote_nonexistent_user_fails(self, runner):
        result = runner.invoke(args=["create-admin", "ghostuser", "--promote"])
        assert result.exit_code == 0
        assert "no user named" in result.output

    def test_promote_already_admin_is_noop(self, runner, create_user):
        create_user(username="alreadyadmin", is_admin=True)
        result = runner.invoke(args=["create-admin", "alreadyadmin", "--promote"])
        assert result.exit_code == 0
        assert "already an administrator" in result.output


class TestSeedReferenceDataCommand:
    def test_seed_command_runs(self, runner):
        result = runner.invoke(args=["seed-reference-data"])
        assert result.exit_code == 0, result.output
        assert "Reference data seeded." in result.output
