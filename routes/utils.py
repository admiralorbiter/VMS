from datetime import datetime

def parse_date(date_str):
    """Parse date string from Salesforce CSV or API"""
    if not date_str:
        return None
    
    try:
        # First try parsing ISO 8601 format (from Salesforce API)
        # Example: 2025-03-05T14:15:00.000+0000
        if 'T' in date_str:
            return datetime.strptime(date_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
            
        # Try CSV format with time (YYYY-MM-DD HH:MM:SS)
        try:
            parsed_date = datetime.strptime(date_str.strip(), '%Y-%m-%d %H:%M:%S')
            return parsed_date
        except ValueError:
            # If that fails, try without seconds (YYYY-MM-DD HH:MM)
            try:
                parsed_date = datetime.strptime(date_str.strip(), '%Y-%m-%d %H:%M')
                return parsed_date
            except ValueError:
                # Fallback for dates without times
                try:
                    return datetime.strptime(date_str.strip(), '%Y-%m-%d')
                except ValueError:
                    return None
    except Exception as e:
        print(f"Error parsing date {date_str}: {str(e)}")  # Debug logging
        return None