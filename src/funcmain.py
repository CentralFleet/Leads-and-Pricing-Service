# src/funcmain.py
from utils.helpers import *
from utils.model import *

import azure.functions as func
import json
import os
import pandas as pd
from src.dbConnector import *
from src.recom import CarrierRecommendationModel

from sqlalchemy import and_, text, func as sqlfunc
from sqlalchemy.exc import IntegrityError
from pyzohocrm import ZohoApi, TokenManager

from dotenv import load_dotenv
load_dotenv()


logger = get_logger(__name__)


TEMP_DIR = "/tmp"

TOKEN_INSTANCE =  TokenManager(
                                domain_name="Canada",
                                refresh_token=os.getenv("REFRESH_TOKEN"),
                                client_id=os.getenv("CLIENT_ZOHO_ID"),
                                client_secret=os.getenv("CLIENT_ZOHO_SECRET"),
                                grant_type="refresh_token",
                                token_dir=TEMP_DIR
                                )

ZOHO_API = ZohoApi(base_url="https://www.zohoapis.ca/crm/v2")
CARRIER_DATA = pd.read_csv("CarriersT.csv")


class LeadHandler:

    def __init__(self):
        """
        Initialize the Lead handler class.
        """
        self.recom_model = CarrierRecommendationModel(logger)

    async def add_carrier_and_quotes(self, body) -> dict:
        """
        Create a Potential Carrier in the CRM.
        """
        try:
            token = TOKEN_INSTANCE.get_access_token()
            deal_id = body.get("deal_id", "")
            order_id = body.get("order_id", "")
            pickupcity = body.get("pickup_city", "")
            dropoffcity = body.get("dropoff_city", "")
            pickup_province = body.get("pickup_province", "")
            dropoff_province = body.get("dropoff_province", "")
            pickup_location = body.get("pickup_loc", "")
            dropoff_location = body.get("dropoff_loc", "")

            logger.info(f"Adding Potential Carriers for {deal_id}")

            # Handle database operations
            with DatabaseConnection(connection_string=os.getenv("SQL_CONN_STR")) as session:
                logger.info("Database connection established")
                leads= self.recom_model.recommend_carriers(
                        CARRIER_DATA, pickupcity, dropoffcity, pickup_province, dropoff_province
                    )
                carrier_response =  self._create_n_attach_carrier_in_crm(
                    session, token,leads, deal_id
                )
                quote_response = self._check_and_create_quotes_in_crm(
                    session, token, pickupcity, dropoffcity, pickup_location, dropoff_location, order_id, deal_id
                )

                return {
                    "status": "success",
                    "attach_response": {
                        "potential carrier": carrier_response,
                        "quotations": quote_response
                    }
                }

        except Exception as e:
            logger.error(f"Main function error: {e}")
            return {
                "status":"failed",
                "error": str(e),
                "code":500
            }


    def _create_n_attach_carrier_in_crm(self, session, token, leads, deal_id):
        """
        Process carrier recommendations and update the CRM.
        """
        try:
     
            if not leads.empty:
                logger.info(f"Processing recommendations: {leads['Carrier Name'].tolist()}")
                leads["Carrier Name"] = leads["Carrier Name"].apply(standardize_name)
                carrier_names = leads["Carrier Name"].tolist()

                carriers = session.query(Vendor).filter(Vendor.VendorName.in_(carrier_names)).all()
                carriers_with_ids = {c.VendorName: c.ZohoRecordID for c in carriers}

                data = []
                for index, row in leads.iterrows(): ## prepare batch request data
                    try:
                        carrier_name = row["Carrier Name"]
                        Lead_Name = f"{standardize_name(carrier_name)}"
                        lead_data = {
                            "VendorID": carriers_with_ids[carrier_name],
                            "Name": Lead_Name,
                            "Carrier_Score": row['Lead Score'], # assing score
                            "DealID": deal_id,
                            "Progress_Status": "To Be Contacted",
                        }
                        data.append(lead_data)
                        logger.info(f"data {lead_data}")
                    except Exception as e:
                        logger.error(f"Error Adding/Parsing lead: {e}")

                payload = {"data": data}

                lead_response = ZOHO_API.create_record(moduleName="Potential_Carrier",data=payload,token=token)
                if lead_response.status_code == 200:
                    return {
                        "status": "success",
                        "message": "Leads added successfully",
                    }
                else:
                    return {
                        "status": "failed",
                        "message": lead_response.json(),
                        "code": lead_response.status_code,
                    }

        except Exception as e:
            logger.warning(f"Error while generating recommendations: {e}")
            return {
                "status": "failed",
                "message": "No Potential Carrier Found",
                "code": 500
            }

    def _check_and_create_quotes_in_crm(self, session, token, pickup_city, destination_city, pickup_location, dropoff_location, order_id, deal_id):
        """
        Check for existing quotes and create them if applicable.
        """
        logger.info("Checking existing quote availability")
        matching_quotes = session.query(TransportQuotation).filter(
            and_(
                TransportQuotation.QuoteStatus == "Active",
                TransportQuotation.PickupCity.like(f"%{pickup_city}%"),
                TransportQuotation.DestinationCity.like(f"%{destination_city}%")
            )
        ).all()

        if matching_quotes:
            batch_quote = []

            for quote in matching_quotes:
                logger.info(f"Quote Details: {[quote.CarrierID, quote.Estimated_Amount, quote.EstimatedPickupTime, quote.EstimatedDropoffTime, quote.CreateDate]}")
                logger.info(f"pcikup city {pickup_city}, dropoff {destination_city}")
                data = {
                    "Name": f"{order_id}-{quote.CarrierName}",
                    "VendorID": quote.CarrierID,
                    "Pickup_Location": pickup_location,
                    "Dropoff_Location": dropoff_location,
                    "DealID": deal_id,
                    "Estimated_Amount": quote.Estimated_Amount,
                    "pickup_date_range": quote.EstimatedPickupTime,
                    "Delivery_Date_Range": quote.EstimatedDropoffTime,
                    "CreateDate": quote.CreateDate.strftime("%Y-%m-%d"),
                    "Approval_Status": "Not sent",
                    "Pickup_City": pickup_city,
                    "Drop_off_City": destination_city,
                    "Customer_Price_Excl_Tax": quote.CustomerPrice_excl_tax
                }
                batch_quote.append(data)

            payload = {"data":batch_quote}
            batch_quote_response = ZOHO_API.create_record(moduleName="Transport_Offers",data=payload,token=token)
            logger.info(f"{batch_quote_response.json()}")
            ZOHO_API.update_record(moduleName="Deals",id=deal_id,data={"data":[{
                "Stage": "Send Quote to Customer",
                "Order_Status": "Quote Ready"
            }]},token=token)
            return {
                "status": "success",
                "message": "Quotes created successfully",
                "code":200
            }
        
        else:
            logger.info("No matching quotes found.")
            return {
                "status": "failed",
                "message": "No matching quotes found.",
                "code":500
            }


class QuoteHandler:
    def __init__(self):
        """
        Initialize the QuoteHandler class.
        """
        self.db_connection_string = os.getenv("SQL_CONN_STR")
        self.slack_token = os.getenv("BOT_TOKEN")
        self.slack_channel = os.getenv("QUOTE_CHANNEL_ID")

    async def store_sql_quote(self, body: dict) -> func.HttpResponse:
        """
        Handle the storage of a new quote in the database.
        """
        try:
            token = TOKEN_INSTANCE.get_access_token()
            pickup_city = body.get("Pickup_City", "")
            destination_city = body.get("Dropoff_City", "")
            tax_Province = body.get("Tax_Province", "")
            
            tax = self._fetch_tax_details(tax_Province)
        
            with DatabaseConnection(connection_string=self.db_connection_string) as session:
                if self._quote_exists(session, body, pickup_city, destination_city):
                    return {"status": "failed", "message": "Quote already exists", "code": 500}
                try:
                    self._deactivate_existing_quotes(session, pickup_city, destination_city, body.get("CarrierName"))
                except Exception as e:
                    logger.info(f"Failed to deactivate")
                self._add_new_quote(session, body, pickup_city, destination_city, tax)
                ZOHO_API.update_record(moduleName="Transport_Offers",data={"data":[{
                       "Pickup_City":pickup_city,
                        "Drop_off_City":destination_city
                }] },id=body.get("QuotationRequestID","-"),token=token)

                slack_msg = f"""💼📜 New Quote Added in Database! \n *Details* \n - Carrier Name: `{ body.get("CarrierName")}` \n - Pickup City: `{pickup_city}` \n - Destination City: `{destination_city}` \n - Est. Amount: `{body.get("Estimated_Amount", "-")}` \n - Est. Pickup Time: `{body.get("EstimatedPickupTime", "-")}` \n - Est. Dropoff Time: `{body.get("EstimatedDropoffTime", "-")}`"""
                send_message_to_channel(os.getenv("BOT_TOKEN"),os.getenv("QUOTE_CHANNEL_ID"),slack_msg)
            
                return {"status":"success","message":"quote is successfully addded!","code":200}
        except Exception as e:
            logger.error(f"Quote Creation Error: {e}")
            send_message_to_channel(
                os.getenv("BOT_TOKEN"),
                os.getenv("QUOTE_CHANNEL_ID"),
                f" \n *Details* \n - Carrier Name: `{body.get('CarrierName')}` \n - Pickup City: `{pickup_city}` \n - Destination City: `{destination_city}` \n Error adding quote in sql: {e}"
            )            
            return  {"status":"failed","message":"error adding quote in sql","code":500}

    def _fetch_tax_details(self, tax_province):
        """Fetch tax details based on location."""
        with DatabaseConnection(connection_string=self.db_connection_string) as session:
            return session.query(TaxDataBase).filter(TaxDataBase.province == tax_province).first()

    def _quote_exists(self, session, body, pickup_city, destination_city):
        """Check if a similar quote already exists."""
        return session.query(TransportQuotation).filter(
            and_(
                TransportQuotation.PickupCity == pickup_city,
                TransportQuotation.DestinationCity == destination_city,
                TransportQuotation.CarrierName == body.get("CarrierName"),
                TransportQuotation.QuoteStatus == "ACTIVE",
                TransportQuotation.Estimated_Amount == body.get("Estimated_Amount"),
                TransportQuotation.Additional == body.get("Additional",'0'),
                TransportQuotation.Surcharge == body.get("Surcharge",'0'),
            )
        ).count() > 0

    def _deactivate_existing_quotes(self, session, pickup_city, destination_city, carrier_name):
        """Deactivate existing quotes for the same route and carrier."""
        session.query(TransportQuotation).filter(
            and_(
                TransportQuotation.PickupCity == pickup_city,
                TransportQuotation.DestinationCity == destination_city,
                TransportQuotation.CarrierName == carrier_name,
                TransportQuotation.QuoteStatus == "ACTIVE",
            )
        ).update({"QuoteStatus": "INACTIVE"})

    def _add_new_quote(self, session, body, pickup_city, destination_city, tax):
        """Add a new quote to the database."""
        new_quote = TransportQuotation(
            CarrierID=body.get("CarrierID", "-"),
            CarrierName=body.get("CarrierName", "-"),
            DropoffLocation=body.get("DropoffLocation", "-"),
            PickupLocation=body.get("PickupLocation", "-"),
            EstimatedPickupTime=body.get("EstimatedPickupTime", "-"),
            EstimatedDropoffTime=body.get("EstimatedDropoffTime", "-"),
            Estimated_Amount=body.get("Estimated_Amount", "-"),
            PickupCity=pickup_city,
            DestinationCity=destination_city,
            TaxRate=tax.tax_rate,
            TaxName=tax.tax_name,
            QuoteStatus="ACTIVE",
            Additional=body.get("Additional", "0"),
            Surcharge=body.get("Surcharge", "0"),
        )
        session.add(new_quote)
        session.commit()

    def _format_quote(self, quote):
        """Format quote details into a dictionary."""
        return {
            "CarrierName": quote.CarrierName,
            "Estimated_Amount": quote.Estimated_Amount,
            "EstimatedPickupTime": quote.EstimatedPickupTime,
            "EstimatedDropoffTime": quote.EstimatedDropoffTime,
            "PickupCity": quote.PickupCity,
            "DestinationCity": quote.DestinationCity,
            "TaxRate": quote.TaxRate,
            "TaxName": quote.TaxName,
            "TaxAmount": quote.TaxAmount,
            "TotalAmount": quote.TotalAmount,
            "Additional": quote.Additional,
            "Surcharge": quote.Surcharge
        }

    async def update_sql_quote(self, body: dict) -> dict:
        """
        Update an existing quote in the database.
        """
        try:
                # Extract data from the input
            primary_key_values = {
                "CarrierName": body.get("CarrierName"),
                "PickupCity": body.get("PickupCity"),
                "DestinationCity": body.get("DestinationCity"),
                "QuoteStatus": "ACTIVE",
            }
            customer_price = body.get("Customer_Price")

            with DatabaseConnection(connection_string=self.db_connection_string) as session:
                quote = session.query(TransportQuotation).filter_by(**primary_key_values).first()

                if not quote:
                    return {
                        "status":"failed",
                        "message":"invalid quote update",
                        "code":400
                    }

                try:
                    quote.CustomerPrice_excl_tax = float(customer_price)
                    quote.TaxAmount = quote.CustomerPrice_excl_tax * (quote.TaxRate/100)
                    quote.TotalAmount = quote.TaxAmount + quote.CustomerPrice_excl_tax
                except Exception as e:
                    logger.warning(f"Error converting Customer Price to float: {e}")

                if body.get("Approval_status") == "Accepted":
                    quote.Rating = quote.Rating + 1

                # Commit the changes
                session.commit()
                logger.info("Record updated successfully")

                return {
                    "status":"success",
                    "message":"quote update successfully",
                    "code":200
                }
        except Exception as e:
            logger.error(f"Update Error: {e}")
            return {
                "status":"failed",
                "error":str(e),
                "code":500
            }

    async def get_quote(self,pickup_city : str,destination_city : str) -> dict:
        """
        Retrieve an active quote based on input criteria.
        """
        try:
            with DatabaseConnection(connection_string=self.db_connection_string) as session:
                quote = session.query(TransportQuotation).filter(
                    and_(
                        TransportQuotation.PickupCity == pickup_city,
                        TransportQuotation.DestinationCity == destination_city,
                        TransportQuotation.QuoteStatus == "ACTIVE",
                    )
                ).order_by(TransportQuotation.Rating.asc()).first()

                if not quote:
                    return {
                        "status":"not found",
                        "message":"quote is not avaiable",
                        "code":404
                    }

                return {
                    "status":"success",
                    "message":"quote retrieved successfully",
                    "code":200,
                    "data":self._format_quote(quote)
                }
        except Exception as e:
            logger.error(f"Retrieval Error: {e}")
            return {
                "status":"failed",
                "error":str(e),
                "code":500
            }
