import json

import click
import requests


class BadRequestException(Exception):
    def __init__(self, message, rv):
        super(BadRequestException, self).__init__(message)
        self.rv = rv


def api_get(domain, api_key, path):
    url = "http://{}/api/v2/{}".format(domain, path)
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
    url = "http://{}/api/v2/{}".format(domain, path)
    rv = requests.post(url, json=body, auth=(api_key, ""))
    if rv.status_code >= 400:
        raise BadRequestException(
            "Server returned status {}. Response:\n{}".format(
                rv.status_code, json.dumps(rv.json())
            ),
            rv,
        )
    return rv.json()


def get_existing_registered_chain_with_aa_sequence(
    domain, api_key, chain_schema_id, aa_sequence
):
    """Get the existing registered Chain with the given AA sequence, if one exists.
    
    If no registered Chain has the same AA sequence, return None.
    """
    response = api_get(
        domain,
        api_key,
        # https://docs.benchling.com/v2/reference#list-amino-acid-sequences
        "aa-sequences?schemaId={}&aminoAcids={}".format(chain_schema_id, aa_sequence),
    )
    matching_registered_chains = [
        chain_json
        for chain_json in response["aaSequences"]
        # Ignore unregistered Chain entities
        if chain_json["entityRegistryId"] is not None
    ]

    if len(matching_registered_chains) > 0:
        # The Chain schema has a unique constraint on the AA sequence, so there should never be
        # multiple registered Chain entities with the same AA sequence.
        assert (
            len(matching_registered_chains) == 1
        ), "Expected only one Chain with AA sequence {}".format(aa_sequence)
        [chain_json] = matching_registered_chains
        return chain_json
    else:
        return None


def find_or_create_chain_with_aa_sequence(
    domain, api_key, folder_id, registry_id, chain_schema_id, chain_name, aa_sequence
):
    """Find or create a Chain entity with the given amino acid sequence.
    
    :returns: an AA Sequence Resource (https://docs.benchling.com/reference#protein-resource)
    """
    # The Chain schema has a unique constraint on the AA sequence,
    # so if there's already a registered Chain with the same sequence,
    # we should use the existing Chain instead of creating a new one.
    existing_registered_chain_json = get_existing_registered_chain_with_aa_sequence(
        domain, api_key, chain_schema_id, aa_sequence
    )
    if existing_registered_chain_json is not None:
        return existing_registered_chain_json

    # No Chain was registered with the same AA sequence, so create a new one.
    chain_json = api_post(
        domain,
        api_key,
        # https://docs.benchling.com/v2/reference#create-protein
        "aa-sequences",
        {
            "aminoAcids": aa_sequence,
            "folderId": folder_id,
            "name": chain_name,
            "schemaId": chain_schema_id,
        },
    )
    return chain_json


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
@click.option("--chain-schema-id", help="ID of the Chain schema", required=True)
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

    for antibody_json in antibodies_json["antibodies"]:
        # Create Heavy Chain
        heavy_chain_json = find_or_create_chain_with_aa_sequence(
            domain,
            api_key,
            folder_id,
            registry_id,
            chain_schema_id,
            "Heavy Chain for {}".format(antibody_json["name"]),
            antibody_json["Heavy Chain"],
        )

        # Create Light Chain
        light_chain_json = find_or_create_chain_with_aa_sequence(
            domain,
            api_key,
            folder_id,
            registry_id,
            chain_schema_id,
            "Light Chain for {}".format(antibody_json["name"]),
            antibody_json["Light Chain"],
        )

        # Create antibody
        create_antibody_response_json = api_post(
            domain,
            api_key,
            # https://docs.benchling.com/v2/reference#create-custom-inventory
            "custom-entities",
            {
                "name": antibody_json["name"],
                "schemaId": antibody_schema_id,
                "folderId": folder_id,
                "fields": {
                    "Heavy Chain": {"value": heavy_chain_json["id"]},
                    "Light Chain": {"value": light_chain_json["id"]},
                },
            },
        )

        # Register
        try:
            entity_ids_to_register = [create_antibody_response_json["id"]]
            if heavy_chain_json["entityRegistryId"] is None:
                entity_ids_to_register.append(heavy_chain_json["id"])
            if light_chain_json["entityRegistryId"] is None:
                entity_ids_to_register.append(light_chain_json["id"])
            api_post(
                domain,
                api_key,
                # https://docs.benchling.com/v2/reference#register-files
                "registries/{}:register-entities".format(registry_id),
                {
                    "entityIds": entity_ids_to_register,
                    # Generate a new Registry ID but also keep the original name
                    "namingStrategy": "NEW_IDS",
                },
            )
        except BadRequestException as e:
            if e.rv.status_code == 400:
                print(
                    "Could not register {}. Error response from server:\n{}".format(
                        antibody_json["name"], json.dumps(e.rv.json())
                    )
                )
                continue
            else:
                raise e

        # Get the new name of the Antibody entity that we registered
        registered_antibody_response_json = api_get(
            domain,
            api_key,
            # https://docs.benchling.com/reference#get-custom-inventory
            "custom-entities/{}".format(create_antibody_response_json["id"]),
        )
        # As well as the Chain entities
        heavy_chain_json, light_chain_json = api_get(
            domain,
            api_key,
            # https://docs.benchling.com/reference#bulkget-protein
            "aa-sequences:bulk-get?aaSequenceIds={},{}".format(
                heavy_chain_json["id"], light_chain_json["id"]
            ),
        )["aaSequences"]

        print(
            "Registered new Antibody {} with Heavy Chain {} and Light Chain {}".format(
                registered_antibody_response_json["entityRegistryId"],
                heavy_chain_json["entityRegistryId"],
                light_chain_json["entityRegistryId"],
            )
        )


if __name__ == "__main__":
    main()

