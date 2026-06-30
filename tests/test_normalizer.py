from app.core.normalizer import NormalizerService

def test_normalization():
    normalizer = NormalizerService()

    raw = {
        "email": "VARSHA@GMAIL.COM ",
        "phone": "+91-98765-43210",
        "skills": ["Python3", "ReactJS"]
    }

    result = normalizer.normalize(raw)

    assert result["email"] == "varsha@gmail.com"
    assert result["phone"] == "9876543210"
    assert "Python" in result["skills"]
