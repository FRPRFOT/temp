# Example Usage of G-code Analyzer

## Quick Start

Analyze the included G-code file for issues at Z=31.8mm (where the freeze occurs):

```bash
python3 analyze_gcode.py KNFORG1_150x90x40_5_0.2mm_PETG_MK3S_21h17m.gcode.zip
```

## Example Output

The tool will:
1. Extract and parse 1.3+ million lines of G-code
2. Identify 253 unique Z-heights
3. Focus analysis on layers around Z=31.8mm
4. Generate both console output and a detailed report

### Console Output Preview

```
G-CODE ANALYZER
================================================================================

Extracting G-code from KNFORG1_150x90x40_5_0.2mm_PETG_MK3S_21h17m.gcode.zip...
Found G-code file: KNFORG1_150x90x40_5_0.2mm_PETG_MK3S_21h17m.gcode
Loaded 1,324,410 lines of G-code
Parsing G-code...
Found 253 unique Z-heights

================================================================================
ANALYZING Z=31.8mm (±0.5mm)
================================================================================

Found 5 layers in range: [31.4, 31.6, 31.8, 32.0, 32.2]

ANOMALIES FOUND: 5

MEDIUM:
  - Found 79 large movement(s) >50mm at Z=31.4mm
  - Found 80 large movement(s) >50mm at Z=31.6mm
  - Found 81 large movement(s) >50mm at Z=31.8mm
  - Found 82 large movement(s) >50mm at Z=32.0mm
  - Found 81 large movement(s) >50mm at Z=32.2mm

LAYER STATISTICS:
  Z=31.400mm: Lines 860,534-871,126, 5,567 commands
  Z=31.600mm: Lines 865,504-876,802, 5,606 commands
  Z=31.800mm: Lines 871,131-881,784, 4,915 commands
  Z=32.000mm: Lines 876,807-886,924, 5,071 commands
  Z=32.200mm: Lines 881,789-892,072, 5,080 commands
```

## Analysis Results for This File

### What Was Found
- **No critical issues** - No pause commands (M0, M1, M25, M226)
- **No high-priority issues** - No excessive arcs or buffer-overwhelming command counts
- **Only medium-priority items** - Large travel movements >50mm (normal for this print)

### Conclusion
The G-code at Z=31.8mm appears **normal** with no anomalies that would cause freezing.

### Recommendations
Since the G-code is clean, the freeze is likely caused by:
1. **SD card issues** - Try a different, high-quality SD card
2. **Firmware bug** - Update to latest Prusa firmware
3. **Hardware problem** - Check thermistor, power supply, stepper drivers
4. **Overheating** - Monitor printer temperatures
5. **File corruption** - Re-slice the model and compare

## Advanced Usage Examples

### Analyze a Different Z-Height
```bash
python3 analyze_gcode.py KNFORG1_150x90x40_5_0.2mm_PETG_MK3S_21h17m.gcode.zip -z 50.0
```

### Wider Analysis Window
```bash
python3 analyze_gcode.py KNFORG1_150x90x40_5_0.2mm_PETG_MK3S_21h17m.gcode.zip -z 31.8 -w 1.0
```

### Custom Output File
```bash
python3 analyze_gcode.py KNFORG1_150x90x40_5_0.2mm_PETG_MK3S_21h17m.gcode.zip -o my_analysis.txt
```

## Report Structure

The detailed report (`gcode_analysis_report.txt`) includes:

1. **Overall Statistics** - Total lines, layers, command breakdown
2. **Detailed Layer Analysis** - Command counts, movements, extrusions
3. **Anomaly Detection** - Categorized by severity (CRITICAL, HIGH, MEDIUM, LOW)
4. **Recommendations** - Specific actions based on findings

## Performance

- **File size**: 5.4 MB (compressed), ~50+ MB uncompressed
- **Processing time**: ~2 minutes on modern hardware
- **Memory usage**: ~200-300 MB during parsing
- **Output size**: ~60 KB detailed report

## What the Tool Checks

✅ Pause/wait commands (M0, M1, M25, M226)
✅ Temperature changes (M104, M109, M140, M190)
✅ Tool changes (T0, T1)
✅ Arc commands (G2, G3) - can cause buffer issues
✅ Large coordinate jumps
✅ Extrusion anomalies
✅ Fan changes (M106, M107)
✅ Command count spikes
✅ Buffer-overwhelming operations

## Troubleshooting the Freeze

If this analysis shows no G-code issues (as in this case), try:

1. **Test at same height with different file** - Re-slice and test
2. **Test at different height** - See if issue is Z-height specific or time-based
3. **Check SD card** - Format with SD Card Formatter, try different card
4. **Update firmware** - Get latest from Prusa
5. **Check logs** - Look for errors in printer's diagnostic logs
6. **Hardware check** - Inspect connections, thermistors, power supply
7. **Temperature monitoring** - Watch for overheating components
