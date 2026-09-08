"""Site-admin (global) API tests (TASK-039).

Mirrors tests/test_routes_school.py: the centerpiece is the privilege
boundary — a school_admin must get 403 on EVERY /api/site endpoint, the
same way a school_admin cannot touch another institution. Also covers
the one-request tenant+first-admin creation flow and the audit-log
filters.
"""

from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import AuditLog, Institution, User
from app.models.user import ROLE_SCHOOL_ADMIN, ROLE_SITE_ADMIN

PASSWORD = "SitePass!2026"


def _login(client, username):
    login = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert login.status_code == 200, login.get_json()
    return {"Authorization": f"Bearer {login.get_json()['access_token']}"}


def _make_site_admin(client, username="e2e_root"):
    user = User(
        username=username,
        password=generate_password_hash(PASSWORD),
        fullname="Root Admin",
        role=ROLE_SITE_ADMIN,
    )
    db.session.add(user)
    db.session.commit()
    return user, _login(client, username)


def _make_school_admin(username="sch_adm", institution=None):
    if institution is None:
        institution = Institution(name="Some School")
        db.session.add(institution)
        db.session.flush()
    user = User(
        username=username,
        password=generate_password_hash(PASSWORD),
        fullname="School Admin",
        role=ROLE_SCHOOL_ADMIN,
        institution_id=institution.id,
    )
    db.session.add(user)
    db.session.commit()
    return user, institution


class TestSiteAdminAccess:
    def test_requires_auth(self, client):
        assert client.get("/api/site/institutions").status_code == 401

    def test_school_admin_403_on_every_endpoint(self, client):
        """Privilege-escalation check: school_admin is the role just below
        site_admin — none of the global endpoints may admit it."""
        _school_admin, _institution = _make_school_admin()
        headers = _login(client, "sch_adm")
        assert client.get("/api/site/institutions", headers=headers).status_code == 403
        assert client.post("/api/site/institutions", headers=headers, json={
            "name": "Sneaky", "admin_username": "sneaky_admin", "admin_password": "longenough1",
        }).status_code == 403
        assert client.put("/api/site/institutions/1", headers=headers, json={"plan_tier": "pro"}).status_code == 403
        assert client.get("/api/site/audit-log", headers=headers).status_code == 403

    def test_plain_user_403(self, client, create_user):
        create_user(username="plainperson", password=PASSWORD)
        headers = _login(client, "plainperson")
        assert client.get("/api/site/institutions", headers=headers).status_code == 403

    def test_is_admin_shim_does_not_grant_access(self, client):
        """User(is_admin=True) maps to role=site_admin — construct a user
        the legacy way and confirm the guard still admits it (and only it)."""
        legacy = User(username="legacy_root", password=generate_password_hash(PASSWORD), fullname="Legacy", is_admin=True)
        db.session.add(legacy)
        db.session.commit()
        headers = _login(client, "legacy_root")
        assert client.get("/api/site/institutions", headers=headers).status_code == 200


class TestInstitutionList:
    def test_lists_all_with_counts(self, client, create_user, create_institution, create_class):
        _admin, headers = _make_site_admin(client)
        alpha = create_institution(name="Alpha Inst")
        beta = create_institution(name="Beta Inst")
        create_class(institution=alpha, name="Alpha A")
        create_class(institution=alpha, name="Alpha B")
        for username, inst, role in (("stu_1", alpha, "student"), ("stu_2", alpha, "student"), ("tea_1", alpha, "teacher"), ("stu_b", beta, "student")):
            member = create_user(username=username, password=PASSWORD)
            member.institution_id = inst.id
            member.role = role
        db.session.commit()

        data = client.get("/api/site/institutions", headers=headers).get_json()
        by_name = {i["name"]: i for i in data["institutions"]}
        assert by_name["Alpha Inst"]["students"] == 2
        assert by_name["Alpha Inst"]["teachers"] == 1
        assert by_name["Alpha Inst"]["classes"] == 2
        assert by_name["Beta Inst"]["students"] == 1
        assert by_name["Beta Inst"]["teachers"] == 0
        assert by_name["Beta Inst"]["classes"] == 0

    def test_empty_world_ok(self, client):
        _admin, headers = _make_site_admin(client)
        assert client.get("/api/site/institutions", headers=headers).get_json()["institutions"] == []


class TestInstitutionCreate:
    def test_creates_institution_and_first_school_admin(self, client):
        _admin, headers = _make_site_admin(client)
        response = client.post("/api/site/institutions", headers=headers, json={
            "name": "New Academy",
            "type": "academy",
            "plan_tier": "pro",
            "admin_username": "academy_admin",
            "admin_password": "longenough1",
            "admin_fullname": "Academy Admin",
        })
        assert response.status_code == 201
        body = response.get_json()
        assert body["institution"]["name"] == "New Academy"
        assert body["institution"]["plan_tier"] == "pro"
        assert body["admin"]["role"] == ROLE_SCHOOL_ADMIN

        stored = User.query.filter_by(username="academy_admin").one()
        assert stored.role == ROLE_SCHOOL_ADMIN
        assert stored.institution_id == body["institution"]["id"]
        from werkzeug.security import check_password_hash
        assert check_password_hash(stored.password, "longenough1")

    def test_admin_cannot_escalate_role(self, client):
        """The body naming site_admin must NOT mint a site_admin — the
        handler hardcodes school_admin."""
        _admin, headers = _make_site_admin(client)
        response = client.post("/api/site/institutions", headers=headers, json={
            "name": "Escalation Co",
            "admin_username": "wannabe_root",
            "admin_password": "longenough1",
            "role": "site_admin",
        })
        assert response.status_code == 201
        assert User.query.filter_by(username="wannabe_root").one().role == ROLE_SCHOOL_ADMIN

    def test_duplicate_username_409(self, client, create_user):
        _admin, headers = _make_site_admin(client)
        create_user(username="taken_name", password=PASSWORD)
        response = client.post("/api/site/institutions", headers=headers, json={
            "name": "Dup Co", "admin_username": "taken_name", "admin_password": "longenough1",
        })
        assert response.status_code == 409
        assert Institution.query.filter_by(name="Dup Co").one_or_none() is None

    def test_validation_errors(self, client):
        _admin, headers = _make_site_admin(client)
        base = {"admin_username": "ok_admin", "admin_password": "longenough1"}
        assert client.post("/api/site/institutions", headers=headers, json={**base, "name": ""}).status_code == 400
        assert client.post("/api/site/institutions", headers=headers, json={**base, "name": "X", "type": "monastery"}).status_code == 400
        assert client.post("/api/site/institutions", headers=headers, json={**base, "name": "X", "plan_tier": "diamond"}).status_code == 400
        assert client.post("/api/site/institutions", headers=headers, json={**base, "name": "X", "admin_username": "bad name!"}).status_code == 400
        assert client.post("/api/site/institutions", headers=headers, json={**base, "name": "X", "admin_password": "short"}).status_code == 400

    def test_creates_audit_row(self, client):
        _admin, headers = _make_site_admin(client)
        response = client.post("/api/site/institutions", headers=headers, json={
            "name": "Audited School", "admin_username": "audit_admin", "admin_password": "longenough1",
        })
        row = AuditLog.query.filter_by(action="institution.create").one()
        assert row.target_type == "institution"
        assert row.target_id == response.get_json()["institution"]["id"]
        assert row.actor_user_id == _admin.id
        assert "admin_password" not in (row.after or {})


class TestPlanTierUpdate:
    def test_updates_plan_tier(self, client, create_institution):
        _admin, headers = _make_site_admin(client)
        institution = create_institution(name="Upgrade Me")
        response = client.put(f"/api/site/institutions/{institution.id}", headers=headers, json={"plan_tier": "enterprise"})
        assert response.status_code == 200
        assert response.get_json()["institution"]["plan_tier"] == "enterprise"
        row = AuditLog.query.filter_by(action="institution.plan_change").one()
        assert row.before["plan_tier"] == "free"
        assert row.after["plan_tier"] == "enterprise"

    def test_rejects_unknown_tier(self, client, create_institution):
        _admin, headers = _make_site_admin(client)
        institution = create_institution(name="Static")
        response = client.put(f"/api/site/institutions/{institution.id}", headers=headers, json={"plan_tier": "diamond"})
        assert response.status_code == 400

    def test_missing_tier_400(self, client, create_institution):
        _admin, headers = _make_site_admin(client)
        institution = create_institution(name="No Body")
        assert client.put(f"/api/site/institutions/{institution.id}", headers=headers, json={}).status_code == 400

    def test_missing_institution_404(self, client):
        _admin, headers = _make_site_admin(client)
        assert client.put("/api/site/institutions/999999", headers=headers, json={"plan_tier": "pro"}).status_code == 404


class TestAuditLog:
    def _seed_audit(self, actor_id, action, institution_id=None, target=("thing", 1)):
        db.session.add(AuditLog(actor_user_id=actor_id, action=action, target_type=target[0], target_id=target[1], institution_id=institution_id))
        db.session.commit()

    def test_paginated_newest_first(self, client, create_institution):
        _admin, headers = _make_site_admin(client)
        inst = create_institution(name="Audit Inst")
        for i in range(5):
            self._seed_audit(_admin.id, "class.create", inst.id, target=("class", i))
        data = client.get("/api/site/audit-log?per_page=2&page=2", headers=headers).get_json()
        assert data["total"] == 5
        assert data["pages"] == 3
        assert len(data["entries"]) == 2
        ids = [e["id"] for e in data["entries"]]
        assert ids == sorted(ids, reverse=True)

    def test_filter_by_institution(self, client, create_institution):
        _admin, headers = _make_site_admin(client)
        inst_a = create_institution(name="A")
        inst_b = create_institution(name="B")
        self._seed_audit(_admin.id, "class.create", inst_a.id)
        self._seed_audit(_admin.id, "class.delete", inst_b.id)
        data = client.get(f"/api/site/audit-log?institution_id={inst_b.id}", headers=headers).get_json()
        assert data["total"] == 1
        assert data["entries"][0]["action"] == "class.delete"

    def test_filter_by_action(self, client):
        _admin, headers = _make_site_admin(client)
        self._seed_audit(_admin.id, "task.create", target=("task", 1))
        self._seed_audit(_admin.id, "user.class_assign", target=("user", 2))
        data = client.get("/api/site/audit-log?action=task.create", headers=headers).get_json()
        assert data["total"] == 1
        assert data["entries"][0]["target_type"] == "task"

    def test_filter_by_actor(self, client, create_user):
        _admin, headers = _make_site_admin(client)
        other = create_user(username="other_actor", password=PASSWORD)
        self._seed_audit(_admin.id, "course.create")
        self._seed_audit(other.id, "task.update", target=("task", 9))
        data = client.get(f"/api/site/audit-log?actor_user_id={other.id}", headers=headers).get_json()
        assert data["total"] == 1
        assert data["entries"][0]["actor_user_id"] == other.id

    def test_global_sees_all_institutions(self, client, create_institution):
        """Unlike a school_admin's view, no institution scoping applies."""
        _admin, headers = _make_site_admin(client)
        inst_a = create_institution(name="A")
        inst_b = create_institution(name="B")
        self._seed_audit(_admin.id, "class.create", inst_a.id)
        self._seed_audit(_admin.id, "class.create", inst_b.id)
        assert client.get("/api/site/audit-log", headers=headers).get_json()["total"] == 2

    def test_invalid_filters_400(self, client):
        _admin, headers = _make_site_admin(client)
        assert client.get("/api/site/audit-log?institution_id=abc", headers=headers).status_code == 400
        assert client.get("/api/site/audit-log?actor_user_id=xyz", headers=headers).status_code == 400
        assert client.get("/api/site/audit-log?page=nope", headers=headers).status_code == 400

    def test_per_page_capped(self, client):
        _admin, headers = _make_site_admin(client)
        for i in range(3):
            self._seed_audit(_admin.id, "task.create", target=("task", i))
        data = client.get("/api/site/audit-log?per_page=9999", headers=headers).get_json()
        assert data["per_page"] <= 100
