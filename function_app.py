import azure.functions as func
import logging

import iot_hub_utils
import models
from util import init_connection, validate_jwt
import json

app = func.FunctionApp()

container = init_connection()

@app.function_name(name="historical-data-function")
@app.route(route="v1/smart-house/historical-data", auth_level=func.AuthLevel.FUNCTION)
def main(req: func.HttpRequest) -> func.HttpResponse:
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


@app.function_name(name="historical-data-report-function")
@app.route(route="v1/smart-house/historical-data/report", auth_level=func.AuthLevel.FUNCTION)
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    print('\nQuerying for a report\n')

    # Validate JWT token
    token = req.headers.get('Authorization')
    if not token.startswith('Bearer '):
        raise Exception("Invalid token format. Expected token to start with 'Bearer'")
    token = token[len('Bearer '):]
    payload = validate_jwt(token)
    user_id = payload["sub"]

    # Retrieve the request body
    req_body = req.get_json()
    # Retrieve query parameters from request body
    device_name = req_body.get('deviceName')
    date_from = req_body.get('dateFrom')
    date_to = req_body.get('dateTo')
    labels = req_body.get('labels')

    # Get IoT hub info by user ID
    db = next(iot_hub_utils.get_db())
    try:
        iot_hub = iot_hub_utils.get_iothub_by_user_id(db, user_id)
    finally:
        db.close()
    iot_hub_name = iot_hub.name

    # Including the partition key value of account_number in the WHERE filter results in a more efficient query
    query = prepareSQLForReport(labels)
    items = list(container.query_items(
        query=query,
        parameters=[
            {'name': '@date_from', 'value': date_from},
            {'name': '@date_to', 'value': date_to},
            {'name': '@iot_hub_name', 'value': iot_hub_name},
            {'name': '@iot_device_name', 'value': device_name}
        ],
        enable_cross_partition_query=True  # Enable cross-partition query
    ))

    # with open('query.txt', 'w') as file:
    #     file.write(str(items))

    report = items[0]

    pdf = generate_pdf(report, date_from, date_to)

    # Return PDF as response
    response_headers = {
        "Content-Type": "application/pdf",
        "Content-Disposition": "attachment; filename=telemetry_report.pdf"
    }
    return func.HttpResponse(body=pdf, headers=response_headers, status_code=200)

def prepareSQLForReport(labels):
    where_clause = ("WHERE c.SystemProperties['iothub-connection-device-id'] = @iot_device_name "
                    "AND c['iothub-name'] = @iot_hub_name "
                    "AND c.SystemProperties['iothub-enqueuedtime'] >= @date_from "
                    "AND c.SystemProperties['iothub-enqueuedtime'] <= @date_to")

    # Constructing the SELECT clauses dynamically for each label
    udf_select_clauses = []
    aggregation_select_clauses = []
    for label in labels:
        udf_select_clauses.append(f"udf.decodeBase64AndExtractValue(c.Body, '{label}') AS {label},")
        aggregation_select_clauses.append(f"MAX(telemetry.{label}) AS Max{label.capitalize()},")
        aggregation_select_clauses.append(f"MIN(telemetry.{label}) AS Min{label.capitalize()},")
        aggregation_select_clauses.append(f"AVG(telemetry.{label}) AS Avg{label.capitalize()},")

    udf_select_clause = "\n".join(udf_select_clauses)
    aggregation_select_clause = "\n".join(aggregation_select_clauses)

    # Constructing the SQL query with parameters
    sql_query = f"""
            SELECT VALUE root FROM(
                SELECT
                    {aggregation_select_clause[:-1]}  -- Remove the trailing comma
                FROM (
                    SELECT
                        {udf_select_clause[:-1]}  -- Remove the trailing comma
                    FROM c
                    {where_clause}
                ) AS telemetry) as root
        """
    return sql_query

def generate_pdf(report_data, date_from, date_to):
    from fpdf import FPDF

    # Create PDF object
    pdf = FPDF()
    pdf.add_page()

    # Add title
    pdf.set_font("Arial", style='B', size=18)
    pdf.cell(200, 10, txt="Telemetry Report", ln=True, align='C')
    pdf.ln()

    pdf.set_font("Arial", size=14)

    pdf.cell(200, 10, txt="Date From: " + date_from)
    pdf.ln()
    pdf.cell(200, 10, txt="Date To: " + date_to)
    pdf.ln()
    pdf.ln()

    # Add report data
    for i in range(0, len(report_data), 3):
        # Extract telemetry name
        telemetry_fields = list(report_data.keys())[i:i + 3]
        telemetry_name = telemetry_fields[0][3:]  # Extract telemetry name

        # Add telemetry name and value to PDF
        pdf.set_font("Arial", style='B')
        pdf.cell(200, 10, txt=f"{telemetry_name}", ln=True)
        for field in telemetry_fields:
            value = report_data[field]
            field_name = field[0:3]  # Extract aggregation type
            pdf.set_font("Arial")
            pdf.cell(250, 10, txt=f"{field_name} value: {value}", ln=True)
        pdf.ln()


    # Return PDF binary data
    return pdf.output(dest='S').encode('latin1')
