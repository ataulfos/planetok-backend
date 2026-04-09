def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_auth_register_and_login(client):
    r = client.post("/auth/register", json={"username": "gonza", "password": "1234"})
    assert r.status_code == 201
    user = r.json()
    assert user["username"] == "gonza"
    assert "id" in user

    r = client.post("/auth/login", json={"username": "gonza", "password": "1234"})
    assert r.status_code == 200
    assert r.json()["id"] == user["id"]


def test_tasks_create_and_list(client):
    r = client.post("/auth/register", json={"username": "u1", "password": "pw"})
    user_id = r.json()["id"]

    r = client.post(
        "/api/tasks/",
        headers={"X-User-Id": user_id},
        json={"title": "Task 1", "description": "Desc"},
    )
    assert r.status_code == 201
    task = r.json()
    assert task["title"] == "Task 1"
    assert task["status"] == "pending"

    r = client.get("/api/tasks/", headers={"X-User-Id": user_id})
    assert r.status_code == 200
    tasks = r.json()
    assert isinstance(tasks, list)
    assert len(tasks) == 1
