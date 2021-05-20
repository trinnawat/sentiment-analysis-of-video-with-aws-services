# Notes

### Prerequisite

- Create AWS account
- Install Python (in this case I use conda) and set up env

[Generate access keys](https://docs.aws.amazon.com/powershell/latest/userguide/pstools-appendix-sign-up.html)

[Install AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-windows.html)

[Install and set up Chalice](https://aws.github.io/chalice/quickstart.html)

[Botocore vs Boto 3](https://www.reddit.com/r/aws/comments/apdaoo/boto3_vs_botocore/)

[Install Boto 3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html)

    pip install boto3

    pip install basicauth

[Generate presigned URLs to upload videos to S3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html)

[Set up CORS for S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ManageCorsUsing.html)

[Testing Chalice](https://aws.github.io/chalice/topics/testing.html)

[Elastic Transcoder on Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elastictranscoder.html)

- [example](https://docs.aws.amazon.com/code-samples/latest/catalog/python-elastictranscoder-create_hls_job.py.html)

[DynamoDB Python Boto3 Query Cheat Sheet](https://dynobase.dev/dynamodb-python-with-boto3/#scan)

### DynamoDB Schema

    project_step (partition key) STRING,
    mail (sort key) STRING,
    video STRING
