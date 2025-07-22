import boto3
import os
import json


sns = boto3.client('sns')
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']


def lambda_handler(event, context):

    # The DynamoDb stream data has a list called records that contains the logs/updates in the associated dynamodb
    # We loop through Records to find our desired record and perform some actions when some condition is met
    for record in event['Records']:

        # Inside each record we have a dictionary called eventName
        # The dictionary eventName specifies the type of event the record has recorded
        # Types of event are "INSERT", "MODIFY", "REMOVE"
        # Our if check deals with "INSERT"
        if record['eventName'] == 'INSERT':

            # On the same level as event name we have the dictionary dynamodb
            # Inside dictionary we will have data for NewImage and OldImage
            # Inserted data will only have newImage and deleted will only have oldImage
            # We can select NewImage or OldImage
            new_image = record['dynamodb']['NewImage']

            # Get float value of the string placed inside the data of our intrest
            temp = float(new_image['temp_val']['S'])

            # If condition to decide if we have to send SNS
            if temp > 45:
                message = f"Heat Alert: Temperature recorded is {temp}°F"
                sns.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Message=message,
                    Subject="Weather Alert"
                )

if __name__ == "__main__":
    # Simulate a DynamoDB Stream event
    mock_event = {
        "Records": [
            {
                "eventName": "INSERT",
                "dynamodb": {
                    "NewImage": {
                        "temp_val": {"s": "54.78"},
                        "id": {"S": "001"},
                        "name": {"S": "Alice"}
                    }
                }
            },
            {
                "eventName": "MODIFY",
                "dynamodb": {
                    "OldImage": {
                        "id": {"S": "001"},
                        "name": {"S": "Alice"}
                    },
                    "NewImage": {
                        "id": {"S": "001"},
                        "name": {"S": "Alicia"}
                    }
                }
            },
            {
                "eventName": "REMOVE",
                "dynamodb": {
                    "OldImage": {
                        "id": {"S": "001"},
                        "name": {"S": "Alicia"}
                    }
                }
            }
        ]
    }

    print(lambda_handler(mock_event, None))