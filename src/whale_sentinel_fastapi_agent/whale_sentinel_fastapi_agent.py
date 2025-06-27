from dotenv import load_dotenv
import os
from fastapi import Request, UploadFile, Form, Depends
from fastapi.responses import JSONResponse
from functools import wraps
from typing import Callable
from .wslogger import wslogger
from .wsprotection import Protection
from .wsagent import Agent
import asyncio
from datetime import datetime, timezone
from cachetools import TTLCache

cache = TTLCache(maxsize=1000, ttl=60)  # Max size of 1000 and TTL of 60 seconds

class WhaleSentinelFastApiAgent(object):
    """
    Whale Sentinel FastAPI Agent
    """

    def __init__(self):
        """
        Initialize the Whale Sentinel FastAPI Agent
        """
        # Load environment variables from .env file
        try:
            load_dotenv()

            LOG_MAX_SIZE = os.getenv("LOG_MAX_SIZE", 10000000)  # in bytes
            LOG_MAX_BACKUPS = os.getenv("LOG_MAX_BACKUPS", 3)  # number of backup files
            WS_GATEWAY_API = os.getenv("WS_GATEWAY_API")
            WS_AGENT_AUTH_TOKEN = os.getenv('WS_AGENT_AUTH_TOKEN')
            WS_AGENT_ID = os.getenv("WS_AGENT_ID")
            WS_AGENT_NAME = os.getenv("WS_AGENT_NAME")
            WS_VERIFY_TLS = os.getenv("WS_VERIFY_TLS", "true").lower() == "true"
            self.log_max_size = int(LOG_MAX_SIZE)
            self.log_max_backups = int(LOG_MAX_BACKUPS)
            self.ws_gateway_api = WS_GATEWAY_API
            self.ws_agent_auth_token = WS_AGENT_AUTH_TOKEN
            self.agent_id = WS_AGENT_ID
            self.agent_name = WS_AGENT_NAME
            self.ws_verity_tls = WS_VERIFY_TLS
            self._initialize()
        except Exception as e:
            wslogger.error(f"Error initializing Whale Sentinel FastAPI Agent: {e}")
            raise

    def _initialize(self):
        """
        Initialize the Whale Sentinel FastAPI Agent
        """
        try:
            if not self.ws_gateway_api:
                raise ValueError("WS_GATEWAY_API must be set")
            if not self.ws_agent_auth_token:
                raise ValueError("WS_AGENT_AUTH_TOKEN must be set")
            if not self.agent_id:
                raise ValueError("WS_AGENT_ID must be set")
            if not self.agent_name:
                raise ValueError("WS_AGENT_NAME must be set")
            Agent.__init__(self)
        except Exception as e:
            wslogger.error(f"Error in Whale Sentinel FastAPI Agent initialization: {e}")

    def whale_sentinel_agent_protection(self):
        def _whale_sentinel_agent_protection(func: Callable):
            """
            Decorator to protect the FastAPI with Whale Sentinel Protection
            """
            @wraps(func)
            async def wrapper(request: Request, *args, **kwargs):
                profile = Agent._profile(self)
                if profile is None:
                    wslogger.info("Whale Sentinel FastAPI Agent Protection: No profile found, skipping protection")
                    request_meta_data = await Protection.do(self, request)
                    asyncio.create_task(Agent._write_to_storage(self, request_meta_data))
                    return await func(request, *args, **kwargs)

                running_mode = profile.get("running_mode", "lite")
                last_run_mode = profile.get("last_run_mode", "lite")
                data_synchronized = profile.get("lite_mode_data_is_synchronized", False)
                data_synchronize_status = profile.get("lite_mode_data_synchronize_status", "fail")
                rate_limit_enable = profile.get("ws_request_rate_limit", {}).get("enable", False)
                rate_limit_threshold = profile.get("ws_request_rate_limit", {}).get("threshold", 100)
                secure_response_enabled = profile.get("secure_response_headers", {}).get("enable", False)
                
                client_ip_address = (
                    request.client.host
                )
                result = await func(request, *args, **kwargs)

                if running_mode == "off":
                    return result

                if rate_limit_enable:
                    client_request_temp_id = (
                        f"{client_ip_address}_{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
                    )
                    request_count = cache.get(client_request_temp_id)
                    if request_count is None:
                        cache[client_request_temp_id] = 1
                    elif request_count >= rate_limit_threshold:
                        request_meta_data = Protection.do(self, request)
                        asyncio.create_task(Agent._write_to_storage(self, request_meta_data))

                        wslogger.info("Whale Sentinel FastAPI Agent Protection: Request blocked by Whale Sentinel Protection")
                        return JSONResponse(
                            status_code=403,
                            content={
                                "msg": "Forbidden: Request blocked by Whale Sentinel Protection.",
                                "time": str(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')),
                                "ip": client_ip_address
                            }
                        )
                    else:
                        cache[client_request_temp_id] += 1

                if running_mode  == "lite":
                    request_meta_data = await Protection.do(self, request)
                    asyncio.create_task(Protection._mode_lite(self, request_meta_data))

                if running_mode != "lite" and last_run_mode == "lite" and not data_synchronized and data_synchronize_status == "none":
                    asyncio.create_task(Agent._synchronize(self, profile))

                if running_mode == "monitor":
                    request_meta_data = await Protection.do(self, request)
                    asyncio.create_task(Protection._mode_monitor(self, request_meta_data))
                
                if running_mode == "protection":
                    request_meta_data = await Protection.do(self, request)
                    is_blocked = await Protection._mode_protection(self, profile, request_meta_data)
                    if is_blocked:
                        wslogger.info("Whale Sentinel FastAPI Agent Protection: Request blocked by Whale Sentinel Protection")
                        return JSONResponse(
                            status_code=403,
                            content={
                                "msg": "Forbidden: Request blocked by Whale Sentinel Protection.",
                                "time": str(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')),
                                "ip": client_ip_address
                            }
                        )

                if secure_response_enabled:
                    result = await Protection._secure_response(self, profile, result)

                return result
            return wrapper
        return _whale_sentinel_agent_protection
    