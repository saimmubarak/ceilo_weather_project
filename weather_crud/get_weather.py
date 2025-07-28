# get_weather Lambda
import json
from common import helper_functions as hf
import time
import boto3
import os
import uuid

sqs = boto3.client('sqs')

#send_back_queue_url = os.environ['RECEIVE_QUEUE_URL']  # processed-weather-queue.fifo

send_back_queue_url = "https://sqs.eu-north-1.amazonaws.com/392894084273/processed-weather-queue.fifo"


#An object created to refer to client and table name
#Specifies dynamodb usage and the table used (table_name)
#specifies client that is used for invoke (lambda)
AwsInfo = hf.AwsResources("lambda", "weather", None)


def lambda_handler(event, context):

    for record in event['Records']:
        body = json.loads(record["body"])
        postal_code = body["postal_code"]
        city = body["city"]
        request_id = body["request_id"]

        # postal_code = event["postal_code"]
        # city = event["city"]
        # request_id = event["request_id"]



        # Get item from DynamoDB
        # specify the partition and sort keys of Database and their values
        key = {
            "postal_code": postal_code,
            "city": city
        }

        # requires table_name(AwsInfo.table), key_dit (key)
        response = hf.read_from_db(AwsInfo.table, key)


        # Initializing data
        expression_attribute_values = {}
        expression_attribute_names = {}
        parts = []
        service_available = True

        # Used in processing update strings. To exclude keys from data
        keys_to_exclude = {'postal_code', 'city'}
        if "Item" not in response: # Data was not found in the database
            print("Data was not found in the database")###
            # Receive weather data dict from visual_crossing and process it
            # Visual Crossing fetches weather data against the posta_code and city
            # The dict received will contain weather_data and some checks attacked to it.
            weather_data_dict = hf.get_and_handle_data_from_visual_crossing(postal_code, city)

            # Extracting location_valid boolean from dict
            is_location_valid = weather_data_dict.get("Is_location_valid")
            if is_location_valid:
                print("Data was not found in the database + location was valid")###
                # Entered location is

                # Extracting visual_crossing_limit_reached boolean from dict
                visualcrossing_limit_reached = weather_data_dict.get("visual_crossing_limit_reached")
                if visualcrossing_limit_reached: # Visual Crossing was unable to send data and there was no data present in the DB as well
                    print("Data was not found in the database + location was valid + limit reached")  ###
                    # No weather data available
                    is_location_valid = True
                    service_available = False
                    resource = "NA"

                    # # Key sent to database update function
                    # key = {
                    #     "postal_code": postal_code,
                    #     "city": city
                    # }
                    # # Handles the entire process of updating database
                    # complete_processing_and_db_update(weather_data_dict, service_available, resource, keys_to_exclude,
                    #                                   parts, expression_attribute_names,
                    #                                   expression_attribute_values, key)

                else: # Weather data received from visual
                    print("Data was not found in the database + location was valid + limit not reached")
                    service_available = True
                    is_location_valid = True
                    resource = "Data From Visual Crossing"

                    # Key sent to database update function
                    key = {
                        "postal_code": postal_code,
                        "city": city
                    }
                    # Handles the entire process of updating database
                    hf.complete_processing_and_db_update(weather_data_dict, service_available, resource, keys_to_exclude,
                                                      parts, expression_attribute_names,
                                                      expression_attribute_values, key,AwsInfo.table)


            else: # Location entered by user is not valid
                print("Data was not found in the database + location was not valid")###
                is_location_valid = False
                resource = "NA"
                service_available = True

                # # Key sent to database update function
                # key = {
                #     "postal_code": postal_code,
                #     "city": city
                # }
                # # Handles the entire process of updating database
                # complete_processing_and_db_update(weather_data_dict, service_available, resource, keys_to_exclude,
                #                                   parts, expression_attribute_names,
                #                                   expression_attribute_values, key)
        else: # Data found in database
            print("Data was found in the database")
            # We don't put data with invalid location into the db so for data inside the db we don't need invalid location check

            # Extracting weather data from the response we received
            weather_data_dict = response.get("Item")

            # Cleaning decimals of weather data
            weather_data_dict = hf.clean_decimals(weather_data_dict)

            # Making a temp storage of weather data from database
            temp_cleaned_item = weather_data_dict

            # Epoch-time of the data received from database
            time_of_last_data_update = weather_data_dict.get("datetimeEpoch_val")
            passed_time = hf.time_difference(time_of_last_data_update)

            if passed_time>=21600: # Data was in database but was too old
                print("Data was found in the database + data too old")###
                # Receive weather data dict from visual_crossing and process it
                # Visual Crossing fetches weather data against the posta_code and city
                # The dict received will contain weather_data and some checks attacked to it.
                weather_data_dict = hf.get_and_handle_data_from_visual_crossing(postal_code, city)

                # As data with same location was already present in dynamodb we can conclude that location is valid so no location check

                visualcrossing_limit_reached = weather_data_dict.get("visual_crossing_limit_reached")
                if visualcrossing_limit_reached: # Visual crossing limit was reached so we will send current dynamodb data
                    print("Data was found in the database + data too old + limit reached")###
                    service_available = True
                    is_location_valid = True
                    resource = "Data From DynamoDB"
                    # Using current dynamodb data to send to user.
                    weather_data_dict = temp_cleaned_item

                    # # Key sent to database update function
                    # key = {
                    #     "postal_code": postal_code,
                    #     "city": city
                    # }
                    # # Handles the entire process of updating database
                    # complete_processing_and_db_update(weather_data_dict, service_available, resource, keys_to_exclude,
                    #                                   parts, expression_attribute_names,
                    #                                   expression_attribute_values, key)

                else: # Visual Crossing limit not reached thus send data from visual_crossing
                    print("Data was found in the database + data too old + limit not reached")###
                    service_available = True
                    is_location_valid = True
                    resource = "Data From Visual Crossing"

                    # Key sent to database update function
                    key = {
                        "postal_code": postal_code,
                        "city": city
                    }
                    # Handles the entire process of updating database
                    hf.complete_processing_and_db_update(weather_data_dict, service_available, resource, keys_to_exclude,
                                                      parts, expression_attribute_names,
                                                      expression_attribute_values, key, AwsInfo.table)


            else: # Data was in database and not old
                print("Data was found found in the database + data not too old")###
                visualcrossing_limit_reached = False
                service_available = True
                is_location_valid = True
                resource = "Data From DynamoDB"

                # # Key sent to database update function
                # key = {
                #     "postal_code": postal_code,
                #     "city": city
                # }
                # # Handles the entire process of updating database
                # complete_processing_and_db_update(weather_data_dict, service_available, resource, keys_to_exclude,
                #                                   parts, expression_attribute_names,
                #                                   expression_attribute_values, key)

        # Data to be sent back to read_user through queue
        # Data sent to show users their weather data
        temp_val = weather_data_dict.get("temp_val")
        feelsLike_val = weather_data_dict.get("feelsLike_val")
        conditions = weather_data_dict.get("conditions")
        humidity_val = weather_data_dict.get("humidity_val")
        windspeed_val= weather_data_dict.get("windspeed_val")
        pressure_val= weather_data_dict.get("pressure_val")
        print("pressure_val*************",pressure_val)

        # Making a combined dict for data to be sent back to read_user
        processed_result ={
            "temp_val": temp_val,
            "feelsLike_val": feelsLike_val,
            "conditions": conditions,
            "humidity_val": humidity_val,
            "windspeed_val": windspeed_val,
            "pressure_val": pressure_val,
            "is_location_valid": is_location_valid,
            "service_available": service_available,
            "resource": resource,
            "difference": request_id
        }

        # Creating MessageGroupId for asynchronous parallel queues
        location = f"{postal_code}-{city}".replace(" ", "-")
        # Send back processed result to LambdaA
        result=sqs.send_message(
            QueueUrl=send_back_queue_url,
            MessageBody=json.dumps(processed_result),
            MessageGroupId=location,
            MessageDeduplicationId = request_id,
            MessageAttributes={
                "RequestId": {
                    "StringValue": request_id,
                    "DataType": "String"
                }
            }
        )
        if result.get("ResponseMetadata", {}).get("HTTPStatusCode") == 200 and "MessageId" in result:
            print("Message successfully sent to SQS :)")
        else:
            print("Failed to send message to SQS :(")
        print("weather_data_dict",weather_data_dict)
        #return processed_result



    return {
        "statusCode": 200,
        "body": "Processed all weather data"
    }
if __name__ == "__main__":
    test_event = {
        "Records": [
            {
                "body": json.dumps({
                    "postal_code": "53031",
                    "city": "Wisconsin",
                    "request_id": str(uuid.uuid4())
                })
            }
        ]
    }
    print(lambda_handler(test_event, None))
