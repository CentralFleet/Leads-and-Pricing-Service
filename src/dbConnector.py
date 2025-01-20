
from sqlalchemy import create_engine, Column, String, DateTime, PrimaryKeyConstraint, Integer, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import func as sqlfunc
import logging


Base = declarative_base()

class DatabaseConnection:
    # Class variable to hold the engine
    engine = None

    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.session = None

        # Create the engine only once when the class is first initialized
        if DatabaseConnection.engine is None:
            DatabaseConnection.engine = create_engine(
                self.connection_string,
                pool_size=10,          # Max connections to keep in the pool
                max_overflow=5,       # Max additional connections beyond pool_size
                pool_timeout=30,      # Timeout for getting a connection
                pool_recycle=1800     # Recycle connections every 30 minutes
            )

    def __enter__(self):
        self.session = sessionmaker(bind=DatabaseConnection.engine)()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logging.error(f"Error occurred: {exc_val}")
            if self.session:
                self.session.rollback()
        if self.session:
            self.session.close()

class Vendor(Base):
    __tablename__ = 'Vendors'

    id = Column(Integer, primary_key=True, autoincrement=True)
    VendorName = Column(String(255), nullable=False)
    NumTransportJobs = Column(Integer, default=0)
    ZohoRecordID = Column(String(255), unique=True, nullable=False, primary_key=True)

from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func as sqlfunc
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class OrdersDB(Base):
    __tablename__ = 'TransportOrders'
    
    # Auto-increment OrderID
    OrderID = Column(Integer, primary_key=True, nullable=False, autoincrement=True)  # Auto-increment set here
    TransportRequestID = Column(String(255), nullable=False, unique=True)  # Ensure TransportRequestID is unique
    CustomerID = Column(String(255), nullable=True)
    CustomerName = Column(String(255), nullable=True)
    CreateTime = Column(DateTime, default=sqlfunc.now(), nullable=False)
    EstimatedPickupTime = Column(String(255), nullable=True)
    EstimatedDropoffTime = Column(String(255), nullable=True)
    JobPrice = Column(String(255), nullable=True)
    CarrierCost = Column(String(255), nullable=True)
    Status = Column(String(255), nullable=True)
    PickupLocation = Column(String(255), nullable=True)
    DropoffLocation = Column(String(255), nullable=True)
    ActualPickupTime = Column(DateTime, nullable=True)
    ActualDeliveryTime = Column(DateTime, nullable=True)
    CarrierName = Column(String(255), nullable=True)
    CarrierID = Column(String(255), nullable=True)




class TransportQuotation(Base):
    __tablename__ = 'TransportQuotation'

    # Define both columns as part of the composite primary key
    CarrierName = Column(String(255), nullable=False)
    DropoffLocation = Column(String(255), nullable=True)
    PickupLocation = Column(String(255), nullable=True)
    EstimatedPickupTime = Column(String(255), nullable=True)
    EstimatedDropoffTime = Column(String(255), nullable=True)
    Estimated_Amount = Column(String(255), nullable=False)
    CarrierID = Column(String(255), nullable=True)
    PickupCity = Column(String(255), nullable=True)
    DestinationCity = Column(String(255), nullable=True)
    CreateDate = Column(DateTime, default=sqlfunc.now(), nullable=False)
    TaxName = Column(String(50), nullable=True)
    TaxRate = Column(Float, nullable=True)
    TaxAmount = Column(Float, nullable=True)
    CustomerPrice_excl_tax = Column(Float, nullable=True)
    TotalAmount = Column(Float, nullable=True)
    QuoteStatus = Column(String(50), nullable=True)
    Rating = Column(Float, default=0, nullable=True)
    Currency = Column(String(50), nullable=True)
    Additional = Column(Float, nullable=False, default=0)
    Surcharge = Column(Float, nullable=False, default=0)
    DeactivatedDateTime = Column(DateTime, nullable=True)
        # Composite primary key
    __table_args__ = (
        PrimaryKeyConstraint(
            'PickupCity',
            'DestinationCity',
            'CarrierName',
            'QuoteStatus',
            'Estimated_Amount',
            'Additional',
            'Surcharge',
            name='quotation_request_pk'
        ),
    )




class TaxDataBase(Base):
    __tablename__ = 'Taxdb'

    tax_id = Column(String(255),nullable=False)
    province = Column(String(255), nullable=False,primary_key=True)
    tax_name = Column(String(255), nullable=False)
    tax_rate = Column(Float, nullable=False)
    tax_type = Column(String(255), nullable=False)
