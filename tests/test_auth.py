from tests.constants import IMAGE_PATH, MULTIPLE_FACE_IMAGE_PATH, NO_FACE_IMAGE_PATH

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

class TestAuthRegister:
    async def test_register_user(self, client):
        with open(IMAGE_PATH, "rb") as f:
            response = await client.post(
                    "/auth/register",
                    data={
                        "name": "Test",
                        "email": "test@example.com",
                        "password": "password",
                        "gender": "male",
                        "role": "student",
                        },
                    files={"image": (IMAGE_PATH.name, f, "image/jpeg")},
                    )

        assert response.status_code == 201, response.json()

    async def test_register_duplicate_email_fails(self, client):
        payload = {
                "name": "Test",
                "email": "test@example.com",
                "password": "password",
                "gender": "male",
                "role": "student",
                }
        with open(IMAGE_PATH, "rb") as f:
            await client.post("/auth/register", data=payload, files={"image": (IMAGE_PATH.name, f, "image/jpeg")})

        with open(IMAGE_PATH, "rb") as f:
            response = await client.post("/auth/register", data=payload, files={"image": (IMAGE_PATH.name, f, "image/jpeg")})

        assert response.status_code == 409

    async def test_register_missing_image_fails(self,client):
        response = await client.post(
                "/auth/register",
                data={
                    "name": "Test",
                    "email": "test@example.com",
                    "password": "password",
                    "gender": "male",
                    "role": "student",
                    },
                files={"image": ("empty.jpg", b"", "image/jpeg")},
                )
        assert response.status_code == 400

    async def test_register_multiple_faces_fails(self, client):
        with open(MULTIPLE_FACE_IMAGE_PATH, "rb") as f:
            response = await client.post(
                    "/auth/register",
                    data={
                        "name": "Test",
                        "email": "test@example.com",
                        "password": "password",
                        "gender": "male",
                        "role": "student",
                        },
                    files={"image": (MULTIPLE_FACE_IMAGE_PATH.name, f, "image/jpeg")},
                    )
        assert response.status_code == 400

    async def test_register_no_faces_fails(self, client):
        with open(NO_FACE_IMAGE_PATH, "rb") as f:
            response = await client.post(
                    "/auth/register",
                    data={
                        "name": "Test",
                        "email": "test@example.com",
                        "password": "password",
                        "gender": "male",
                        "role": "student",
                        },
                    files={"image": (NO_FACE_IMAGE_PATH.name, f, "image/jpeg")},
                    )
        assert response.status_code == 400


