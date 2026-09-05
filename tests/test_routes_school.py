"""School-admin (institution-scoped) API tests (TASK-038).

The core of this file is the cross-institution matrix at the bottom: a
school_admin from institution A must never read or modify anything
belonging to institution B. Co-located in tests/test_routes_school.py
because the fixtures (client, create_institution, create_class) make each
isolation case a three-liner; the happy-path CRUD shape mirrors
test_routes_api.py.
"""

from app.extensions import db
from app.repositories import ClassRepo, UserRepo


def _make_school_admin(client, create_user, create_institution, username, institution_name):
    """Create an institution + a school_admin for it; log in via the API;
    return (user, bearer headers, institution)."""
    institution = create_institution(name=institution_name)
    user = create_user(username=username, password="testpass123")
    user.role = "school_admin"
    user.institution_id = institution.id
    db.session.commit()
    login = client.post("/api/auth/login", json={"username": username, "password": "testpass123"})
    headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}
    return user, headers, institution


def _make_member(create_user, institution, username, role="student"):
    member = create_user(username=username)
    member.institution_id = institution.id
    member.role = role
    db.session.commit()
    return member


class TestSchoolAdminAccess:
    def test_requires_auth(self, client):
        assert client.get("/api/school/overview").status_code == 401

    def test_requires_role(self, client, create_user, create_institution):
        institution = create_institution(name="Inst")
        plain = create_user(username="plainuser", password="testpass123")
        plain.institution_id = institution.id
        db.session.commit()
        login = client.post("/api/auth/login", json={"username": "plainuser", "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}
        assert client.get("/api/school/overview", headers=headers).status_code == 403

    def test_site_admin_role_not_enough(self, client, create_user):
        """site_admin is a different role — school endpoints reject it."""
        create_user(username="siteadm", password="testpass123", is_admin=True)
        login = client.post("/api/auth/login", json={"username": "siteadm", "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}
        assert client.get("/api/school/overview", headers=headers).status_code == 403

    def test_requires_institution(self, client, create_user):
        """school_admin without an institution administers nothing."""
        create_user(username="orphan_admin", password="testpass123", role="school_admin")
        login = client.post("/api/auth/login", json={"username": "orphan_admin", "password": "testpass123"})
        headers = {"Authorization": f"Bearer {login.get_json()['access_token']}"}
        assert client.get("/api/school/overview", headers=headers).status_code == 403

    def test_me_includes_role(self, auth_client):
        client, _ = auth_client
        assert client.get("/api/me").get_json()["user"]["role"] == "student"


class TestSchoolAdminOverview:
    def test_scoped_to_own_institution(self, client, create_user, create_institution, create_class):
        _admin, headers, inst_a = _make_school_admin(client, create_user, create_institution, "admin_a", "School A")
        other = create_institution(name="School B")
        _make_member(create_user, inst_a, "stu_a")
        _make_member(create_user, other, "stu_b")
        create_class(institution=inst_a, name="A-class")
        create_class(institution=other, name="B-class")

        data = client.get("/api/school/overview", headers=headers).get_json()
        assert data["institution_id"] == inst_a.id
        assert [u["username"] for u in data["students"]] == ["stu_a"]
        assert [u["username"] for u in data["teachers"]] == []
        assert [c["name"] for c in data["classes"]] == ["A-class"]

    def test_users_list_scoped_and_filterable(self, client, create_user, create_institution):
        _admin, headers, inst_a = _make_school_admin(client, create_user, create_institution, "admin_a2", "School A2")
        other = create_institution(name="School B2")
        _make_member(create_user, inst_a, "tea_a", role="teacher")
        _make_member(create_user, other, "tea_b", role="teacher")
        _make_member(create_user, inst_a, "stu_a")

        teachers = client.get("/api/school/users?role=teacher", headers=headers).get_json()["users"]
        assert [u["username"] for u in teachers] == ["tea_a"]
        everyone = client.get("/api/school/users", headers=headers).get_json()["users"]
        assert {u["username"] for u in everyone} == {"tea_a", "stu_a"}


class TestSchoolAdminClasses:
    def test_create_class_in_own_institution(self, client, create_user, create_institution):
        _admin, headers, inst_a = _make_school_admin(client, create_user, create_institution, "admin_c", "School C")
        response = client.post("/api/school/classes", headers=headers, json={"name": "10A", "grade_level": "10"})
        assert response.status_code == 201
        assert response.get_json()["class"]["institution_id"] == inst_a.id
        assert response.get_json()["class"]["grade_level"] == "10"

    def test_create_class_requires_name(self, client, create_user, create_institution):
        _admin, headers, _inst = _make_school_admin(client, create_user, create_institution, "admin_c2", "School C2")
        assert client.post("/api/school/classes", headers=headers, json={"name": "  "}).status_code == 400

    def test_update_own_class_ok(self, client, create_user, create_institution, create_class):
        _admin, headers, inst_a = _make_school_admin(client, create_user, create_institution, "admin_f", "School F")
        klass = create_class(institution=inst_a, name="Old")
        response = client.put(f"/api/school/classes/{klass.id}", headers=headers, json={"name": "New", "grade_level": "11"})
        assert response.status_code == 200
        assert response.get_json()["class"]["name"] == "New"
        assert response.get_json()["class"]["grade_level"] == "11"

    def test_update_foreign_class_403_and_unchanged(self, client, create_user, create_institution, create_class):
        _admin, headers, _inst_a = _make_school_admin(client, create_user, create_institution, "admin_d", "School D")
        other = create_institution(name="School E")
        foreign_class = create_class(institution=other, name="B-own")
        response = client.put(f"/api/school/classes/{foreign_class.id}", headers=headers, json={"name": "hijacked"})
        assert response.status_code == 403
        assert ClassRepo.get(foreign_class.id).name == "B-own"

    def test_update_missing_class_404(self, client, create_user, create_institution):
        _admin, headers, _inst = _make_school_admin(client, create_user, create_institution, "admin_d2", "School D2")
        assert client.put("/api/school/classes/999999", headers=headers, json={"name": "X"}).status_code == 404


class TestSchoolAdminAssign:
    def test_assign_own_student_to_own_class(self, client, create_user, create_institution, create_class):
        _admin, headers, inst_a = _make_school_admin(client, create_user, create_institution, "admin_g", "School G")
        student = _make_member(create_user, inst_a, "stu_g")
        klass = create_class(institution=inst_a, name="G-class")
        response = client.put(f"/api/school/users/{student.id}", headers=headers, json={"class_id": klass.id})
        assert response.status_code == 200
        assert response.get_json()["user"]["class_id"] == klass.id

    def test_assign_foreign_user_403(self, client, create_user, create_institution, create_class):
        """Institution A's admin cannot assign B's student — even into A's
        own class."""
        _admin, headers, inst_a = _make_school_admin(client, create_user, create_institution, "admin_h", "School H")
        other = create_institution(name="School I")
        foreign_student = _make_member(create_user, other, "stu_i")
        own_class = create_class(institution=inst_a, name="H-class")
        response = client.put(f"/api/school/users/{foreign_student.id}", headers=headers, json={"class_id": own_class.id})
        assert response.status_code == 403
        assert UserRepo.get(foreign_student.id).class_id is None

    def test_assign_to_foreign_class_403(self, client, create_user, create_institution, create_class):
        """Institution A's admin cannot place A's student into B's class."""
        _admin, headers, inst_a = _make_school_admin(client, create_user, create_institution, "admin_j", "School J")
        other = create_institution(name="School K")
        student = _make_member(create_user, inst_a, "stu_j")
        foreign_class = create_class(institution=other, name="K-class")
        response = client.put(f"/api/school/users/{student.id}", headers=headers, json={"class_id": foreign_class.id})
        assert response.status_code == 403
        assert UserRepo.get(student.id).class_id is None

    def test_assign_nonexistent_class_404(self, client, create_user, create_institution):
        _admin, headers, inst_a = _make_school_admin(client, create_user, create_institution, "admin_l", "School L")
        student = _make_member(create_user, inst_a, "stu_l")
        response = client.put(f"/api/school/users/{student.id}", headers=headers, json={"class_id": 999999})
        assert response.status_code == 404

    def test_assign_missing_class_id_400(self, client, create_user, create_institution):
        _admin, headers, inst_a = _make_school_admin(client, create_user, create_institution, "admin_m", "School M")
        student = _make_member(create_user, inst_a, "stu_m")
        response = client.put(f"/api/school/users/{student.id}", headers=headers, json={})
        assert response.status_code == 400

    def test_assign_clears_with_null(self, client, create_user, create_institution, create_class):
        _admin, headers, inst_a = _make_school_admin(client, create_user, create_institution, "admin_n", "School N")
        student = _make_member(create_user, inst_a, "stu_n")
        klass = create_class(institution=inst_a, name="N-class")
        client.put(f"/api/school/users/{student.id}", headers=headers, json={"class_id": klass.id})
        response = client.put(f"/api/school/users/{student.id}", headers=headers, json={"class_id": None})
        assert response.status_code == 200
        assert response.get_json()["user"]["class_id"] is None

    def test_cannot_assign_school_admin_accounts(self, client, create_user, create_institution):
        """Only students/teachers are assignable — other admins of the same
        institution are not pawns."""
        admin, headers, inst_a = _make_school_admin(client, create_user, create_institution, "admin_o", "School O")
        fellow_admin = create_user(username="peer_admin", role="school_admin")
        fellow_admin.institution_id = inst_a.id
        db.session.commit()
        response = client.put(f"/api/school/users/{fellow_admin.id}", headers=headers, json={"class_id": None})
        assert response.status_code == 403


class TestSchoolAdminCrossInstitutionMatrix:
    """The core tenancy guarantee: admin of A sees/does nothing in B."""

    def test_full_isolation(self, client, create_user, create_institution, create_class):
        _admin_a, headers_a, inst_a = _make_school_admin(client, create_user, create_institution, "adm_a", "Alpha")
        _admin_b, headers_b, inst_b = _make_school_admin(client, create_user, create_institution, "adm_b", "Beta")
        student_b = _make_member(create_user, inst_b, "student_beta")
        class_b = create_class(institution=inst_b, name="Beta-class")
        class_a = create_class(institution=inst_a, name="Alpha-class")

        # Each overview contains nothing from the other institution.
        a_view = client.get("/api/school/overview", headers=headers_a).get_json()
        b_view = client.get("/api/school/overview", headers=headers_b).get_json()
        assert class_b.id not in [c["id"] for c in a_view["classes"]]
        assert class_a.id not in [c["id"] for c in b_view["classes"]]
        assert "student_beta" not in [u["username"] for u in a_view["students"]]
        assert "stu_a" not in [u["username"] for u in b_view["students"]]

        # A cannot rename B's class.
        assert client.put(f"/api/school/classes/{class_b.id}", headers=headers_a, json={"name": "X"}).status_code == 403
        # A cannot assign B's student into either A's or B's class.
        assert client.put(f"/api/school/users/{student_b.id}", headers=headers_a, json={"class_id": class_a.id}).status_code == 403
        assert client.put(f"/api/school/users/{student_b.id}", headers=headers_a, json={"class_id": class_b.id}).status_code == 403
        # B's student is still unassigned after all of A's attempts.
        assert UserRepo.get(student_b.id).class_id is None
