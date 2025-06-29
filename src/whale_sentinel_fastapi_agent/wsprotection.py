import base64
import hashlib
from starlette.datastructures import UploadFile
from starlette.responses import JSONResponse
from user_agents import parse
from datetime import datetime, timezone
from .wslogger import wslogger
from .wsagent import Agent
import os, sys, platform, threading, multiprocessing, psutil

class Protection(object):
    """
    Whale Sentinel FastAPI Agent Protection
    """
    def __init__(self):
        """
        Initialize the Whale Sentinel FastAPI Agent Protection
        """
    
    async def _mode_lite(self, request_meta_data) -> None:
        """
        Perform the Whale Sentinel FastAPI Agent Protection in lite mode
        """
        try:
            await Agent._write_to_storage(self, request_meta_data)
        except Exception as e:
            wslogger.error(f"Something went wrong at Protection.__init__.\n Error message - {e}")
    
    async def _mode_monitor(self, request_meta_data) -> None:
        """
        Perform the Whale Sentinel FastAPI Agent Protection in monitor mode
        """
        try:
            detection = Agent._detection(self, request_meta_data)
            if detection is None:
                await Agent._write_to_storage(self, request_meta_data)
        except Exception as e:
            wslogger.error(f"Something went wrong at Protection._mode_monitor.\n Error message - {e}")

    async def _mode_protection(self, profile, request_meta_data) -> None:
        """
        Perform the Whale Sentinel FastAPI Agent Protection in protection mode
        """
        try:
            wad_threshold = profile.get("ws_module_web_attack_detection", {}).get("threshold", {})
            dgad_threshold = profile.get("ws_module_dga_detection", {}).get("threshold", {})
            analysis_metrix, analysis_result = Agent._detection(self, request_meta_data)
            if analysis_metrix is None or analysis_result is None:
                Agent._write_to_storage(self, request_meta_data)
                return False
            wad = analysis_metrix.get("ws_module_web_attack_detection_score", 0)
            dgad = analysis_metrix.get("ws_module_dga_detection_score", 0)
            cad = analysis_metrix.get("ws_module_common_attack_detection", {})
            agent_action = analysis_result
            agent_self_action = "ALLOW" #Default agent action is allow
            if wad >= wad_threshold or dgad >= dgad_threshold or any(cad.values()):
                agent_self_action = "BLOCK"
            if (agent_action == "ABNORMAL_REQUEST") and agent_self_action == "BLOCK":
                return True
            return False
        except Exception as e:
            wslogger.error(f"Something went wrong at Protection._mode_protection.\n Error message - {e}")

    async def _secure_response(self, profile, response):
        """
        Secure the response headers
        """
        try:
            if isinstance(response, JSONResponse):
                secure_headers = profile.get("secure_response_headers", {}).get("headers", {})
                for key, value in secure_headers.items():
                    response.headers[key] = value
                return response
            return response
        except Exception as e:
            wslogger.error(f"Something went wrong at Protection._secure_response.\n Error message - {e}")
               
    async def do(self, request) -> None:
        """
        Perform the Whale Sentinel FastAPI Agent Protection
        """
        try:
            req_method = request.method
            req_path = request.url.path
            req_host = request.client.host if request.client else "unknown"
            req_headers = request.headers   
            req_query_string = str(request.url.query)
            req_ip = request.client.host if request.client else "N/A"
            req_user_agent = req_headers.get("User-Agent", "N/A")
            req_content_type = req_headers.get("Content-Type", "N/A")
            req_content_length = int(req_headers.get("Content-Length", 0))
            req_referrer = req_headers.get("Referrer", "N/A")
            
            parsed_ua = parse(req_user_agent)
            req_device = parsed_ua.device.family
            req_ua_platform = parsed_ua.os.family
            req_ua_browser = parsed_ua.browser.family
            req_ua_browser_version = parsed_ua.browser.version_string
            req_network = "unknown"  # Starlette/FastAPI doesn't expose "network" info
            
            mem = psutil.virtual_memory()
            total = mem.total           # Tổng RAM (bytes)
            available = mem.available   # RAM còn trống (bytes)
            used = total - available       # RAM đã dùng (bytes)

            used_percent = round((used / total) * 100, 2)  # Phần trăm RAM đã dùng

            uploaded_files_info = []            
            req_body = None
            if "multipart/form-data" in request.headers.get("content-type", ""):
                form = await request.form()
                for _, field in form.multi_items():
                    if isinstance(field, UploadFile) and field.filename:
                        file_content = await field.read()
                        sha256_hash = hashlib.sha256(file_content).hexdigest()
                        encoded_content = base64.b64encode(file_content).decode("utf-8")
                        size = len(file_content)
                        file_info = {
                            "file_name": field.filename,
                            "file_size": size,
                            "file_content": encoded_content,
                            "file_type": field.content_type,
                            "file_hash": sha256_hash
                        }
                        uploaded_files_info.append(file_info)

                        await field.seek(0)
            else:
                body_bytes = await request.body()
                req_body = body_bytes.decode('utf-8') if body_bytes else None

            meta_data = {
                "payload": {
                    "data": {
                        "agent_id": self.agent_id,
                        "agent_name": self.agent_name,
                        "client_information": {
                            "ip": req_ip,
                            "device_type": req_device,
                            "platform": req_ua_platform,
                            "browser": req_ua_browser,
                            "browser_version": req_ua_browser_version,
                            "network_type": req_network,
                        },
                        "http_request": {
                            "method": req_method,
                            "url": req_path,
                            "host": req_host,
                            "headers": {
                                "user-agent": req_user_agent,
                                "content-type": req_content_type,
                                "content-length": req_content_length,
                                "referrer": req_referrer
                            },
                            "body": req_body,
                            "query_parameters": req_query_string,
                            "files": uploaded_files_info
                        },
                        "runtime_information": {
                            "ip_address": self.ip_address,
                            "pid": os.getpid(),
                            "run_as": psutil.Process().username(),
                            "executable_path": psutil.Process().exe(),
                            "executable_name": threading.current_thread().name,
                            "executable_version": platform.python_version(),
                            "process_name": multiprocessing.current_process().name,
                            "process_path": os.getcwd(),
                            "process_command": psutil.Process().cmdline(),
                            "platform": platform.system(),
                            "cpu_usage": psutil.cpu_percent(interval=1),
                            "memory_usage": used_percent,
                            "architecture": platform.machine(),
                            "os_name": platform.system(),
                            "os_version": platform.version(),
                            "os_build": platform.release(),
                        }
                    }
                },
                "request_created_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            return meta_data
        except Exception as e:
            wslogger.error(f"Something went wrong at Protection.do.\n Error message - {e}")