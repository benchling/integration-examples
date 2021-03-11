# lambda_function.py

import json
import os
import urllib3


def lambda_handler(event, context):
    http = urllib3.PoolManager()
    assignee_handles = []
    for assignee in event["detail"]["request"]["assignees"]:
        assignee_handles.append("@" + str(assignee["user"]["handle"]))

    # Create data payload for Slack POST request
    # see https://api.slack.com/block-kit for more formatting options for the message
    data = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": " New Benchling Request Here!\n"
                    + "<"
                    + event["detail"]["request"]["webURL"]
                    + "|Go To Benchling Request >",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": " *Requestor*:\n"
                        + "@"
                        + str(event["detail"]["request"]["creator"]["handle"]),
                    },
                    {"type": "mrkdwn", "text": " *Assignee(s)*:\n" + ", ".join(assignee_handles)},
                    {
                        "type": "mrkdwn",
                        "text": " *Comments*:\n"
                        + str(event["detail"]["request"]["fields"]["request_comments"]["value"]),
                    },
                ],
            },
            {"type": "divider"},
        ]
    }

    # Send POST request to webhook URL generated in Slack App admin settings
    resp = http.request(
        "POST",
        os.environ["SLACK_WEBHOOK_URL"],
        body=json.dumps(data),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(os.environ["SLACK_TOKEN"]),
        },
    )

    return {"statusCode": resp.status, "statusData": resp.data}
