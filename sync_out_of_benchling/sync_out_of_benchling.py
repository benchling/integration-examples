import csv
import json
import sys

import click
import requests


def api_get(domain, api_key, path, params={}):
    url = "https://{}/api/v2/{}".format(domain, path)
    rv = requests.get(url, auth=(api_key, ""), params=params)
    if rv.status_code >= 400:
        raise Exception(
            "Server returned status {}. Response:\n{}".format(
                rv.status_code, json.dumps(rv.json())
            )
        )
    return rv.json()


@click.command()
@click.option(
    "--domain",
    help="Domain name of your Benchling instance, e.g. example.benchling.com",
    required=True,
)
@click.option("--api-key", help="Your API key", required=True)
@click.option(
    "--registry-id",
    help=(
        "ID of the Benchling Registry. "
        "To get the ID of your registry, you can get a list of all registries "
        "from the List Registries endpoint (https://docs.benchling.com/reference#get-registries) "
        'and copy the "id" field of your registry.'
    ),
    required=True,
)
@click.option("--antibody-schema-id", help="ID of the Antibody schema", required=True)
@click.option(
    "--last-sync-timestamp",
    help=(
        "Timestamp of the previous sync, in RFC 3339 format (e.g. 2019-06-27T20:58:21.225189+00:00). "
        "If not given, this script will export all Antibody entities."
    ),
)
def main(domain, api_key, registry_id, antibody_schema_id, last_sync_timestamp):
    """Export registered Antibody entities that were modified after the given timestamp.
    
    The entities are exported as a CSV and printed to standard output. 

    Example output:

    Registry ID,Name,Last Modified At,Heavy Chain,Light Chain
TA003,AB-BRCA2-003,2019-06-27T20:58:21.225189+00:00,Heavy Chain for AB-BRCA2-002,Light Chain for AB-BRCA2-003
    """
    # Get ordered field names so we can keep the CSV columns in a consistent order
    all_schemas_json = api_get(
        domain,
        api_key,
        # https://docs.benchling.com/v2/reference#list-entity-schemas
        "registries/{registry_id}/entity-schemas".format(registry_id=registry_id),
    )["entitySchemas"]
    [antibody_schema_json] = [
        schema_json
        for schema_json in all_schemas_json
        if schema_json["id"] == antibody_schema_id
    ]
    antibody_field_names = [
        field_definition_json["name"]
        for field_definition_json in antibody_schema_json["fieldDefinitions"]
    ]

    # Get all modified Antibody entities. There may be multiple pages,
    # so we need to keep calling the API until all entities have been returned.
    newly_modified_antibodies_json = []
    next_token = None
    while True:
        response_json = api_get(
            domain,
            api_key,
            # https://docs.benchling.com/v2/reference#list-custom-entities
            "custom-entities",
            params={
                "registryId": registry_id,
                "schemaId": antibody_schema_id,
                "modifiedAt": (
                    "> {timestamp}".format(timestamp=last_sync_timestamp)
                    if last_sync_timestamp
                    else None
                ),
                "nextToken": next_token,
            },
        )
        newly_modified_antibodies_json += response_json["customEntities"]
        next_token = response_json["nextToken"]
        if not next_token:
            break

    # Write the CSV
    writer = csv.DictWriter(
        sys.stdout,
        fieldnames=["Registry ID", "Name", "Last Modified At"] + antibody_field_names,
    )
    writer.writeheader()
    for antibody_json in newly_modified_antibodies_json:
        csv_row_json = {
            "Registry ID": antibody_json["entityRegistryId"],
            "Name": antibody_json["name"],
            "Last Modified At": antibody_json["modifiedAt"],
        }
        csv_row_json.update(
            {
                field_name: antibody_json["fields"][field_name]["textValue"]
                for field_name in antibody_field_names
            }
        )
        writer.writerow(csv_row_json)


if __name__ == "__main__":
    main()
