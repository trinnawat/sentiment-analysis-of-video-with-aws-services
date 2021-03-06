from chalice.test import Client
from app import app, MAIL_VIDEO_TABLE_NAME, TRANSCODED_VIDEO_BUCKET_NAME, WEB_PRESET_ID
from app import set_file_extension
from pytest import fixture


@fixture
def test_client():
    with Client(app) as client:
        yield client


def test_basic_auth_unauthorized_case(test_client):
    response = test_client.http.get("/videos")
    assert response.status_code == 401
    assert response.json_body == {"message": "Unauthorized"}


def test_basic_auth_authorized_case(test_client):
    response = test_client.http.get(
        "/videos", headers={"Authorization": "Basic Z290OmdvdA=="}
    )
    assert response.status_code == 200
    assert response.json_body != {"message": "Unauthorized"}


def test_get_presigned_url_func(test_client):
    response = test_client.http.get(
        "/presignedurl/testProject/0?mail=test@test.com",
        headers={"Authorization": "Basic Z290OmdvdA=="},
    )
    body = response.json_body
    has_key = lambda x: (x in body)
    assert all(map(has_key, ["url", "fields"]))
    has_key_in_fields = lambda x: (x in body["fields"])
    assert all(map(has_key_in_fields, ["key", "AWSAccessKeyId", "policy", "signature"]))
    assert body["url"] == "https://video-upload-bucket-trinnawat.s3.amazonaws.com/"


def test_handle_object_created(test_client):
    event = test_client.events.generate_s3_event(
        bucket=MAIL_VIDEO_TABLE_NAME, key="test.mp4"
    )
    response = test_client.lambda_.invoke("handle_object_created", event)
    job_info = response.payload["Job"]
    print(job_info["Outputs"])
    assert job_info["Input"] == {"Key": "test.mp4"}
    # assert job_info["Output"]["Key"] == "web_test.mp4"
    # assert job_info["Output"]["PresetId"] == WEB_PRESET_ID


def test_handle_audio_object_created(test_client):
    event = test_client.events.generate_s3_event(
        bucket=MAIL_VIDEO_TABLE_NAME, key="test.mp3"
    )
    response = test_client.lambda_.invoke("handle_audio_object_created", event)
    # job_info = response.payload["Job"]
    # print(job_info["Outputs"])
    # assert job_info["Input"] == {"Key": "test.mp4"}


def test_handle_transcript_json_object_created(test_client):
    event = test_client.events.generate_s3_event(
        bucket=TRANSCODED_VIDEO_BUCKET_NAME,
        key="audio/TestProject/0/transcribe/012511_ITWH_SOTU.json",
    )
    response = test_client.lambda_.invoke(
        "handle_transcript_json_object_created", event
    )
    print(response)


def test_set_file_extension():
    input_filename = "testfile.mp4"
    extension = ".mp3"
    output_filename = set_file_extension(input_filename, extension)
    assert output_filename == "testfile.mp3"
