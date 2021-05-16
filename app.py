import logging
from chalice import Chalice, AuthResponse, AuthRoute, CORSConfig, BadRequestError
import botocore
import boto3
from basicauth import decode
from hashlib import blake2b

from chalice import CORSConfig

# cors_config = CORSConfig(
#     allow_origin="*",
#     allow_headers=["X-Special-Header"],
#     max_age=600,
#     expose_headers=["X-Special-Header"],
#     allow_credentials=True,
# )

app = Chalice(app_name="sentiment-analysis-of-video-with-aws-services")

VIDEO_UPLOAD_BUCKET_NAME = "video-upload-bucket-trinnawat"
users_video_dictionary = {}


def validate_mail(request):
    if not request.query_params:
        return False, {"error": "please insert query params"}
    mail = request.query_params.get("mail")
    if not mail:
        return False, {"error": "please insert mail"}
    return True, None


def generate_file_name(mail):
    h = blake2b(digest_size=10)
    h.update(bytes(mail, "utf-8"))
    return h.hexdigest()


def count_video_by_mail(mail):
    video_list = users_video_dictionary.get(mail, [])
    return len(video_list)


def update_users_video_dictionary(mail, file_name):
    video_list = users_video_dictionary.get(mail, [])
    video_list.append(file_name)
    users_video_dictionary[mail] = video_list


@app.authorizer()
def basic_auth(auth_request):
    username, password = decode(auth_request.token)
    if username == password:
        context = {"is_admin": True}
        return AuthResponse(
            routes=[AuthRoute("/*", ["GET", "POST"])],
            principal_id=username,
            context=context,
        )
    else:
        return AuthResponse(routes=[], principal_id=None)


@app.route("/presignedurl", methods=["GET"], authorizer=basic_auth, cors=True)
def get_presigned_url():
    have_mail, response = validate_mail(app.current_request)
    if not have_mail:
        return response
    s3_client = boto3.client("s3")
    mail = app.current_request.query_params.get("mail")
    file_name = generate_file_name(mail) + "_" + str(count_video_by_mail(mail)) + ".mp4"
    try:
        response = s3_client.generate_presigned_post(
            VIDEO_UPLOAD_BUCKET_NAME,
            file_name,
            ExpiresIn=3600,
        )
    except botocore.exceptions.ClientError as e:
        logging.error(e)
        raise BadRequestError("Internal Error generating presigned post ")
    else:
        update_users_video_dictionary(mail, file_name)
    return response


@app.route("/videos", methods=["GET"], authorizer=basic_auth, cors=True)
def count_videos():
    have_mail, response = validate_mail(app.current_request)
    if not have_mail:
        return response
    mail = app.current_request.query_params.get("mail")
    return {"total": count_video_by_mail(mail)}
