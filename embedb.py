import sqlite3
import json
from helper import generate, gen_embed
from pydantic_core import from_json


conn = sqlite3.connect('data_classification.db', check_same_thread=False)
c = conn.cursor()


c.execute('''
CREATE TABLE IF NOT EXISTS RAG_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    class TEXT,
    structure TEXT,
    summary TEXT,
    embedding TEXT
)
''')
conn.commit()


def clear_database():
    """Clears all entries from the database."""
    try:
        c.execute('DELETE FROM RAG_data')
        
        c.execute('DELETE FROM sqlite_sequence WHERE name="RAG_data"')
        conn.commit()
        return True
    except Exception as e:
        print(f"Error clearing database: {e}")
        return False


classes = [
    "SurveillanceLog",
    "CommunicationMessage",
    "StrategicMaritimeZone",
    "StrategicChokepointAndSurveillanceArea",
    "NavalSpecialOperationsExerciseArea",
    "NavalOperationZone",
    "NavalMineWarfareExerciseArea",
    "MaritimeInterdictionOperationExerciseArea",
    "AntiSubmarineWarfareExerciseArea",
    "AmphibiousOperationExerciseArea",
    "NavalAirPatrolZone",
    "NavalAirDefenseExerciseArea",
]

def classify_text(text):
    """Classifies the text into predefined classes."""
    prompt = f"""
    Given text containing multiple data structures, your task is to extract and classify them according to provided categories.

Important guidelines:
1. Process each structure independently and classify it into the provided categories
2. Extract ALL fields exactly as they appear, with no modifications
3. Return ONLY the complete JSON array containing all structures
4. Maintain proper JSON formatting 
5. Preserve exact field names and values as they appear in the source
6. Do not include ANY TEXT before or after the JSON
7. Output must be valid, parseable JSON
8. Do not add comments or descriptions
9. Each structure should be represented as an object with two fields:
  - "class": The category from the provided list
  - "structure": Complete JSON object containing all original fields

You are given:
1. Text containing one or more data structures:
{text}

2. List of valid classification categories:
{classes}

Example input:

1. Date: 2024-10-20
  Time: 14:30 UTC  
  Location: Patrol Vessel Alpha
  Report: Cargo vessel "Pacific Trader" observed at 13°15'N, 71°30'W. Heading 045°, speed 12 knots. IMO number 9876543. No suspicious activity.

2. FROM: DEEP-SEA MINING VESSEL TANGO
  TO: INTERNATIONAL SEABED AUTHORITY
  PRIORITY: URGENT
  DTG: 250930Z OCT 24
  1. ENCOUNTERED UNEXPECTED GEOLOGICAL FORMATION AT MINING SITE.
  2. LOCATION: 12°50'N, 71°40'W, DEPTH 4500 METERS.
  3. INITIAL SCANS INDICATE PRESENCE OF UNKNOWN CRYSTALLINE STRUCTURES.
  4. UNUSUAL ELECTROMAGNETIC READINGS EMANATING FROM FORMATION.
  5. REQUEST IMMEDIATE CONSULTATION WITH GEOLOGY EXPERTS AND POSSIBLE SUSPENSION OF MINING ACTIVITIES.

Example output:
{"""
[
   {
       "class": "SurveillanceLog",
       "structure": {
           "Date": "2024-10-20",
           "Time": "14:30 UTC",
           "Location": "Patrol Vessel Alpha", 
           "Report": "Cargo vessel 'Pacific Trader' observed at 13°15'N, 71°30'W. Heading 045°, speed 12 knots. IMO number 9876543. No suspicious activity."
       }
   },
   {
       "class": "CommunicationMessage",
       "structure": {
           "FROM": "DEEP-SEA MINING VESSEL TANGO",
           "TO": "INTERNATIONAL SEABED AUTHORITY",
           "PRIORITY": "URGENT",
           "DTG": "250930Z OCT 24",
           "1": "ENCOUNTERED UNEXPECTED GEOLOGICAL FORMATION AT MINING SITE.",
           "2": "LOCATION: 12°50'N, 71°40'W, DEPTH 4500 METERS.",
           "3": "INITIAL SCANS INDICATE PRESENCE OF UNKNOWN CRYSTALLINE STRUCTURES.",
           "4": "UNUSUAL ELECTROMAGNETIC READINGS EMANATING FROM FORMATION.", 
           "5": "REQUEST IMMEDIATE CONSULTATION WITH GEOLOGY EXPERTS AND POSSIBLE SUSPENSION OF MINING ACTIVITIES."
       }
   }
]
"""
    }
    """
    return generate(prompt)


def summarise(text):
    """Summarises the text using an AI model."""
    prompt = f"""
    Given a piece of text, your task is to generate a comprehensive summary of the content.

Important guidelines:
1. Summarize the text in a clear and concise manner
2. Include all key points and important details
3. Maintain the original context and meaning
4. Do not include any irrelevant information
5. The summary should be coherent and well-structured
6. The output should be a single paragraph
7. Do not include any text before or after the summary

You are given:
{text}
"""
    return generate(prompt)


def add_to_database(text):
    """Adds the extracted text to the database."""
    output = classify_text(text)
    output = output.split("[", 1)[1]
    output = f"[{output}"
    
    try:
        output = json.loads(output)
    except Exception as e:
        print("Error parsing JSON:", e)
        try:
            output = from_json(output, allow_partial=True)
        except Exception as e:
            print("Error parsing Pydantic JSON:", e)

    for entry in output:
        entry["summary"] = summarise(json.dumps(entry["structure"]))
        entry["embedding"] = gen_embed(entry["summary"])

        
        c.execute('''
            INSERT INTO RAG_data (text, class, structure, summary, embedding)
            VALUES (?, ?, ?, ?, ?)
        ''', (text, entry["class"], json.dumps(entry["structure"]), entry["summary"], json.dumps(entry["embedding"])))
        conn.commit()


def get_data():
    """Returns the entire database content."""
    c.execute("SELECT * FROM RAG_data")
    rows = c.fetchall()
    formatted_rows = []
    for row in rows:
        formatted_row = {
            "id": row[0],
            "text": row[1],
            "class": row[2],
            "structure": json.loads(row[3]),
            "summary": row[4],
            "embedding": json.loads(row[5])
        }
        formatted_rows.append(formatted_row)
    return formatted_rows


def update_database_entry(index, new_text):
    """Updates an entry in the database."""
    output = classify_text(new_text)
    output = output.split("[", 1)[1]
    output = f"[{output}]"
    
    try:
        output = json.loads(output)
    except Exception as e:
        print("Error parsing JSON:", e)
        try:
            output = from_json(output, allow_partial=True)
        except Exception as e:
            print("Error parsing Pydantic JSON:", e)

    for entry in output:
        entry["summary"] = summarise(json.dumps(entry["structure"]))
        entry["embedding"] = gen_embed(entry["summary"])

        
        c.execute('''
            UPDATE RAG_data
            SET text = ?, class = ?, structure = ?, summary = ?, embedding = ?
            WHERE id = ?
        ''', (new_text, entry["class"], json.dumps(entry["structure"]), entry["summary"], entry["embedding"], index))
        conn.commit()


def delete_database_entry(index):
    """Deletes an entry from the database."""
    c.execute('DELETE FROM RAG_data WHERE id = ?', (index,))
    conn.commit()