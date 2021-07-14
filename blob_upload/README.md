# **Upload Blobs To Benchling**

Example code for uploading blobs to Benchling, part of the [Uploading Instrument Results](https://docs.benchling.com/docs/example-creating-results) guide available on Benchling Developer Platform Documentation Page.   

# How to run the script

- First, ask Benchling support to enable API access on your account, and create API credentials. Instructions: https://help.benchling.com/articles/2353570-access-the-benchling-api-enterprise
- Install Python 3 and [Pipenv](https://docs.pipenv.org/en/latest/)
- Install dependencies using `pipenv install`
- Run `pipenv shell` to work in a virtualenv that includes the dependencies.
- Run the script. For example:

```
python blob_upload.py \
  --domain example.benchling.com \
  --api-key $YOUR_API_KEY \
  --filepath path/to/chromatogram_file
```