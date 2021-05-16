from chalice.test import Client
from app import app, users_video_dictionary


def test_basic_auth_unauthorized_case():
    with Client(app) as client:
        response = client.http.get("/videos")
        assert response.status_code == 401
        assert response.json_body == {"message": "Unauthorized"}


def test_basic_auth_authorized_case():
    with Client(app) as client:
        response = client.http.get(
            "/videos", headers={"Authorization": "Basic Z290OmdvdA=="}
        )
        assert response.status_code == 200
        assert response.json_body != {"message": "Unauthorized"}


def test_get_presigned_url_func():
    with Client(app) as client:
        response = client.http.get(
            "/presignedurl?mail=test@test.com",
            headers={"Authorization": "Basic Z290OmdvdA=="},
        )
        body = response.json_body
        has_key = lambda x: (x in body)
        assert all(map(has_key, ["url", "fields"]))
        has_key_in_fields = lambda x: (x in body["fields"])
        assert all(
            map(has_key_in_fields, ["key", "AWSAccessKeyId", "policy", "signature"])
        )
        assert body["url"] == "https://video-upload-bucket-trinnawat.s3.amazonaws.com/"

        assert users_video_dictionary == {
            "test@test.com": ["42112ae3cb322f13f865_0.mp4"]
        }
