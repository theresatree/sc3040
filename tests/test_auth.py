class TestAuthLogin:
    async def test_login(self, client):
        response = await client.post(
            "/auth/login",
            json={
                "email": "edmund@test.com",
                "password": "password",
            },
        )

        assert response.status_code == 200, response.json()

    async def test_login_with_password_fail(self, client):
        response = await client.post(
            "/auth/login",
            json={
                "email": "edmund@test.com",
                "password": "fake_password",
            },
        )

        assert response.status_code == 401

    async def test_login_with_email_fail(self, client):
        response = await client.post(
            "/auth/login",
            json={
                "email": "fake@gmail.com",
                "password": "password",
            },
        )

        assert response.status_code == 401
