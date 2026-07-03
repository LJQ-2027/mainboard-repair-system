"""Admin 路由测试"""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.diagnosis import DiagnosisRecord
from app.models.project import Project
from app.models.user import User


def _unique(name: str) -> str:
    return f"test_{name}_{uuid.uuid4().hex[:8]}"


def _get_admin_token(client, db_session: Session) -> str:
    """注册一个用户并提升为 admin，返回 token"""
    username = _unique("admin")
    client.post("/auth/register", json={"username": username, "password": "AdminPass123!"})
    user = db_session.query(User).filter(User.username == username).first()
    user.role = "admin"
    db_session.commit()
    login = client.post("/auth/login", json={"username": username, "password": "AdminPass123!"})
    return login.json()["access_token"]


def test_list_projects_requires_admin(client):
    """列出项目需要管理员权限"""
    username = _unique("user")
    client.post("/auth/register", json={"username": username, "password": "UserPass123!"})
    login = client.post("/auth/login", json={"username": username, "password": "UserPass123!"})
    token = login.json()["access_token"]

    resp = client.get("/admin/api/projects", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_list_projects_empty(client, db_session):
    """管理员可列出项目列表"""
    token = _get_admin_token(client, db_session)
    resp = client.get("/admin/api/projects", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_project(client, db_session):
    """管理员可创建项目"""
    token = _get_admin_token(client, db_session)
    resp = client.post(
        "/admin/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "X6878", "name": "X6878 主板", "version": "V1.0"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "X6878"
    assert data["name"] == "X6878 主板"
    assert data["version"] == "V1.0"


def test_create_project_duplicate_code(client, db_session):
    """重复项目编码应返回 409"""
    token = _get_admin_token(client, db_session)
    client.post(
        "/admin/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "X6878", "name": "X6878 主板"},
    )
    resp = client.post(
        "/admin/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "X6878", "name": "另一个名称"},
    )
    assert resp.status_code == 409


def test_create_project_invalid_code(client, db_session):
    """非法项目编码应被拒绝"""
    token = _get_admin_token(client, db_session)
    resp = client.post(
        "/admin/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "X6878<script>", "name": "非法编码"},
    )
    assert resp.status_code == 422


def test_get_project(client, db_session):
    """管理员可获取项目详情"""
    token = _get_admin_token(client, db_session)
    client.post(
        "/admin/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "X6878", "name": "X6878 主板"},
    )

    resp = client.get("/admin/api/projects/X6878", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "X6878 主板"


def test_get_project_not_found(client, db_session):
    """获取不存在的项目应返回 404"""
    token = _get_admin_token(client, db_session)
    resp = client.get("/admin/api/projects/NOT_EXIST", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_update_project(client, db_session):
    """管理员可更新项目"""
    token = _get_admin_token(client, db_session)
    client.post(
        "/admin/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "X6878", "name": "X6878 主板"},
    )

    resp = client.put(
        "/admin/api/projects/X6878",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "X6878 主板修订版", "version": "V1.1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "X6878 主板修订版"
    assert data["version"] == "V1.1"


def test_delete_project(client, db_session):
    """管理员可删除项目"""
    token = _get_admin_token(client, db_session)
    client.post(
        "/admin/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "X6878", "name": "X6878 主板"},
    )

    resp = client.delete("/admin/api/projects/X6878", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204

    resp = client.get("/admin/api/projects/X6878", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_list_project_diagnoses(client, db_session):
    """管理员可查看项目关联的诊断记录"""
    token = _get_admin_token(client, db_session)
    client.post(
        "/admin/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "X6878", "name": "X6878 主板"},
    )

    # 创建一条诊断记录
    user = db_session.query(User).filter(User.username == token.split(".")[0]).first()
    # token 不是 username，直接创建用户更稳妥
    diagnosis_user = User(username=_unique("diag_user"), hashed_password="fake")
    db_session.add(diagnosis_user)
    db_session.commit()

    record = DiagnosisRecord(
        user_id=diagnosis_user.id,
        mode="AI",
        symptom="不开机",
        project_model="X6878",
        result_text="建议检查电源IC",
    )
    db_session.add(record)
    db_session.commit()

    resp = client.get(
        "/admin/api/projects/X6878/diagnoses",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["symptom"] == "不开机"


def test_project_diagnosis_count_in_list(client, db_session):
    """项目列表应返回诊断数量统计"""
    token = _get_admin_token(client, db_session)
    client.post(
        "/admin/api/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "X6878", "name": "X6878 主板"},
    )

    diagnosis_user = User(username=_unique("diag_user"), hashed_password="fake")
    db_session.add(diagnosis_user)
    db_session.commit()

    record = DiagnosisRecord(
        user_id=diagnosis_user.id,
        mode="AI",
        symptom="不开机",
        project_model="X6878",
    )
    db_session.add(record)
    db_session.commit()

    resp = client.get("/admin/api/projects", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["diagnosis_count"] == 1
