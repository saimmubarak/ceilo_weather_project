import json
from common import helper_functions as hf

# An object created to refer to client and table name
# Specifies dynamodb usage and the table used (table_name)
# Specifies client that is used for invoke (lambda)
AwsInfo = hf.AwsResources("lambda", "users", None)

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


    # Get item from DynamoDB
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



    print("postal_code:", postal_code)
    print("city:", city)

    # We will get weather data for the user from either visual_crossing or dynamodb
    # Invoke get_weather() "a lambda that handles getting weather data"
    # Getweather requires a payload with postal_code and city
    payload = {
        "postal_code": postal_code,
        "city": city
    }
    # The function aws_lambda_invoke invokes the lambda specified
    # The function requires Function_Name, Invocation_Type, Payload, s3 Client
    # The function return a dictionary containing weather data or error message
    weatherdata= hf.aws_lambda_invoke("serverless-crud-dev-getWeather","RequestResponse",payload,AwsInfo.client)


    print("weatherdata:", weatherdata)

    # In the create-weather lambda that we invoked just now...
    # ...we have a if block what returns a boolean instead of a body...
    # ...this boolean indicates weather we got weatherdata or not...
    # ...if this boolean is set to false we return an error message...
    # ...of service not available
    service_disabled_check = weatherdata.get("body")
    if service_disabled_check == False:
        return {
            "statusCode": 200,
            "body": "Our Service is currently Unavailable"
        }


    # Extract resource string that specifies where the data comes from Visual Crossing or DynamoDB
    resource = weatherdata.get("resource")


    # Extract is_location_valid boolean that specifies is the location provided by user exists or not
    is_location_valid = weatherdata.get("Is_Location_valid")

    # A check for valid location
    # We will have some weather data only if location is valid
    # If our get_weather indicated valid location only then will...
    # ...we have some weather data to give to user
    if is_location_valid:
        #location is valid

        # storing response in weather dict
        if weatherdata.get("statusCode") == 200:
            weather_dict = json.loads(weatherdata["body"])

        else:
            weather_dict = None

        # Attributes that we want to return read request with names changed eg temp not temp_val
        selected_weather = {
            "temp": weather_dict.get("temp_val"),
            "feelsLike": weather_dict.get("feelsLike_val"),
            "conditions": weather_dict.get("conditions"),
            "humidity": weather_dict.get("humidity_val"),
            "windspeed": weather_dict.get("windspeed_val"),
            "pressure": weather_dict.get("pressure_val")
        }

        # We will be creating a dictionary(combined) that has the combined dictionaries of user-data, ...
        # ...weather-data, profile-pic url
        # This if statement checks whether we have an imageURL
        # If we have an imageURL we place it inside combined dictionary
        if image_url:
            combined = {
                "resource": resource,
                "user": item,
                "weather": selected_weather,
                "profile_pic": image_url
            }
        else:
            combined = {
                "resource": resource,
                "user": item,
                "weather": selected_weather
            }
    else:
        # Location is not valid
        # We will have some weather data only if location is valid
        # If our get_weather lambda indicated invalid location then we...
        # ...will have no weather data to give to user

        # We will be creating a dictionary(combined) that has the combined dictionaries of user-data, ...
        # ...weather-data, profile-pic url
        # This if statement checks whether we have an imageURL
        # If we have an imageURL we place it inside combined dictionary
        if image_url:
            combined = {
                "resource": resource,
                "user": item,
                "profile_pic": image_url,
                "location_error": "Unable to get weather data of your location"
            }
        else:
            combined = {
                "resource": resource,
                "user": item,
                "location_error": "Unable to get weather data of your location"
            }

    return {
        "statusCode": 200,
        "body": json.dumps(combined)
    }

if __name__ == "__main__":

    event = {
        "queryStringParameters": {
            "id": "ad53d09f-ff31-407f-bfe2-1dcd0671c4de",
            "name": "Taimoor"
        }
    }

    # Call the lambda handler function
    print(lambda_handler(event, None))



