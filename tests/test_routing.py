from app.engine.routing import EVENT_ROUTES, get_recipients


class TestGetRecipients:
    def test_known_event_type(self):
        recipients = get_recipients("PatientRegistered")
        assert recipients == ["reception", "admin"]

    def test_unknown_event_type(self):
        recipients = get_recipients("NonExistentEvent")
        assert recipients == []

    def test_all_event_types_covered(self):
        known_types = [
            "PatientRegistered",
            "AppointmentCreated",
            "PatientCheckedIn",
            "AdmissionRequested",
            "AdmissionApproved",
            "VitalsRecorded",
            "HighSugarDetected",
            "WarningAlertGenerated",
            "CriticalAlertGenerated",
            "MedicationPrescribed",
            "MedicationAdministered",
            "PatientReviewed",
            "CheckupCompleted",
            "DischargeApproved",
        ]
        for event_type in known_types:
            recipients = get_recipients(event_type)
            assert len(recipients) > 0, f"No recipients defined for {event_type}"

    def test_route_dict_matches_get_recipients(self):
        for event_type, expected_roles in EVENT_ROUTES.items():
            assert get_recipients(event_type) == expected_roles

    def test_empty_string(self):
        assert get_recipients("") == []

    def test_case_sensitivity(self):
        assert get_recipients("patientregistered") == []
        assert get_recipients("PatientRegistered") == ["reception", "admin"]
