import datetime
import json
import os
import urllib.parse
import urllib.request

# You'll need to setup a development pack for these
# https://aws.amazon.com/premiumsupport/knowledge-center/build-python-lambda-deployment-package/
# make sure to install python3-pip and call using pip3
# https://stackoverflow.com/questions/4495120/combine-user-with-prefix-error-with-setup-py-install
# Also see: "with a virtual environment"
# https://docs.aws.amazon.com/lambda/latest/dg/python-package.html#python-package-venv
from googleapiclient import discovery
from google.oauth2 import service_account

# AWS LAMBDA ENVIRONMENT VARIABLES
# See https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html

SPREADSHEET_ID = str(os.environ['SPREADSHEET_ID'])
TELEGRAM_BOT_TOKEN = str(os.environ['TELEGRAM_BOT_TOKEN'])
TELEGRAM_CHAT_ID = str(os.environ['TELEGRAM_CHAT_ID'])
UTC_TIME_DIFFERENCE = int(os.environ['UTC_TIME_DIFFERENCE'])

TRIGGER_INTERVAL = 5
INACTIVE_START_HOUR = 0
INACTIVE_END_HOUR = 8
DEBUG_MODE = 0

if 'TRIGGER_INTERVAL' in os.environ:
    TRIGGER_INTERVAL = int(os.environ['TRIGGER_INTERVAL'])
if 'INACTIVE_START_HOUR' in os.environ:
    INACTIVE_START_HOUR = int(os.environ['INACTIVE_START_HOUR'])
if 'INACTIVE_END_HOUR' in os.environ:
    INACTIVE_END_HOUR = int(os.environ['INACTIVE_END_HOUR'])
if 'DEBUG_MODE' in os.environ:
    DEBUG_MODE = os.environ['DEBUG_MODE']

# Other constants specific to the spreadsheet
DAY_JUMP_INDEX = 3
day_col_index = [i for i in range(0, 7 * DAY_JUMP_INDEX, DAY_JUMP_INDEX)]
DATA_START_INDEX = 3
hour_row_index = [i for i in range(DATA_START_INDEX, 24 + DATA_START_INDEX)]

# Other constants
SCOPES = ["https://www.googleapis.com/auth/drive", 
    "https://www.googleapis.com/auth/drive.file", 
    "https://www.googleapis.com/auth/spreadsheets"
]

def ret_msg(text):
    if DEBUG_MODE:
        return text
    else:
        return "operational"

def get_formatted_date(datetime_object):
    # Return "17 Jun" for example
    # https://stackabuse.com/converting-strings-to-datetime-in-python/
    return datetime_object.strftime('%d %b')

def get_day_str(sheet_data, day_index):
    # Get day from ss headers
    col_index = day_col_index[day_index]
    return sheet_data["sheets"][0]["data"][0]["rowData"][0]["values"][col_index]["formattedValue"]

def get_item_str(sheet_data, day_index, hour, is_second_half):
    # Get item from ss
    col_index = day_col_index[day_index] + (1 if is_second_half else 0)
    row_index = hour_row_index[hour]
    return sheet_data["sheets"][0]["data"][0]["rowData"][row_index]['values'][col_index]['formattedValue']

def get_item_str_from_datetime(sheet_data, datetime_object):
    day_index = get_day_index(sheet_data, datetime_object)
    hour = datetime_object.hour
    is_second_half = datetime_object.minute >= 30
    return get_item_str(sheet_data, day_index, hour, is_second_half)

def get_day_index(sheet_data, datetime_object):
    # Iteratively check if the given day string is equals to anyy
    day_str = get_formatted_date(datetime_object)
    for i in range(len(day_col_index)):
        if day_str == get_day_str(sheet_data, i):
            return i
    raise ValueError("Could not find day_index for " + day_str)

def is_inactive_time(datetime_object):
    # Check it's not night
    return not (datetime_object.hour > INACTIVE_END_HOUR or datetime_object.hour < INACTIVE_START_HOUR)

def get_previous_item_str(sheet_data, datetime_object):
    # Assumes same day, doesn't work if it needs to check a previous sheet
    day_index = get_day_index(sheet_data, datetime_object)
    hour = datetime_object.hour
    is_second_half = datetime_object.minute >= 30
    if is_second_half:
        is_second_half = 0
    else:
        hour -= 1
        is_second_half = 1
    if (hour < 0):
        day_index -= 1
        hour = 23
    # if day < 0: unsupported
    return get_item_str(sheet_data, day_index, hour, is_second_half)
    
def send_telegram_message(text):
    text = str(text)
    # https://www.twilio.com/blog/2016/12/http-requests-in-python-3.html
    # https://stackoverflow.com/questions/40557606/how-to-url-encode-in-python-3
    url = 'https://api.telegram.org/bot' + TELEGRAM_BOT_TOKEN \
        + '/sendMessage?chat_id=' + TELEGRAM_CHAT_ID + '&text='
    payload = urllib.parse.quote(text)
    url += payload
    urllib.request.urlopen(url)

def is_time_to_ping(datetime_object):
    # Only ping after every hour or half hour
    return (datetime_object.minute - TRIGGER_INTERVAL < 0) \
        or (datetime_object.minute > 30 and datetime_object.minute - TRIGGER_INTERVAL <= 30)
    
def lambda_handler(event, context):
    datetime_object = datetime.datetime.strptime(event["time"], '%Y-%m-%dT%H:%M:%SZ')
    datetime_object += datetime.timedelta(hours=UTC_TIME_DIFFERENCE)

    if DEBUG_MODE:
        send_telegram_message("Event time: " + str(event["time"]))
        send_telegram_message("Processed time: " + str(datetime_object.strftime("%Y-%m-%d %H:%M")))

    if not is_time_to_ping(datetime_object):
        if DEBUG_MODE:
            send_telegram_message("not is_time_to_ping")
        return { 'statusCode': 200, 'body': json.dumps(ret_msg('It is not yet time to ping user')) }

    if is_inactive_time(datetime_object):
        if DEBUG_MODE:
            send_telegram_message("is_inactive_time")
        return { 'statusCode': 200, 'body': json.dumps(ret_msg('User on silent mode at this time')) }

    try:
        # Setup access
        key_json = json.loads(os.environ['SERVICE_ACCOUNT_SECRET'])
        creds = service_account.Credentials.from_service_account_info(key_json, scopes=SCOPES)
        service = discovery.build('sheets', 'v4', credentials=creds, cache_discovery=False)
        del key_json
        # See for API: http://googleapis.github.io/google-api-python-client/docs/dyn/sheets_v4.spreadsheets.html     
        # Get last sheet
        # https://stackoverflow.com/questions/38245714/get-list-of-sheets-and-latest-sheet-in-google-spreadsheet-api-v4-in-python
        sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = sheet_metadata.get('sheets', '')
        sheet_index = len(sheets) - 1
        sheet_title = sheets[sheet_index].get("properties", {}).get("title", "Sheet1")
        # Generate range name
        range_name = "\'" + sheet_title + "\'!B2:U28"
        # Get sheet data
        sheet_data = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID, ranges=range_name, includeGridData=True).execute()

        now_item = get_item_str_from_datetime(sheet_data, datetime_object)
        prev_item = get_previous_item_str(sheet_data, datetime_object)
        if (now_item != prev_item):
            if DEBUG_MODE:
                send_telegram_message("Old Item: " + prev_item)
            send_telegram_message("New Item: " + now_item)
            return { 'statusCode': 200, 'body': json.dumps(ret_msg("ping sent")) }
        else:
            if DEBUG_MODE:
                send_telegram_message("Items the same: " + now_item)
            return { 'statusCode': 200, 'body': json.dumps(ret_msg("ping not sent as items were the same")) }
    except ValueError as error:
        if DEBUG_MODE:
            send_telegram_message(error)
        return { 'statusCode': 500, 'body': json.dumps(ret_msg(error)) }

    # Process should not reach this point
    return { 'statusCode': 200, 'body': json.dumps(ret_msg('should not have reached here')) }

# lambda_handler({"time": "2020-06-27T12:35:20Z"}, None)