"""
Webhook notification with retry logic
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional

MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 10


async def send_webhook(
    webhook_url: str,
    payload: Dict[str, Any],
    attempt: int = 1
) -> Dict[str, Any]:
    """
    Send webhook notification with retry logic

    Args:
        webhook_url: Target webhook URL
        payload: JSON payload to send
        attempt: Current attempt number (1-indexed)

    Returns:
        Dict with success status and details
    """
    if not webhook_url:
        return {"success": False, "error": "No webhook URL"}

    print(f"📞 Calling webhook (attempt {attempt}/{MAX_ATTEMPTS}): {webhook_url}")

    try:
        timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                webhook_url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'ContentGenerationService/1.0'
                }
            ) as response:

                if response.status >= 200 and response.status < 300:
                    print(f"   ✅ Webhook successful (status: {response.status})")
                    return {
                        "success": True,
                        "status_code": response.status,
                        "attempts": attempt
                    }
                else:
                    raise Exception(f"Webhook returned {response.status}")

    except asyncio.TimeoutError:
        error_msg = f"Webhook timeout after {TIMEOUT_SECONDS}s"
        print(f"   ❌ {error_msg}")

        if attempt < MAX_ATTEMPTS:
            delay = 2 ** (attempt - 1)  # 1s, 2s, 4s
            print(f"   🔄 Retrying in {delay}s...")
            await asyncio.sleep(delay)
            return await send_webhook(webhook_url, payload, attempt + 1)

        return {
            "success": False,
            "error": error_msg,
            "attempts": attempt
        }

    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ Webhook failed: {error_msg}")

        if attempt < MAX_ATTEMPTS:
            delay = 2 ** (attempt - 1)
            print(f"   🔄 Retrying in {delay}s...")
            await asyncio.sleep(delay)
            return await send_webhook(webhook_url, payload, attempt + 1)

        return {
            "success": False,
            "error": error_msg,
            "attempts": attempt
        }


def create_completion_payload(job_data: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """Create webhook payload for job completion"""
    payload = {
        "event": "job.completed",
        "jobId": job_data.get("jobId"),
        "userId": job_data.get("userId"),
        "type": job_data.get("type"),
        "status": "completed",
        "completedAt": datetime.utcnow().isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }

    # Add type-specific data
    if job_data.get("type") == "lora-training":
        payload["lora"] = {
            "modelUrl": result.get("modelUrl"),
            "version": result.get("version"),
            "trigger": job_data.get("config", {}).get("trigger")
        }

    return payload


def create_failure_payload(job_data: Dict[str, Any], error: str) -> Dict[str, Any]:
    """Create webhook payload for job failure"""
    return {
        "event": "job.failed",
        "jobId": job_data.get("jobId"),
        "userId": job_data.get("userId"),
        "type": job_data.get("type"),
        "status": "failed",
        "error": error,
        "failedAt": datetime.utcnow().isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }
