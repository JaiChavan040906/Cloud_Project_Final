from app.engine.risk import evaluate_vitals


class TestEvaluateVitals:
    def test_normal_vitals(self):
        result = evaluate_vitals(
            heart_rate=75,
            bp_systolic=120,
            bp_diastolic=80,
            spo2=98.0,
            temperature=98.6,
            blood_sugar=100.0,
        )
        assert result["status"] == "normal"
        assert result["reasons"] == []
        assert result["severity_score"] == 0

    def test_warning_one_issue_high_hr(self):
        result = evaluate_vitals(
            heart_rate=110,
            bp_systolic=120,
            bp_diastolic=80,
            spo2=98.0,
            temperature=98.6,
            blood_sugar=100.0,
        )
        assert result["status"] == "warning"
        assert len(result["reasons"]) == 1
        assert "Heart rate" in result["reasons"][0]
        assert result["severity_score"] == 1

    def test_warning_one_issue_low_spo2(self):
        result = evaluate_vitals(
            heart_rate=75,
            bp_systolic=120,
            bp_diastolic=80,
            spo2=92.0,
            temperature=98.6,
            blood_sugar=100.0,
        )
        assert result["status"] == "warning"
        assert len(result["reasons"]) == 1
        assert "oxygen" in result["reasons"][0]
        assert result["severity_score"] == 1

    def test_critical_two_issues(self):
        result = evaluate_vitals(
            heart_rate=110,
            bp_systolic=150,
            bp_diastolic=80,
            spo2=98.0,
            temperature=98.6,
            blood_sugar=100.0,
        )
        assert result["status"] == "critical"
        assert len(result["reasons"]) == 2
        assert result["severity_score"] == 2

    def test_critical_many_issues(self):
        result = evaluate_vitals(
            heart_rate=150,
            bp_systolic=180,
            bp_diastolic=110,
            spo2=85.0,
            temperature=103.0,
            blood_sugar=200.0,
        )
        assert result["status"] == "critical"
        assert len(result["reasons"]) == 6
        assert result["severity_score"] == 6

    def test_low_heart_rate(self):
        result = evaluate_vitals(
            heart_rate=40,
            bp_systolic=120,
            bp_diastolic=80,
            spo2=98.0,
            temperature=98.6,
            blood_sugar=100.0,
        )
        assert result["status"] == "warning"
        assert "Heart rate" in result["reasons"][0]

    def test_high_temperature(self):
        result = evaluate_vitals(
            heart_rate=75,
            bp_systolic=120,
            bp_diastolic=80,
            spo2=98.0,
            temperature=102.0,
            blood_sugar=100.0,
        )
        assert result["status"] == "warning"
        assert "Temperature" in result["reasons"][0]

    def test_low_blood_sugar(self):
        result = evaluate_vitals(
            heart_rate=75,
            bp_systolic=120,
            bp_diastolic=80,
            spo2=98.0,
            temperature=98.6,
            blood_sugar=50.0,
        )
        assert result["status"] == "warning"
        assert "Blood sugar" in result["reasons"][0]

    def test_high_blood_sugar(self):
        result = evaluate_vitals(
            heart_rate=75,
            bp_systolic=120,
            bp_diastolic=80,
            spo2=98.0,
            temperature=98.6,
            blood_sugar=200.0,
        )
        assert result["status"] == "warning"
        assert "Blood sugar" in result["reasons"][0]

    def test_boundary_values_normal(self):
        result = evaluate_vitals(
            heart_rate=60,
            bp_systolic=90,
            bp_diastolic=60,
            spo2=95.0,
            temperature=97.0,
            blood_sugar=70.0,
        )
        assert result["status"] == "normal"
        assert result["severity_score"] == 0

    def test_boundary_values_high(self):
        result = evaluate_vitals(
            heart_rate=100,
            bp_systolic=140,
            bp_diastolic=90,
            spo2=100.0,
            temperature=100.4,
            blood_sugar=140.0,
        )
        assert result["status"] == "normal"
        assert result["severity_score"] == 0
