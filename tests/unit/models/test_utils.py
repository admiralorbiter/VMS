from datetime import datetime, timezone

from models.utils import get_utc_now


def test_get_utc_now():
    """Test the get_utc_now utility function"""
    # Test that the function returns a datetime object
    result = get_utc_now()
    assert isinstance(result, datetime)

    # Test that the datetime has timezone info
    assert result.tzinfo is not None

    # Test that it's in UTC timezone
    assert result.tzinfo == timezone.utc

    # Test that the time is recent (within last 5 seconds)
    now = datetime.now(timezone.utc)
    time_diff = abs((now - result).total_seconds())
    assert time_diff < 5, f"Time difference too large: {time_diff} seconds"


def test_get_utc_now_consistency():
    """Test that get_utc_now returns consistent UTC times"""
    result1 = get_utc_now()
    result2 = get_utc_now()

    # Both should be datetime objects with UTC timezone
    assert isinstance(result1, datetime)
    assert isinstance(result2, datetime)
    assert result1.tzinfo == timezone.utc
    assert result2.tzinfo == timezone.utc

    # Second call should be later than or equal to first call
    assert result2 >= result1


def test_get_utc_now_timezone_awareness():
    """Test that get_utc_now always returns timezone-aware datetime"""
    result = get_utc_now()

    # Should not be naive datetime
    assert result.tzinfo is not None

    # Should be UTC timezone
    assert result.tzinfo == timezone.utc

    # Should be able to convert to other timezones
    from datetime import timedelta

    eastern = timezone(timedelta(hours=-5))
    eastern_time = result.astimezone(eastern)
    assert eastern_time.tzinfo == eastern
