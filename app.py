import logging
from chalice import Chalice, AuthResponse, AuthRoute, CORSConfig, BadRequestError
import botocore
import boto3
from boto3.dynamodb.conditions import Key
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

app = Chalice(app_name="video-sentiment-analysis")

VIDEO_UPLOAD_BUCKET_NAME = "video-upload-bucket-trinnawat"
TRANSCODED_VIDEO_BUCKET_NAME = "transcoded-video-upload-bucket-trinnawat"
PIPELINE_ID = "1621434510607-z75v6k"
WEB_PRESET_ID = "1351620000001-100070"
MAIL_VIDEO_TABLE_NAME = "responses"


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


@app.route(
    "/presignedurl/{project}/{step}", methods=["GET"], authorizer=basic_auth, cors=True
)
def get_presigned_url(project, step):
    have_mail, response = validate_mail(app.current_request)
    if not have_mail:
        return response
    mail = app.current_request.query_params.get("mail")
    # file_name = generate_file_name(mail)
    file_name = "${filename}"
    file_name = "/".join([project, step, file_name])
    try:
        s3_client = boto3.client("s3")
        response = s3_client.generate_presigned_post(
            VIDEO_UPLOAD_BUCKET_NAME,
            file_name,
            ExpiresIn=3600,
        )
    except botocore.exceptions.ClientError as e:
        logging.error(e)
        raise BadRequestError("Internal Error generating presigned post ")
    else:
        table = boto3.resource("dynamodb").Table(MAIL_VIDEO_TABLE_NAME)
        item = {"project_step": project + "-" + step, "mail": mail, "video": file_name}
        table.put_item(Item=item)
    return response


@app.route("/videos", methods=["GET"], authorizer=basic_auth, cors=True)
def count_videos():
    table = boto3.resource("dynamodb").Table(MAIL_VIDEO_TABLE_NAME)
    response = table.scan()
    data = response["Items"]
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        data.extend(response["Items"])
    return data


# S3 event triggered functions
@app.on_s3_event(bucket=VIDEO_UPLOAD_BUCKET_NAME, events=["s3:ObjectCreated:*"])
def handle_object_created(event):
    input_filename = event.key
    etc_client = boto3.client("elastictranscoder")
    outputs = [{"Key": "web_" + input_filename, "PresetId": WEB_PRESET_ID}]
    try:
        response = etc_client.create_job(
            PipelineId=PIPELINE_ID, Input={"Key": input_filename}, Outputs=outputs
        )
    except botocore.exceptions.ClientError as e:
        print(f"ERROR: {e}")
    else:
        return response
