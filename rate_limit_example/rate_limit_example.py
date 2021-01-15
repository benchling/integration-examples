import requests
import os
import json
import time
import click

class BadRequestException(Exception):
    def __init__(self, message, rv):
        super(BadRequestException, self).__init__(message)
        self.rv = rv

class RateLimitExceededException(Exception):
    def __init__(self, message, rv):
        super(RateLimitExceededException, self).__init__(message)
        self.rv = rv

def api_get(domain, api_key, path):
    url = "https://{}/api/v2/{}".format(domain, path)
    rv = requests.get(url, auth=(api_key, ""))
    if rv.status_code >= 400:
        if rv.status_code == 429:
            raise RateLimitExceededException(
                "Server returned status {}. Response:\n{}".format(
                    rv.status_code, json.dumps(rv.json())
                ),
                rv,
            )
        else:
            raise BadRequestException(
                "Server returned status {}. Response:\n{}".format(
                    rv.status_code, json.dumps(rv.json())
                ),
                rv,
            )
    return rv.json()

def api_get_safe(domain, api_key, path):
    b = 1
    k = 5
    while True:
        try:
            rjson = api_get(domain, api_key, path)
            return rjson
        except RateLimitExceededException as rle:
            print(rle.message)
            delay(b, k)
            b <<= 1

def get_dna_sequence(domain, api_key):
    """
    Make a GET API call using the provided domain and api_key
    """
    response = api_get_safe(
            domain,
            api_key,
            "dna-sequences?pageSize=1"
    )
    return response

def delay(b, k):
    """
    time.sleep() for b * k seconds.
    """
    print("Sleeping %d seconds" % (b * k))
    time.sleep(b * k)

@click.command()
@click.option(
    "--domain",
    help="Domain name of your Benchling instance, e.g. example.benchling.com",
    required=True,
)
@click.option("--api-key", help="Your API key", required=True)
def main(
    domain,
    api_key,
):
    i = 0
    while True:
        response = get_dna_sequence(domain, api_key)
        i += 1
        print("%s: %d" % (time.strftime('%c'), i))

if __name__ == "__main__":
    main()
