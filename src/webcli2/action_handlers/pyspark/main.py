import logging
logger = logging.getLogger(__name__)

from typing import Any, Optional, Literal
import time
from base64 import b64encode, b64decode
import threading
from pydantic import BaseModel, ValidationError
import oci
import json

from webcli2 import WebCLIEngine, ActionHandler
from oracle_spark_tools import OciApiKeyClientFactory
from oracle_spark_tools.cli import CLIPackage, PackageType, CommandType
from pydantic import ValidationError

def get_value(value:Optional[str]) -> Optional[str]:
    return None if value is None else b64decode(value.encode("ascii")).decode("utf-8")

####################################################################################################
# CLIActionHandler is a plugin that is registered with CLIHandler
# CLIHandler will pass request to us if we say we can handle it -- if can_handle returns True
####################################################################################################

####################################################################################################
# We will poll message from a kafka topic
# We will drop following kafka messages
#   - Not JSON serialization of CLIPackage
#   - Not PackageType.RESPONSE package
#
# For each CLIPackage (RESPONSE) we got, we will notify the browser via respective web socket
####################################################################################################

class PySparkRequest(BaseModel):
    type: Literal["spark-cli"]
    server_id: str
    client_id: str
    command_text: str

    #########################################################################
    # Given a PySparkRequest model, try to get CLI package from it
    #########################################################################
    def get_cli_package(self, action_id:int):
        log_prefix = "PySparkActionHandler.get_cli_package"
        logger.debug(f"{log_prefix}: enter")

        lines = self.command_text.strip().split("\n")
        if len(lines) < 2:
            logger.debug(f"{log_prefix}: no title")
            logger.debug(f"{log_prefix}: exit")
            return None

        title = lines[0].strip()
        command_type = {
            "%system%":     CommandType.SYSTEM,
            "%pyspark%":    CommandType.PYTHON,
            "%bash%":       CommandType.BASH,
        }.get(title)

        if command_type is None:
            logger.debug(f"{log_prefix}: invalid title: {title}")
            logger.debug(f"{log_prefix}: exit")
            return None

        cli_package = CLIPackage(
            package_type = PackageType.REQUEST,
            command_type = command_type,
            command_text = "\n".join(lines[1:]),
            server_id = self.server_id,
            client_id = self.client_id,
            sequence = action_id
        )
        # caller need to further set client_id
        logger.debug(f"{log_prefix}: exit")
        return cli_package

class SparkResponse(BaseModel):
    type: Literal["spark-cli"]
    cli_package: CLIPackage

class PySparkActionHandler(ActionHandler):
    oakcf: OciApiKeyClientFactory       # this factory can create many different type of oci clients
    stream_id: str                      # The OSS stream (actually a kafka topic)'s ocid
    kafka_consumer_group_name:str       # when polling message from kafka, this is the consumer group name

    listener_thread:Any                 # A thread that poll's kafka messages
    stream_client: Any                  # OCI stream client

    def startup(self, webcli_engine:WebCLIEngine):
        log_prefix = "PySparkActionHandler.startup"
        logger.debug(f"{log_prefix}: enter")
        super().startup(webcli_engine)

        # start listener thread so we can receive kafka messages
        assert self.listener_thread is None
        self.listener_thread = threading.Thread(target=self.listener, daemon=True)
        self.listener_thread.start()
        self.stream_client = self.oakcf.get_stream_client()
        logger.debug(f"{log_prefix}: exit")

    def shutdown(self):
        log_prefix = "PySparkActionHandler.shutdown"
        logger.debug(f"{log_prefix}: enter")

        assert self.listener_thread is not None
        assert self.require_shutdown == False
        assert self.webcli_engine is not None

        # ask listener to shutdown and then wait for it to shutdown
        self.require_shutdown = True
        self.listener_thread.join()
        self.webcli_engine = None

        logger.debug(f"{log_prefix}: exit")


    def listener(self):
        log_prefix = "PySparkActionHandler.listener"
        logger.debug(f"{log_prefix}: enter")
        stream_client = self.oakcf.get_stream_client() # we create a spearate stream_client, the member stream_client is for sending messages
        r = stream_client.create_group_cursor(
            self.stream_id,
            oci.streaming.models.CreateGroupCursorDetails(
                type = oci.streaming.models.CreateGroupCursorDetails.TYPE_LATEST,
                group_name = self.kafka_consumer_group_name,
                instance_name = "main",
                commit_on_get = True,
            )
        )
        cursor = r.data.value
        # TODO: handle exception and restart loop
        try:
            while True:
                if self.require_shutdown:
                    # quit if we are asked to quit
                    break
                r = stream_client.get_messages(self.stream_id, cursor)
                if len(r.data) > 0:
                    for message in r.data:
                        message_text = b64decode(message.value.encode("ascii")).decode("utf-8")
                        try:
                            payload_json = json.loads(message_text)
                        except json.decoder.JSONDecodeError:
                            logger.debug(f"{log_prefix}: bad JSON")
                            continue

                        try:
                            cli_package = CLIPackage.model_validate(payload_json)
                        except ValidationError:
                            logger.debug(f"{log_prefix}: not a CLIPackage")
                            continue

                        if cli_package.package_type != PackageType.RESPONSE:
                            logger.debug(f"{log_prefix}: not a CLIPackage for response")
                            continue

                        logger.debug(f"{log_prefix}: got cli package: {cli_package}")
                        # let's complete the action
                        spark_response = SparkResponse(type="spark-cli", cli_package=cli_package)
                        self.webcli_engine.complete_action(
                            cli_package.sequence, 
                            spark_response.model_dump(mode="json")
                        )
                        # notify browser via web socket
                        self.webcli_engine.notify_websockt_client(
                            cli_package.client_id, 
                            cli_package.sequence, 
                            spark_response
                        )
                else:
                    time.sleep(2)
                cursor = r.headers["opc-next-cursor"]
        except Exception:
            logger.error(f"{log_prefix}: failed polling oss messages", exc_info=True)
        logger.debug(f"{log_prefix}: exit")

    def __init__(self, *, stream_id:str, kafka_consumer_group_name:str):
        log_prefix = "PySparkActionHandler.__init__"
        logger.debug(f"{log_prefix}: enter")
        self.oakcf = OciApiKeyClientFactory()
        self.stream_id = stream_id
        self.kafka_consumer_group_name = kafka_consumer_group_name
        self.listener_thread = None
        self.stream_client = self.oakcf.get_stream_client()
        logger.debug(f"{log_prefix}: exit")

    def parse_request(self, request:Any, action_id:int) -> Optional[PySparkRequest]:
        log_prefix = "PySparkActionHandler.parse_request"
        # check if we recognize the request JSON
        logger.debug(f"{log_prefix}: enter")
        try:
            spark_request = PySparkRequest.model_validate(request)
        except ValidationError:
            logger.debug(f"{log_prefix}: invalid request format")
            logger.debug(f"{log_prefix}: exit")
            return None
        
        cli_package = spark_request.get_cli_package(action_id)
        if cli_package is None:
            logger.debug(f"{log_prefix}: cannot get CLIPackage from it")
            logger.debug(f"{log_prefix}: exit")
            return None
        
        logger.debug(f"{log_prefix}: exit")
        return spark_request


    # can you handle this request?
    def can_handle(self, request:Any) -> bool:
        log_prefix = "PySparkActionHandler.can_handle"
        logger.debug(f"{log_prefix}: enter")
        spark_request = self.parse_request(request, 0)
        r = spark_request is not None
        logger.debug(f"{log_prefix}: {'Yes' if r else 'No'}")
        logger.debug(f"{log_prefix}: exit")
        return r

    def send_cli_package(self, cli_package:CLIPackage):
        #####################################################
        # send a CLIPackage to kafka so a spark driver can pick it up
        #####################################################
        log_prefix = "PySparkActionHandler.send_cli_package"
        logger.debug(f"{log_prefix}: enter")
        text_to_send = cli_package.model_dump_json()
        message = oci.streaming.models.PutMessagesDetailsEntry(
            key=None,
            value=b64encode(text_to_send.encode("utf-8")).decode("ascii")
        )
        pmd = oci.streaming.models.PutMessagesDetails(
            messages = [message]
        )
        self.stream_client.put_messages(self.stream_id, pmd)
        logger.debug(f"{log_prefix}: exit")

    # The request is a dict, type field is already spark-cli
    # the "command" field is text
    # if frist line is %bash%, then rest is bash code
    # if first line is %pyspark%, then rest is pyspark code
    def handle(self, action_id:int, request:Any):
        log_prefix = "PySparkActionHandler.handle"
        logger.debug(f"{log_prefix}: enter")
        # TODO: if we are not able to send message, we should complete the action, set error code
        try:
            spark_request = self.parse_request(request, action_id)
            assert spark_request is not None # since handle only called if can_handle returns True, so we MUST have a cli_package
            cli_package = spark_request.get_cli_package(action_id)
            assert cli_package is not None
            self.send_cli_package(cli_package)
            logger.debug(f"{log_prefix}: exit")
        except:
            logger.debug(f"{log_prefix}: exception captured", exc_info=True)
