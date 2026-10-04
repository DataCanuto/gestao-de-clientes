# PDF Data Extraction Pipeline

A comprehensive Python-based data processing pipeline for extracting, consolidating, and analyzing information from multiple PDF document types using OCR and pattern matching techniques.

## 🎯 Project Overview

This project automates the extraction and consolidation of data from three types of PDF documents:
- **Invoice PDFs (NF)**: Extract emission dates and client information
- **Spreadsheet PDFs (Planilha)**: Extract broker and status information  
- **Account Statement PDFs (Prestação)**: Extract process numbers and client names

The pipeline handles both text-based and scanned (image-based) PDFs using OCR technology, consolidates data across document types, and generates unified reports for analysis.

## ✨ Key Features

### Data Extraction
- 🔍 **Multi-format PDF Processing**: Handles both text and image-based PDFs
- 🖼️ **OCR Integration**: Tesseract OCR for scanned document text extraction
- 📅 **Pattern Matching**: Regex-based extraction of dates, names, and identifiers
- 🔄 **Automated File Discovery**: Recursive directory scanning and classification

### Data Consolidation
- 🔗 **Intelligent Matching**: Cross-references clients across multiple document sources
- 📊 **Complete Data Merging**: Full outer join to preserve all records
- 🗂️ **Duplicate Handling**: Manages multiple documents per client
- ✅ **Data Validation**: Identifies missing documents and inconsistencies

### Output & Reporting
- 📄 **Multi-format Export**: CSV and Excel output with formatted data
- 📋 **Missing Files Report**: Identifies gaps in documentation
- 🔀 **PDF Merging**: Combines all client documents into single PDFs
- 📈 **Data Quality Metrics**: Statistics on completeness and duplicates

## 🛠️ Technologies Used

- **Python 3.x**
- **PyMuPDF (fitz)**: PDF rendering and image extraction
- **Tesseract OCR**: Optical character recognition
- **Pillow (PIL)**: Image processing
- **PyPDF2**: PDF manipulation and merging
- **pandas**: Data manipulation and analysis
- **openpyxl**: Excel file generation
- **regex**: Pattern matching and text extraction

## 📋 Requirements

```bash
pip install PyMuPDF pytesseract Pillow PyPDF2 pandas openpyxl
```

**Additional Requirements:**
- Tesseract OCR installed on your system
  - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
  - Linux: `sudo apt-get install tesseract-ocr`
  - Mac: `brew install tesseract`

## 🚀 Usage

### 1. Configure Paths

Update the path variables in the notebook:
```python
PATH_NF = 'path_to_invoice_files'
PATH_PLANILHAS_PRESTACOES = 'path_to_statements_and_spreadsheets'
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### 2. Run Data Extraction

Execute the notebook cells in order:
1. **Imports & Setup**: Load libraries and configure paths
2. **File Discovery**: Scan directories and populate initial tables
3. **Name Processing**: Standardize client names across sources
4. **Data Extraction**: Extract dates, process numbers, and metadata
5. **Consolidation**: Merge data from all sources
6. **Export**: Generate reports and merged PDFs

### 3. Review Outputs

The pipeline generates:
- `tabela_final_clientes.csv`: Complete consolidated data
- `tabela_final_clientes.xlsx`: Formatted Excel report
- `clientes_arquivos_faltantes.xlsx`: Missing documents report
- `PDFs_Mesclados/`: Individual merged PDFs per client

## 📊 Data Structure

### Input Tables
- **nf_table**: Invoice data (origin, name, date, broker, status)
- **pr_table**: Account statements (origin, name, name_found, process_number)
- **pl_table**: Spreadsheets (origin, name, broker, status)

### Output Table (final_table)
Consolidated view with all client information:
- Client name
- Document origins (lists for multiple files)
- Extracted metadata (dates, process numbers, status)
- Data quality indicators

## 🔍 Core Functions

### `extrair_texto_pdf_ocr(file)`
Extracts text from scanned PDFs using OCR technology.
- Converts PDF pages to high-resolution images
- Applies Tesseract OCR
- Returns complete extracted text

### `extrair_data_texto(texto)`
Extracts emission date from invoice text using regex patterns.
- Matches Portuguese date formats
- Handles variations in label text
- Returns date in dd/mm/yyyy format

### `processar_nome(nome)`
Standardizes client names for matching across documents.
- Removes prefixes and suffixes
- Handles special cases (estates, companies)
- Ensures consistent formatting

## 📈 Project Highlights

This project demonstrates:
- ✅ **ETL Pipeline Design**: Complete extract-transform-load workflow
- ✅ **Unstructured Data Handling**: Processing PDFs with varied formats
- ✅ **Data Quality Management**: Validation and missing data identification
- ✅ **Automated Document Processing**: Batch operations on hundreds of files
- ✅ **Cross-referencing Skills**: Matching entities across multiple sources
- ✅ **Report Generation**: Professional Excel/CSV outputs

## 🎓 Skills Showcased

- Data Engineering
- Python Programming
- OCR & Image Processing
- PDF Manipulation
- Data Consolidation & Merging
- Regex & Pattern Matching
- Pandas & Data Analysis
- Error Handling & Logging
- File System Operations
- Automation & Scripting

## 📝 Notes

- This is a portfolio version with sample code structure
- Real client data has been removed for privacy
- Designed to process financial documents but adaptable to other domains
- Optimized for batch processing of large document sets

## 🤝 Contributing

Feel free to fork this project and adapt it to your own document processing needs!

## 📄 License

This project is open source and available for educational and portfolio purposes.

---

**Author**: Pedro Canuto  
**Purpose**: Data Engineering Portfolio Project  
**Year**: 2025
