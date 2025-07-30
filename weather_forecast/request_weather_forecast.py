import json
import boto3


# Connection to dynamodb
dynamodb = boto3.resource("dynamodb")
users_table = dynamodb.Tabel("users")
weather_table = dynamodb.Table("weather")


def lambda_handler(event, context):
    # Gets location from user and sets up a request to fetch weather forecast of that location.

    # Parse event received
    body = json.loads(event["body"])

    # Extract id and name from body
    user_id = body.get("id")
    name = body.get("name")


    # Get location of user against user_id and name from dynamodb
    user_data = users_table.get_item(
        key={
            "id": user_id,
            "name": name
        }
    )

    # Extracting postal code and city from user data
    postal_code = user_data.get("postal_code")
    city = user_data.get("city")

    # Method to send request to EC2 forecast machine

