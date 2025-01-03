import sqlite3
import json
import re
from typing import Dict, Any, Tuple, List
from groq import Groq
from dotenv import load_dotenv
import os
import logging
import datetime
from datetime import datetime
import traceback
from embedb import add_to_database as add_to_embedb


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


TABLE_DEFINITIONS = {
    "SurveillanceLog": """
        CREATE TABLE IF NOT EXISTS SurveillanceLog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            location TEXT,
            coordinates TEXT,
            heading TEXT,
            speed TEXT,
            report TEXT,
            utc_offset TEXT
        )
    """,
    "CommunicationMessage": """
        CREATE TABLE IF NOT EXISTS CommunicationMessage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            priority TEXT,
            dtg TEXT,
            message TEXT
        )
    """,
    "ReconnaissanceNotes": """
        CREATE TABLE IF NOT EXISTS ReconnaissanceNotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            location TEXT,
            details TEXT
        )
    """,
    "Zones": """
        CREATE TABLE IF NOT EXISTS Zones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            significance TEXT,
            coordinates TEXT
        )
    """
}


try:
    client = Groq(api_key=os.getenv("GROQ_API"))
    if not os.getenv("GROQ_API"):
        raise ValueError("GROQ_API environment variable not found")
except Exception as e:
    logger.error(f"Failed to initialize Groq client: {e}")
    raise

class DatabaseConnection:
    def __init__(self, db_path='data_classification.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def __enter__(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            return self
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()

def split_entries(text: str) -> List[str]:
    """
    Split multiple entries in the text into individual entries with improved handling.
    """
    
    entries = re.split(r'```\s*|\s*```', text)
    entries = [entry.strip() for entry in entries if entry.strip()]
    
    if not entries:
        
        date_patterns = [
            r'(?=\d{6}Z\s+[A-Z]{3}\s+\d{2})',  
            r'(?=\w{3}\s+\d{1,2},?\s+\d{4})',   
            r'(?=\d{4}-\d{2}-\d{2})',           
            r'(?=ENTRY\s+\d+[:.])',             
            r'(?=\d+\.\s+)'                     
        ]
        
        
        for pattern in date_patterns:
            potential_entries = re.split(pattern, text)
            cleaned_entries = [entry.strip() for entry in potential_entries if entry.strip()]
            if len(cleaned_entries) > 1:  
                entries = cleaned_entries
                break
        
        
        if not entries:
            entries = [e.strip() for e in text.split('\n\n') if e.strip()]
    
    return entries

def validate_entry(entry: Dict[str, Any], entry_type: str) -> bool:
    """
    Validate entry data before database insertion.
    """
    required_fields = {
        "surveillance": ["date", "time", "location", "coordinates", "report"],
        "message": ["sender", "receiver", "priority", "dtg", "message"],
        "reconnaissance": ["date", "location", "details"],
        "zone": ["name", "type", "significance", "coordinates"]
    }
    
    
    fields = required_fields.get(entry_type, [])
    is_valid = all(key in entry and entry[key] for key in fields)
    
    if not is_valid:
        missing = [f for f in fields if f not in entry or not entry[f]]
        logger.warning(f"Invalid {entry_type} entry. Missing or empty fields: {missing}")
        
    return is_valid

def clean_text(text: str) -> str:
    """Clean and standardize input text."""
    text = re.sub(r'\s+', ' ', text.strip())
    text = ''.join(char for char in text if char.isprintable())
    return text

def parse_date_time(date_str: str) -> Tuple[str, str]:
    """Parse date and time from various formats."""
    try:
        
        patterns = [
            r'(\w{3}\s+\d{1,2},?\s+\d{4})\s*-?\s*(\d{1,2}:\d{2})',  
            r'(\d{4}-\d{2}-\d{2})\s*[T\s](\d{2}:\d{2})',            
            r'(\d{2}/\d{2}/\d{4})\s*[T\s](\d{2}:\d{2})'             
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                date_part, time_part = match.groups()
                
                parsed_date = datetime.strptime(date_part, "%b %d, %Y").strftime("%Y-%m-%d")
                return parsed_date, time_part
                
        return "", ""
    except Exception as e:
        logger.error(f"Error parsing date/time: {e}")
        return "", ""

def extract_coordinates(text: str) -> str:
    """Extract coordinates from text."""
    coord_pattern = r'(\d{1,2})°(\d{1,2})\'[NS],\s*(\d{1,2})°(\d{1,2})\'[WE]'
    match = re.search(coord_pattern, text)
    if match:
        return f"{match.group(0)}"
    return ""

def create_extraction_prompt(text: str, data_type: str) -> str:
    """Creates a prompt for data extraction."""
    base_prompt = """
    Extract information from the following text and return ONLY a JSON object.
    - Return ONLY the JSON object with no additional text or explanation
    - If a field is missing, use null or empty string
    - Use exactly the field names specified
    - Format dates as YYYY-MM-DD
    - Format times as HH:MM
    """
    
    prompts = {
        "surveillance": f"""{base_prompt}
        Required JSON format:
        {{
            "date": "YYYY-MM-DD",
            "time": "HH:MM",
            "location": "station or vessel name",
            "coordinates": "coordinate string (e.g. 12°34'N, 56°78'W)",
            "heading": "heading in degrees (e.g. 045°)",
            "speed": "speed in knots",
            "report": "main content",
            "utc_offset": "UTC"
        }}
        Text: {clean_text(text)}
        """,
        
        "message": f"""{base_prompt}
        Required JSON format:
        {{
            "sender": "sender name/id",
            "receiver": "receiver name/id",
            "priority": "priority level",
            "dtg": "date-time group",
            "message": "message content"
        }}
        Text: {clean_text(text)}
        """,
        
        "reconnaissance": f"""{base_prompt}
        Required JSON format:
        {{
            "date": "YYYY-MM-DD",
            "location": "location string",
            "details": "reconnaissance details"
        }}
        Text: {clean_text(text)}
        """,
        
        "zone": f"""{base_prompt}
        Required JSON format:
        {{
            "name": "zone name",
            "type": "zone type",
            "significance": "strategic details",
            "coordinates": "coordinate string"
        }}
        Text: {clean_text(text)}
        """
    }
    
    return prompts.get(data_type, "")

def generate(prompt: str, max_retries: int = 2) -> str:
    """Generate response with retry logic."""
    for attempt in range(max_retries):
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-70b-8192",
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Failed to generate response after {max_retries} attempts: {e}")
            logger.warning(f"Attempt {attempt + 1} failed, retrying...")
            continue

def process_surveillance_entry(entry: str) -> Dict[str, str]:
    """Process a single surveillance entry with enhanced field support."""
    try:
        
        date_str = re.search(r'\w{3}\s+\d{1,2},?\s+\d{4}', entry)
        time_str = re.search(r'(\d{1,2}:\d{2})', entry)
        
        date = datetime.strptime(date_str.group(), "%b %d, %Y").strftime("%Y-%m-%d") if date_str else ""
        time = time_str.group(1) if time_str else ""
        
        
        coord_pattern = r'(\d{1,2}°\d{1,2}\'[NS],\s*\d{1,2}°\d{1,2}\'[WE])'
        coordinates = re.search(coord_pattern, entry)
        coordinates = coordinates.group(1) if coordinates else ""
        
        
        location_pattern = r'(?:Station|Vessel|Platform)\s+[A-Za-z0-9\s]+|[A-Z][A-Za-z\s]+\b(?=\s+reporting)'
        location = re.search(location_pattern, entry)
        location = location.group() if location else ""
        
        
        heading_pattern = r'heading\s+(\d{1,3}°)|(\d{1,3}°)\s+true'
        heading = re.search(heading_pattern, entry, re.IGNORECASE)
        heading = heading.group(1) or heading.group(2) if heading else None
        
        
        speed_pattern = r'(\d+(?:\.\d+)?)\s*(?:knots?|kts?)'
        speed = re.search(speed_pattern, entry, re.IGNORECASE)
        speed = f"{float(speed.group(1)):.1f} knots" if speed else None
        
        
        report = entry
        
        report = re.sub(r'\w{3}\s+\d{1,2},?\s+\d{4}\s*-?\s*\d{1,2}:\d{2}\s*(?:UTC|local)?', '', report)
        
        report = re.sub(coord_pattern, '', report)
        
        report = re.sub(heading_pattern, '', report, flags=re.IGNORECASE)
        
        report = re.sub(speed_pattern, '', report, flags=re.IGNORECASE)
        report = clean_text(report)
        
        return {
            "date": date,
            "time": time,
            "location": location,
            "coordinates": coordinates,
            "heading": heading,
            "speed": speed,
            "report": report,
            "utc_offset": "UTC"  
        }
    except Exception as e:
        logger.error(f"Error processing surveillance entry: {e}")
        return {
            "date": "", 
            "time": "", 
            "location": "", 
            "coordinates": "",
            "heading": None,
            "speed": None,
            "report": entry,
            "utc_offset": "UTC"
        }
    
def process_entry_with_llm(entry: str, entry_type: str) -> Dict[str, Any]:
    """
    Use LLM to extract structured data from entry text.
    """
    try:
        prompt = create_extraction_prompt(entry, entry_type)
        response = generate(prompt)
        
        
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response as JSON: {response}")
            return None
            
        
        if validate_entry(data, entry_type):
            return data
        return None
        
    except Exception as e:
        logger.error(f"Error in LLM processing: {str(e)}")
        return None

def add_to_database(text: str, classifications: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Enhanced database addition with improved error handling and validation.
    """
    logger.info("Starting database upload process")
    logger.info(f"Classifications: {json.dumps(classifications, indent=2)}")
    add_to_embedb(text)
    
    try:
        
        entries = split_entries(text)
        logger.info(f"Found {len(entries)} entries to process")
        
        successful_entries = 0
        failed_entries = 0
        errors = []
        
        with DatabaseConnection() as db:
            for idx, entry in enumerate(entries, 1):
                try:
                    logger.info(f"Processing entry {idx}/{len(entries)}")
                    
                    for class_type in classifications['class_types']:
                        
                        type_mapping = {
                            "Surveillance": ("surveillance", process_surveillance_entry),
                            "Message": ("message", process_message_entry),
                            "Reconnaissance": ("reconnaissance", process_reconnaissance_entry),
                            "ZonalArea": ("zone", process_zone_entry)
                        }
                        
                        if class_type in type_mapping:
                            entry_type, process_func = type_mapping[class_type]
                            
                            
                            data = process_func(entry)
                            
                            
                            if not validate_entry(data, entry_type):
                                logger.info(f"Attempting LLM processing for entry {idx}")
                                data = process_entry_with_llm(entry, entry_type)
                            
                            if data and validate_entry(data, entry_type):
                                
                                if class_type == "Surveillance":
                                    db.cursor.execute('''
                                        INSERT INTO SurveillanceLog 
                                        (date, time, location, coordinates, heading, speed, report, utc_offset)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (data['date'], data['time'], data['location'], data['coordinates'],
                                        data['heading'], data['speed'], data['report'], data['utc_offset']))
                                    
                                elif class_type == "Message":
                                    db.cursor.execute('''
                                        INSERT INTO CommunicationMessage 
                                        (sender, receiver, priority, dtg, message)
                                        VALUES (?, ?, ?, ?, ?)
                                    ''', (data['sender'], data['receiver'], data['priority'],
                                         data['dtg'], data['message']))
                                    
                                elif class_type == "Reconnaissance":
                                    db.cursor.execute('''
                                        INSERT INTO ReconnaissanceNotes (date, location, details)
                                        VALUES (?, ?, ?)
                                    ''', (data['date'], data['location'], data['details']))
                                    
                                elif class_type == "ZonalArea":
                                    db.cursor.execute('''
                                        INSERT INTO Zones (name, type, significance, coordinates)
                                        VALUES (?, ?, ?, ?)
                                    ''', (data['name'], data['type'], data['significance'],
                                         json.dumps(data['coordinates'])))
                                
                                successful_entries += 1
                                logger.info(f"Successfully processed entry {idx}")
                            else:
                                raise ValueError(f"Failed to extract valid data for entry {idx}")
                                
                except Exception as e:
                    error_msg = f"Error processing entry {idx}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    failed_entries += 1
                    continue
        
        
        status_message = (
            f"Processing complete:\n"
            f"- Successfully processed: {successful_entries} entries\n"
            f"- Failed: {failed_entries} entries\n"
            f"- Total entries: {len(entries)}\n"
            f"\nErrors encountered:\n" + "\n".join(errors) if errors else ""
        )
        
        logger.info(status_message)
        return successful_entries > 0, status_message
        
    except Exception as e:
        error_msg = f"Database error: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, error_msg

def process_message_entry(entry: str) -> Dict[str, str]:
    """Process a single message entry."""
    try:
        
        dtg_pattern = r'\d{6}Z\s+[A-Z]{3}\s+\d{2}'  
        dtg = re.search(dtg_pattern, entry)
        dtg = dtg.group() if dtg else ""
        
        
        priority_patterns = ['FLASH', 'IMMEDIATE', 'PRIORITY', 'ROUTINE']
        priority = next((p for p in priority_patterns if p in entry.upper()), "")
        
        
        sender_pattern = r'FROM:\s*([^\n]+)'
        receiver_pattern = r'TO:\s*([^\n]+)'
        
        sender = re.search(sender_pattern, entry)
        receiver = re.search(receiver_pattern, entry)
        
        sender = sender.group(1) if sender else ""
        receiver = receiver.group(1) if receiver else ""
        
        
        message = re.sub(r'^.*?(?=\n[A-Z]+:)', '', entry, flags=re.DOTALL)
        message = clean_text(message)
        
        return {
            "sender": sender,
            "receiver": receiver,
            "priority": priority,
            "dtg": dtg,
            "message": message
        }
    except Exception as e:
        logger.error(f"Error processing message entry: {e}")
        return {"sender": "", "receiver": "", "priority": "", "dtg": "", "message": entry}

def process_reconnaissance_entry(entry: str) -> Dict[str, str]:
    """Process a single reconnaissance entry."""
    try:
        
        date_str = re.search(r'\w{3}\s+\d{1,2},?\s+\d{4}', entry)
        date = datetime.strptime(date_str.group(), "%b %d, %Y").strftime("%Y-%m-%d") if date_str else ""
        
        
        location = extract_coordinates(entry)
        
        
        details = re.sub(r'\w{3}\s+\d{1,2},?\s+\d{4}\s*-?\s*\d{1,2}:\d{2}\s*local', '', entry)
        details = clean_text(details)
        
        return {
            "date": date,
            "location": location,
            "details": details
        }
    except Exception as e:
        logger.error(f"Error processing reconnaissance entry: {e}")
        return {"date": "", "location": "", "details": entry}

def process_zone_entry(entry: str) -> Dict[str, Any]:
    """Process a single zone entry."""
    try:
        
        name_match = re.search(r'Zone Name:\s*([^\n]+)', entry) or re.search(r'^([^\n]+)', entry)
        name = name_match.group(1) if name_match else ""
        
        
        type_match = re.search(r'Type:\s*([^\n]+)', entry)
        zone_type = type_match.group(1) if type_match else ""
        
        
        sig_match = re.search(r'Significance:\s*([^\n]+)', entry) or \
                   re.search(r'Description:\s*([^\n]+)', entry)
        significance = sig_match.group(1) if sig_match else ""
        
        
        coordinates = extract_coordinates(entry)
        
        return {
            "name": clean_text(name),
            "type": clean_text(zone_type),
            "significance": clean_text(significance),
            "coordinates": coordinates
        }
    except Exception as e:
        logger.error(f"Error processing zone entry: {e}")
        return {"name": "", "type": "", "significance": "", "coordinates": ""}

def init_database():
    """Initialize database tables with error handling"""
    try:
        with DatabaseConnection() as db:
            for table_name, table_definition in TABLE_DEFINITIONS.items():
                logger.info(f"Creating/verifying table: {table_name}")
                db.cursor.execute(table_definition)
            logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


try:
    init_database()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    raise