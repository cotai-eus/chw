"""
Date and time utilities for the application.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, List
import pytz
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta


class DateTimeUtils:
    """Utility class for date and time operations."""
    
    @staticmethod
    def now_utc() -> datetime:
        """Get current UTC datetime."""
        return datetime.now(timezone.utc)
    
    @staticmethod
    def now_local(tz: str = 'UTC') -> datetime:
        """Get current datetime in specified timezone."""
        timezone_obj = pytz.timezone(tz)
        return datetime.now(timezone_obj)
    
    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        """Convert datetime to UTC."""
        if dt.tzinfo is None:
            # Assume naive datetime is UTC
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    
    @staticmethod
    def to_timezone(dt: datetime, tz: str) -> datetime:
        """Convert datetime to specified timezone."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        target_tz = pytz.timezone(tz)
        return dt.astimezone(target_tz)
    
    @staticmethod
    def parse_datetime(
        date_string: str,
        default_tz: str = 'UTC'
    ) -> Optional[datetime]:
        """Parse datetime string with timezone handling."""
        try:
            dt = parse_date(date_string)
            
            # If no timezone info, assume default timezone
            if dt.tzinfo is None:
                default_timezone = pytz.timezone(default_tz)
                dt = default_timezone.localize(dt)
            
            return dt
        except Exception:
            return None
    
    @staticmethod
    def format_datetime(
        dt: datetime,
        format_string: str = '%Y-%m-%d %H:%M:%S',
        tz: Optional[str] = None
    ) -> str:
        """Format datetime with optional timezone conversion."""
        if tz:
            dt = DateTimeUtils.to_timezone(dt, tz)
        
        return dt.strftime(format_string)
    
    @staticmethod
    def add_business_days(dt: datetime, days: int) -> datetime:
        """Add business days to datetime (excluding weekends)."""
        current_date = dt.date()
        
        while days > 0:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                days -= 1
        
        return datetime.combine(current_date, dt.time(), dt.tzinfo)
    
    @staticmethod
    def get_business_days_between(start: datetime, end: datetime) -> int:
        """Get number of business days between two dates."""
        start_date = start.date()
        end_date = end.date()
        
        business_days = 0
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                business_days += 1
            current_date += timedelta(days=1)
        
        return business_days
    
    @staticmethod
    def is_business_day(dt: datetime) -> bool:
        """Check if datetime falls on a business day."""
        return dt.weekday() < 5
    
    @staticmethod
    def get_next_business_day(dt: datetime) -> datetime:
        """Get next business day."""
        next_day = dt + timedelta(days=1)
        
        while next_day.weekday() >= 5:  # Saturday = 5, Sunday = 6
            next_day += timedelta(days=1)
        
        return next_day
    
    @staticmethod
    def get_previous_business_day(dt: datetime) -> datetime:
        """Get previous business day."""
        prev_day = dt - timedelta(days=1)
        
        while prev_day.weekday() >= 5:  # Saturday = 5, Sunday = 6
            prev_day -= timedelta(days=1)
        
        return prev_day
    
    @staticmethod
    def get_date_range(
        start: datetime,
        end: datetime,
        step: timedelta = timedelta(days=1)
    ) -> List[datetime]:
        """Get list of dates in range."""
        dates = []
        current = start
        
        while current <= end:
            dates.append(current)
            current += step
        
        return dates
    
    @staticmethod
    def get_week_start(dt: datetime) -> datetime:
        """Get start of week (Monday) for given datetime."""
        days_since_monday = dt.weekday()
        return dt - timedelta(days=days_since_monday)
    
    @staticmethod
    def get_week_end(dt: datetime) -> datetime:
        """Get end of week (Sunday) for given datetime."""
        days_until_sunday = 6 - dt.weekday()
        return dt + timedelta(days=days_until_sunday)
    
    @staticmethod
    def get_month_start(dt: datetime) -> datetime:
        """Get start of month for given datetime."""
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def get_month_end(dt: datetime) -> datetime:
        """Get end of month for given datetime."""
        next_month = dt + relativedelta(months=1)
        return next_month.replace(day=1) - timedelta(microseconds=1)
    
    @staticmethod
    def get_quarter_start(dt: datetime) -> datetime:
        """Get start of quarter for given datetime."""
        quarter = (dt.month - 1) // 3
        start_month = quarter * 3 + 1
        return dt.replace(month=start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def get_quarter_end(dt: datetime) -> datetime:
        """Get end of quarter for given datetime."""
        quarter = (dt.month - 1) // 3
        end_month = quarter * 3 + 3
        end_date = dt.replace(month=end_month)
        return DateTimeUtils.get_month_end(end_date)
    
    @staticmethod
    def get_year_start(dt: datetime) -> datetime:
        """Get start of year for given datetime."""
        return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def get_year_end(dt: datetime) -> datetime:
        """Get end of year for given datetime."""
        return dt.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
    
    @staticmethod
    def time_ago(dt: datetime, now: Optional[datetime] = None) -> str:
        """Get human-readable time difference."""
        if now is None:
            now = DateTimeUtils.now_utc()
        
        # Ensure both datetimes are timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        
        diff = now - dt
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years != 1 else ''} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    @staticmethod
    def time_until(dt: datetime, now: Optional[datetime] = None) -> str:
        """Get human-readable time until future date."""
        if now is None:
            now = DateTimeUtils.now_utc()
        
        # Ensure both datetimes are timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        
        if dt <= now:
            return "Past due"
        
        diff = dt - now
        
        if diff.days > 365:
            years = diff.days // 365
            return f"In {years} year{'s' if years != 1 else ''}"
        elif diff.days > 30:
            months = diff.days // 30
            return f"In {months} month{'s' if months != 1 else ''}"
        elif diff.days > 0:
            return f"In {diff.days} day{'s' if diff.days != 1 else ''}"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"In {hours} hour{'s' if hours != 1 else ''}"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"In {minutes} minute{'s' if minutes != 1 else ''}"
        else:
            return "Very soon"
    
    @staticmethod
    def is_weekend(dt: datetime) -> bool:
        """Check if datetime falls on weekend."""
        return dt.weekday() >= 5
    
    @staticmethod
    def get_age_in_years(birth_date: datetime, reference_date: Optional[datetime] = None) -> int:
        """Calculate age in years."""
        if reference_date is None:
            reference_date = DateTimeUtils.now_utc()
        
        age = reference_date.year - birth_date.year
        
        # Adjust if birthday hasn't occurred this year
        if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
            age -= 1
        
        return age
    
    @staticmethod
    def get_common_timezones() -> List[str]:
        """Get list of common timezones."""
        return [
            'UTC',
            'US/Eastern',
            'US/Central',
            'US/Mountain',
            'US/Pacific',
            'Europe/London',
            'Europe/Paris',
            'Europe/Berlin',
            'Asia/Tokyo',
            'Asia/Shanghai',
            'Asia/Kolkata',
            'Australia/Sydney',
            'America/New_York',
            'America/Chicago',
            'America/Denver',
            'America/Los_Angeles',
            'America/Sao_Paulo',
            'Africa/Cairo',
        ]
    
    @staticmethod
    def validate_timezone(tz: str) -> bool:
        """Validate if timezone string is valid."""
        try:
            pytz.timezone(tz)
            return True
        except pytz.exceptions.UnknownTimeZoneError:
            return False


class WorkingHoursUtils:
    """Utilities for working with business hours."""
    
    def __init__(
        self,
        start_hour: int = 9,
        end_hour: int = 17,
        working_days: List[int] = None,
        timezone: str = 'UTC'
    ):
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.working_days = working_days or [0, 1, 2, 3, 4]  # Mon-Fri
        self.timezone = timezone
    
    def is_working_hours(self, dt: datetime) -> bool:
        """Check if datetime is within working hours."""
        # Convert to business timezone
        local_dt = DateTimeUtils.to_timezone(dt, self.timezone)
        
        # Check day of week
        if local_dt.weekday() not in self.working_days:
            return False
        
        # Check hour
        return self.start_hour <= local_dt.hour < self.end_hour
    
    def get_next_working_time(self, dt: datetime) -> datetime:
        """Get next working time after given datetime."""
        current = DateTimeUtils.to_timezone(dt, self.timezone)
        
        while True:
            # If it's a working day
            if current.weekday() in self.working_days:
                # If before working hours, move to start of working day
                if current.hour < self.start_hour:
                    current = current.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
                    break
                # If during working hours, it's already working time
                elif current.hour < self.end_hour:
                    break
            
            # Move to next day at start of working hours
            current = current + timedelta(days=1)
            current = current.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
        
        return DateTimeUtils.to_utc(current)
    
    def add_working_hours(self, dt: datetime, hours: float) -> datetime:
        """Add working hours to datetime."""
        current = DateTimeUtils.to_timezone(dt, self.timezone)
        remaining_hours = hours
        
        while remaining_hours > 0:
            if self.is_working_hours(current):
                # Calculate hours until end of working day
                hours_until_end = self.end_hour - current.hour - current.minute / 60
                
                if remaining_hours <= hours_until_end:
                    # Can finish within this working day
                    total_minutes = current.minute + remaining_hours * 60
                    hours_to_add = int(total_minutes // 60)
                    minutes_to_add = int(total_minutes % 60)
                    
                    current = current + timedelta(hours=hours_to_add, minutes=minutes_to_add)
                    break
                else:
                    # Move to next working day
                    remaining_hours -= hours_until_end
                    current = current + timedelta(days=1)
                    current = current.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)
                    
                    # Skip non-working days
                    while current.weekday() not in self.working_days:
                        current = current + timedelta(days=1)
            else:
                # Move to next working time
                current = self.get_next_working_time(current)
        
        return DateTimeUtils.to_utc(current)
