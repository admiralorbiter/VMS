# utils/salesforce_client.py
"""
Enhanced Salesforce client for data validation with caching and error handling.
"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

# Try to import Redis, but make it optional
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    from simple_salesforce import Salesforce
    from simple_salesforce.exceptions import SalesforceError

    SALESFORCE_AVAILABLE = True
except ImportError:
    SALESFORCE_AVAILABLE = False
    Salesforce = None
    SalesforceError = None

logger = logging.getLogger(__name__)


class SalesforceClientError(Exception):
    """Base exception for Salesforce client errors."""

    pass


class SalesforceRateLimitError(SalesforceClientError):
    """Exception raised when Salesforce rate limits are exceeded."""

    pass


class SalesforceConnectionError(SalesforceClientError):
    """Exception raised when connection to Salesforce fails."""

    pass


class SalesforceClient:
    """
    Enhanced Salesforce client with caching, rate limiting, and error handling.

    This client provides methods to fetch record counts and samples for various
    Salesforce objects, with Redis caching for improved performance.
    """

    def __init__(
        self,
        username: str = None,
        password: str = None,
        security_token: str = None,
        domain: str = "login",
        redis_client=None,
    ):
        """
        Initialize the Salesforce client.

        Args:
            username: Salesforce username
            password: Salesforce password
            security_token: Salesforce security token
            domain: Salesforce domain (login or test)
            redis_client: Redis client for caching (optional)
        """
        self.username = username or os.environ.get("SF_USERNAME")
        self.password = password or os.environ.get("SF_PASSWORD")
        self.security_token = security_token or os.environ.get("SF_SECURITY_TOKEN")
        self.domain = domain

        # Initialize Redis client if available
        self.redis_client = None
        if REDIS_AVAILABLE and redis_client:
            self.redis_client = redis_client
        elif REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=os.environ.get("VALIDATION_REDIS_HOST", "localhost"),
                    port=int(os.environ.get("VALIDATION_REDIS_PORT", 6379)),
                    db=int(os.environ.get("VALIDATION_REDIS_DB", 0)),
                    decode_responses=True,
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis connection established successfully")
            except Exception as e:
                logger.warning(
                    f"Redis connection failed: {e}. Caching will be disabled."
                )
                self.redis_client = None

        # Initialize Salesforce connection
        self.sf = None
        self._connection_attempts = 0
        self._last_connection_attempt = None

        # Rate limiting
        self._last_query_time = 0
        self._min_query_interval = 0.1  # 100ms between queries

        # Cache settings
        self.cache_ttl = int(os.environ.get("VALIDATION_CACHE_TTL", 300))  # 5 minutes

        # Connection retry settings
        self.max_retries = int(os.environ.get("VALIDATION_MAX_RETRIES", 3))
        self.retry_delay = float(os.environ.get("VALIDATION_RETRY_DELAY", 1.0))

    def _connect(self) -> bool:
        """Establish connection to Salesforce with retry logic."""
        if self._connection_attempts >= self.max_retries:
            raise SalesforceConnectionError("Maximum connection attempts exceeded")

        if (
            self._last_connection_attempt
            and datetime.now() - self._last_connection_attempt
            < timedelta(seconds=self.retry_delay)
        ):
            return False

        try:
            if not SALESFORCE_AVAILABLE:
                raise SalesforceClientError("simple_salesforce package not available")

            self.sf = Salesforce(
                username=self.username,
                password=self.password,
                security_token=self.security_token,
                domain=self.domain,
            )

            # Test connection
            self.sf.describe()
            logger.info("Salesforce connection established successfully")
            self._connection_attempts = 0
            return True

        except Exception as e:
            self._connection_attempts += 1
            self._last_connection_attempt = datetime.now()
            logger.error(
                f"Salesforce connection attempt {self._connection_attempts} failed: {e}"
            )
            return False

    def _ensure_connection(self):
        """Ensure Salesforce connection is established."""
        if not self.sf:
            if not self._connect():
                raise SalesforceConnectionError(
                    "Failed to establish Salesforce connection"
                )

    def _rate_limit(self):
        """Implement rate limiting for Salesforce queries."""
        current_time = time.time()
        time_since_last = current_time - self._last_query_time

        if time_since_last < self._min_query_interval:
            sleep_time = self._min_query_interval - time_since_last
            time.sleep(sleep_time)

        self._last_query_time = time.time()

    def _get_cache_key(self, query_type: str, **kwargs) -> str:
        """Generate a cache key for the given query."""
        key_parts = [f"sf:{query_type}"]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return ":".join(key_parts)

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if available."""
        if not self.redis_client:
            return None

        try:
            import json

            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")

        return None

    def _set_cache(self, cache_key: str, data: Any, ttl: int = None):
        """Set data in cache."""
        if not self.redis_client:
            return

        try:
            import json

            ttl = ttl or self.cache_ttl
            self.redis_client.setex(cache_key, ttl, json.dumps(data))
        except Exception as e:
            logger.warning(f"Cache setting failed: {e}")

    def get_volunteer_count(self) -> int:
        """Get the total count of volunteers in Salesforce."""
        cache_key = self._get_cache_key("volunteer_count")
        cached_count = self._get_from_cache(cache_key)

        if cached_count is not None:
            return cached_count

        try:
            self._ensure_connection()
            self._rate_limit()

            # Query for volunteer count
            result = self.sf.query(
                "SELECT COUNT() FROM Contact WHERE Contact_Type__c = 'Volunteer' OR Contact_Type__c = ''"
            )
            count = result["totalSize"]

            self._set_cache(cache_key, count)
            return count

        except Exception as e:
            logger.error(f"Failed to get volunteer count: {e}")
            raise SalesforceClientError(f"Failed to get volunteer count: {e}")

    def get_organization_count(self) -> int:
        """Get the total count of organizations in Salesforce."""
        cache_key = self._get_cache_key("organization_count")
        cached_count = self._get_from_cache(cache_key)

        if cached_count is not None:
            return cached_count

        try:
            self._ensure_connection()
            self._rate_limit()

            # Query for organization count
            result = self.sf.query(
                "SELECT COUNT() FROM Account WHERE Type NOT IN ('Household', 'School District', 'School')"
            )
            count = result["totalSize"]

            self._set_cache(cache_key, count)
            return count

        except Exception as e:
            logger.error(f"Failed to get organization count: {e}")
            raise SalesforceClientError(f"Failed to get organization count: {e}")

    def get_event_count(self) -> int:
        """Get the total count of events in Salesforce."""
        cache_key = self._get_cache_key("event_count")
        cached_count = self._get_from_cache(cache_key)

        if cached_count is not None:
            return cached_count

        try:
            self._ensure_connection()
            self._rate_limit()

            # Query for event count
            result = self.sf.query("SELECT COUNT() FROM Event")
            count = result["totalSize"]

            self._set_cache(cache_key, count)
            return count

        except Exception as e:
            logger.error(f"Failed to get event count: {e}")
            raise SalesforceClientError(f"Failed to get event count: {e}")

    def get_student_count(self) -> int:
        """Get the total count of students in Salesforce."""
        cache_key = self._get_cache_key("student_count")
        cached_count = self._get_from_cache(cache_key)

        if cached_count is not None:
            return cached_count

        try:
            self._ensure_connection()
            self._rate_limit()

            # Query for student count
            result = self.sf.query(
                "SELECT COUNT() FROM Contact WHERE Contact_Type__c = 'Student'"
            )
            count = result["totalSize"]

            self._set_cache(cache_key, count)
            return count

        except Exception as e:
            logger.error(f"Failed to get student count: {e}")
            raise SalesforceClientError(f"Failed to get student count: {e}")

    def get_teacher_count(self) -> int:
        """Get the total count of teachers in Salesforce."""
        cache_key = self._get_cache_key("teacher_count")
        cached_count = self._get_from_cache(cache_key)

        if cached_count is not None:
            return cached_count

        try:
            self._ensure_connection()
            self._rate_limit()

            # Query for teacher count
            result = self.sf.query(
                "SELECT COUNT() FROM Contact WHERE Contact_Type__c = 'Teacher'"
            )
            count = result["totalSize"]

            self._set_cache(cache_key, count)
            return count

        except Exception as e:
            logger.error(f"Failed to get teacher count: {e}")
            raise SalesforceClientError(f"Failed to get teacher count: {e}")

    def get_volunteer_sample(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a sample of volunteer records from Salesforce."""
        cache_key = self._get_cache_key("volunteer_sample", limit=limit)
        cached_sample = self._get_from_cache(cache_key)

        if cached_sample is not None:
            return cached_sample

        try:
            self._ensure_connection()
            self._rate_limit()

            # Query for volunteer sample - include fields needed for relationship validation
            query = f"""
                SELECT Id, FirstName, LastName, Email, Phone, MailingCity, MailingState,
                       Contact_Type__c, AccountId, npsp__Primary_Affiliation__c
                FROM Contact
                WHERE Contact_Type__c = 'Volunteer' OR Contact_Type__c = ''
                LIMIT {limit}
            """
            result = self.sf.query(query)
            records = result["records"]

            # Clean up records (remove Salesforce metadata)
            clean_records = []
            for record in records:
                clean_record = {
                    k: v for k, v in record.items() if not k.startswith("attributes")
                }
                clean_records.append(clean_record)

            self._set_cache(cache_key, clean_records, ttl=60)  # Shorter TTL for samples
            return clean_records

        except Exception as e:
            logger.error(f"Failed to get volunteer sample: {e}")
            raise SalesforceClientError(f"Failed to get volunteer sample: {e}")

    def get_organization_sample(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a sample of organization records from Salesforce."""
        cache_key = self._get_cache_key("organization_sample", limit=limit)
        cached_sample = self._get_from_cache(cache_key)

        if cached_sample is not None:
            return cached_sample

        try:
            self._ensure_connection()
            self._rate_limit()

            # Query for organization sample - include fields needed for relationship validation
            query = f"SELECT Id, Name, Type, BillingCity, BillingState, Phone, Website FROM Account WHERE Type NOT IN ('Household', 'School District', 'School') LIMIT {limit}"
            result = self.sf.query(query)
            records = result["records"]

            # Clean up records (remove Salesforce metadata)
            clean_records = []
            for record in records:
                clean_record = {
                    k: v for k, v in record.items() if not k.startswith("attributes")
                }
                clean_records.append(clean_record)

            self._set_cache(cache_key, clean_records, ttl=60)  # Shorter TTL for samples
            return clean_records

        except Exception as e:
            logger.error(f"Failed to get organization sample: {e}")
            raise SalesforceClientError(f"Failed to get organization sample: {e}")

    def get_event_sample(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a sample of event records from Salesforce."""
        cache_key = self._get_cache_key("event_sample", limit=limit)
        cached_sample = self._get_from_cache(cache_key)

        if cached_sample is not None:
            return cached_sample

        try:
            self._ensure_connection()
            self._rate_limit()

            # Query for event sample
            query = f"SELECT Id, Subject, StartDateTime, EndDateTime, Location, Description FROM Event LIMIT {limit}"
            result = self.sf.query(query)
            records = result["records"]

            # Clean up records (remove Salesforce metadata)
            clean_records = []
            for record in records:
                clean_record = {
                    k: v for k, v in record.items() if not k.startswith("attributes")
                }
                clean_records.append(clean_record)

            self._set_cache(cache_key, clean_records, ttl=60)  # Shorter TTL for samples
            return clean_records

        except Exception as e:
            logger.error(f"Failed to get event sample: {e}")
            raise SalesforceClientError(f"Failed to get event sample: {e}")

    def get_student_sample(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a sample of student records from Salesforce."""
        cache_key = self._get_cache_key("student_sample", limit=limit)
        cached_sample = self._get_from_cache(cache_key)

        if cached_sample is not None:
            return cached_sample

        try:
            self._ensure_connection()
            self._rate_limit()

            # Query for student sample
            query = f"SELECT Id, FirstName, LastName, Contact_Type__c, Email, Phone, MailingCity, MailingState FROM Contact WHERE Contact_Type__c = 'Student' LIMIT {limit}"
            result = self.sf.query(query)
            records = result["records"]

            # Clean up records (remove Salesforce metadata)
            clean_records = []
            for record in records:
                clean_record = {
                    k: v for k, v in record.items() if not k.startswith("attributes")
                }
                clean_records.append(clean_record)

            self._set_cache(cache_key, clean_records, ttl=60)  # Shorter TTL for samples
            return clean_records

        except Exception as e:
            logger.error(f"Failed to get student sample: {e}")
            raise SalesforceClientError(f"Failed to get student sample: {e}")

    def get_teacher_sample(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a sample of teacher records from Salesforce."""
        cache_key = self._get_cache_key("teacher_sample", limit=limit)
        cached_sample = self._get_from_cache(cache_key)

        if cached_sample is not None:
            return cached_sample

        try:
            self._ensure_connection()
            self._rate_limit()

            # Query for teacher sample
            query = f"SELECT Id, FirstName, LastName, Contact_Type__c, Title, Email, Phone, MailingCity, MailingState FROM Contact WHERE Contact_Type__c = 'Teacher' LIMIT {limit}"
            result = self.sf.query(query)
            records = result["records"]

            # Clean up records (remove Salesforce metadata)
            clean_records = []
            for record in records:
                clean_record = {
                    k: v for k, v in record.items() if not k.startswith("attributes")
                }
                clean_records.append(clean_record)

            self._set_cache(cache_key, clean_records, ttl=60)  # Shorter TTL for samples
            return clean_records

        except Exception as e:
            logger.error(f"Failed to get teacher sample: {e}")
            raise SalesforceClientError(f"Failed to get teacher sample: {e}")

    def get_health_status(self) -> Dict[str, Any]:
        """Get the health status of the Salesforce connection."""
        status = {
            "connected": False,
            "redis_available": REDIS_AVAILABLE and self.redis_client is not None,
            "salesforce_available": SALESFORCE_AVAILABLE,
            "connection_attempts": self._connection_attempts,
            "last_connection_attempt": (
                self._last_connection_attempt.isoformat()
                if self._last_connection_attempt
                else None
            ),
            "errors": [],
        }

        try:
            if self.sf:
                # Test connection
                self.sf.describe()
                status["connected"] = True
                status["errors"] = []
            else:
                status["errors"].append("No Salesforce connection established")

        except Exception as e:
            status["errors"].append(str(e))

        return status

    def clear_cache(self, pattern: str = "sf:*"):
        """Clear cached data matching the given pattern."""
        if not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache keys matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.warning(f"Cache clearing failed: {e}")
            return 0

    def close(self):
        """Close the Salesforce connection and cleanup resources."""
        if self.sf:
            try:
                self.sf.close()
                logger.info("Salesforce connection closed")
            except Exception as e:
                logger.warning(f"Error closing Salesforce connection: {e}")

        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")


# Convenience functions for quick access
def get_salesforce_client() -> SalesforceClient:
    """Get a configured Salesforce client instance."""
    return SalesforceClient()


def get_entity_count(entity_type: str) -> int:
    """Get the count for a specific entity type."""
    client = get_salesforce_client()

    count_methods = {
        "volunteer": client.get_volunteer_count,
        "organization": client.get_organization_count,
        "event": client.get_event_count,
        "student": client.get_student_count,
        "teacher": client.get_teacher_count,
    }

    if entity_type not in count_methods:
        raise ValueError(f"Unsupported entity type: {entity_type}")

    try:
        return count_methods[entity_type]()
    finally:
        client.close()
