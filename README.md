# timetable-pinger-py

Using AWS Lambda + Cloudwatch to read your timetable from Google Sheets and keep you updated with Telegram bot API

## How?

* Basically you use Google Sheets as your  timetable. With every new week, duplicate the tab and update the dates on the 2nd row (just update the first cell then drag across the rest). 
   * The pinger will only work if it can find a column section marked with today's date on the last sheet in the spreadsheet.
* Fill in your timetable (you can use the fill helper at the bottom right, but it's not very well documented :p). Each cell is half an hour.
* The AWS lambda (once setup) will read the last sheet (which is presumably the sheet with the latest date) and compare the current cell with the previous cell. If there is a difference, it will send you a message using Telegram.

## Steps

## Integrating Google Sheets
1. I use this [template](https://docs.google.com/spreadsheets/d/15L7JJgl1YgaGM9b8nN6eNuTSHaSWa5_IQUya8mL9dXw/edit?usp=sharing) for my own timetabling purposes. You can make a copy. Note that the date format for the first row matters ("17 Jun", "18 Feb" etc). The application expects that the date is numerical and the month is 3 characters. However if you're using the template this should be automatically formatted for you.
2. There are numerous tutorials online on how to access google sheets. [The one I used](https://medium.com/@denisluiz/python-with-google-sheets-service-account-step-by-step-8f74c26ed28e) didn't involve gspread.
3. Although you don't need to setup the code, you'll need to undergo the steps in the tutorial to:
    * Get the SPREADSHEET_ID (which is the id in your spreadsheet url)
    * Get SERVICE_ACCOUNT_SECRET (you'll need to enable google drive API, create a service account etc
    * Make sure the lambda can access your spreadsheet by granting the service account access to your spreadsheet

## Integrating Telegram
1. Create a telegram bot (See [this](https://core.telegram.org/bots)).
2. Get it's **token**.
3. Send it a start message via Telegram using your account. The bot will send you messages via this chat.
    * Using your browser, call the [getUpdates method](https://core.telegram.org/bots/api#getupdates) using [Telegram Bot API](https://core.telegram.org/bots/api#making-requests). You can identify the **chat_id** this way.

## Integrating AWS Lambda & AWS Cloudwatch
1. Make sure you have an AWS account. Using this application uses about ~10k lambda requests per month if you set the scheduler to ping every 5 minutes, so it's definitely still within the free tier. With cron jobs you ping every 30 minutes. 
2. Take the zip file and upload it onto AWS lambda. You can follow [this](https://docs.aws.amazon.com/lambda/latest/dg/getting-started-create-function.html) to create a function, but you'll need to click Actions > upload zip file to upload it (the UI may change in the future though).
    * If you want to create your own zipfile (deployment package) refer to [this](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html#python-package-venv).
3. Use AWS Cloudwatch to trigger scheduled lambdas. See [this](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/RunLambdaSchedule.html) tutorial. You can also use cron (here is a [tool](https://crontab.guru/) for that). For my own uses, I used the cron expression `0,30 0-16 * * ? *`. 
   * Make sure to account for the GMT offset into your hours parameters. (e.g. Singapore time is GMT+8 and I want to set the inactive times from 00:00 to 08:00 in SG time, so that's 16:00 to 00:00 in GMT time). 
   * Note that you can combine commas and ranges in your cron expression.
   * AWS cloudwatch's cron expression is also little different from the usual cron params (See [accepted answer](https://stackoverflow.com/questions/59496652/aws-cloudwatch-rule-schedule-cron-expression-to-skip-2-hours-in-a-day)). If you got it right you'll see the next 10 trigger dates in the UI.
4. Set all the necessary environmental variables for the lambda (See "AWS Lambda Config Parameters above).

## AWS Lambda Config Parameters
Once you've got the lambda up and running, there are some environment variables you'll need to set for your lambda. See [this](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html) on how to setup environment variables. Basically you'll be setting the variables you got from the previous steps as environment variables for your lambda to reference.

Necessary:
* **SPREADSHEET_ID**: Your spreadsheet ID.
* **SERVICE_ACCOUNT_SECRET**: The secret JSON key for your service account. Copy the entire json in. Make sure your env. variables are encrypted (it should be automatically performed for you).
* **TELEGRAM_BOT_TOKEN**: Token which identifies your bot, used for Telegram bot API.
* **TELEGRAM_CHAT_ID**: The bot will use this chat id to send you notifications.
* **UTC_TIME_DIFFERENCE**: Time difference from UTC (e.g. Singapore is UTC+8, so it would be "8"). Unfortunately current implementation probably doesn't account for daylight saving time

Optional:
* **TRIGGER_INTERVAL**: Integer, set this as the interval (in minutes) you set your cloudwatch to trigger the lambda code. Treat this as the precision number if you use a cron or something (e.g. if your code triggers every half an hour, set it to 30 or 31, but 5 still works since it's precise enough). Default 5.
* **INACTIVE_START_HOUR** Integer, start hour (inclusive) where the lambda stops sending pings (e.g. for when you are sleeping). Range 0-23, default 0. Note that this is relative to your own time after `UTC_TIME_DIFFERENCE` has been applied.
* **INACTIVE_END_HOUR** Integer, end hour (exclusive) where the lambda stops sending pings (e.g. for when you are sleeping). Range 0-23, default 8. Note that this is relative to your own time after `UTC_TIME_DIFFERENCE` has been applied.
* **DEBUG_MODE**: If set to a value, then messages will be more verbose. Telegram bot will also receive debug messages.


## Others directory
* Contains development package for googleapiclient & google-oauth2-tools for AWS Lambda (necessary for running python code that uses these libraries on AWS Lambda)

## Potential issues
* The item checking system is quite rudimentary, so it only check the latest sheet.
* Your lambda may timeout with default settings. I set mine to use 15s, 192 mb of memory.
    * With debug mode off, a check that doesn't require pinging usually bills 0.1s; otherwise ~7 to 10s (still very much within 400,000-GB seconds).
    * With debug mode on, a check takes ~1s (to send message to telegram), otherwise ~10s.
