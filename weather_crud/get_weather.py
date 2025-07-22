# get_weather Lambda
import json
from common import helper_functions as hf
import time


#An object created to refer to client and table name
#Specifies dynamodb usage and the table used (table_name)
#specifies client that is used for invoke (lambda)
AwsInfo = hf.AwsResources("lambda", "weather", None)




def lambda_handler(event, context):

    #extract postal code from payload
    postal_code = event.get("postal_code")
    city = event.get("city")


    # Get item from DynamoDB
    # specify the partition and sort keys of Database and their values
    key = {
        "postal_code": postal_code,
        "city": city
    }

    # requires table_name(AwsInfo.table), key_dit (key)
    response = hf.read_from_db(AwsInfo.table, key)


    #initialize variables that will be used in the if statements
    resource = ""
    time_from_database = ""
    visualcrossing_limit_reached = False
    is_location_valid = False
    expression_attribute_values = {}
    expression_attribute_names = {}
    parts = []
    service_available = True
    expiry_date = None

    #used in processing
    keys_to_exclude = {'postal_code', 'city'}


    if "Item" not in response:
        # Data was not found in the database

        # Receive weather data dict from visual_crossing and process it
        # Visual Crossing fetches weather data against the posta_code and city
        # The dict received will contain weather_data and some checks attacked to it.
        weather_data_dict = hf.get_and_handle_data_from_visual_crossing(postal_code, city)


        # Resource is a string that indicates the source of weather data
        resource = "Got Data From Visual Crossing"

        # Extracting location_valid boolean from dict
        is_location_valid = weather_data_dict.get("Is_location_valid")

        if is_location_valid:
            # Entered location is valid

            # Extracting visual_crossing_limit_reached boolean from dict
            visualcrossing_limit_reached = weather_data_dict.get("visual_crossing_limit_reached")

            # Visual Crossing was unable to send data and there was no data present in the DB as well
            if visualcrossing_limit_reached:
                # No weather data available
                service_available = False
                return {
                    "resource": resource,
                    "statusCode": 200,
                    "body": service_available,
                    "Is_Location_valid": is_location_valid
                }



            # Adding an Expiry_date value to the table entry for time to live functionality
            expiry_date = hf.expiry_date()
            weather_data_dict["expire_at"] = expiry_date

            print("weather_data_dict",type(weather_data_dict["datetime_val"]))

            # The database must be now updated with the new data received
            # All the preprocessing required before DataBase Update
            # Very Important to send this function Dict of data we want to update(cleaned item), list of keys to exclude(basically keys of DB), Empty parts list
            update_expr, expression_attribute_names, expression_attribute_values = hf.preprocessing_before_update(weather_data_dict, keys_to_exclude, parts, expression_attribute_names, expression_attribute_values)

            key = {
                "postal_code": postal_code,
                "city": city
            }
            # requires table_name(AwsInfo.table), key_dit (key)
            hf.update_db(AwsInfo.table, key, update_expr, expression_attribute_names,
                                    expression_attribute_values)

        else:
            return {
                "resource": resource,
                "statusCode": 200,
                "body": json.dumps(weather_data_dict),
                "Is_Location_valid": is_location_valid,
                "message": "Your entered location was not valid"
            }

    else:
        # Data was found in database

        # Resource is a string that indicates the source of weather data
        resource = "Got Data From DynamoDB"

        # Receive weather data dict from database and process it
        # Weather data received against the posta_code and city
        # The dict received will contain weather_data and some checks attacked to it.
        item = response.get("Item")

        # Converting data to float values
        weather_data_dict = hf.clean_decimals(item)

        is_location_valid = True


        # Make a temp value for database data as it will be used...
        # ...when we get visualcrossing data but there is some...
        # ...problem in visual crossing data and we need to revert...
        # ...back to data from database
        temp_cleaned_item = weather_data_dict

        # Epoch-time of the data received from database
        time_from_database = weather_data_dict.get("datetimeEpoch_val")

        # If statement prevents an error if the database has no epoch-time
        # Time data from db wasn't present
        if time_from_database:

            # Function gives us difference in seconds between time from database and present time
            passed_time = hf.time_difference(time_from_database)

            # Statement checks is the passed time is more than 6hrs
            # If data in the database was too old
            if passed_time >= 21600:
                # Data was present in the database but was too old
                # We will now get fresh data from visual crossing

                # Receive weather data dict from visual_crossing and process it
                # Visual Crossing fetches weather data against the posta_code and city
                # The dict received will contain weather_data and some checks attacked to it.
                visual_crossing_item = hf.get_and_handle_data_from_visual_crossing(postal_code, city)

                # Extracting visual_crossing_limit_reached boolean from dict
                # Limit_reached boolean will try to send user the current Database data instead of Visual Crossing data
                visualcrossing_limit_reached = visual_crossing_item.get("visual_crossing_limit_reached")

                # Limit_reached boolean will send user the current Database data instead of Visual Crossing data
                if visualcrossing_limit_reached:
                    # Database data
                    resource = "Got Data From DynamoDB"
                    weather_data_dict = temp_cleaned_item
                else:
                    # Visual crossing data
                    resource = "Got Data From Visual Crossing"
                    weather_data_dict = visual_crossing_item

                    # Adding an Expiry_date value to the table entry for time to live functionality
                    expiry_date = hf.expiry_date()
                    weather_data_dict["expire_at"] = expiry_date

                    # The database must be now updated with the new data received
                    # All the preprocessing required before DataBase Update
                    # Very Important to send this function Dict of data we want to update(cleaned item), list of keys to exclude(basically keys of DB), Empty parts list
                    update_expr, expression_attribute_names, expression_attribute_values = hf.preprocessing_before_update(
                        weather_data_dict, keys_to_exclude, parts, expression_attribute_names, expression_attribute_values)

                    # update database function
                    key = {
                        "postal_code": postal_code,
                        "city": city
                    }
                    # requires table_name(AwsInfo.table), key_dit (key)
                    response = hf.update_db(AwsInfo.table, key, update_expr, expression_attribute_names,
                                            expression_attribute_values)


    # Removing limit_reached boolean from payload
    weather_data_dict.pop("visual_crossing_limit_reached", None)

    #cleaned_item = hf.clean_decimals(cleaned_item)

    return {
        "resource": resource,
        "statusCode": 200,
        "body": json.dumps(weather_data_dict),
        "Is_Location_valid": is_location_valid
    }

if __name__ == "__main__":
    test_event = {
        "postal_code": "74602",
        "city": "Texas",
    }
    print(lambda_handler(test_event, None))
