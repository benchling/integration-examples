import json

import click
import requests
import time


class BadRequestException(Exception):
    def __init__(self, message, rv):
        super(BadRequestException, self).__init__(message)
        self.rv = rv


def api_get(domain, api_key, path):
    url = "https://{}/api/v2/{}".format(domain, path)
    rv = requests.get(url, auth=(api_key, ""))
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
    rv = requests.post(url, json=body, auth=(api_key, ""))
    if rv.status_code >= 400:
        raise BadRequestException(
            "Server returned status {}. Response:\n{}".format(
                rv.status_code, json.dumps(rv.json())
            ),
            rv,
        )
    return rv.json()


def wait_on_task_response(domain, api_key, task_resource):
    task_id = task_resource["taskId"]
    while True:
        task_response = api_get(domain, api_key, "tasks/{}".format(task_id))
        status = task_response["status"]
        if status == "RUNNING":
            time.sleep(10)
        else:
            if status == "FAILED":
                return "FAILED", task_response["message"], task_response["errors"]
            elif status == "SUCCEEDED":
                return "SUCCEEDED", task_response["response"]


@click.command()
@click.option(
    "--domain",
    help="Domain name of your Benchling instance, e.g. example.benchling.com",
    required=True,
)
@click.option("--api-key", help="Your API key", required=True)
@click.option(
    "--folder-id", help="ID of a folder to create the antibody in", required=True
)
@click.option("--registry-id", help="ID of the Benchling Registry", required=True)
@click.option("--antibody-schema-id", help="ID of the Antibody schema", required=True)
@click.option(
    "--chain-schema-id",
    help="ID of the Chain schema (Must be an AA-Sequence)",
    required=True,
)
@click.argument("json_file_to_import", type=click.File("r"))
def main(
    domain,
    api_key,
    antibody_schema_id,
    registry_id,
    chain_schema_id,
    folder_id,
    json_file_to_import,
):
    antibodies_json = json.loads(json_file_to_import.read())
    antibody_jsons = antibodies_json["antibodies"]

    # Bulk create heavy chains into registry
    task_resource = api_post(
        domain,
        api_key,
        # https://docs.benchling.com/reference#create-custom-entity
        "aa-sequences:bulk-create",
        {
            "aaSequences": [
                {
                    "aminoAcids": antibody_json["Heavy Chain"],
                    "folderId": folder_id,
                    "name": "Heavy Chain for {}".format(antibody_json["name"]),
                    "schemaId": chain_schema_id,
                    "registryId": registry_id,
                    "namingStrategy": "NEW_IDS",
                }
                for antibody_json in antibody_jsons
            ]
        },
    )
    task_response = wait_on_task_response(domain, api_key, task_resource)
    if task_response[0] == "FAILED":
        print(
            "Could not register at least one heavy chain. Error response from server:\n{}\n{}".format(
                task_response[1],
                task_response[2],
            )
        )
        return

    bulk_registered_heavy_chain_response_json = task_response[1]["aaSequences"]
    print("Successfully registered heavy chains")

    # Bulk create light chains into registry
    task_resource = api_post(
        domain,
        api_key,
        # https://docs.benchling.com/reference#create-custom-entity
        "aa-sequences:bulk-create",
        {
            "aaSequences": [
                {
                    "aminoAcids": antibody_json["Light Chain"],
                    "folderId": folder_id,
                    "name": "Light Chain for {}".format(antibody_json["name"]),
                    "schemaId": chain_schema_id,
                    "registryId": registry_id,
                    "namingStrategy": "NEW_IDS",
                }
                for antibody_json in antibody_jsons
            ]
        },
    )

    task_response = wait_on_task_response(domain, api_key, task_resource)
    if task_response[0] == "FAILED":
        print(
            "Could not register at least one light chain. Error response from server:\n{}\n{}".format(
                task_response[1],
                task_response[2],
            )
        )
        return

    bulk_registered_light_chain_response_json = task_response[1]["aaSequences"]
    print("Successfully registered light chains")

    # Bulk create antibodies in registry
    task_resource = api_post(
        domain,
        api_key,
        # https://docs.benchling.com/reference#create-custom-entity
        "custom-entities:bulk-create",
        {
            "customEntities": [
                {
                    "name": antibody_json["name"],
                    "schemaId": antibody_schema_id,
                    "folderId": folder_id,
                    "registryId": registry_id,
                    "namingStrategy": "NEW_IDS",
                    "fields": {
                        "Heavy Chain": {"value": heavy_chain_json["entityRegistryId"]},
                        "Light Chain": {"value": light_chain_json["entityRegistryId"]},
                    },
                }
                for antibody_json, heavy_chain_json, light_chain_json in zip(
                    antibody_jsons,
                    bulk_registered_heavy_chain_response_json,
                    bulk_registered_light_chain_response_json,
                )
            ]
        },
    )
    task_response = wait_on_task_response(domain, api_key, task_resource)
    if task_response[0] == "FAILED":
        print(
            "Could not register at least one antibody. Error response from server:\n{}\n{}".format(
                task_response[1],
                task_response[2],
            )
        )
        return
    bulk_registred_antibody_response_json = task_response[1]["customEntities"]

    for antibody_json, heavy_chain_json, light_chain_json in zip(
        bulk_registred_antibody_response_json,
        bulk_registered_heavy_chain_response_json,
        bulk_registered_light_chain_response_json,
    ):

        print(
            "Registered new Antibody {} with Heavy Chain {} and Light Chain {}".format(
                antibody_json["entityRegistryId"],
                heavy_chain_json["entityRegistryId"],
                light_chain_json["entityRegistryId"],
            )
        )


if __name__ == "__main__":
    main()
