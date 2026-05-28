# PowerPoint Creation Methodology
## Scripts, Methods, Tools, and Best Practices

**Document Version**: 1.0  
**Date**: November 2025  
**Purpose**: Comprehensive guide for PowerPoint processing, extraction, analysis, and creation  
**Scope**: Complete workflow from source PPT files to structured data and reports

---

## Table of Contents
1. [Overview](#overview)
2. [Tools and Technologies](#tools-and-technologies)
3. [Extraction Methodology](#extraction-methodology)
4. [Analysis Techniques](#analysis-techniques)
5. [Creation and Generation](#creation-and-generation)
6. [Best Practices](#best-practices)
7. [Common Pitfalls](#common-pitfalls)
8. [Advanced Techniques](#advanced-techniques)
9. [Complete Example Workflow](#complete-example-workflow)

---

## Overview

### Purpose of This Document
This methodology document provides a complete guide for working with PowerPoint presentations programmatically, including:
- **Extraction**: Reading and parsing existing presentations
- **Analysis**: Extracting insights from slide content
- **Creation**: Generating new presentations programmatically
- **Transformation**: Converting between formats
- **Automation**: Building scalable PPT processing pipelines

### When to Use This Methodology
- **Content Analysis**: Extracting text, data, and insights from large presentation libraries
- **Data Migration**: Moving presentation content to other systems
- **Automated Reporting**: Generating presentations from data
- **Slide Management**: Cataloging and organizing presentation content
- **Quality Assurance**: Validating presentation standards and formats

### Workflow Overview

```
┌─────────────────┐
│ Source PPT Files│
└────────┬────────┘
         │
         ↓ [EXTRACTION]
         │
┌────────▼────────────┐
│ Structured Data     │
│ (JSON/CSV/Database) │
└────────┬────────────┘
         │
         ↓ [ANALYSIS]
         │
┌────────▼────────────┐
│ Insights & Reports  │
└────────┬────────────┘
         │
         ↓ [CREATION/TRANSFORMATION]
         │
┌────────▼────────────┐
│ Output Artifacts    │
│ (Reports, New PPTs) │
└─────────────────────┘
```

---

## Tools and Technologies

### Python-pptx Library (Recommended)

#### Overview
**python-pptx** is a Python library for creating and updating PowerPoint (.pptx) files.

#### Installation
```bash
pip install python-pptx
```

#### Capabilities
- ✅ Read existing presentations
- ✅ Extract text from slides
- ✅ Access slide layouts and masters
- ✅ Extract tables and shapes
- ✅ Access images and charts
- ✅ Read notes and comments
- ✅ Create new presentations
- ✅ Add slides, text, images, tables
- ✅ Apply formatting and styles

#### Limitations
- ❌ Cannot directly extract charts data (shows as shape)
- ❌ Complex SmartArt not fully parsed
- ❌ Some animations/transitions not accessible
- ❌ Embedded videos limited support

#### When to Use
- **Primary use case**: Structured extraction and creation
- **Best for**: Text, tables, basic shapes, and metadata
- **Not ideal for**: Complex graphics, animations, embedded objects

### Alternative Tools

#### 1. LibreOffice (Command Line)

**Installation**:
```bash
sudo apt-get install libreoffice
```

**Use Cases**:
- High-fidelity format conversion (PPT → PDF)
- Visual layout preservation
- Batch processing

**Commands**:
```bash
# Convert to PDF
libreoffice --headless --convert-to pdf presentation.pptx

# Convert to HTML
libreoffice --headless --convert-to html presentation.pptx

# Batch conversion
libreoffice --headless --convert-to pdf --outdir output/ *.pptx
```

**Pros**:
- ✅ Preserves visual fidelity
- ✅ Wide format support
- ✅ Free and open-source

**Cons**:
- ❌ Lossy for text extraction
- ❌ Requires LibreOffice installation
- ❌ Limited programmatic control

#### 2. Cloud APIs

**Microsoft Graph API**:
- Native PowerPoint API
- Cloud-based
- Requires authentication

**Google Slides API**:
- For Google Slides format
- Real-time collaboration
- Requires API key

**Pros**:
- ✅ Cloud-native
- ✅ Real-time collaboration
- ✅ Rich API capabilities

**Cons**:
- ❌ Internet connectivity required
- ❌ API rate limits
- ❌ Cost considerations
- ❌ Authentication complexity

#### 3. Apache POI (Java)

**Use Case**: Java-based environments

**Library**: `org.apache.poi.xslf`

**Capabilities**: Similar to python-pptx

#### 4. Aspose.Slides (Commercial)

**Use Case**: Enterprise applications with complex requirements

**Platforms**: .NET, Java, Python, C++

**Pros**:
- ✅ Most comprehensive features
- ✅ High-fidelity processing
- ✅ Commercial support

**Cons**:
- ❌ Paid license required
- ❌ Higher complexity

---

## Extraction Methodology

### Phase 1: Preparation

#### Step 1.1: Environment Setup

```bash
# Create project directory
mkdir ppt_extraction_project
cd ppt_extraction_project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install python-pptx
pip install pandas  # for data manipulation
pip install openpyxl  # for Excel export

# Create directory structure
mkdir -p source_files
mkdir -p extracted_data
mkdir -p reports
mkdir -p scripts
```

#### Step 1.2: File Organization

```bash
# Organize source files
# Convention: [Category] - [Title].pptx
source_files/
├── QSYS - Top-level system description.pptx
├── QSYS - IADR Overview.pptx
└── QSYS - Commissioning Overview.pptx
```

**Best Practices**:
- Use consistent naming conventions
- Include version dates if applicable
- Separate by category/project
- Keep originals immutable (process copies)

### Phase 2: Extraction Script Development

#### Complete Extraction Script

```python
"""
PowerPoint Extraction Script
Extracts complete structured data from .pptx files
"""

from pptx import Presentation
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PowerPointExtractor:
    """Extract structured data from PowerPoint presentations."""
    
    def __init__(self, source_dir: str, output_dir: str):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_shape_content(self, shape) -> Dict[str, Any]:
        """Extract content from a shape."""
        shape_data = {
            "name": shape.name if hasattr(shape, "name") else "Unknown",
            "shape_type": str(shape.shape_type),
            "text": "",
            "table": None,
            "has_image": False
        }
        
        # Extract text
        if hasattr(shape, "text"):
            shape_data["text"] = shape.text
        
        # Extract table
        if hasattr(shape, "has_table") and shape.has_table:
            table_data = []
            for row in shape.table.rows:
                row_data = []
                for cell in row.cells:
                    row_data.append(cell.text)
                table_data.append(row_data)
            shape_data["table"] = table_data
        
        # Check for image
        if hasattr(shape, "image"):
            shape_data["has_image"] = True
            # Could extract image bytes here if needed
            # shape_data["image_bytes"] = shape.image.blob
        
        return shape_data
    
    def extract_slide_content(self, slide, slide_number: int) -> Dict[str, Any]:
        """Extract all content from a single slide."""
        slide_data = {
            "slide_number": slide_number,
            "title": "",
            "subtitle": "",
            "body_text": [],
            "shapes": [],
            "tables": [],
            "notes": "",
            "layout_name": slide.slide_layout.name if hasattr(slide, "slide_layout") else "Unknown"
        }
        
        # Extract title
        if slide.shapes.title:
            slide_data["title"] = slide.shapes.title.text
        
        # Extract content from all shapes
        for shape in slide.shapes:
            shape_content = self.extract_shape_content(shape)
            slide_data["shapes"].append(shape_content)
            
            # Collect body text (non-title text)
            if shape_content["text"] and shape != slide.shapes.title:
                slide_data["body_text"].append(shape_content["text"])
            
            # Collect tables
            if shape_content["table"]:
                slide_data["tables"].append({
                    "shape_name": shape_content["name"],
                    "data": shape_content["table"]
                })
        
        # Extract notes
        if slide.has_notes_slide:
            notes_slide = slide.notes_slide
            if notes_slide.notes_text_frame:
                slide_data["notes"] = notes_slide.notes_text_frame.text
        
        return slide_data
    
    def extract_presentation_metadata(self, prs: Presentation, filepath: Path) -> Dict[str, Any]:
        """Extract presentation-level metadata."""
        metadata = {
            "filename": filepath.name,
            "filepath": str(filepath),
            "total_slides": len(prs.slides),
            "slide_width": prs.slide_width,
            "slide_height": prs.slide_height,
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        # Extract core properties if available
        if hasattr(prs, "core_properties"):
            props = prs.core_properties
            metadata.update({
                "title": props.title or "",
                "author": props.author or "",
                "subject": props.subject or "",
                "created": props.created.isoformat() if props.created else None,
                "modified": props.modified.isoformat() if props.modified else None
            })
        
        return metadata
    
    def extract_presentation(self, filepath: Path) -> Dict[str, Any]:
        """Extract all content from a PowerPoint presentation."""
        logger.info(f"Processing: {filepath.name}")
        
        try:
            # Load presentation
            prs = Presentation(filepath)
            
            # Extract metadata
            presentation_data = self.extract_presentation_metadata(prs, filepath)
            
            # Extract all slides
            slides = []
            for idx, slide in enumerate(prs.slides, 1):
                try:
                    slide_content = self.extract_slide_content(slide, idx)
                    slides.append(slide_content)
                except Exception as e:
                    logger.error(f"Error extracting slide {idx} from {filepath.name}: {e}")
                    slides.append({
                        "slide_number": idx,
                        "error": str(e),
                        "status": "extraction_failed"
                    })
            
            presentation_data["slides"] = slides
            presentation_data["extraction_status"] = "success"
            
            logger.info(f"✓ Extracted {len(slides)} slides from {filepath.name}")
            return presentation_data
            
        except Exception as e:
            logger.error(f"✗ Error processing {filepath.name}: {e}")
            return {
                "filename": filepath.name,
                "filepath": str(filepath),
                "extraction_status": "failed",
                "error": str(e)
            }
    
    def extract_all_presentations(self, pattern: str = "*.pptx") -> List[Dict[str, Any]]:
        """Extract content from all matching presentations."""
        all_presentations = []
        
        # Find all matching files
        pptx_files = list(self.source_dir.glob(pattern))
        logger.info(f"Found {len(pptx_files)} presentation(s) to process")
        
        # Process each file
        for pptx_file in pptx_files:
            pres_data = self.extract_presentation(pptx_file)
            all_presentations.append(pres_data)
        
        return all_presentations
    
    def save_to_json(self, data: List[Dict[str, Any]], filename: str = "extracted_data.json"):
        """Save extracted data to JSON file."""
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Saved JSON to: {output_path}")
        return output_path
    
    def create_slide_inventory_csv(self, data: List[Dict[str, Any]]):
        """Create a CSV inventory of all slides."""
        rows = []
        
        for pres in data:
            if pres.get("extraction_status") == "success":
                for slide in pres.get("slides", []):
                    rows.append({
                        "Presentation": pres["filename"],
                        "Slide Number": slide.get("slide_number"),
                        "Title": slide.get("title", ""),
                        "Layout": slide.get("layout_name", ""),
                        "Body Text Words": len(" ".join(slide.get("body_text", [])).split()),
                        "Table Count": len(slide.get("tables", [])),
                        "Shape Count": len(slide.get("shapes", [])),
                        "Has Notes": "Yes" if slide.get("notes") else "No"
                    })
        
        df = pd.DataFrame(rows)
        output_path = self.output_dir / "slide_inventory.csv"
        df.to_csv(output_path, index=False)
        
        logger.info(f"✓ Created slide inventory: {output_path}")
        return output_path
    
    def generate_summary_report(self, data: List[Dict[str, Any]]):
        """Generate a summary report."""
        total_presentations = len(data)
        successful = sum(1 for p in data if p.get("extraction_status") == "success")
        failed = total_presentations - successful
        total_slides = sum(p.get("total_slides", 0) for p in data if p.get("extraction_status") == "success")
        
        report = f"""
# PowerPoint Extraction Summary Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overview
- **Total Presentations Processed**: {total_presentations}
- **Successful Extractions**: {successful}
- **Failed Extractions**: {failed}
- **Total Slides Extracted**: {total_slides}

## Presentation Details
"""
        
        for pres in data:
            status = "✓" if pres.get("extraction_status") == "success" else "✗"
            report += f"\n### {status} {pres['filename']}\n"
            
            if pres.get("extraction_status") == "success":
                report += f"- Slides: {pres.get('total_slides', 0)}\n"
                report += f"- Author: {pres.get('author', 'Unknown')}\n"
                if pres.get("created"):
                    report += f"- Created: {pres.get('created', 'Unknown')}\n"
            else:
                report += f"- Error: {pres.get('error', 'Unknown error')}\n"
        
        output_path = self.output_dir / "extraction_summary.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"✓ Generated summary report: {output_path}")
        return output_path


# Main execution
if __name__ == "__main__":
    # Configuration
    SOURCE_DIR = "source_files"
    OUTPUT_DIR = "extracted_data"
    
    # Create extractor
    extractor = PowerPointExtractor(SOURCE_DIR, OUTPUT_DIR)
    
    # Extract all presentations
    logger.info("=" * 60)
    logger.info("PowerPoint Extraction Started")
    logger.info("=" * 60)
    
    extracted_data = extractor.extract_all_presentations()
    
    # Save outputs
    extractor.save_to_json(extracted_data, "full_extraction.json")
    extractor.create_slide_inventory_csv(extracted_data)
    extractor.generate_summary_report(extracted_data)
    
    logger.info("=" * 60)
    logger.info("Extraction Complete!")
    logger.info("=" * 60)
```

### Phase 3: Execution

#### Running the Extraction

```bash
# Activate virtual environment
source venv/bin/activate

# Run extraction script
python scripts/extract_presentations.py

# Check outputs
ls -lh extracted_data/
# Expected outputs:
# - full_extraction.json (structured data)
# - slide_inventory.csv (searchable inventory)
# - extraction_summary.md (human-readable summary)
```

#### Output Structure

**full_extraction.json**:
```json
[
  {
    "filename": "QSYS - Top-level system description.pptx",
    "total_slides": 25,
    "extraction_status": "success",
    "slides": [
      {
        "slide_number": 1,
        "title": "QSYS Overview",
        "body_text": ["System architecture...", "Key components..."],
        "tables": [],
        "shapes": [...],
        "notes": "Presenter notes here"
      }
    ]
  }
]
```

---

## Analysis Techniques

### Text Analysis

#### Word Frequency Analysis

```python
from collections import Counter
import re
import json

def analyze_word_frequency(json_path, top_n=50):
    """Analyze word frequency across all presentations."""
    
    # Load extracted data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Collect all text
    all_text = []
    for pres in data:
        if pres.get("extraction_status") == "success":
            for slide in pres.get("slides", []):
                all_text.append(slide.get("title", ""))
                all_text.extend(slide.get("body_text", []))
                all_text.append(slide.get("notes", ""))
    
    # Process text
    text = " ".join(all_text).lower()
    
    # Remove punctuation and extract words
    words = re.findall(r'\b\w+\b', text)
    
    # Remove common stop words (simplified)
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "is", "are", "was", "were"}
    words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Count frequency
    word_freq = Counter(words).most_common(top_n)
    
    return word_freq

# Usage
freq = analyze_word_frequency("extracted_data/full_extraction.json", top_n=30)
for word, count in freq:
    print(f"{word:20s}: {count:4d} {'█' * (count // 10)}")
```

#### Topic/Theme Identification

```python
def identify_themes(json_path):
    """Identify major themes based on keyword presence."""
    
    # Define theme keywords
    themes = {
        "architecture": ["architecture", "system", "design", "structure", "component"],
        "data": ["database", "data", "storage", "query", "table"],
        "process": ["process", "workflow", "procedure", "step", "phase"],
        "installation": ["install", "setup", "deploy", "configuration"],
        "monitoring": ["monitor", "alert", "dashboard", "metrics", "performance"],
        "security": ["security", "authentication", "authorization", "access", "permission"]
    }
    
    # Load data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Count theme occurrences
    theme_counts = {theme: 0 for theme in themes}
    
    for pres in data:
        if pres.get("extraction_status") == "success":
            pres_text = []
            for slide in pres.get("slides", []):
                pres_text.append(slide.get("title", ""))
                pres_text.extend(slide.get("body_text", []))
            
            pres_text_lower = " ".join(pres_text).lower()
            
            for theme, keywords in themes.items():
                for keyword in keywords:
                    theme_counts[theme] += pres_text_lower.count(keyword)
    
    return theme_counts

# Usage
themes = identify_themes("extracted_data/full_extraction.json")
print("\nTheme Analysis:")
for theme, count in sorted(themes.items(), key=lambda x: x[1], reverse=True):
    print(f"{theme:15s}: {count:4d} mentions")
```

### Slide Structure Analysis

```python
def analyze_slide_structure(json_path):
    """Analyze slide structure patterns."""
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    layout_counts = Counter()
    table_slides = 0
    text_heavy_slides = 0  # >100 words
    title_only_slides = 0
    
    for pres in data:
        if pres.get("extraction_status") == "success":
            for slide in pres.get("slides", []):
                # Layout analysis
                layout_counts[slide.get("layout_name", "Unknown")] += 1
                
                # Table detection
                if slide.get("tables"):
                    table_slides += 1
                
                # Text density
                word_count = len(" ".join(slide.get("body_text", [])).split())
                if word_count > 100:
                    text_heavy_slides += 1
                
                # Title-only detection
                if slide.get("title") and not slide.get("body_text"):
                    title_only_slides += 1
    
    return {
        "layout_distribution": dict(layout_counts),
        "table_slides": table_slides,
        "text_heavy_slides": text_heavy_slides,
        "title_only_slides": title_only_slides
    }
```

---

## Creation and Generation

### Creating New Presentations

#### Basic Presentation Creation

```python
from pptx import Presentation
from pptx.util import Inches, Pt

def create_simple_presentation():
    """Create a simple PowerPoint presentation."""
    
    # Create presentation object
    prs = Presentation()
    
    # Slide 1: Title Slide
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = "Project Report"
    subtitle.text = "Generated Automatically"
    
    # Slide 2: Content Slide
    bullet_slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(bullet_slide_layout)
    shapes = slide.shapes
    
    title_shape = shapes.title
    body_shape = shapes.placeholders[1]
    
    title_shape.text = "Key Findings"
    
    tf = body_shape.text_frame
    tf.text = "First finding"
    
    p = tf.add_paragraph()
    p.text = "Second finding"
    p.level = 0
    
    p = tf.add_paragraph()
    p.text = "Third finding"
    p.level = 0
    
    # Save presentation
    prs.save("generated_report.pptx")
    print("✓ Created generated_report.pptx")

create_simple_presentation()
```

#### Adding Tables

```python
def add_table_slide(prs, title_text, table_data):
    """Add a slide with a table."""
    
    blank_slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(blank_slide_layout)
    
    # Add title
    left = Inches(0.5)
    top = Inches(0.5)
    width = Inches(9)
    height = Inches(0.5)
    
    title_box = slide.shapes.add_textbox(left, top, width, height)
    title_frame = title_box.text_frame
    title_frame.text = title_text
    
    # Add table
    rows = len(table_data)
    cols = len(table_data[0]) if table_data else 0
    
    left = Inches(1)
    top = Inches(1.5)
    width = Inches(8)
    height = Inches(4)
    
    table = slide.shapes.add_table(rows, cols, left, top, width, height).table
    
    # Fill table
    for i, row_data in enumerate(table_data):
        for j, cell_value in enumerate(row_data):
            table.cell(i, j).text = str(cell_value)
    
    return slide

# Usage
prs = Presentation()
table_data = [
    ["Metric", "Q1", "Q2", "Q3", "Q4"],
    ["Revenue", "$1M", "$1.2M", "$1.5M", "$1.8M"],
    ["Users", "10K", "15K", "22K", "30K"]
]
add_table_slide(prs, "Quarterly Metrics", table_data)
prs.save("table_report.pptx")
```

---

## Best Practices

### 1. File Management
- ✅ Use consistent naming conventions
- ✅ Version control for source files
- ✅ Keep originals immutable
- ✅ Organize by category/project
- ✅ Document file provenance

### 2. Extraction Quality
- ✅ Always validate extraction completeness
- ✅ Handle errors gracefully
- ✅ Log all processing steps
- ✅ Verify slide counts match
- ✅ Check for encoding issues

### 3. Performance
- ✅ Process files incrementally
- ✅ Use generators for large datasets
- ✅ Cache expensive operations
- ✅ Parallel processing for batch jobs
- ✅ Monitor memory usage

### 4. Data Quality
- ✅ Normalize text encoding (UTF-8)
- ✅ Clean special characters
- ✅ Remove duplicates
- ✅ Validate JSON structure
- ✅ Implement data quality checks

### 5. Documentation
- ✅ Document extraction methodology
- ✅ Preserve decision rationale
- ✅ Include sample outputs
- ✅ Provide usage examples
- ✅ Maintain changelog

---

## Common Pitfalls

| Pitfall | Impact | Solution |
|---------|--------|----------|
| **Embedded objects not extracted** | Missing content | Use shape.image for embedded images; consider OCR for complex objects |
| **Charts show as generic shapes** | Data loss | Extract underlying data if available; use chart APIs or manual parsing |
| **Notes slides missing** | Lost presenter notes | Always check `slide.has_notes_slide` before accessing |
| **Large files cause memory errors** | Process crashes | Process files one at a time; use streaming for very large presentations |
| **Encoding errors** | Corrupted text | Always use UTF-8 encoding; set `ensure_ascii=False` in JSON |
| **Layout-specific assumptions** | Brittle code | Use flexible slide parsing; don't assume placeholder positions |
| **Version compatibility** | Extraction failures | Test with various PowerPoint versions; handle legacy formats |

---

## Advanced Techniques

### 1. Image Extraction with OCR

```python
from pptx import Presentation
from PIL import Image
import pytesseract
import io

def extract_images_with_ocr(pptx_path, output_dir="images"):
    """Extract images and perform OCR."""
    
    Path(output_dir).mkdir(exist_ok=True)
    prs = Presentation(pptx_path)
    
    for slide_num, slide in enumerate(prs.slides, 1):
        for shape_num, shape in enumerate(slide.shapes, 1):
            if hasattr(shape, "image"):
                # Extract image
                image = shape.image
                image_bytes = image.blob
                
                # Save image
                image_filename = f"slide{slide_num}_shape{shape_num}.{image.ext}"
                image_path = Path(output_dir) / image_filename
                
                with open(image_path, 'wb') as f:
                    f.write(image_bytes)
                
                # Perform OCR
                img = Image.open(io.BytesIO(image_bytes))
                ocr_text = pytesseract.image_to_string(img)
                
                print(f"Image: {image_filename}")
                print(f"OCR Text: {ocr_text[:100]}...")
                print()
```

### 2. Slide Comparison

```python
def compare_presentations(pptx1_path, pptx2_path):
    """Compare two presentations for differences."""
    
    prs1 = Presentation(pptx1_path)
    prs2 = Presentation(pptx2_path)
    
    differences = []
    
    # Compare slide counts
    if len(prs1.slides) != len(prs2.slides):
        differences.append(f"Slide count: {len(prs1.slides)} vs {len(prs2.slides)}")
    
    # Compare slide by slide
    for i, (slide1, slide2) in enumerate(zip(prs1.slides, prs2.slides), 1):
        # Compare titles
        title1 = slide1.shapes.title.text if slide1.shapes.title else ""
        title2 = slide2.shapes.title.text if slide2.shapes.title else ""
        
        if title1 != title2:
            differences.append(f"Slide {i} title: '{title1}' vs '{title2}'")
        
        # Compare shape counts
        if len(slide1.shapes) != len(slide2.shapes):
            differences.append(f"Slide {i} shape count: {len(slide1.shapes)} vs {len(slide2.shapes)}")
    
    return differences
```

### 3. Automated Report Generation from Data

```python
def generate_report_from_data(data_dict, output_path="report.pptx"):
    """Generate presentation from structured data."""
    
    prs = Presentation()
    
    # Title slide
    title_slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_slide.shapes.title.text = data_dict["title"]
    title_slide.placeholders[1].text = data_dict["subtitle"]
    
    # Content slides
    for section in data_dict["sections"]:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = section["title"]
        
        tf = slide.placeholders[1].text_frame
        for bullet in section["bullets"]:
            p = tf.add_paragraph()
            p.text = bullet
            p.level = 0
    
    # Chart slide (if data provided)
    if "chart_data" in data_dict:
        # Add chart slide (requires chart creation - more complex)
        pass
    
    prs.save(output_path)
    print(f"✓ Generated report: {output_path}")

# Example usage
report_data = {
    "title": "Q4 2025 Results",
    "subtitle": "Executive Summary",
    "sections": [
        {
            "title": "Key Achievements",
            "bullets": ["Revenue up 25%", "10K new users", "3 product launches"]
        },
        {
            "title": "Challenges",
            "bullets": ["Market competition increased", "Supply chain delays"]
        }
    ]
}

generate_report_from_data(report_data)
```

---

## Complete Example Workflow

### End-to-End: QSYS Analysis Project

This is the complete workflow used in the actual QSYS analysis project.

#### Step 1: Setup (5 minutes)

```bash
# Project initialization
mkdir qsys_analysis && cd qsys_analysis
python -m venv venv
source venv/bin/activate
pip install python-pptx pandas

# Create structure
mkdir -p Uploads extracted_data reports scripts
```

#### Step 2: Place Source Files (manual)

```bash
# Copy 19 QSYS presentation files to Uploads/
cp /path/to/presentations/*.pptx Uploads/
```

#### Step 3: Run Extraction (10 minutes)

```bash
# Save extraction script as scripts/extract.py
# Run extraction
python scripts/extract.py

# Verify outputs
ls -lh extracted_data/
# Expected:
# - qsys_slide_dump.json (2.0M)
# - slide_inventory.csv
# - extraction_summary.md
```

#### Step 4: Analysis (30 minutes)

```python
# analysis.py
import json
from collections import Counter

with open("extracted_data/qsys_slide_dump.json", "r") as f:
    data = json.load(f)

# Quick stats
total_slides = sum(p["total_slides"] for p in data)
print(f"Total slides: {total_slides}")

# Word frequency
# ... (use code from Analysis Techniques section)

# Theme identification
# ... (use code from Analysis Techniques section)
```

#### Step 5: Generate Reports (20 minutes)

```python
# Generate comprehensive analysis report
# Save as reports/qsys_analysis_report.md

report_template = """
# QSYS Analysis Report

## Executive Summary
{summary}

## System Overview
{overview}

## Component Analysis
{components}

## Integration Points
{integration}

## Recommendations
{recommendations}
"""

# Fill in sections based on analysis
# Export to Markdown, PDF, etc.
```

#### Step 6: Handover (ongoing)

```bash
# Package all artifacts
tar -czf qsys_analysis_package.tar.gz \
    Uploads/ \
    extracted_data/ \
    reports/ \
    scripts/

# Document methodology (this document!)
```

### Results
- ✅ 389 slides extracted from 19 presentations
- ✅ 2.0M JSON file with structured data
- ✅ Comprehensive analysis reports generated
- ✅ Complete methodology documented
- ✅ Handover package created

---

## Document Metadata
- **Document Type**: PowerPoint Methodology - Complete Guide
- **Version**: 1.0
- **Created**: November 2025
- **Author**: DeepAgent AI Assistant
- **Purpose**: Comprehensive PPT processing guide
- **Audience**: Data engineers, analysts, developers
- **Status**: Complete
- **Previous Document**: 05_dmaic_iteration.md
- **Next Step**: Package all handover artifacts

---

**END OF POWERPOINT CREATION METHODOLOGY**
