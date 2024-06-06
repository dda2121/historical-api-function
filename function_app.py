import azure.functions as func
import logging

import iot_hub_utils
import models
from util import init_connection, validate_jwt
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

container = init_connection()

@app.route(route="v1/smart-house/historical-data/")
def historicalAPI(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # Retrieve the request body
    req_body = req.get_json()

    # Validate JWT token
    token = req.headers.get('Authorization')
    if not token.startswith('Bearer '):
        raise Exception("Invalid token format. Expected token to start with 'Bearer'")
    token = token[len('Bearer '):]
    payload = validate_jwt(token)
    user_id = payload["sub"]

    # Get IoT hub info by user ID
    db = next(iot_hub_utils.get_db())
    try:
        iot_hub = iot_hub_utils.get_iothub_by_user_id(db, user_id)
    finally:
        db.close()
    iot_hub_name = iot_hub.name
    # iot_hub_name = "smart-house-iot-hub"

    # Retrieve query parameters from request body
    device_name = req_body.get('deviceName')
    date_from = req_body.get('dateFrom')
    date_to = req_body.get('dateTo')

    # Query items from Cosmos DB
    items = container.query_items(
        query="SELECT * FROM c WHERE c.SystemProperties['iothub-enqueuedtime'] >= @date_from "
              "AND c.SystemProperties['iothub-enqueuedtime'] <= @date_to "
              "AND c['iothub-name'] = @iot_hub_name "
              "AND c.SystemProperties['iothub-connection-device-id'] = @iot_device_name",
        parameters=[
            {'name': '@date_from', 'value': date_from},
            {'name': '@date_to', 'value': date_to},
            {'name': '@iot_hub_name', 'value': iot_hub_name},
            {'name': '@iot_device_name', 'value': device_name}
        ],
        enable_cross_partition_query=True
    )

    response = []
    for item in items:
        body = item.get('Body', None)
        enqueued_time = item.get('SystemProperties', {}).get('iothub-enqueuedtime', None)
        if body is not None and enqueued_time is not None:
            query_response = models.QueryResponse(body=body, enqueuedTime=enqueued_time)
            response.append(query_response)

    json_response = json.dumps([r.dict() for r in response])
    return func.HttpResponse(json_response, mimetype='application/json')