import logging
import os
import ast
import sys
import json
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/myTesla.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_HOST = os.environ['TESLA_API_BASE_URL']
require_token_refesh = False

headers = {
    'Authorization': f"Bearer {os.environ['TESLA_AUTH_TOKEN']}",
    'Content-Type': 'application/json;charset=utf-8'
}

def get_tesla_api_settings(env_path="auth_settings.json"):
    if not os.path.exists(env_path):
        logger.error(f"Settings file {env_path} does not exist.")
        sys.exit(1)

    with open(env_path, "r") as f:
        return json.load(f)

def update_env_variable(key, value, env_path=".env"):
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"{key}={value}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)

async def get_new_token_and_update_env():
    global require_token_refesh

    # Load credentials from .env
    settings = get_tesla_api_settings()

    client_id_setting = settings.get("env:TESLA_CLIENT_ID")
    client_secret_setting = settings.get("env:TESLA_CLIENT_SECRET")
    
    client_id = os.environ(client_id_setting)
    client_secret = os.environ(client_secret_setting)

    grant_type = settings.get("grant_type_cc")
    scope = settings.get("scope")
    audience = settings.get("audience")
    token_url = settings.get("token_url")

    if not all([client_id, client_secret, grant_type, scope, audience, token_url]):
        logger.error("Missing credentials in .env")
        print("Missing credentials in .env")
        return

    payload = {
        "grant_type": grant_type,
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope,
        "audience": audience
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, data=payload, headers=headers) as res:
            if res.status != 200:
                logger.error(f"Failed to get token: {res.status}")
                logger.error(await res.text())
                return
            data = await res.json()
            token = data.get("access_token")
            if token:
                update_env_variable("TESLA_AUTH_TOKEN", token)
                print("TESLA_AUTH_TOKEN updated in .env")
                logger.info("TESLA_AUTH_TOKEN updated in .env")
                require_token_refesh = False
            else:
                logger.error("Token not found in response")
                print("Token not found in response")

async def get_charging_history(reload=False):
    global require_token_refesh
    if 'TESLA_AUTH_TOKEN' not in os.environ:
        logger.error("Please set the TESLA_AUTH_TOKEN environment variable.")
        sys.exit(1)

    filename = 'charging_history.json'

    if os.path.exists(filename):
        print(f"{filename} already exists.")
        if reload:
            logger.info("Reloading data...")
        else:
            logger.info("Use --reload to reload data.")
            return

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f"{API_HOST}/api/1/dx/charging/history") as res:
            data = await res.text()
    if res.status == 401:
        require_token_refesh = True
        logger.error(f"Unauthorized. Please check your TESLA_AUTH_TOKEN. {data}")
        sys.exit(1)

    json_object = json.loads(data)
    with open(filename, 'w') as f:
        json.dump(json_object, f, indent=2)
    print(f"Charging history saved to {filename}")

async def get_chargingInvoice_by_id(chargingId, reload=False):
    global require_token_refesh
    if not os.path.exists('Invoices'):
        os.makedirs('Invoices')
 
    file_path = f'Invoices/{chargingId}.pdf'
 
    if os.path.exists(file_path) and not reload:
        logger.info(f"{chargingId}.pdf already exists.")
        return

    if 'TESLA_AUTH_TOKEN' not in os.environ:
        logger.error("Please set the TESLA_AUTH_TOKEN environment variable.")
        sys.exit(1)

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f"{API_HOST}/api/1/dx/charging/invoice/{chargingId}") as res:
            data = await res.read()

    if res.status== 401:
        require_token_refesh = True
        logger.error(f"Unauthorized. Please check your TESLA_AUTH_TOKEN. {data}")
        sys.exit(1)
    
    with open(file_path, 'wb') as f:
        f.write(data)
    logger.info(f"Invoice PDF saved to {file_path}")

async def extract_invoice_info(filename="charging_history.json"):
    loop = asyncio.get_event_loop()
    def read_json():
        with open(filename, "r") as f:
            return json.load(f)
    data = await loop.run_in_executor(None, read_json)

    results = []
    for session in data.get("data", []):
        vin = session.get("vin")
        start = session.get("chargeStartDateTime")
        end = session.get("chargeStopDateTime")
        for invoice in session.get("invoices", []):
            file_name = invoice.get("fileName")
            content_id = invoice.get("contentId")
            results.append({
                "vin": vin,
                "chargeStartDateTime": start,
                "chargeStopDateTime": end,
                "fileName": file_name,
                "contentId": content_id
            })
    return results

async def get_user_info():
    global require_token_refesh
   
    if 'TESLA_AUTH_TOKEN' not in os.environ:
        logger.error("Please set the TESLA_AUTH_TOKEN environment variable.")
        sys.exit(1)

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f"{API_HOST}/api/1/users/me") as res:
            data = await res.read()

    if res.status== 401:
        require_token_refesh = True
        logger.error(f"Unauthorized. Please check your TESLA_AUTH_TOKEN. {data}")
        sys.exit(1)
    user_info = json.loads(data)
    print(f"User Info: {user_info}")


if __name__ == "__main__":
    async def main():

      await get_new_token_and_update_env()
      await get_charging_history()
      
      invoices = await extract_invoice_info()
      logger.info(f'Found {len(invoices)} invoices')

      for invoice in invoices:
              logger.info(f"Processing invoice for VIN {invoice['vin']} and file {invoice['fileName']}")
              content_id = invoice["contentId"]
              await get_chargingInvoice_by_id(content_id, reload=False)      
              logger.info("\n")        
       
      if require_token_refesh:
        await get_new_token_and_update_env()
        logger.info("Token refreshed. Please run the script again.")
        return          
      # Uncomment the line below to get a specific invoice by ID
      # invoice_id = "your_invoice_id_here"  # Replace with actual invoice ID
       # await get_chargingInvoice_by_id(invoice_id)

    asyncio.run(main())

