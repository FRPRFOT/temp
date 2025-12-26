# G-code Analyzer for 3D Printer Freezing Issues

A Python tool to analyze G-code files and identify anomalies that may cause 3D printer freezing, specifically designed to investigate a Prusa MK3S freeze at Z=31.8mm during PETG printing.

## Problem Description

The Prusa MK3S printer freezes at Z=31.8mm during a PETG print. The printer stops completely but doesn't end the print - the menu is still accessible but the print cannot be restarted.

## Features

This tool provides comprehensive G-code analysis:

### Extraction & Parsing
- ✅ Extracts G-code from `.zip` files
- ✅ Parses all G-code commands
- ✅ Tracks Z-height changes throughout the print

### Analysis Capabilities
- ✅ **Unusual commands**: Detects non-standard or problematic G-code
- ✅ **Buffer-heavy operations**: Identifies complex arcs (G2/G3) and excessive micro-movements
- ✅ **Temperature changes**: Tracks M104, M109, M140, M190 commands
- ✅ **Tool changes**: Detects T0, T1 commands (multi-material)
- ✅ **Pause/wait commands**: Finds M0, M1, M25, M226 (likely freeze cause!)
- ✅ **Coordinate jumps**: Detects large sudden movements
- ✅ **Extrusion issues**: Analyzes E-axis anomalies and retractions
- ✅ **Fan changes**: Tracks M106, M107 commands
- ✅ **Command count analysis**: Identifies buffer overflow risks

### Reporting
- ✅ Console output with key findings
- ✅ Detailed text report file
- ✅ Layer-by-layer statistics
- ✅ Comparison with neighboring layers
- ✅ Line number references for issues
- ✅ Severity-based anomaly classification

## Installation

### Requirements
- Python 3.6 or higher (standard library only - no external dependencies!)

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd temp

# Make the script executable (optional)
chmod +x analyze_gcode.py
```

## Usage

### Basic Usage
```bash
# Analyze the included G-code file at Z=31.8mm
python3 analyze_gcode.py KNFORG1_150x90x40_5_0.2mm_PETG_MK3S_21h17m.gcode.zip
```

### Advanced Options
```bash
# Specify custom Z-height
python3 analyze_gcode.py file.gcode.zip -z 50.0

# Adjust analysis window (±mm around target Z)
python3 analyze_gcode.py file.gcode.zip -z 31.8 -w 1.0

# Custom output file name
python3 analyze_gcode.py file.gcode.zip -o my_report.txt

# Combine options
python3 analyze_gcode.py file.gcode.zip -z 31.8 -w 0.5 -o analysis.txt
```

### Command Line Arguments
```
positional arguments:
  gcode_file            G-code file or .zip file containing G-code

optional arguments:
  -h, --help            Show help message and exit
  -z, --target-z FLOAT  Target Z-height to analyze (default: 31.8mm)
  -w, --window FLOAT    Analysis window around target Z (default: ±0.5mm)
  -o, --output FILE     Output report file (default: gcode_analysis_report.txt)
```

## Output

The tool generates two types of output:

### 1. Console Summary
Displays key findings immediately:
- Overall file statistics
- Number of layers analyzed
- Detected anomalies by severity (CRITICAL, HIGH, MEDIUM, LOW)
- Quick identification of likely causes

### 2. Detailed Report File
A comprehensive text file (`gcode_analysis_report.txt` by default) containing:
- **Overall Statistics**: Total lines, layers, command counts
- **Layer-by-Layer Analysis**: Detailed breakdown of each layer near target Z
- **Anomalies Section**: All detected issues with severity ratings
- **Recommendations**: Specific suggestions for fixing issues

## Example Output

```
G-CODE ANALYZER
================================================================================

Extracting G-code from KNFORG1_150x90x40_5_0.2mm_PETG_MK3S_21h17m.gcode.zip...
Found G-code file: KNFORG1_150x90x40_5_0.2mm_PETG_MK3S_21h17m.gcode
Loaded 1,234,567 lines of G-code
Parsing G-code...
Found 200 unique Z-heights

================================================================================
ANALYZING Z=31.8mm (±0.5mm)
================================================================================

Found 3 layers in range: [31.6, 31.8, 32.0]

================================================================================
ANALYSIS SUMMARY
================================================================================

File: KNFORG1_150x90x40_5_0.2mm_PETG_MK3S_21h17m.gcode.zip
Total lines: 1,234,567
Total layers: 200
Z range: 0.200mm to 40.000mm

Target Z: 31.8mm
Layers analyzed: 3
Z-heights in range: 31.600mm, 31.800mm, 32.000mm

ANOMALIES FOUND: 1

CRITICAL:
  - Found 1 pause command(s) at Z=31.800mm

⚠️  CRITICAL: Found 1 pause command(s) at Z=31.800mm
   This is likely the cause of the printer freeze!
```

## Understanding Results

### Severity Levels
- **CRITICAL**: Issues that directly cause freezing (pause commands, etc.)
- **HIGH**: Issues that may cause problems (buffer overflow, excessive commands)
- **MEDIUM**: Potential issues (large movements, temperature changes)
- **LOW**: Minor anomalies worth noting

### Common Issues & Solutions

#### Pause Commands (CRITICAL)
**Problem**: M0, M1, M25, or M226 commands cause printer to wait for user input
**Solution**: Remove or comment out these commands in the G-code file

#### Excessive Arc Commands (HIGH)
**Problem**: Too many G2/G3 commands overwhelm the printer's buffer
**Solution**: Adjust slicer settings to reduce arc resolution or use line segments

#### Command Count Spike (HIGH)
**Problem**: One layer has significantly more commands than neighbors
**Solution**: Check for complex geometry; simplify model or adjust slicer settings

#### Buffer Overflow (HIGH)
**Problem**: Layer has >10,000 commands
**Solution**: Reduce print resolution or use command simplification

## Technical Details

### G-code File Specifications
- **File**: `KNFORG1_150x90x40_5_0.2mm_PETG_MK3S_21h17m.gcode.zip`
- **Layer height**: 0.2mm
- **Target Z**: 31.8mm (approximately layer 159)
- **Printer**: Prusa MK3S
- **Material**: PETG
- **Estimated print time**: 21 hours 17 minutes

### Layer Calculation
With 0.2mm layer height:
- Layer number = Z-height / 0.2
- Z=31.8mm = Layer 159
- Analysis window ±0.5mm covers layers 156-162

## Troubleshooting

### "No .gcode file found in the zip archive"
The zip file doesn't contain a `.gcode` file. Ensure you're using the correct zip file.

### "No layers found near Z=X.Xmm"
The specified Z-height doesn't exist in the file. The tool will suggest the closest Z-height available.

### Script runs but no anomalies found
This means no obvious issues were detected. Consider:
- Checking printer firmware logs
- Verifying SD card integrity
- Testing with different G-code at the same height
- Updating printer firmware
- Checking for hardware issues (thermistor, power supply, etc.)

## Contributing

Feel free to submit issues or pull requests to improve the analysis capabilities.

## License

This project is provided as-is for troubleshooting 3D printing issues.

## Author

Created to diagnose Prusa MK3S freezing issues during PETG prints.
