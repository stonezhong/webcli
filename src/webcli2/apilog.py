IGNORED_PREFIX = set([
    "PySparkActionHandler.startup",
    "PySparkActionHandler.listener",
    "ClientManager.publish_notification",
    "ClientManager.pop_notification",
    "WebSocketConnectionManager.publish_notification",
    "WebSocketConnectionManager.websocket_endpoint",
    "ConfigHandler.handle",
    "ConfigHandler.can_handle",
    "ConfigHandler.parse_request",
    "MermaidHandler.handle",
    "MermaidHandler.can_handle",
    "MermaidHandler.parse_request",    
    "PySparkActionHandler.handle",
    "PySparkActionHandler.can_handle",
    "PySparkActionHandler.parse_request",
    "PySparkActionHandler.get_cli_package",
    "OpenAIActionHandler.handle",
    "OpenAIActionHandler.can_handle",
    "OpenAIActionHandler.parse_request",    
])

def log_api_enter(logger, log_prefix):
    if log_prefix in IGNORED_PREFIX:
        return
    logger.debug(f"{log_prefix}: enter")

def log_api_exit(logger, log_prefix):
    if log_prefix in IGNORED_PREFIX:
        return
    logger.debug(f"{log_prefix}: exit")
