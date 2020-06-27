# timetable-pinger-py

Using AWS Lambda + Cloudwatch to read your timetable from Google Sheets and keep you updated with Telegram bot API

## How?

* Basically you use Google Sheets as your  timetable. With every new week, duplicate the tab and update the dates on the 2nd row (just update the first cell then drag across the rest). 
* Fill in your timetable (you can use the fill helper at the bottom right, but it's not very well documented :p). Each cell is half an hour.
* The AWS lambda (once setup) will read the last sheet (which is presumably the sheet with the latest date) and compare the current cell with the previous cell. If there is a difference, it will send you a message using Telegram.

## [AWS Lambda Config Parameters](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)
Necessary:
* **SPREADSHEET_ID**: Your spreadsheet ID.
* **SERVICE_ACCOUNT_SECRET**: The secret JSON key for your service account. Copy the entire json in. Make sure your env. variables are encrypted.
* **TELEGRAM_BOT_TOKEN**: Token which identifies your bot, used for Telegram bot API.
* **TELEGRAM_CHAT_ID**: The bot will use this chat id to send you notifications.
* **UTC_TIME_DIFFERENCE**: Time difference from UTC (e.g. Singapore is UTC+8, so it would be "8"). Unfortunately current implementation probably doesn't account for daylight saving time

Optional:
* **TRIGGER_INTERVAL**: Integer, set this as the interval (in minutes) you set your cloudwatch to trigger the lambda code. Treat this as the precision number if you use a cron or something (e.g. if your code triggers every half an hour, set it to 30 or 31, but 5 still works since it's precise enough). Default 5.
* **INACTIVE_START_HOUR** Integer, start hour (inclusive) where the lambda stops sending pings (e.g. for when you are sleeping). Range 0-23, default 0.
* **INACTIVE_END_HOUR** Integer, end hour (exclusive) where the lambda stops sending pings (e.g. for when you are sleeping). Range 0-23, default 8.
* **DEBUG_MODE**: If set to a value, then messages will be more verbose. Telegram bot will also receive debug messages.

## Steps

## Integrating Google Sheets
1. I use this [template](https://docs.google.com/spreadsheets/d/15L7JJgl1YgaGM9b8nN6eNuTSHaSWa5_IQUya8mL9dXw/edit?usp=sharing) for my own timetabling purposes. You can make a copy. Note that the date format matters (17 Jun, 18 Feb etc)
2. There are numerous tutorials online on how to access google sheets. [The one I used](https://medium.com/@denisluiz/python-with-google-sheets-service-account-step-by-step-8f74c26ed28e) didn't involve gspread.
3. Although you don't need to setup the code, you'll need to undergo the steps in the tutorial to obtain:
    * SPREADSHEET_ID
    * SERVICE_ACCOUNT_SECRET
    * Make sure the lambda can access your spreadsheet

## Integrating Telegram
1. Create a telegram bot (See [this](https://core.telegram.org/bots)).
2. Get it's **token**.
3. Send it a start message via Telegram using your account. The bot will send you messages via this chat.
    * Using your browser, call the [getUpdates method](https://core.telegram.org/bots/api#getupdates) using [Telegram Bot API](https://core.telegram.org/bots/api#making-requests). You can identify the **chat_id** this way.

## Integrating AWS Lambda & AWS Cloudwatch
1. Make sure you have an AWS account. Using this application uses about ~10k lambda requests per month if you set the scheduler to ping every 5 minutes, so it's definitely still within the free tier. 
2. Take the zip file and upload it onto AWS lambda. You can follow [this](https://docs.aws.amazon.com/lambda/latest/dg/getting-started-create-function.html) to create a function, but you'll need to click Actions > upload zip file to upload it (the UI may change in the future though).
    * If you want to create your own zipfile (development package) refer to [this](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html#python-package-venv).
3. Use AWS Cloudwatch to trigger scheduled lambdas. See [this](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/RunLambdaSchedule.html) tutorial. I schedule mine to trigger every 5 minutes because I like the guarantee of precision, but you can get by with 10 or even 30 minutes. You can also use cron (here is a [tool](https://crontab.guru/) for that). I like to use the cron expression `0,30 8-23 * * ? *`. If you got it right you'll see the next 10 trigger dates.
4. Set all the necessary environmental variables for the lambda (See "AWS Lambda Config Parameters above).

## Others directory
* Contains development package for googleapiclient & google-oauth2-tools for AWS Lambda (necessary for running python code that uses these libraries on AWS Lambda)

## Potential issues
* The item checking system is quite rudimentary, so it only check the latest sheet.
* Your lambda may timeout with default settings. I set mine to use 15s, 192 mb of memory.
    * With debug mode off, a check that doesn't require pinging usually bills 0.1s; otherwise ~7 to 8s (still very much within 400,000-GB seconds)