import boto3


def main():
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.create_table(
        TableName="metadata",
        KeySchema=[{"AttributeName": "JsonFile", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "JsonFile", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    print(table)


if __name__ == "__main__":
    main()
