<div align="center">

# <span style="font-size: 2.5em">⚓ Naksha Maritime Surveillance System</span>
</div>

## 👥 Team Jaltarang

### Team Members:
* 👨‍💻 Arnab Sengupta
* 👨‍💻 Jit Roy
* 👨‍💻 Soumyadip Roy
* 👨‍💻 Debojyoti Das
* 👨‍💻 Subhrajyoti Basu
---

## 🌊 **Real-Time Maritime Situational Awareness System**

Naksha is a Streamlit-based application designed to provide naval personnel with real-time situational awareness through interactive maps and automatic threat alerts. The system leverages advanced **OCR** (Optical Character Recognition), **RAG** (Retrieval-Augmented Generation), and **AI** models to scan, process, and interpret textual maritime reports. It dynamically plots vessels and other contacts on a radar/map interface, enhancing operational efficiency and maritime security.

---

## 🚢 Features

* **Text Extraction**: Uses OCR to extract vital details like coordinates, vessel types, speeds, and headings from surveillance reports
* **RAG-Powered Intelligence**: Uses Hugging Face's RAG model for contextual information retrieval and structured data extraction
* **Interactive Maps**: Displays contacts (ships, submarines, aircraft) on both zonal and surveillance maps with real-time updates
* **Automated Alerts**: Triggers alerts for potential threats, including unidentified objects or vessels in restricted waters
* **Naksha AI**: An intelligent assistant capable of answering complex queries in natural language based on the extracted data

---

## 📜 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/asengupta07/jaltarang.git
cd jaltarang
```

### 2. Install Dependencies
Make sure you have Python 3.8+ installed, then install the required dependencies:
```bash
pip install -r requirements.txt
```

### 3. Run Naksha Surveillance System
To start the application, simply run the following command:
```bash
streamlit run app.py
```
This will open the Naksha Maritime Surveillance System in your default web browser.

### 4. Set Up GROQ API Key
Before running the system, ensure you add your **GROQ_API** to the environment:
```bash
export GROQ_API=your_api_key_here
```
---

## 🌍 Key Components

### OCR Integration
* **Tools Used**: PyMuPDF, Pytesseract
* **Functionality**: Extracts handwritten and printed text from uploaded reports

### RAG-Based Information Retrieval
* **API Used**: Hugging Face RAG model
* **Functionality**: Extracts key details such as locations, vessel types, and time of sightings, cross-referencing with existing databases

### Map Visualization
* **Frontend**: Built using Streamlit, Leaflet.js and Folium for radar and map interfaces
* **Backend**: Python (FastAPI) handles all data processing and real-time updates

---

## 📊 Performance Metrics

The system is evaluated based on:
* **Accuracy of OCR and RAG**: The precision in extracting coordinates, headings, and vessel descriptions
* **Real-Time Updates**: The frequency and accuracy of map updates as new reports are processed
* **Threat Detection**: Effectiveness in identifying and alerting naval personnel to potential threats

---

## 🚀 Future Enhancements

* **Speech-to-Text Integration**: Adding capabilities to transcribe spoken surveillance reports
* **Historical Trend Analysis**: Incorporating more advanced features for tracking vessel movement trends over time

---

<div align="center">

# <span style="font-size: 2.5em">🌊 Stay Vigilant, Stay Informed with Naksha 🌊</span>
</div>
