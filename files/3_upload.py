import streamlit as st
from ocr import extract_text_from_file
from data import add_to_database
import logging
import json
from typing import Dict, Any
import traceback


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def handle_file_upload(uploaded_file, classifications: Dict[str, Any]):
    """Handle single file upload with detailed error reporting"""
    try:
        logger.info(f"Processing file: {uploaded_file.name}")
        extracted_text = extract_text_from_file(uploaded_file)
        
        if not extracted_text:
            raise ValueError("No text extracted from file")
            
        success, message = add_to_database(
            text=extracted_text,
            classifications=classifications
        )
        
        return {
            "filename": uploaded_file.name,
            "success": success,
            "message": message,
            "text": extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
        }
        
    except Exception as e:
        logger.error(f"Error processing {uploaded_file.name}: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "filename": uploaded_file.name,
            "success": False,
            "message": str(e),
            "text": None
        }

def validate_database_entry(text, classifications):
    """Validate the data before adding to database"""
    if not text or len(text.strip()) == 0:
        raise ValueError("Empty text content")
    
    required_keys = {'main_category', 'selected_types', 'class_types'}
    if not all(key in classifications for key in required_keys):
        raise ValueError("Missing required classification fields")
    
    return True

def add_to_database_with_validation(text, classifications):
    """Wrapper function to add data to database with validation and logging"""
    try:
        
        logger.info("Attempting to add to database with:")
        logger.info(f"Text length: {len(text)}")
        logger.info(f"Classifications: {json.dumps(classifications, indent=2)}")
        
        
        validate_database_entry(text, classifications)
        
        
        result = add_to_database(text=text, classifications=classifications)
        
        
        logger.info(f"Successfully added to database: {result}")
        return True, None
        
    except Exception as e:
        error_msg = f"Database insertion failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def reset_form():
    """Initialize or reset the form state"""
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'db_update_status' not in st.session_state:
        st.session_state.db_update_status = None
    if 'debug_info' not in st.session_state:
        st.session_state.debug_info = []


reset_form()

st.title("Upload New Reports")

with st.expander("Debug Information"):
    if st.session_state.debug_info:
        for info in st.session_state.debug_info:
            st.code(info)
    if st.button("Clear Debug Info"):
        st.session_state.debug_info = []

def extract_selected_classes(category, selected_classes):
    """
    Extract and categorize user selections from the upload form.
    """
    result = {
        'main_category': category,
        'selected_types': selected_classes,
        'class_types': []
    }
    
    if category == "Zones":
        result['class_types'].append("ZonalArea")
        
    elif category == "Messages/Notes":
        for selection in selected_classes:
            if selection == "SurveillanceLog":
                result['class_types'].append("Surveillance")
            elif selection == "CommunicationMessage":
                result['class_types'].append("Message")
            elif selection == "ReconnaissanceNotes":
                result['class_types'].append("Reconnaissance")
    
    return result

CATEGORIES = {
    "Messages/Notes": [
        "SurveillanceLog",
        "CommunicationMessage",
        "ReconnaissanceNotes"  
    ],
    "Zones": [
        "StrategicMaritimeZone",
        "StrategicChokepointAndSurveillanceArea",
        "NavalSpecialOperationsExerciseArea",
        "NavalOperationZone",
        "NavalMineWarfareExerciseArea",
        "MaritimeInterdictionOperationExerciseArea",
        "AntiSubmarineWarfareExerciseArea",
        "AmphibiousOperationExerciseArea",
        "NavalAirPatrolZone",
        "NavalAirDefenseExerciseArea"
    ]
}


if st.session_state.db_update_status:
    st.success(st.session_state.db_update_status)

if st.session_state.processing_complete:
    if st.button("Upload More Files"):
        st.session_state.processing_complete = False
        st.session_state.form_submitted = False
        st.session_state.db_update_status = None
        st.rerun()
else:
    
    col1, col2 = st.columns([1, 2])

    with col1:
        category = st.radio(
            "Select Category",
            ["Messages/Notes", "Zones"],
            key="category_selection"
        )

    with col2:
        selected_classes = st.multiselect(
            f"Select {category} Types",
            CATEGORIES[category],
            key="class_selection"
        )

    
    classifications = None
    if selected_classes:
        classifications = extract_selected_classes(category, selected_classes)
        with st.expander("View Selected Classifications"):
            st.write(f"Main Category: {classifications['main_category']}")
            st.write(f"Specific Types: {classifications['selected_types']}")
            st.write(f"Class Types: {classifications['class_types']}")

    
    uploaded_files = st.file_uploader(
        "Upload Reports (PDF or MD)", 
        type=["pdf", "md"], 
        accept_multiple_files=True,
        key="file_uploader"
    )

    if uploaded_files and classifications:
        status_container = st.empty()
        success_container = st.empty()
        error_container = st.empty()
        
        all_processed_texts = []
        
        with status_container:
            st.subheader("Processing Files")
            process_bar = st.progress(0)
            
            for idx, uploaded_file in enumerate(uploaded_files):
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    try:
                        extracted_text = extract_text_from_file(uploaded_file)
                        
                        file_data = {
                            "filename": uploaded_file.name,
                            "text": extracted_text,
                            "classifications": classifications
                        }
                        all_processed_texts.append(file_data)
                        
                        process_bar.progress((idx + 1) / len(uploaded_files))
                        
                        with st.expander(f"View extracted text from {uploaded_file.name}"):
                            st.text_area("Extracted Text", extracted_text, height=200)
                            
                    except Exception as e:
                        error_container.error(f"Error processing {uploaded_file.name}: {str(e)}")
                        continue

        if all_processed_texts:
            if st.button("Add All to Database", key="add_to_db"):
                with st.spinner("Adding to database..."):
                    success_count = 0
                    error_count = 0
                    debug_info = []
                    
                    db_progress = st.progress(0)
                    
                    for idx, file_data in enumerate(all_processed_texts):
                        try:
                            
                            debug_info.append(f"Processing file: {file_data['filename']}")
                            debug_info.append(f"Classifications: {json.dumps(file_data['classifications'], indent=2)}")
                            
                            
                            success, message = add_to_database(
                                text=file_data["text"],
                                classifications=file_data["classifications"]
                            )
                            
                            if success:
                                success_count += 1
                                debug_info.append(f"✅ Successfully processed {file_data['filename']}")
                            else:
                                error_count += 1
                                debug_info.append(f"❌ Failed to process {file_data['filename']}: {message}")
                            
                            
                            db_progress.progress((idx + 1) / len(all_processed_texts))
                            
                        except Exception as e:
                            error_count += 1
                            error_msg = f"Error processing {file_data['filename']}: {str(e)}"
                            debug_info.append(f"❌ {error_msg}")
                            st.error(error_msg)
                        
                        
                        with st.expander(f"Processing Details for {file_data['filename']}"):
                            st.code(json.dumps(debug_info[-3:], indent=2))
                    
                    
                    st.session_state.debug_info = debug_info
                    
                    
                    status_message = f"""
                        Database Update Status:
                        - Successfully processed: {success_count} files
                        - Failed: {error_count} files
                        - Total files: {len(all_processed_texts)}
                        
                        Check the Debug Information expander for details.
                    """
                    st.session_state.db_update_status = status_message
                    st.session_state.processing_complete = True
                    st.rerun()