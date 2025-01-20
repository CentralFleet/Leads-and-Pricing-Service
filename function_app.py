import azure.functions as func
from src.funcmain import *
import pandas as pd
from azure.storage.blob import BlobServiceClient, BlobClient

Lead = LeadHandler()
Quote = QuoteHandler()

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="v1/ping", methods=['GET', 'POST'])
async def ping(req: func.HttpRequest) -> func.HttpResponse:
    logger.info(f'Request received from {req.url}')
    logger.info('Ping request received.')
    return func.HttpResponse("Service is up", status_code=200)

@app.route(route="v1/leads", methods=["POST"])
async def lead_and_pricing(req: func.HttpRequest) -> func.HttpResponse:
    logger.info(f"Request received from {req.url}")
        
    body = req.get_json()
    logger.info(f"body : {body}")
    try:
        response = await Lead.add_carrier_and_quotes(body)

        logger.info(f"Func app :{response}")
        return func.HttpResponse(json.dumps(response), status_code=200)

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return func.HttpResponse("Internal server error", status_code=500)

@app.route(route="v1/store-quotes", methods=["POST"])
async def store_quote_in_sql(req: func.HttpRequest) -> func.HttpResponse:
    logger.info(f"Request received from {req.url}")
    body = req.get_json()
    logger.info(f"body : {body}")
    response = await Quote.store_sql_quote(body)
    return func.HttpResponse(json.dumps(body), status_code=200)


@app.route(route="v1/update-quotes", methods=["POST"])
async def update_quotes_in_sql(req: func.HttpRequest) -> func.HttpResponse:
    logger.info(f"Request received from {req.url}")
    body = req.get_json()
    logger.info(f"body : {body}")
    response = await Quote.update_sql_quote(body)
    return func.HttpResponse(json.dumps(body), status_code=200)


@app.route(route="v1/get-quote", methods=["GET"])
async def get_quote_from_sql(req: func.HttpRequest) -> func.HttpResponse:
    pickupcity = req.params.get("pickupcity")
    destinationcity = req.params.get("destinationcity")
    response = await Quote.get_quote(pickupcity,destinationcity)
    return func.HttpResponse(json.dumps(response), status_code=200)
