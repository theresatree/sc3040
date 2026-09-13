class TestRegistration:
    async def test_get_my_registration(self, client, logged_in_student):
        response = await client.get(
            "/register/me",
            headers={"Authorization": f"Bearer {logged_in_student['access_token']}"},
        )

        assert response.status_code == 200, response.json()

    async def test_get_my_registration_not_logged_in(self, client):
        response = await client.get("/register/me")

        assert response.status_code == 401, response.json()
