import os
import random
import time
import json

from logging import getLogger, DEBUG

from opentelemetry import metrics, trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from azure.monitor.opentelemetry import configure_azure_monitor
from azure.monitor.events.extension import track_event

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

configure_azure_monitor(
    connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
)

tracer = trace.get_tracer(__name__)
logger = getLogger(__name__)
logger.setLevel(DEBUG)
meter = metrics.get_meter_provider().get_meter("items")

sample_counter = meter.create_counter(
    name="sample_counter",
    description="A sample counter",
    unit="1"
)

sample_histogram = meter.create_histogram(
    name="sample_histogram",
    description="A sample time histogram",
    unit="ms",
)

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)


@app.get("/hello")
async def test():
    return {"message": "Hello World"}

@app.get("/exception")
async def exception():
    raise Exception("Hit an exception")

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    span = trace.get_current_span()
    span.record_exception(exc)
    span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
    return PlainTextResponse(json.dumps({ "detail" : str(exc.detail) }), status_code=exc.status_code)

@app.get("/fastapi_exception")
async def fastapi_exception():
    raise HTTPException(status_code=404, detail="FastAPI exception")

@app.get("/custom_event")
async def custom_event():
    track_event("Custom event", {"key1": "value1", "key2": "value2"})
    return {"message": "Custom event sent"}

@app.get("/custom_dimension")
async def custom_dimension():
    span = trace.get_current_span()
    span.set_attribute("CustomDimension1", "value1")
    span.set_attribute("CustomDimension2", "value2")
    return {"message": "Custom dimension set"}

@app.get("/counter")
async def counter():
    sample_counter.add(1)
    return {"message": "Counter incremented"}

@app.get("/histogram")
async def histogram():
    sample_histogram.record(random.randint(1, 100))
    return {"message": "Histogram value recorded"}

@app.get("/user_id")
async def user_id(request: Request):
    span = trace.get_current_span()
    if "x-ms-client-principal-id" in request.headers:
        span.set_attribute("enduser.id", request.headers["x-ms-client-principal-id"])
    else:
        span.set_attribute("enduser.id", "anonymous")
    return {"message": "User ID set"}

@app.get("/span")
async def span():
    pre_time = random.randint(1, 2000)
    child_time = random.randint(1, 2000)
    post_time = random.randint(1, 2000)
    logger.info(f"Sleeping for {pre_time}ms")
    time.sleep(pre_time / 1000)
    with tracer.start_as_current_span("child_span"):
        logger.info(f"Sleeping for {child_time}ms")
        time.sleep(child_time / 1000)
    logger.info(f"Sleeping for {post_time}ms")
    time.sleep(post_time / 1000)
    return {"message": "Child span created"}
