import json
import os

import click
import requests
import time

from file_helpers import calculate_md5, encode_base64


class BadRequestException(Exception):
    def __init__(self, message, rv):
        super(BadRequestException, self).__init__(message)
        self.rv = rv


def api_get(domain, api_key, path):
    url = "https://{}/api/v2/{}".format(domain, path)
    rv = requests.get(url, auth=(api_key, ""), verify=False)
    if rv.status_code >= 400:
        raise BadRequestException(
            "Server returned status {}. Response:\n{}".format(
                rv.status_code, json.dumps(rv.json())
            ),
            rv,
        )
    return rv.json()


def api_post(domain, api_key, path, body):
    url = "https://{}/api/v2/{}".format(domain, path)
    rv = requests.post(url, json=body, auth=(api_key, ""), verify=False)
    if rv.status_code >= 400:
        raise BadRequestException(
            "Server returned status {}. Response:\n{}".format(
                rv.status_code, json.dumps(rv.json())
            ),
            rv,
        )
    return rv.json()


def wait_on_blob_upload_status_response(domain, api_key, blob_id):
    while True:
        blob_status_response = api_get(domain, api_key, "blobs/{}".format(blob_id))
        status = blob_status_response["uploadStatus"]
        if status == "IN_PROGRESS":
            print("Waiting for blob to complete uploading...")
            time.sleep(5)
        else:
            if status == "ABORTED":
                return "ABORTED"
            elif status == "COMPLETE":
                return "COMPLETE", blob_status_response


@click.command()
@click.option(
    "--domain",
    help="Domain name of your Benchling instance, e.g. example.benchling.com",
    required=True,
)
@click.option("--api-key", help="Your API key", required=True)
@click.option("--filepath", help="Filepath of blob to upload", required=True)
@click.option("--destination-filename", help="Name of file (omit to keep same name as source)", required=False)
def main(
        domain,
        api_key,
        filepath,
        destination_filename,
):
    name = destination_filename
    if name is None:
        name = os.path.basename(filepath)

    with open(filepath, "rb") as file:
        file_contents = file.read()
        encoded64 = encode_base64(file_contents)
        md5 = calculate_md5(file_contents)
        res = api_post(domain, api_key, "blobs", {
            "data64": encoded64,
            "md5": md5,
            "mimeType": "application/octet-stream",
            "name": name,
            "type": "RAW_FILE",
        })
        blob_id = res["id"]
        status = wait_on_blob_upload_status_response(domain, api_key, blob_id)
        if status[0] == "ABORTED":
            print("Failed to upload blob.")
        else:
            assert (status[0] == "COMPLETE")
            print("Finished uploading {} with blob ID {}".format(
                status[1]["name"], status[1]["id"]
            ))
        print(res)


if __name__ == "__main__":
    main()
