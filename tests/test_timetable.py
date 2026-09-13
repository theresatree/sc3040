class TestTimetable:
    async def test_get_all_timetable(self, client):
        response = await client.get("/timetables/")

        assert response.status_code == 200, response.json()

    async def test_get_all_timetable_by_day(self, client):
        response = await client.get(
            "/timetables/",
            params={"day_of_week": "monday"},
        )

        assert response.status_code == 200, response.json()

    async def test_get_all_timetable_by_subject(self, client):
        response = await client.get(
            "/timetables/",
            params={"subject": "SC3040"},
        )

        assert response.status_code == 200, response.json()

        data = response.json()

        for timetable in data:
            assert timetable["subject"] == "SC3040"

    async def test_get_all_timetable_by_staff(self, client):
        response = await client.get(
            "/timetables/",
            params={"staff_id": 1},
        )

        assert response.status_code == 200, response.json()

        data = response.json()

        for timetable in data:
            assert timetable["staff_id"] == 1

    async def test_get_all_timetable_by_room(self, client):
        response = await client.get(
            "/timetables/",
            params={"room_id": "1"},
        )

        assert response.status_code == 200, response.json()

        data = response.json()

        for timetable in data:
            assert timetable["room_id"] == "1"

    async def test_get_all_timetable_multiple_filters(self, client):
        response = await client.get(
            "/timetables/",
            params={
                "day_of_week": "monday",
                "subject": "SC3040",
            },
        )

        assert response.status_code == 200, response.json()

    async def test_get_all_subjects(self, client):
        response = await client.get("/timetables/subjects")

        assert response.status_code == 200, response.json()

        data = response.json()

        assert data == sorted(data)
        assert "SC3040" in data
        assert "SC3000" in data

    async def test_get_timetable_by_id(self, client):
        response = await client.get("/timetables/1")

        assert response.status_code == 200, response.json()

    async def test_get_timetable_by_id_not_found(self, client):
        response = await client.get("/timetables/99999")

        assert response.status_code == 404, response.json()


class TestStaffTimetable:
    async def test_get_my_timetable(self, client, logged_in_staff):
        response = await client.get(
            "/timetables/me",
            headers={"Authorization": f"Bearer {logged_in_staff['access_token']}"},
        )

        assert response.status_code == 200, response.json()

    async def test_get_my_timetable_student(self, client, logged_in_student):
        response = await client.get(
            "/timetables/me",
            headers={"Authorization": f"Bearer {logged_in_student['access_token']}"},
        )

        assert response.status_code == 403, response.json()
