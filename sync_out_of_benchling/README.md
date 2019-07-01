This script demonstrates how to export all registered entities that were modified after a certain timestamp, so that the changes can be imported into some external system.

In this example, we are exporting entities as a CSV printed to standard output. For example, if the script is asked to export all Antibody entities exported after June 26, 2019, it could print a CSV like this:

```
Registry ID,Name,Last Modified At,Heavy Chain,Light Chain
TA003,AB-BRCA2-003,2019-06-27T20:58:21.225189+00:00,Heavy Chain for AB-BRCA2-002,Light Chain for AB-BRCA2-003
TA002,AB-BRCA2-002,2019-06-27T20:58:21.225189+00:00,Heavy Chain for AB-BRCA2-002,Light Chain for AB-BRCA2-002
TA001,AB-BRCA2-001,2019-06-27T20:58:21.225189+00:00,Heavy Chain for AB-BRCA2-001,Light Chain for AB-BRCA2-001
```

# Prerequisites

This script requires the Registry application. In addition, an **entity schema** must be [configured](https://help.benchling.com/articles/2725066-configure-your-registry), and at least one entity must have been [created and registered](https://help.benchling.com/en/articles/2725346-create-and-register-a-single-entity).

# How to run the script

- First, ask Benchling support to enable API access on your account, and create API credentials. Instructions: https://help.benchling.com/articles/2353570-access-the-benchling-api-enterprise
- Install Python 3 and [Pipenv](https://docs.pipenv.org/en/latest/)
- Install dependencies using `pipenv install`
- Run `pipenv shell` to work in a virtualenv that includes the dependencies.
- Run the script. For example:

```
python sync_into_benchling.py \
  --domain example.benchling.com \
  --api-key $YOUR_API_KEY
  --registry-id src_Lmysq16b \
  --antibody-schema-id ts_LpAfe6xV \
  --last-sync-timestamp 2019-06-27T20:58:17.464834+00:00
```

- The script should print a CSV like this:

```
Registry ID,Name,Last Modified At,Heavy Chain,Light Chain
TA003,AB-BRCA2-003,2019-06-27T20:58:21.225189+00:00,Heavy Chain for AB-BRCA2-002,Light Chain for AB-BRCA2-003
TA002,AB-BRCA2-002,2019-06-27T20:58:21.225189+00:00,Heavy Chain for AB-BRCA2-002,Light Chain for AB-BRCA2-002
TA001,AB-BRCA2-001,2019-06-27T20:58:21.225189+00:00,Heavy Chain for AB-BRCA2-001,Light Chain for AB-BRCA2-001
```
