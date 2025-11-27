"""
MongoDB client for updating job status
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import os
from datetime import datetime

class JobDatabase:
    """MongoDB client for job management"""

    def __init__(self):
        self.client = None
        self.db = None
        self.jobs = None

    async def connect(self):
        """Connect to MongoDB"""
        try:
            mongodb_uri = os.getenv('MONGODB_URI')
            if not mongodb_uri:
                raise ValueError("MONGODB_URI not set in environment")

            self.client = AsyncIOMotorClient(mongodb_uri)
            # Get database name from URI or default
            self.db = self.client.get_default_database()
            self.jobs = self.db.jobs

            # Test connection
            await self.client.admin.command('ping')
            print(f"✅ Connected to MongoDB: {self.db.name}")

        except Exception as e:
            print(f"❌ MongoDB connection error: {e}")
            raise

    async def update_job_status(self, job_id: str, status: str, progress: int = None, error: str = None):
        """Update job status and progress"""
        update_data = {
            "status": status,
            "updatedAt": datetime.utcnow()
        }

        if progress is not None:
            update_data["progress"] = progress

        if status == "processing" and progress == 0:
            update_data["startedAt"] = datetime.utcnow()

        if status == "completed":
            update_data["completedAt"] = datetime.utcnow()
            update_data["progress"] = 100

        if error:
            update_data["error"] = error

        result = await self.jobs.update_one(
            {"jobId": job_id},
            {"$set": update_data}
        )

        return result.modified_count > 0

    async def add_version(self, job_id: str, version_data: dict):
        """Add a new version to the job"""
        result = await self.jobs.update_one(
            {"jobId": job_id},
            {
                "$push": {
                    "versions": version_data
                },
                "$inc": {
                    "usage.storageBytes": version_data.get("sizeBytes", 0)
                },
                "$set": {
                    "usage.lastUsed": datetime.utcnow()
                }
            }
        )

        return result.modified_count > 0

    async def get_job(self, job_id: str):
        """Get job by ID"""
        return await self.jobs.find_one({"jobId": job_id})

    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()

# Global database instance
db = JobDatabase()
