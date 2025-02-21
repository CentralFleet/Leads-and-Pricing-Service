import pytest
from unittest.mock import patch, MagicMock
from src.funcmain import LeadHandler, QuoteHandler
import azure.functions as func
import os
os.environ["REFRESH_TOKEN"] = "fake_refresh_token"
os.environ["CLIENT_ZOHO_ID"] = "fake_client_id"
os.environ["CLIENT_ZOHO_SECRET"] = "fake_client_secret"
os.environ["BOT_TOKEN"] = "fake_bot_token"
os.environ["QUOTE_CHANNEL_ID"] = "fake_channel_id"
@pytest.fixture
def mock_request():
    def _mock_request(body):
        req = MagicMock(spec=func.HttpRequest)
        req.get_json.return_value = body
        return req
    return _mock_request
@pytest.fixture
def lead_handler():
    return LeadHandler()
@pytest.fixture
def quote_handler():
    return QuoteHandler()
# :white_tick: Fully mocked API and database calls
@pytest.mark.asyncio
@patch("src.funcmain.TOKEN_INSTANCE.get_access_token", return_value="fake_token")
@patch("src.funcmain.ZOHO_API.create_record", return_value=MagicMock(status_code=200, json=lambda: {"data": [{"details": {"id": "12345"}}]}))
@patch("src.funcmain.DatabaseConnection")  # Fully mock DB interactions
async def test_add_carrier_and_quotes(mock_db, mock_zoho, mock_token, lead_handler, mock_request):
    # :white_tick: Mock DB session
    mock_session = mock_db.return_value.__enter__.return_value
    mock_session.query.return_value.filter.return_value.all.return_value = []
    req = mock_request({
        "deal_id": "D123",
        "order_id": "O456",
        "pickup_city": "Toronto",
        "dropoff_city": "Vancouver",
        "pickup_province": "ON",
        "dropoff_province": "BC",
        "pickup_loc": "123 Main St",
        "dropoff_loc": "789 Elm St"
    })
    response = await lead_handler.add_carrier_and_quotes(req.get_json())
    assert response["status"] == "success"
@pytest.mark.asyncio
@patch("src.funcmain.ZOHO_API.update_record", return_value=MagicMock(status_code=200, json=lambda: {"status": "success"}))
@patch("src.funcmain.send_message_to_channel", return_value=None)
@patch("src.funcmain.DatabaseConnection")
@patch("src.funcmain.TOKEN_INSTANCE.get_access_token", return_value="fake_token")
async def test_store_sql_quote(mock_token, mock_db, mock_slack,mock_zoho_update, quote_handler, mock_request):
    mock_session = mock_db.return_value.__enter__.return_value
    mock_session.query.return_value.filter_by.return_value.first.return_value = None
    mock_session.query.return_value.filter.return_value.count.return_value = 0
    req = mock_request({
        "CarrierName": "TestCarrier",
        "Pickup_City": "Toronto",
        "Dropoff_City": "Vancouver",
        "Estimated_Amount": 500
    })
    response = await quote_handler.store_sql_quote(req.get_json())
    assert response["status"] == "success"
@pytest.mark.asyncio
@patch("src.funcmain.DatabaseConnection")
async def test_get_quote(mock_db, quote_handler):
    mock_session = mock_db.return_value.__enter__.return_value
    mock_quote = MagicMock()
    mock_quote.PickupCity = "Toronto"
    mock_quote.DestinationCity = "Vancouver"
    mock_quote.QuoteStatus = "ACTIVE"
    mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_quote
    response = await quote_handler.get_quote("Toronto", "Vancouver")
    assert response["status"] == "success"