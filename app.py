import os, logging
import json
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

# S3 buckets
VIDEO_UPLOAD_BUCKET_NAME = "video-upload-bucket-trinnawat"
TRANSCODED_VIDEO_BUCKET_NAME = "transcoded-video-upload-bucket-trinnawat"
S3_URI = "s3://transcoded-video-upload-bucket-trinnawat/"

# DynamoDB
MAIL_VIDEO_TABLE_NAME = "responses"
METADATA_TABLE_NAME = "metadata"

# Elastic Transcoder
PIPELINE_ID = "1621434510607-z75v6k"
WEB_PRESET_ID = "1351620000001-100070"
IPHONE4S_PRESET_ID = "1351620000001-100020"
AUDIO_MP3_128K_PRESET_ID = "1351620000001-300040"
GIF_ANIMATED_PRESET_ID = "1351620000001-100200"


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


def set_file_extension(filename, extension):
    if not extension.startswith("."):
        extension = "." + extension
    filename, file_extension = os.path.splitext(filename)
    return filename + extension


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
    audio_output_filename = set_file_extension(input_filename, ".mp3")
    gif_output_filename = set_file_extension(input_filename, ".gif")
    outputs = [
        {"Key": "web/" + input_filename, "PresetId": WEB_PRESET_ID},
        {"Key": "phone/" + input_filename, "PresetId": IPHONE4S_PRESET_ID},
        {"Key": "gif/" + gif_output_filename, "PresetId": GIF_ANIMATED_PRESET_ID},
        {"Key": "audio/" + audio_output_filename, "PresetId": AUDIO_MP3_128K_PRESET_ID},
    ]
    try:
        response = etc_client.create_job(
            PipelineId=PIPELINE_ID, Input={"Key": input_filename}, Outputs=outputs
        )
    except botocore.exceptions.ClientError as e:
        print(f"ERROR: {e}")
    else:
        return response


@app.on_s3_event(bucket=TRANSCODED_VIDEO_BUCKET_NAME, events=["s3:ObjectCreated:*"])
def handle_audio_or_json_created(event):
    input_filename = event.key
    job_uri = S3_URI + input_filename
    print(job_uri)
    if input_filename.endswith("mp3"):
        print(input_filename)
        input_filename_split = input_filename.split("/")
        job_name = input_filename_split[-1]
        output_filename = set_file_extension(input_filename_split[-1], ".json")
        input_filename_split = input_filename_split[:-1]
        input_filename_split.extend(["transcribe", output_filename])
        output_filename = "/".join(input_filename_split)
        print(output_filename)
        transcribe = boto3.client("transcribe")
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": job_uri},
            MediaFormat="mp3",
            LanguageCode="en-US",
            OutputBucketName=TRANSCODED_VIDEO_BUCKET_NAME,
            OutputKey=output_filename,
        )
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        print(status)
    elif input_filename.endswith("json"):
        try:
            s3_client = boto3.client("s3")
            obj = s3_client.get_object(
                Bucket=TRANSCODED_VIDEO_BUCKET_NAME, Key=input_filename
            )
            obj_dict = json.loads(obj["Body"].read())
            transcript = obj_dict["results"]["transcripts"][0]["transcript"]
        except botocore.exceptions.ClientError as e:
            logging.error(e)
            raise BadRequestError("Internal Error generating presigned post ")
        else:
            table = boto3.resource("dynamodb").Table(METADATA_TABLE_NAME)
            item = {
                "JsonFile": input_filename,
                "transcript": transcript,
            }
            table.put_item(Item=item)
            print(transcript)
