import time
from decimal import Decimal
import boto3
from external_weather import visual_crossing_request as vc
import json


# This function receives weather data from visualcrossing and makes its decimal values float
# Calls get_weather_data_from_visual_crossing to get weather data
# Calls clean_decimals to process weather_data
def get_and_handle_data_from_visual_crossing(postal_code, city):
    # Receive weather data dict from visual_crossing and process it
    weather_data = vc.get_weather_data_from_visual_crossing(postal_code, city)
    weather_data = clean_decimals(weather_data)

    return weather_data


# todo change name DONE///
# Class definition
# This class makes attributes for boto3 client, dynamodb name, table name, s3 bucket name, s3 bucket client
class AwsResources:
    def __init__(self, client_name = None, table_name = None, bucket_name = None):

        if client_name:
            self.client = boto3.client(client_name)
        if table_name:
            self.dynamodb = boto3.resource('dynamodb')
            self.table = self.dynamodb.Table(table_name)
        if bucket_name:
            self.s3_bucket = bucket_name
            self.s3 = boto3.client('s3')


#todo make this method dynamic (work for any table that is given in input) DONE////
#todo pep8 standards

# Functions for simple dynamodb calls
# These methods are dynamic (work for any table that is given in input)

# 1 Put data in database
def put_to_db(table_name, item_dict):
    response = table_name.put_item(Item=item_dict)
    return response

# 2 delete from database against id and name
def delete_from_db(table_name, user_id, user_name):
    response = table_name.delete_item(
        Key={
            "id": user_id,
            "name": user_name
        }
    )
    return response

# 3 read from database against partition key and sort key
def read_from_db(table_name,table_key):
    response = table_name.get_item(Key=table_key)
    return response

# 4 update database against partition key and sort key
def update_db(table_name, table_key, update_expr, expression_attribute_names, expression_attribute_values):
    response = table_name.update_item(
        Key=table_key,
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values,
        ReturnValues="ALL_NEW")
    return response

# Todo change name to awslambda invoke DONE///
# This function invokes a lambda
# eg we can call this function to invoke Lambda A from within Lambda B
def aws_lambda_invoke(func_name,invo_type,payload,client):
    # Invoke (get_weather)
    response = client.invoke(
        FunctionName=func_name,

        InvocationType=invo_type,
        Payload=json.dumps(payload)
    )
    response_payload = response["Payload"].read().decode("utf-8")
    parsed_response = json.loads(response_payload)

    return parsed_response



# Function parse data based on type of data either body or form-data "queryStringParameters"
def parse_data(event,context):
    params = event.get("queryStringParameters")
    if params:
        #data sent as parameters probably a get request
        return params
    if "body" in event and event["body"]:
        body = json.loads(event["body"])
        return body

    return{
        "statusCode": 400
    }

# When updating some database and sending new data to the database...
# ...the strings keys_to_exclude, expression_attribute_name, expression_attribute_values...
# ...need to be processed and converted to a form that is acceptable for our update_db function
def preprocessing_before_update(cleaned_item, keys_to_exclude, parts, expression_attribute_names, expression_attribute_values):
    # Exclude id and name
    for key, value in cleaned_item.items():
        if key not in keys_to_exclude:
            placeholder_name = f"#{key}"
            placeholder_value = f":{key}"

            # Build the parts
            expression_attribute_names[placeholder_name] = key
            expression_attribute_values[placeholder_value] = value
            parts.append(f"{placeholder_name} = {placeholder_value}")

    # Join parts into SET expression
    update_expr = "SET " + ", ".join(parts)

    return update_expr, expression_attribute_names, expression_attribute_values


# This is a recursive function that converts objects of Decimal type to Float
# On the leaves of this recursive function we have the code "return float(obj)"
# If we dont normalize to float then we will get null values in weather data
def clean_decimals(obj):
    if isinstance(obj, list):
        return [clean_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: clean_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj


# Finds the difference in present time and time-epoch of the weather data stored in our database
# The time-difference/passed-time will be used to determine weather to use existing data or get new data
def time_difference(db_date_time):

    if not db_date_time:
        return 12000

    # Convert string to integer
    epoch_timestamp = int(db_date_time)

    # Get current time as epoch timestamp
    current_epoch = int(time.time())

    passed_time = current_epoch - epoch_timestamp


    return passed_time



# Check if location value received in get request
# Split location input into postal_code and city
def check_and_handle_location(location):
    # a check to verify if location was sent in post request otherwise error produced
    if not location:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'location is required in format postal_code,city'})
        }
    # Split location into postal_code and city
    postal_code, city = location.split(",")
    postal_code = postal_code.strip()
    city = city.strip()

    return postal_code, city


# Contenttype that is placed in headers is needed to process form-data
# We normalize it by converting to lowercase
def get_contenttype_from_form_data(event):
    # To Handle both application/json type and form data we must get content type that is in headers{}
    headers =event.get('headers',{})

    # Convert uppercase letters to lowers case to avoid errors
    headers_normalized = {}
    for k, v in headers.items():
        lower_key = k.lower()
        headers_normalized[lower_key] = v

    # Content type info is placed in content_type within header that we normalized by converting to lowercase
    content_type = headers_normalized.get("content-type", "")
    return content_type

# Function used for placing image to s3 bucket
# The function requires client_name(s3), bucket_name(bucket_name), key(s3_key), contenttype(content_type)
def put_image_in_s3(s3, bucket_name,s3_key, file_bytes, content_type):
    s3.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=file_bytes,
                    ContentType=content_type
                )
    return 0


def expiry_date():
    # Get current time as epoch timestamp
    current_epoch = float(time.time())

    expire_date = current_epoch + 172800

    expire_date = str(clean_decimals(expire_date))

    return expire_date

def complete_processing_and_db_update(weather_data_dict, service_available, resource, keys_to_exclude, parts, expression_attribute_names,
        expression_attribute_values,key,dynamodb_table_name):

    # Adding an Expiry_date value to the table entry for time to live functionality
    expirydate = expiry_date()
    weather_data_dict["expire_at"] = expirydate

    # The database must be now updated with the new data received
    # All the preprocessing required before DataBase Update
    # Very Important to send this function Dict of data we want to update(cleaned item), list of keys to exclude(basically keys of DB), Empty parts list
    update_expr, expression_attribute_names, expression_attribute_values = preprocessing_before_update(
        weather_data_dict, keys_to_exclude, parts, expression_attribute_names,
        expression_attribute_values)

    # requires table_name(AwsInfo.table), key_dit (key)
    update_db(dynamodb_table_name, key, update_expr, expression_attribute_names,
                 expression_attribute_values)


if __name__ == "__main__":
    print(expiry_date())