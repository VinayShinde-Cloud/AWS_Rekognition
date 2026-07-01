from xml.etree.ElementTree import Element, SubElement, tostring
import logging
import os
import requests
import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ── SSM endpoint cached at module level ───────────────────────────────────────
# Fetched once per Lambda container lifetime to avoid an SSM API call on every
# invocation, which reduces latency and avoids SSM throttling under load.
_thirdparty_endpoint_cache = None


def get_thirdparty_endpoint():
    '''
    Get thirdparty endpoint from SSM Parameter Store.
    Result is cached at module level — subsequent calls return the cached value.
    Region is read from the AWS_REGION env var injected by the Lambda runtime.
    '''
    global _thirdparty_endpoint_cache
    if _thirdparty_endpoint_cache is not None:
        return _thirdparty_endpoint_cache

    ssm_client = boto3.client('ssm', region_name=os.environ.get('AWS_REGION'))
    response = ssm_client.get_parameter(
        Name='thirdparty_endpoint', WithDecryption=False)
    _thirdparty_endpoint_cache = response['Parameter']['Value']
    logger.info("Loaded thirdparty_endpoint from SSM: %s", _thirdparty_endpoint_cache)
    return _thirdparty_endpoint_cache


# TODO: Implement json_to_xml function
# KIRO PROMPT: "Create a Python function called json_to_xml that converts a JSON event to an XML string using xml.etree.ElementTree"
# Expected: Function takes event parameter, creates XML structure with 'data' root element, returns XML string

def json_to_xml(event):
    """
    Converts a JSON event to an XML string.

    Args:
        event (dict): JSON event data

    Returns:
        str: XML string representation
    """
    root = Element('data')
    for key, value in (event.items() if isinstance(event, dict) else {}.items()):
        child = SubElement(root, str(key))
        child.text = str(value)
    return tostring(root, encoding='unicode')


# TODO: Implement post_xml function
# KIRO PROMPT: "Create a Python function called post_xml that sends an XML string via HTTP POST to a third-party endpoint"
# Expected: Function takes xml_string parameter, gets endpoint from get_thirdparty_endpoint(), posts with requests.post()

def post_xml(xml_string):
    """
    Sends XML string to third-party endpoint via HTTP POST.

    Args:
        xml_string (str): XML string to send

    Returns:
        requests.Response: HTTP response object

    Raises:
        requests.exceptions.RequestException: If the POST fails
    """
    endpoint = get_thirdparty_endpoint()
    response = requests.post(
        endpoint,
        data=xml_string,
        headers={'Content-Type': 'application/xml'},
        timeout=10,
    )
    response.raise_for_status()
    return response


def handler(event, context):
    logger.info("Received event: %s", event)

    try:
        # TODO: Call json_to_xml function
        # KIRO PROMPT: "Call json_to_xml with the event parameter and store result in variable called xml"
        xml = json_to_xml(event)

        # TODO: Call post_xml function
        # KIRO PROMPT: "Call post_xml with the xml variable"
        response = post_xml(xml)
        logger.info("Posted XML to endpoint, status: %s", response.status_code)

    except requests.exceptions.RequestException as e:
        logger.error("Failed to POST XML to third-party endpoint: %s", e)
        raise

    except Exception as e:
        logger.error("Unexpected error in send_email handler: %s", e)
        raise

    return {
        'statusCode': 200,
        "message": "Success!"
    }
