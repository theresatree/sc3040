from tests.constants import IMAGE_PATH, MULTIPLE_FACE_IMAGE_PATH, NO_FACE_IMAGE_PATH


class TestUserLoggedIn:
    async def test_get_me(self, client, logged_in_student):
        response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {logged_in_student['access_token']}"},
        )

        assert response.status_code == 200, response.json()

    async def test_update_image(self, client, logged_in_student):
        with open(IMAGE_PATH, "rb") as f:
            response = await client.post(
                "/users/me/image",
                headers={
                    "Authorization": f"Bearer {logged_in_student['access_token']}"
                },
                files={
                    "image": (IMAGE_PATH.name, f, "image/jpeg"),
                },
            )

        assert response.status_code == 201, response.json()

    async def test_update_no_image(self, client, logged_in_student):
        response = await client.post(
            "/users/me/image",
            headers={"Authorization": f"Bearer {logged_in_student['access_token']}"},
            files={
                "image": ("empty.jpg", b"", "image/jpeg"),
            },
        )

        assert response.status_code == 400, response.json()

    async def test_update_multiple_image(self, client, logged_in_student):
        with open(MULTIPLE_FACE_IMAGE_PATH, "rb") as f:
            response = await client.post(
                "/users/me/image",
                headers={
                    "Authorization": f"Bearer {logged_in_student['access_token']}"
                },
                files={
                    "image": (MULTIPLE_FACE_IMAGE_PATH.name, f, "image/jpeg"),
                },
            )

        assert response.status_code == 400, response.json()

    async def test_update_no_face_image(self, client, logged_in_student):
        with open(NO_FACE_IMAGE_PATH, "rb") as f:
            response = await client.post(
                "/users/me/image",
                headers={
                    "Authorization": f"Bearer {logged_in_student['access_token']}"
                },
                files={
                    "image": (NO_FACE_IMAGE_PATH.name, f, "image/jpeg"),
                },
            )

        assert response.status_code == 400, response.json()


class TestStaffLoggedIn:
    async def test_get_user_by_id(self, client, logged_in_staff):
        response = await client.get(
            "/users/1",
            headers={"Authorization": f"Bearer {logged_in_staff['access_token']}"},
        )

        assert response.status_code == 200, response.json()

    async def test_get_user_by_id_not_found(self, client, logged_in_staff):
        response = await client.get(
            "/users/99999",
            headers={"Authorization": f"Bearer {logged_in_staff['access_token']}"},
        )

        assert response.status_code == 404
