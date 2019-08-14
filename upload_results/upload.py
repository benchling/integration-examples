# This script parses a .csv file of results, and creates corresponding
# result objects in Benchling.
import csv
import json
import sys

import click
import requests


def api_get(domain, api_key, path):
    url = "https://{}/api/v2/{}".format(domain, path)
    rv = requests.get(url, auth=(api_key, ""))
    if rv.status_code >= 400:
        raise Exception(
            "Server returned status {}. Response:\n{}".format(
                rv.status_code, json.dumps(rv.json())
            )
        )
    return rv.json()


def api_post(domain, api_key, path, body):
    url = "https://{}/api/v2/{}".format(domain, path)
    rv = requests.post(url, json=body, auth=(api_key, ""))
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
@click.option("--run-schema-id", help="ID of run schema", required=True)
@click.option("--result-schema-id", help="ID of result schema", required=True)
def main(domain, api_key, run_schema_id, result_schema_id):
    csv_results = []
    # "plate_reader_data.csv" is the name of our example .csv file
    # This can be changed to match the name of the .csv file you are using
    with open("plate_reader_data.csv") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            csv_results.append(dict(row))

    for csv_result in csv_results:
        assert set(csv_result.keys()) == set(
            # The following are the headings of the columns in our example .csv file
            # This can be changed to match the headings in the .csv file you are using
            [
                "Sample",
                "Well",
                "Signal",
                "Mean",
                "CV",
                "Calc. Concentration",
                "Calc. Conc. Mean",
                "Calc. Conc. CV",
            ]
        )

    response = api_post(
        domain,
        api_key,
        "assay-runs",
        {"assayRuns": [{"schemaId": run_schema_id, "fields": {}}]},
    )
    [run_id] = response["assayRuns"]

    response = api_post(
        domain,
        api_key,
        "assay-results",
        {
            "assayResults": [
                {
                    "schemaId": result_schema_id,
                    # This maps columns in the results .csv file to fields in a Benchling result object
                    # The following is made for the .csv file and results schema used in our example
                    # These can be changed to match the fields of the results schema you are using
                    # The keys on the left must match the field name in Benchling
                    # The keys on the right (being passed into csv_result) must match the column headings
                    # in your .csv file
                    "fields": {
                        "run": run_id,
                        "sample": csv_result["Sample"],
                        "well": csv_result["Well"],
                        "signal": float(csv_result["Signal"]),
                        "mean": float(csv_result["Mean"]),
                        "cv": float(csv_result["CV"]),
                        "calc_concentration": float(csv_result["Calc. Concentration"]),
                        "calc_conc_mean": float(csv_result["Calc. Conc. Mean"]),
                        "calc_conc_cv": float(csv_result["Calc. Conc. CV"]),
                    },
                }
                for csv_result in csv_results
            ]
        },
    )
    print(response)


if __name__ == "__main__":
    main()
