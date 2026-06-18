from app.models import Patient


class TestAuth:
    def test_login_valid(self, client, seed_users):
        r = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "admin"
        assert data["username"] == "admin"

    def test_login_invalid_password(self, client, seed_users):
        r = client.post("/auth/login", json={"username": "admin", "password": "wrongpass"})
        assert r.status_code == 401

    def test_login_invalid_username(self, client, seed_users):
        r = client.post("/auth/login", json={"username": "nonexistent", "password": "admin123"})
        assert r.status_code == 401

    def test_login_missing_fields(self, client, seed_users):
        r = client.post("/auth/login", json={})
        assert r.status_code == 422


class TestHealth:
    def test_health_no_auth(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestReceptionAccess:
    def test_register_patient_allowed(self, client, auth_headers):
        r = client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        assert r.status_code == 200
        assert r.json()["patient_id"] == "P001"

    def test_register_patient_forbidden(self, client, auth_headers):
        r = client.post(
            "/api/patients/register",
            json={"patient_id": "P002", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["doctor"],
        )
        assert r.status_code == 403

    def test_create_appointment_allowed(self, client, auth_headers):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        r = client.post(
            "/api/appointments",
            json={
                "appointment_id": "A001",
                "patient_id": "P001",
                "date": "2025-01-15",
                "time": "10:00",
            },
            headers=auth_headers["reception"],
        )
        assert r.status_code == 200
        assert r.json()["appointment_id"] == "A001"

    def test_create_appointment_forbidden(self, client, auth_headers):
        r = client.post(
            "/api/appointments",
            json={
                "appointment_id": "A002",
                "patient_id": "P001",
                "date": "2025-01-15",
                "time": "10:00",
            },
            headers=auth_headers["nurse"],
        )
        assert r.status_code == 403

    def test_checkin_patient_allowed(self, client, auth_headers):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        r = client.post("/api/patients/P001/checkin", headers=auth_headers["reception"])
        assert r.status_code == 200

    def test_checkin_patient_forbidden(self, client, auth_headers):
        r = client.post("/api/patients/P999/checkin", headers=auth_headers["doctor"])
        assert r.status_code == 403

    def test_list_admissions_allowed(self, client, auth_headers):
        r = client.get("/api/admissions", headers=auth_headers["reception"])
        assert r.status_code == 200
        assert "items" in r.json()

    def test_list_admissions_forbidden(self, client, auth_headers):
        r = client.get("/api/admissions", headers=auth_headers["doctor"])
        assert r.status_code == 403

    def test_list_appointments_allowed(self, client, auth_headers):
        r = client.get("/api/appointments", headers=auth_headers["reception"])
        assert r.status_code == 200
        assert "items" in r.json()

    def test_list_appointments_forbidden(self, client, auth_headers):
        r = client.get("/api/appointments", headers=auth_headers["nurse"])
        assert r.status_code == 403

    def test_get_patients_all_roles(self, client, auth_headers):
        for role in ["reception", "nurse", "doctor", "admin"]:
            r = client.get("/api/patients", headers=auth_headers[role])
            assert r.status_code == 200, f"Role {role} should be allowed"


class TestAdminAccess:
    def test_admin_summary_allowed(self, client, auth_headers):
        r = client.get("/api/admin/summary", headers=auth_headers["admin"])
        assert r.status_code == 200
        data = r.json()
        assert "total_patients" in data

    def test_admin_summary_forbidden(self, client, auth_headers):
        r = client.get("/api/admin/summary", headers=auth_headers["doctor"])
        assert r.status_code == 403

    def test_admin_admissions_allowed(self, client, auth_headers):
        r = client.get("/api/admin/admissions", headers=auth_headers["admin"])
        assert r.status_code == 200
        assert "items" in r.json()

    def test_admin_admissions_forbidden(self, client, auth_headers):
        r = client.get("/api/admin/admissions", headers=auth_headers["nurse"])
        assert r.status_code == 403

    def test_approve_admission_allowed(self, client, auth_headers, db_session):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        patient = db_session.query(Patient).filter(Patient.patient_id == "P001").first()
        patient.status = "Admission Requested"
        db_session.commit()
        r = client.put("/api/admissions/P001/approve", headers=auth_headers["admin"])
        assert r.status_code == 200

    def test_approve_admission_forbidden(self, client, auth_headers):
        r = client.put("/api/admissions/P999/approve", headers=auth_headers["doctor"])
        assert r.status_code == 403

    def test_admin_critical_allowed(self, client, auth_headers):
        r = client.get("/api/admin/critical", headers=auth_headers["admin"])
        assert r.status_code == 200
        assert "items" in r.json()

    def test_admin_critical_forbidden(self, client, auth_headers):
        r = client.get("/api/admin/critical", headers=auth_headers["nurse"])
        assert r.status_code == 403

    def test_admin_alerts_allowed(self, client, auth_headers):
        r = client.get("/api/admin/alerts", headers=auth_headers["admin"])
        assert r.status_code == 200
        assert "items" in r.json()

    def test_admin_alerts_forbidden(self, client, auth_headers):
        r = client.get("/api/admin/alerts", headers=auth_headers["doctor"])
        assert r.status_code == 403


class TestNurseAccess:
    def test_assigned_patients_allowed(self, client, auth_headers):
        r = client.get("/api/patients/assigned", headers=auth_headers["nurse"])
        assert r.status_code == 200
        assert "items" in r.json()

    def test_assigned_patients_forbidden(self, client, auth_headers):
        r = client.get("/api/patients/assigned", headers=auth_headers["doctor"])
        assert r.status_code == 403

    def test_record_vitals_allowed(self, client, auth_headers):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        r = client.post(
            "/api/vitals",
            json={
                "patient_id": "P001",
                "heart_rate": 75,
                "blood_pressure_systolic": 120,
                "blood_pressure_diastolic": 80,
                "oxygen_level": 98,
                "temperature": 98.6,
                "blood_sugar": 100,
            },
            headers=auth_headers["nurse"],
        )
        assert r.status_code == 200
        assert r.json()["severity"] == "Normal"

    def test_record_vitals_forbidden(self, client, auth_headers):
        r = client.post(
            "/api/vitals",
            json={
                "patient_id": "P001",
                "heart_rate": 75,
                "blood_pressure_systolic": 120,
                "blood_pressure_diastolic": 80,
                "oxygen_level": 98,
                "temperature": 98.6,
                "blood_sugar": 100,
            },
            headers=auth_headers["reception"],
        )
        assert r.status_code == 403

    def test_get_alerts_allowed(self, client, auth_headers):
        r = client.get("/api/alerts", headers=auth_headers["nurse"])
        assert r.status_code == 200
        assert "items" in r.json()

    def test_get_alerts_forbidden(self, client, auth_headers):
        r = client.get("/api/alerts", headers=auth_headers["doctor"])
        assert r.status_code == 403

    def test_medication_queue_allowed(self, client, auth_headers):
        r = client.get("/api/medications/queue", headers=auth_headers["nurse"])
        assert r.status_code == 200
        assert "items" in r.json()

    def test_medication_queue_forbidden(self, client, auth_headers):
        r = client.get("/api/medications/queue", headers=auth_headers["reception"])
        assert r.status_code == 403

    def test_administer_medication_allowed(self, client, auth_headers):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        client.post(
            "/api/prescriptions",
            json={
                "medication_id": "M001",
                "patient_id": "P001",
                "medicine_name": "Paracetamol",
                "prescribed_by": "Dr. Smith",
            },
            headers=auth_headers["doctor"],
        )
        r = client.put("/api/medications/M001/administer", headers=auth_headers["nurse"])
        assert r.status_code == 200
        assert r.json()["medication_id"] == "M001"

    def test_administer_medication_forbidden(self, client, auth_headers):
        r = client.put("/api/medications/M999/administer", headers=auth_headers["doctor"])
        assert r.status_code == 403

    def test_complete_checkup_allowed(self, client, auth_headers):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        r = client.put("/api/checkups/P001/complete", headers=auth_headers["nurse"])
        assert r.status_code == 200

    def test_complete_checkup_forbidden(self, client, auth_headers):
        r = client.put("/api/checkups/P999/complete", headers=auth_headers["reception"])
        assert r.status_code == 403


class TestDoctorAccess:
    def test_review_queue_allowed(self, client, auth_headers):
        r = client.get("/api/reviews/queue", headers=auth_headers["doctor"])
        assert r.status_code == 200
        assert "items" in r.json()

    def test_review_queue_forbidden(self, client, auth_headers):
        r = client.get("/api/reviews/queue", headers=auth_headers["nurse"])
        assert r.status_code == 403

    def test_critical_patients_allowed(self, client, auth_headers):
        r = client.get("/api/patients/critical", headers=auth_headers["doctor"])
        assert r.status_code == 200
        assert "items" in r.json()

    def test_critical_patients_forbidden(self, client, auth_headers):
        r = client.get("/api/patients/critical", headers=auth_headers["nurse"])
        assert r.status_code == 403

    def test_patient_history_allowed(self, client, auth_headers):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        r = client.get("/api/patients/P001/history", headers=auth_headers["doctor"])
        assert r.status_code == 200
        data = r.json()
        assert "patient" in data
        assert "events" in data

    def test_patient_history_forbidden(self, client, auth_headers):
        r = client.get("/api/patients/P999/history", headers=auth_headers["reception"])
        assert r.status_code == 403

    def test_prescribe_medication_allowed(self, client, auth_headers):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        r = client.post(
            "/api/prescriptions",
            json={
                "medication_id": "M001",
                "patient_id": "P001",
                "medicine_name": "Paracetamol",
                "prescribed_by": "Dr. Smith",
            },
            headers=auth_headers["doctor"],
        )
        assert r.status_code == 200

    def test_prescribe_medication_forbidden(self, client, auth_headers):
        r = client.post(
            "/api/prescriptions",
            json={
                "medication_id": "M002",
                "patient_id": "P001",
                "medicine_name": "Paracetamol",
                "prescribed_by": "Dr. Smith",
            },
            headers=auth_headers["nurse"],
        )
        assert r.status_code == 403

    def test_submit_review_allowed(self, client, auth_headers):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        r = client.post(
            "/api/reviews",
            json={
                "review_id": "R001",
                "patient_id": "P001",
                "doctor_id": "D001",
                "review_note": "Patient is doing well.",
            },
            headers=auth_headers["doctor"],
        )
        assert r.status_code == 200

    def test_submit_review_forbidden(self, client, auth_headers):
        r = client.post(
            "/api/reviews",
            json={
                "review_id": "R002",
                "patient_id": "P001",
                "doctor_id": "D001",
                "review_note": "Patient is doing well.",
            },
            headers=auth_headers["reception"],
        )
        assert r.status_code == 403

    def test_approve_discharge_allowed(self, client, auth_headers, db_session):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        patient = db_session.query(Patient).filter(Patient.patient_id == "P001").first()
        patient.status = "Admitted"
        db_session.commit()
        r = client.put("/api/discharge/P001/approve", headers=auth_headers["doctor"])
        assert r.status_code == 200

    def test_approve_discharge_forbidden(self, client, auth_headers):
        r = client.put("/api/discharge/P999/approve", headers=auth_headers["nurse"])
        assert r.status_code == 403


class TestPatientFlow:
    def test_full_patient_flow(self, client, auth_headers, db_session):
        r = client.post(
            "/api/patients/register",
            json={
                "patient_id": "P001",
                "name": "Alice",
                "age": 25,
                "gender": "Female",
            },
            headers=auth_headers["reception"],
        )
        assert r.status_code == 200
        assert r.json()["patient_id"] == "P001"

        r = client.post(
            "/api/appointments",
            json={
                "appointment_id": "A001",
                "patient_id": "P001",
                "date": "2025-01-15",
                "time": "10:00",
            },
            headers=auth_headers["reception"],
        )
        assert r.status_code == 200
        assert r.json()["appointment_id"] == "A001"

        r = client.post("/api/patients/P001/checkin", headers=auth_headers["reception"])
        assert r.status_code == 200

        patient = db_session.query(Patient).filter(Patient.patient_id == "P001").first()
        patient.status = "Admission Requested"
        db_session.commit()

        r = client.post(
            "/api/vitals",
            json={
                "patient_id": "P001",
                "heart_rate": 75,
                "blood_pressure_systolic": 120,
                "blood_pressure_diastolic": 80,
                "oxygen_level": 98,
                "temperature": 98.6,
                "blood_sugar": 100,
            },
            headers=auth_headers["nurse"],
        )
        assert r.status_code == 200
        assert r.json()["severity"] == "Normal"

        r = client.put("/api/admissions/P001/approve", headers=auth_headers["admin"])
        assert r.status_code == 200
        assert r.json()["patient_id"] == "P001"

        r = client.post(
            "/api/prescriptions",
            json={
                "medication_id": "M001",
                "patient_id": "P001",
                "medicine_name": "Paracetamol",
                "prescribed_by": "Dr. Smith",
            },
            headers=auth_headers["doctor"],
        )
        assert r.status_code == 200
        assert r.json()["medication_id"] == "M001"

        r = client.put("/api/medications/M001/administer", headers=auth_headers["nurse"])
        assert r.status_code == 200
        assert r.json()["medication_id"] == "M001"

        r = client.post(
            "/api/reviews",
            json={
                "review_id": "R001",
                "patient_id": "P001",
                "doctor_id": "D001",
                "review_note": "Patient recovering well.",
            },
            headers=auth_headers["doctor"],
        )
        assert r.status_code == 200
        assert r.json()["review_id"] == "R001"

        r = client.put("/api/discharge/P001/approve", headers=auth_headers["doctor"])
        assert r.status_code == 200
        assert r.json()["patient_id"] == "P001"

        patient = db_session.query(Patient).filter(Patient.patient_id == "P001").first()
        assert patient.status == "Discharged"


class TestErrorHandling:
    def test_missing_patient_404(self, client, auth_headers):
        r = client.get("/api/patients/P999/history", headers=auth_headers["doctor"])
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_missing_medication_404(self, client, auth_headers):
        r = client.put("/api/medications/M999/administer", headers=auth_headers["nurse"])
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_missing_appointment_patient_404(self, client, auth_headers):
        r = client.post(
            "/api/appointments",
            json={
                "appointment_id": "A001",
                "patient_id": "P999",
                "date": "2025-01-15",
                "time": "10:00",
            },
            headers=auth_headers["reception"],
        )
        assert r.status_code == 404

    def test_duplicate_patient_400(self, client, auth_headers):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        r = client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        assert r.status_code == 400
        assert "already" in r.json()["detail"].lower()

    def test_duplicate_appointment_400(self, client, auth_headers):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        client.post(
            "/api/appointments",
            json={
                "appointment_id": "A001",
                "patient_id": "P001",
                "date": "2025-01-15",
                "time": "10:00",
            },
            headers=auth_headers["reception"],
        )
        r = client.post(
            "/api/appointments",
            json={
                "appointment_id": "A001",
                "patient_id": "P001",
                "date": "2025-01-15",
                "time": "10:00",
            },
            headers=auth_headers["reception"],
        )
        assert r.status_code == 400
        assert "already" in r.json()["detail"].lower()

    def test_double_checkin_400(self, client, auth_headers):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        client.post("/api/patients/P001/checkin", headers=auth_headers["reception"])
        r = client.post("/api/patients/P001/checkin", headers=auth_headers["reception"])
        assert r.status_code == 400

    def test_double_administer_400(self, client, auth_headers, db_session):
        client.post(
            "/api/patients/register",
            json={"patient_id": "P001", "name": "Test", "age": 30, "gender": "Male"},
            headers=auth_headers["reception"],
        )
        patient = db_session.query(Patient).filter(Patient.patient_id == "P001").first()
        patient.status = "Admitted"
        db_session.commit()
        client.post(
            "/api/prescriptions",
            json={
                "medication_id": "M001",
                "patient_id": "P001",
                "medicine_name": "Test",
                "prescribed_by": "Dr.",
            },
            headers=auth_headers["doctor"],
        )
        client.put("/api/medications/M001/administer", headers=auth_headers["nurse"])
        r = client.put("/api/medications/M001/administer", headers=auth_headers["nurse"])
        assert r.status_code == 400

    def test_unauthenticated_401(self, client):
        endpoints = [
            ("GET", "/api/patients/assigned"),
            ("GET", "/api/admin/summary"),
            ("GET", "/api/reviews/queue"),
            ("POST", "/api/patients/register"),
            ("POST", "/api/appointments"),
        ]
        for method, path in endpoints:
            r = client.request(method, path)
            assert r.status_code == 401, f"{method} {path} should return 401"


class TestNotifications:
    def test_get_notifications_no_auth(self, client):
        r = client.get("/api/notifications", params={"role": "nurse"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_mark_notification_read_404(self, client):
        r = client.put("/api/notifications/NONEXISTENT/read")
        assert r.status_code == 404


class TestSimulator:
    def test_simulator_state(self, client):
        r = client.get("/api/simulator/state")
        assert r.status_code == 200
        data = r.json()
        assert "current_step" in data
        assert "total_events" in data

    def test_simulator_reset(self, client):
        r = client.post("/api/simulator/reset")
        assert r.status_code == 200
        assert r.json()["message"] == "Simulation reset"
