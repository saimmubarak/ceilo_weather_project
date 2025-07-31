from flask import Flask, request, jsonify
import datetime
import requests
from datetime import date
import boto3
import os

sns = boto3.client('sns')
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']

app = Flask(__name__)

API_Key = "S37C9TCD3UB38BKH6F7QDS466"
API_Key2 = "LKC7CSJNU53KN6SFMPN3QDDQF"

@app.route('/forecast', methods=['GET'])


def forecast_weather():
    city = request.args.get('city')
    postal_code = request.args.get('postal_code')

    # Get today's date
    today = date.today()
    date1 = today.strftime("%Y-%m-%d")
    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    location1 = f"{postal_code},{city}"

    url = (
        f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location1}/{tomorrow}?unitGroup=us&key={API_Key}&contentType=json"
    )
    url2 = (
        f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location1}/{tomorrow}?unitGroup=us&key={API_Key2}&contentType=json"
    )

    data = {}
    apiresponse = ""
    is_location_valid = True

    response = requests.get(url)

    limit_reached = False
    if response.status_code == 200:
        data = response.json()
        #print("first url worked")
    elif response.status_code == 429:
        #print("Request limit reached and alternative account will be used  ")
        response = requests.get(url2)
        if response.status_code == 200:
            data = response.json()
        elif response.status_code == 429:
            limit_reached = True
        else:
            print(f"Error {response.status_code}: {response.text}")
            limit_reached = True
    else:
        apiresponse = response.status_code
        print(f"Error {response.status_code}: {response.text}")


    #condition when location invalid
    if response.status_code != 200:
        print("Invalid Location")
        is_location_valid = False

    weather_forecast = data.get("days", [{}])[0]

    temp = int(weather_forecast .get("temp"))

    if temp > 75:
        message = f"Heat Alert: Temperature recorded is {temp}°F"
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject="Weather Alert"
        )

    forecast = {
        "postal_code": postal_code,
        "city": city,
        "Is_location_valid": is_location_valid,
        "visual_crossing_limit_reached": limit_reached,
        "datetime_val": str(weather_forecast .get("datetime")),
        "datetimeEpoch_val": str(weather_forecast .get("datetimeEpoch")),
        "temp_val": str(weather_forecast .get("temp")),
        "feelsLike_val": str(weather_forecast .get("feelslike")),
        "conditions": weather_forecast .get("conditions"),
        "humidity_val": str(weather_forecast .get("humidity")),
        "windspeed_val": str(weather_forecast .get("windspeed")),
        "pressure_val": str(weather_forecast .get("pressure"))
    }

    return jsonify(forecast)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
