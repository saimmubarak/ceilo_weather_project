import json
import uuid

from common import helper_functions as hf
import boto3
import os
import time


sqs = boto3.client('sqs')

# ---------- QUEUE URL SETUP ----------
# LOCAL TESTING (Hardcoded):
queue_url = "https://sqs.eu-north-1.amazonaws.com/392894084273/get-weather-queue.fifo"

# FOR DEPLOYMENT (Uncomment this and comment out the above line when deploying):
#queue_url = os.environ['SQS_URL']
# --------------------------------------

#receive_queue_url = os.environ['RECEIVE_QUEUE_URL']  # processed-weather-queue.fifo

receive_queue_url = "https://sqs.eu-north-1.amazonaws.com/392894084273/processed-weather-queue.fifo"


# An object created to refer to client and table name
# Specifies dynamodb usage and the table used (table_name)
# Specifies client that is used for invoke (lambda)
AwsInfo = hf.AwsResources("lambda", "users", None)

AWSTables = hf.AwsResources("lambda", "weather", None)

def lambda_handler(event, context):

    # Read from query string parameters (used in GET requests)
    params = hf.parse_data(event, context)

    # Extract name and id from params
    user_id = params.get("id")
    name = params.get("name")

    # Error message if id and name not sent
    if not user_id or not name:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "id and name are required"})
        }

    # Get user data from DynamoDB
    # specify the partition and sort keys of Database and their values
    key = {
        "id": user_id,
        "name": name
        }
    # requires table_name(AwsInfo.table), key_dit (key)
    response = hf.read_from_db(AwsInfo.table, key)

    # Extracts user data from data received from db
    item = response.get("Item")

    # Gives an error message if item is empty meaning nob user found
    if not item:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "User not found"})
        }

    # Get postal_code, city, and image_url
    postal_code = item.get("postal_code")
    city = item.get("city")
    image_url = item.get("image_url")

    item.pop("image_url", None)

    # Creating MessageGroupId for asynchronous parallel queues
    location = f"{postal_code}-{city}".replace(" ", "-")

    request_id = str(uuid.uuid4())

    # Send message to get_weather through a queue
    weatherdata=sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({
            "postal_code": postal_code,
            "city": city,
            "request_id": request_id
        }),
        MessageGroupId=location
    )

    # Receive message from get_weather through a queue
    messages = sqs.receive_message(
        QueueUrl=receive_queue_url,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=4,
        MessageAttributeNames=["All"]
    )
    queue_success = False
    # Processing data received from queue
    combined = {}
    print("Messages->",messages)
    if "Messages" in messages: # Data received through queue
        sqs_worked = True
        from_db = False
        for message in messages["Messages"]:

            attrs = message.get("MessageAttributes", {})
            msg_request_id = attrs.get("RequestId", {}).get("StringValue")

            print("request_id:", request_id)
            print("msg_request_id",msg_request_id)
            if msg_request_id == request_id:
                print("Message received from SQS")
                # Used of deleting repeating data
                receipt_handle = message["ReceiptHandle"]

                # Extract weather data received from queue
                weather_dict = json.loads(message["Body"])

                # if "Body" in weather_dict:
                #     # Delete message from queue
                sqs.delete_message(
                    QueueUrl=receive_queue_url,
                    ReceiptHandle=receipt_handle
                )
                queue_success = True

    else: # No data received through queue
        queue_success = False

    if queue_success:
        # Extract booleans used in checks from received data
        service_available = weather_dict.get("service_available")
        resource = weather_dict.get("resource")
        is_location_valid = weather_dict.get("is_location_valid")

        if not service_available:  # No weatherdata found database or visualcrossing
            if image_url:
                combined = {
                    "user": item,
                    "profile_pic": image_url,
                    "weather": "Our weather services are not currently available",
                    "Queue Status": "Queue Successful :)"
                }
            else:
                combined = {
                    "user": item,
                    "weather": "Our weather services are not currently available",
                    "Queue Status": "Queue Successful :)"
                }
        elif service_available:  # Weather data from either database or visualcrossing
            if is_location_valid:  # Entered location exists
                # Attributes that we want to return read request with names changed eg temp not temp_val
                selected_weather = {
                    "temp": weather_dict.get("temp_val"),
                    "feelsLike": weather_dict.get("feelsLike_val"),
                    "conditions": weather_dict.get("conditions"),
                    "humidity": weather_dict.get("humidity_val"),
                    "windspeed": weather_dict.get("windspeed_val"),
                    "pressure": weather_dict.get("pressure_val"),
                }

                if image_url:
                    combined = {
                        "user": item,
                        "profile_pic": image_url,
                        "weather": selected_weather,
                        "resource": resource,
                        "Queue Status": "Queue Successful :)"
                    }
                else:
                    combined = {
                        "user": item,
                        "weather": selected_weather,
                        "resource": resource,
                        "Queue Status": "Queue Successful :)"
                    }

            else:  # Entered location does not exist
                if image_url:
                    combined = {
                        "user": item,
                        "profile_pic": image_url,
                        "Location": "Users Location is invalid",
                        "Queue Status": "Queue Successful :)"
                    }
                else:
                    combined = {
                        "user": item,
                        "Location": "Users Location is invalid",
                        "Queue Status": "Queue Successful :)"
                    }
    else:
        print("Queue Failed :( get data from db")
        # Get weather from DynamoDB
        # specify the partition and sort keys of Database and their values
        key = {
            "postal_code": postal_code,
            "city": city
        }
        # requires table_name(AwsInfo.table), key_dit (key)
        response = hf.read_from_db(AWSTables.table, key)

        if "Item" in response:
            from_db = True
            # Extracts user data from data received from db
            weather_dict = response.get("Item")

            # Attributes that we want to return read request with names changed eg temp not temp_val
            selected_weather = {
                "temp": weather_dict.get("temp_val"),
                "feelsLike": weather_dict.get("feelsLike_val"),
                "conditions": weather_dict.get("conditions"),
                "humidity": weather_dict.get("humidity_val"),
                "windspeed": weather_dict.get("windspeed_val"),
                "pressure": weather_dict.get("pressure_val"),
            }

            if image_url:
                combined = {
                    "user": item,
                    "profile_pic": image_url,
                    "weather": selected_weather,
                    "resource": "Data From DynamoDB",
                    "Queue Status": "Queue Failed :( get data from db"
                }
            else:
                combined = {
                    "user": item,
                    "weather": selected_weather,
                    "resource": "Data From DynamoDB",
                    "Queue Status": "Queue Failed :( get data from db"

                }
        else:
            from_db = False
            if image_url:
                combined = {
                    "user": item,
                    "profile_pic": image_url,
                    "weather": "Our weather services are not currently available"
                }
            else:
                combined = {
                    "user": item,
                    "weather": "Our weather services are not currently available"
                }


    if queue_success:
        return {
            "statusCode": 200,
            "body": json.dumps(combined),
            "Message": "yeeesss :)"
        }
    else:
        return {
            "statusCode": 200,
            "body": json.dumps(combined),
            "Message": "sorry :("
        }

if __name__ == "__main__":

    event = {
        "queryStringParameters": {
            "id": "1cc12261-d76f-404e-856e-bac85329a3aa",
            "name": "bilal"
        }
    }

    # Call the lambda handler function
    print(lambda_handler(event, None))



