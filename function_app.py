import azure.functions as func
from src.funcmain import *


Lead = LeadHandler()
Quote = QuoteHandler()

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="ping", methods=['GET','POST'])
async def ping(req: func.HttpRequest) -> func.HttpResponse:
    logger.info(f'Request received from {req.url}')
    logger.info('Ping request received.')
    return func.HttpResponse("Service is up", status_code=200)


@app.route(route="lead-and-pricing", methods=["POST"])
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


@app.route(route="store-quotes", methods=["POST"])
async def store_quote_in_sql(req: func.HttpRequest) -> func.HttpResponse:

    logger.info(f"Request received from {req.url}")
    body = req.get_json()
    logger.info(f"body : {body}")
    response = await Quote.store_sql_quote(body)
    return func.HttpResponse(json.dumps(body), status_code=200)


@app.route(route="update-quotes", methods=["POST"])
async def update_quotes_in_sql(req: func.HttpRequest) -> func.HttpResponse:

    logger.info(f"Request received from {req.url}")
    body = req.get_json()
    logger.info(f"body : {body}")
    response = await Quote.update_sql_quote(body)
    return func.HttpResponse(json.dumps(body), status_code=200)


@app.route(route="get-quote", methods=["POST"])
async def get_quote_from_sql(req: func.HttpRequest) -> func.HttpResponse:

    body = req.get_json()
    logger.info(f"body : {body}")

    response = await Quote.get_quote(body)

    return func.HttpResponse(json.dumps(response), status_code=200)