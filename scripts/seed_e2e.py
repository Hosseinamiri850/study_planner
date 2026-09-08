"""E2E seed: two institutions with school_admins, members, classes.

Run with the app's config already pointed at an EPHEMERAL database, e.g.:

    DATABASE_URL=sqlite:///e2e.db flask --app app db upgrade && \
    DATABASE_URL=sqlite:///e2e.db flask --app app seed-e2e

Idempotent: clears the school fixtures' rows before inserting. Never run
against a shared/production database — it deletes rows matching its own
usernames.
"""

import click
from flask.cli import with_appcontext
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Class, Institution, User
from app.models.user import ROLE_SCHOOL_ADMIN


@click.command("seed-e2e")
@with_appcontext
def seed_e2e():
    """Seed the two-institution school_admin E2E fixture set."""
    password_hash = generate_password_hash("E2ePass!2026")
    usernames = [
        "e2e_admin_a", "e2e_teacher_a", "e2e_stu_a1", "e2e_stu_a2",
        "e2e_admin_b", "e2e_teacher_b", "e2e_stu_b1",
        # TASK-040: support flow fixtures
        "e2e_support", "e2e_site_root",
    ]
    # Query.delete() bypasses ORM cascades, so classes must be swept
    # explicitly — both the fixture institutions' classes and any rows
    # orphaned by earlier non-cascading runs.
    fixture_ids = select(Institution.id).where(Institution.name.in_(["E2E Alpha", "E2E Beta"]))
    Class.query.filter(Class.institution_id.in_(fixture_ids)).delete(synchronize_session=False)
    Class.query.filter(~Class.institution_id.in_(select(Institution.id))).delete(synchronize_session=False)
    Institution.query.filter(Institution.name.in_(["E2E Alpha", "E2E Beta"])).delete(synchronize_session=False)
    User.query.filter(User.username.in_(usernames)).delete(synchronize_session=False)
    db.session.commit()

    alpha = Institution(name="E2E Alpha", type="school")
    beta = Institution(name="E2E Beta", type="school")
    db.session.add_all([alpha, beta])
    db.session.flush()

    admin_a = User(username="e2e_admin_a", password=password_hash, fullname="Admin Alpha", role=ROLE_SCHOOL_ADMIN, institution_id=alpha.id)
    admin_b = User(username="e2e_admin_b", password=password_hash, fullname="Admin Beta", role=ROLE_SCHOOL_ADMIN, institution_id=beta.id)
    teacher_a = User(username="e2e_teacher_a", password=password_hash, fullname="Teacher Alpha", role="teacher", institution_id=alpha.id)
    teacher_b = User(username="e2e_teacher_b", password=password_hash, fullname="Teacher Beta", role="teacher", institution_id=beta.id)
    stu_a1 = User(username="e2e_stu_a1", password=password_hash, fullname="Stu Alpha One", role="student", institution_id=alpha.id)
    stu_a2 = User(username="e2e_stu_a2", password=password_hash, fullname="Stu Alpha Two", role="student", institution_id=alpha.id)
    stu_b1 = User(username="e2e_stu_b1", password=password_hash, fullname="Stu Beta One", role="student", institution_id=beta.id)
    support = User(username="e2e_support", password=password_hash, fullname="Support Agent", role="support")
    site_root = User(username="e2e_site_root", password=password_hash, fullname="Site Root", role="site_admin")
    db.session.add_all([admin_a, admin_b, teacher_a, teacher_b, stu_a1, stu_a2, stu_b1, support, site_root])
    db.session.flush()

    class_a = Class(institution_id=alpha.id, name="Alpha Pre-seeded", grade_level="9")
    class_b = Class(institution_id=beta.id, name="Beta Pre-seeded", grade_level="10")
    db.session.add_all([class_a, class_b])
    db.session.flush()

    stu_a1.class_id = class_a.id
    db.session.commit()
    click.echo(
        f"E2E seeded: alpha={alpha.id} (class_a={class_a.id}, stu_a1 assigned), beta={beta.id} "
        f"(class_b={class_b.id}); password for every fixture: E2ePass!2026"
    )
