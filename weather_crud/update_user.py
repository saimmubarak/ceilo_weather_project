import json
from common import helper_functions as hf

#An object created to refer to client and table name
#Specifies dynamodb usage and the table used (table_name)
#specifies client that is used for invoke (lambda)
AwsInfo = hf.AwsResources(None, "users", None)


def lambda_handler(event, context):

    # Parse data sent in event according to type of data sent
    # json data in body
    # parameters
    body = hf.parse_data(event, context)

    # Extract userid and name from params
    user_id = body.get("id")
    name = body.get("name")

    # Build the expressions
    expression_attribute_values = {}
    expression_attribute_names = {}
    parts = []

    # Exclude id and name
    keys_to_exclude = {'id', 'name'}

    # All the preprocessing required before DataBase Update
    # Very Important to send this function Dict of data we want to update(cleaned item), list of keys to exclude(basically keys of DB), Empty parts list
    update_expr, expression_attribute_names, expression_attribute_values = hf.preprocessing_before_update(
        body, keys_to_exclude, parts, expression_attribute_names, expression_attribute_values)

    # Key dictionary
    key = {
        "id": user_id,
        "name": name
    }

    # Update database
    response = hf.update_db(AwsInfo.table, key, update_expr, expression_attribute_names, expression_attribute_values)



    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Update successful", "updated": response.get("Attributes")})
    }

if __name__ == "__main__":
    # This simulates an API Gateway event sending JSON
    event = {
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "id": "473a072e-80c8-48d7-a598-b16df6ec8568",
            "name": "fahad",
            "email": "saim@example.com",
            "bloodtype": "A=",
            "age":"21"
        })
    }

    context = None

    # Call the Lambda handler
    print(lambda_handler(event, context))

