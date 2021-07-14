import json
import os

import click
import requests
import time

from file_helpers import calculate_md5, encode_base64

CHUNK_SIZE_BYTES = int(10e6)

class BadRequestException(Exception):
    def __init__(self, message, rv):
        super(BadRequestException, self).__init__(message)
        self.rv = rv


def api_post(domain, api_key, path, body):
    url = "https://{}/api/v2/{}".format(domain, path)
    rv = requests.post(url, json=body, auth=(api_key, ""))
    if rv.status_code >= 400:
        raise BadRequestException(
            "Server returned status {}. Response:\n{}".format(
                rv.status_code, json.dumps(rv.json())
            ),
            rv,
        )
    return rv.json()


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
    file_size = os.path.getsize(filepath)
    with open(filepath, "rb") as file:
        if file_size <= CHUNK_SIZE_BYTES:
            upload_single_part_blob(api_key, domain, file, name)
        else:
            upload_multi_part_blob(api_key, domain, file, name)


def upload_single_part_blob(api_key, domain, file, name):
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
    assert(res["uploadStatus"] == "COMPLETE")
    print("Finished uploading {} with blob ID {}".format(
        res["name"], res["id"]
    ))


def upload_multi_part_blob(api_key, domain, file, name):
    chunk_producer = lambda chunk_size: file.read(chunk_size)
    start_blob = api_post(domain, api_key, "blobs:start-multipart-upload", {
        "mimeType": "application/octet-stream",
        "name": name,
        "type": "RAW_FILE",
    })
    part_number = 0
    blob_parts = []
    try:
        while True:
            cursor = chunk_producer(CHUNK_SIZE_BYTES)
            if not cursor:
                break
            part_number += 1
            encoded64 = encode_base64(cursor)
            md5 = calculate_md5(cursor)
            created_part = api_post(domain, api_key, "blobs/{}/parts".format(start_blob["id"]), {
                "data64": encoded64,
                "md5": md5,
                "partNumber": part_number,
            })
            blob_parts.append(created_part)
        api_post(domain, api_key, "blobs/{}:complete-upload".format(start_blob["id"]), {
            "parts": blob_parts
        })
        print("Completed uploading {} parts for blob {}".format(part_number, start_blob["id"]))
    except Exception as e:
        print("Error while uploading part {} for blob {}".format(part_number, start_blob["id"]))
        api_post(domain, api_key, "blobs/{}:abort-upload".format(start_blob["id"]), {})
        raise e

if __name__ == "__main__":
    main()
