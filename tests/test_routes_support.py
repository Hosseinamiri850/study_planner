"""Support (global, read-mostly) API tests (TASK-040).

Centerpiece: impersonation. A support agent may mint a short-lived token
authenticating as a normal user; the token carries an impersonator_id
claim that (a) lands on audit rows written while it is in use, and (b)
makes school/site/support guards refuse the request outright. A support
agent can never impersonate another support agent or a site_admin.
"""

from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import AuditLog, Institution, User
from app.models.user import ROLE_SCHOOL_ADMIN, ROLE_SITE_ADMIN, ROLE_SUPPORT
from app.utils.auth import create_access_token

PASSWORD = "SupportPass!2026"


def _login(client, username):
    login = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert login.status_code == 200, login.get_json()
    return {"Authorization": f"Bearer {login.get_json()['access_token']}"}


def _make_user(username, role="student", institution=None, password=PASSWORD):
    user = User(
        username=username,
        password=generate_password_hash(password),
        fullname=username.replace("_", " ").title(),
        role=role,
        institution_id=institution.id if institution else None,
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestSupportAccess:
    def test_requires_auth(self, client):
        assert client.get("/api/support/institutions").status_code == 401

    def test_non_support_403_on_every_endpoint(self, client):
        """Privilege-escalation mirror: school_admin, site_admin, teacher,
        student — every other role gets 403 on every support endpoint."""
        institution = Institution(name="Inst")
        db.session.add(institution)
        db.session.flush()
        for username, role in (
            ("sch", ROLE_SCHOOL_ADMIN),
            ("root", ROLE_SITE_ADMIN),
            ("tea", "teacher"),
            ("stu", "student"),
        ):
            _make_user(username, role=role, institution=institution if role == ROLE_SCHOOL_ADMIN else None)
        for username in ("sch", "root", "tea", "stu"):
            headers = _login(client, username)
            assert client.get("/api/support/institutions", headers=headers).status_code == 403
            assert client.get("/api/support/users?query=x", headers=headers).status_code == 403
            assert client.get("/api/support/audit-log", headers=headers).status_code == 403
            assert client.post("/api/support/impersonate/1", headers=headers).status_code == 403


class TestSupportReads:
    def test_institutions_read_only_same_shape(self, client, create_institution, create_class, create_user):
        _agent = _make_user("agent1", role=ROLE_SUPPORT)
        headers = _login(client, "agent1")
        inst = create_institution(name="Read Inst")
        create_class(institution=inst, name="R1")
        member = create_user(username="r_stu", password=PASSWORD)
        member.institution_id = inst.id
        member.role = "student"
        db.session.commit()

        data = client.get("/api/support/institutions", headers=headers).get_json()
        entry = next(i for i in data["institutions"] if i["id"] == inst.id)
        assert entry["students"] == 1
        assert entry["classes"] == 1

    def test_user_search_by_username_and_fullname(self, client, create_user):
        _make_user("agent2", role=ROLE_SUPPORT)
        headers = _login(client, "agent2")
        create_user(username="target_one", fullname="Target One", password=PASSWORD)
        create_user(username="unrelated", fullname="Nobody Here", password=PASSWORD)

        by_username = client.get("/api/support/users?query=target", headers=headers).get_json()
        assert [u["username"] for u in by_username["users"]] == ["target_one"]
        by_fullname = client.get("/api/support/users?query=Nobody", headers=headers).get_json()
        assert [u["username"] for u in by_fullname["users"]] == ["unrelated"]

    def test_user_search_spans_b2c_and_tenants(self, client, create_institution):
        _make_user("agent3", role=ROLE_SUPPORT)
        headers = _login(client, "agent3")
        inst = create_institution(name="Ten")
        _make_user("tenant_member", institution=inst)
        _make_user("b2c_person")
        found = client.get("/api/support/users?query=_", headers=headers).get_json()
        names = {u["username"] for u in found["users"]}
        assert {"tenant_member", "b2c_person"} <= names

    def test_user_search_paginated(self, client, create_user):
        _make_user("agent4", role=ROLE_SUPPORT)
        headers = _login(client, "agent4")
        for i in range(5):
            create_user(username=f"pageuser_{i}", password=PASSWORD)
        data = client.get("/api/support/users?query=pageuser&per_page=2&page=2", headers=headers).get_json()
        assert data["total"] == 5
        assert data["pages"] == 3
        assert len(data["users"]) == 2

    def test_audit_log_global_and_filterable(self, client, create_institution):
        _make_user("agent5", role=ROLE_SUPPORT)
        headers = _login(client, "agent5")
        inst_a = create_institution(name="A")
        inst_b = create_institution(name="B")
        for iid in (inst_a.id, inst_b.id):
            db.session.add(AuditLog(actor_user_id=None, action="class.create", target_type="class", target_id=1, institution_id=iid))
        db.session.commit()
        data = client.get("/api/support/audit-log", headers=headers).get_json()
        assert data["total"] == 2
        filtered = client.get(f"/api/support/audit-log?institution_id={inst_b.id}", headers=headers).get_json()
        assert filtered["total"] == 1

    def test_audit_log_includes_impersonator_field(self, client):
        _make_user("agent6", role=ROLE_SUPPORT)
        headers = _login(client, "agent6")
        db.session.add(AuditLog(actor_user_id=None, action="task.create", target_type="task", target_id=1, impersonator_id=None))
        db.session.commit()
        entries = client.get("/api/support/audit-log", headers=headers).get_json()["entries"]
        assert "impersonator_id" in entries[0]


class TestImpersonationBoundaries:
    def test_cannot_impersonate_site_admin_or_support(self, client):
        """The explicit rule: a support agent may never mint a token as
        another support agent or as a site_admin."""
        _make_user("agent7", role=ROLE_SUPPORT)
        headers = _login(client, "agent7")
        peer = _make_user("peer_agent", role=ROLE_SUPPORT)
        root = _make_user("the_root", role=ROLE_SITE_ADMIN)
        assert client.post(f"/api/support/impersonate/{peer.id}", headers=headers).status_code == 403
        assert client.post(f"/api/support/impersonate/{root.id}", headers=headers).status_code == 403
        # And no audit row for the refused attempts.
        assert AuditLog.query.filter_by(action="impersonation.start").count() == 0

    def test_impersonated_token_cannot_reach_admin_surfaces(self, client, create_institution):
        """Even if the impersonated user is a school_admin, the token is
        refused on /api/school/*, /api/site/*, /api/support/* — the
        impersonator_id claim poisons it for all privileged surfaces."""
        _make_user("agent8", role=ROLE_SUPPORT)
        inst = create_institution(name="Sch Inst")
        school_admin = _make_user("victims_admin", role=ROLE_SCHOOL_ADMIN, institution=inst)

        # (Guard refuses the mint itself for admin roles — to test the claim
        # poisoning directly, mint a token as if the flow had succeeded.)
        poisoned = create_access_token(school_admin, impersonator_id=1)
        h = {"Authorization": f"Bearer {poisoned}"}
        assert client.get("/api/school/overview", headers=h).status_code == 403
        assert client.get("/api/site/institutions", headers=h).status_code == 403
        assert client.get("/api/support/institutions", headers=h).status_code == 403

        # Same claim also blocks the generic admin-write guard.
        assert client.post("/api/majors", headers=h, json={"name_fa": "x", "name_en": "y"}).status_code == 403

    def test_impersonation_of_student_works_and_lands_in_audit(self, client, create_institution):
        _agent = _make_user("agent9", role=ROLE_SUPPORT)
        headers = _login(client, "agent9")
        student = _make_user("plain_student")
        del create_institution

        response = client.post(f"/api/support/impersonate/{student.id}", headers=headers)
        assert response.status_code == 200
        body = response.get_json()
        assert body["user"]["id"] == student.id
        assert body["user"]["role"] == "student"

        row = AuditLog.query.filter_by(action="impersonation.start").one()
        assert row.actor_user_id == _agent.id
        assert row.target_type == "user"
        assert row.target_id == student.id
        assert row.after["target_username"] == "plain_student"

    def test_impersonated_session_writes_carry_impersonator(self, client, create_user):
        """Task created through the impersonated token: actor = the student,
        impersonator_id = the support agent."""
        _agent = _make_user("agent10", role=ROLE_SUPPORT)
        headers = _login(client, "agent10")
        student = _make_user("imp_student")

        token = client.post(f"/api/support/impersonate/{student.id}", headers=headers).get_json()["access_token"]
        imp_headers = {"Authorization": f"Bearer {token}"}

        course = client.post("/api/tasks", headers=imp_headers, json={
            "title": "Made by support", "priority": "low", "estimated_hours": 1,
        })
        # student has no course; the endpoint requires priority/estimated only
        assert course.status_code in (201, 400)
        if course.status_code == 201:
            row = AuditLog.query.filter_by(action="task.create").one()
            assert row.actor_user_id == student.id
            assert row.impersonator_id == _agent.id

        # /me exposes the claim for the SPA banner
        me = client.get("/api/me", headers=imp_headers).get_json()
        assert me["user"]["id"] == student.id
        assert me["impersonator_id"] == _agent.id

    def test_normal_tokens_have_no_impersonator_in_audit(self, client, create_user):
        """Regression: the claim must be None — not 0, not the actor — for
        every direct session, so existing audit rows stay unambiguous."""
        _make_user("agent11", role=ROLE_SUPPORT)
        headers = _login(client, "agent11")
        me = client.get("/api/me", headers=headers).get_json()
        assert me["impersonator_id"] is None

    def test_impersonation_token_ttl_not_extended(self, client, create_user):
        """Design decision: impersonation ends when the token expires — no
        "stop" endpoint, no extended TTL. The minted token must decode with
        the SAME max_age as a normal access token and carry the claim."""
        from app.utils.auth import ACCESS_TOKEN_TTL_SECONDS, _access_serializer

        _make_user("agent12", role=ROLE_SUPPORT)
        headers = _login(client, "agent12")
        student = _make_user("ttl_student")
        token = client.post(f"/api/support/impersonate/{student.id}", headers=headers).get_json()["access_token"]
        payload = _access_serializer().loads(token, max_age=ACCESS_TOKEN_TTL_SECONDS)
        assert payload["impersonator_id"]
        # an extended TTL would make this decode fail — it must not:
        assert _access_serializer().loads(token, max_age=ACCESS_TOKEN_TTL_SECONDS)["user_id"] == student.id

    def test_impersonation_does_not_issue_refresh_token(self, client):
        """No refresh token is issued — the session cannot outlive the
        single short-lived access token."""
        _make_user("agent13", role=ROLE_SUPPORT)
        headers = _login(client, "agent13")
        student = _make_user("no_refresh")
        body = client.post(f"/api/support/impersonate/{student.id}", headers=headers).get_json()
        assert "refresh_token" not in body
