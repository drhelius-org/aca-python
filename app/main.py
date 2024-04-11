import os
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from logging import getLogger, DEBUG
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import random

configure_azure_monitor(
    connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
)

logger = getLogger(__name__)
logger.setLevel(DEBUG)

meter = metrics.get_meter_provider().get_meter("items")
create_counter = meter.create_counter(
    name="items_created",
    description="Number of items created",
    unit="1"
)
query_counter = meter.create_counter(
    name="items_queried",
    description="Number of items queried",
    unit="1"
)
query_histogram = meter.create_histogram(
    name="items_query_time",
    description="Time taken to query an item",
    unit="ms",
)
creation_histogram = meter.create_histogram(
    name="items_creation_time",
    description="Time taken to create an item",
    unit="ms",
)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

class Item(BaseModel):
    name: str
    price: float
    id: int

fake_items_db = [
    {
        "name": "Foo",
        "price": 9.99,
        "id": 999
    },
    {
        "name": "Bar",
        "price": 5.99,
        "id": 555
    }
]

@app.get("/items/")
async def all_items(request: Request):
    logger.info("all_items called")
    logger.info("Returning all items")
    return fake_items_db

@app.get("/items/{item_name}")
async def read_item(request: Request, item_name: str):
    logger.info(f"read_item called with {item_name}")
    item = None
    for i in fake_items_db:
        if i["name"] == item_name:
            item = i
            break
    if item is None:
        logger.error("Item not found")
        raise HTTPException(status_code=404, detail="Item not found")
    logger.info(f"Returning item {item_name}")
    query_counter.add(1)
    query_histogram.record(random.randint(1, 500))
    return item

@app.post("/items/{item_name}")
async def create_item(request: Request, item_name: str, item: Item):
    logger.info(f"create_item called with {item_name}")
    item = item.model_dump()
    item["name"] = item_name
    fake_items_db.append(item)
    logger.info(f"Item {item_name} created")
    create_counter.add(1)
    creation_histogram.record(random.randint(1, 500))
    return item
