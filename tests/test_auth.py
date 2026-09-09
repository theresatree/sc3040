class TestAuthLogin:
    async def test_login(self,client, registered_user):
        response = await client.post(
            "/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert response.status_code == 200, response.json()

    async def test_login_with_password_fail(self,client, registered_user):
        response = await client.post(
            "/auth/login",
            json={
                "email": registered_user["email"],
                "password": "fake_password",
            },
        )
        assert response.status_code == 401 

    async def test_login_with_email_fail(self,client, registered_user):
        response = await client.post(
            "/auth/login",
            json={
                "email": "fake@gmail.com",
                "password": registered_user["password"]
            },
        )
        assert response.status_code == 401 
