# Quote and Leads Service

Handle the management of carriers and quotes in a logistics system. It interacts with the Zoho CRM API to manage records and updates and performs database operations for storing and updating quotes.

## Endpoints

### `v1/ping`
**Method:** `GET`, `POST`  
**Description:**  
Ping the service to check if it's up and running.

**Response:**
- `200 OK` - Service is up.

---

### `v1/leads`
**Method:** `POST`  
**Description:**  
Create a potential carrier and associated quotes for a deal based on provided order and location details. The function performs the following actions:
1. Recommends carriers for a deal based on the pickup and drop-off locations.
2. Creates leads for the recommended carriers in Zoho CRM.
3. Checks for existing quotes and creates new ones if applicable.

**Request Body:**
```json
{
    "deal_id": "<deal_id>",
    "OrderID": "<order_id>",
    "pickuploc": "<pickup_location>",
    "dropoffloc": "<dropoff_location>"
    
}
```
### `v1/store-quotes`
**Method:** `POST`
**Description:**
Store a new transport quote in the SQL database. It checks if a similar quote already exists and deactivates existing quotes for the same route and carrier before storing the new quote.

**Request Body:**
```json
{
    "CarrierID": "<carrier_id>",
    "CarrierName": "<carrier_name>",
    "PickupLocation": "<pickup_location>",
    "DropoffLocation": "<dropoff_location>",
    "Estimated_Amount": "<estimated_amount>",
    "EstimatedPickupTime": "<estimated_pickup_time>",
    "EstimatedDropoffTime": "<estimated_dropoff_time>",
    "Additional": "<additional>",
    "Surcharge": "<surcharge>"
}
```

### `v1/update-quotes`
**Method:** `POST`
**Description:**
Update an existing quote in the SQL database. It updates the customer price and tax details and handles the rating based on approval status.

**Request Body**
```json
{
    "CarrierName": "<carrier_name>",
    "PickupCity": "<pickup_city>",
    "DestinationCity": "<destination_city>",
    "Customer_Price": "<customer_price>",
    "Approval_status": "<approval_status>"
}

```
### `v1/get-quote`
**Method:** `GET`
**Description:**
Retrieve an active quote based on the pickup and destination cities.

**Request Parameters:**

 - pickupcity - The city where the pickup will occur.
 - destinationcity - The city where the dropoff will occur.

**Response:**

```json
{
    "status": "success",
    "message": "quote retrieved successfully",
    "code": 200,
    "data": {
        "CarrierName": "NETWORK LOGISTICS AND TRANSPORTATION GROUP INC",
        "Estimated_Amount": "200",
        "EstimatedPickupTime": "2 - 4 Business Days",
        "EstimatedDropoffTime": "2 - 4 Business Days",
        "PickupCity": "Oakville",
        "DestinationCity": "Ottawa",
        "TaxRate": 13.0,
        "TaxName": "ON HST",
        "TaxAmount": 39.0,
        "TotalAmount": 339.0,
        "Additional": 0.0,
        "Surcharge": 0.0
    }
}
```
## 🛠️ Contributing Guide  

Thank you for considering contributing to this project! Follow these steps to get started:  

### 🚀 Steps to Contribute  

1. **Fork the Repository**  
   Click the **Fork** button at the top right of this repository to create your own copy.  

2. **Clone Your Fork**  
   ```sh
   git clone https://github.com/CentralFleet/Leads-and-Pricing-Service.git
   cd Leads-and-Pricing-Service
   ```
3. **Create a New Branch**
   ```sh
   git checkout -b your-branch-name
   ```
4. **Make Your Changes**
    Make your changes and commit them to your local branch

5. **Push Your Changes**
    ```sh
    git push origin your-branch-name
    ```

6. **Create a Pull Request**
    Navigate to your forked repository on GitHub and create a new pull request.

