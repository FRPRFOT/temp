#!/usr/bin/env python3
"""
G-code Analyzer for 3D Printer Freezing Issue
Analyzes G-code to identify anomalies at specific Z-heights
"""

import zipfile
import os
import sys
import re
from collections import defaultdict, Counter
from datetime import datetime


class GCodeAnalyzer:
    def __init__(self, gcode_file):
        self.gcode_file = gcode_file
        self.lines = []
        self.layers = defaultdict(list)  # Z-height -> list of (line_number, command)
        self.z_heights = []  # Ordered list of unique Z heights
        self.current_z = 0.0
        self.stats = {
            'total_lines': 0,
            'total_layers': 0,
            'commands': Counter(),
            'temperature_changes': [],
            'tool_changes': [],
            'pauses': [],
            'fan_changes': [],
        }
        
    def extract_gcode(self):
        """Extract G-code from zip file"""
        print(f"Extracting G-code from {self.gcode_file}...")
        
        if self.gcode_file.endswith('.zip'):
            with zipfile.ZipFile(self.gcode_file, 'r') as zip_ref:
                # Get the list of files in the zip
                file_list = zip_ref.namelist()
                gcode_files = [f for f in file_list if f.endswith('.gcode')]
                
                if not gcode_files:
                    raise ValueError("No .gcode file found in the zip archive")
                
                # Use the first .gcode file
                gcode_filename = gcode_files[0]
                print(f"Found G-code file: {gcode_filename}")
                
                # Read the content
                with zip_ref.open(gcode_filename) as f:
                    content = f.read().decode('utf-8', errors='ignore')
                    self.lines = content.splitlines()
        else:
            # Direct .gcode file
            with open(self.gcode_file, 'r', encoding='utf-8', errors='ignore') as f:
                self.lines = f.readlines()
        
        print(f"Loaded {len(self.lines)} lines of G-code")
        
    def parse_gcode(self):
        """Parse G-code and track Z-heights"""
        print("Parsing G-code...")
        
        for line_num, line in enumerate(self.lines, 1):
            # Remove comments but keep track of them
            line_clean = line.strip()
            
            if not line_clean or line_clean.startswith(';'):
                # Store comment lines for layer markers
                if 'Z:' in line_clean or 'LAYER:' in line_clean:
                    self.layers[self.current_z].append((line_num, line_clean))
                continue
            
            # Remove inline comments
            if ';' in line_clean:
                command, comment = line_clean.split(';', 1)
                command = command.strip()
            else:
                command = line_clean
                comment = ""
            
            if not command:
                continue
            
            # Track command types
            cmd_type = command.split()[0] if command else ""
            self.stats['commands'][cmd_type] += 1
            
            # Check for Z movement (G0, G1)
            if command.startswith('G0 ') or command.startswith('G1 '):
                z_match = re.search(r'Z([-+]?\d*\.?\d+)', command)
                if z_match:
                    new_z = float(z_match.group(1))
                    if new_z != self.current_z:
                        self.current_z = round(new_z, 3)  # Round to avoid floating point issues
                        if self.current_z not in [round(z, 3) for z in self.z_heights]:
                            self.z_heights.append(self.current_z)
            
            # Store command at current Z height
            self.layers[self.current_z].append((line_num, command))
            
            # Track special commands
            if cmd_type in ['M104', 'M109', 'M140', 'M190']:
                self.stats['temperature_changes'].append((line_num, self.current_z, command))
            
            if cmd_type in ['T0', 'T1']:
                self.stats['tool_changes'].append((line_num, self.current_z, command))
            
            if cmd_type in ['M0', 'M1', 'M25', 'M226']:
                self.stats['pauses'].append((line_num, self.current_z, command))
            
            if cmd_type in ['M106', 'M107']:
                self.stats['fan_changes'].append((line_num, self.current_z, command))
        
        self.stats['total_lines'] = len(self.lines)
        self.stats['total_layers'] = len(self.z_heights)
        self.z_heights.sort()
        
        print(f"Found {self.stats['total_layers']} unique Z-heights")
        
    def analyze_z_region(self, target_z, window=0.5):
        """Analyze a specific Z-height region"""
        print(f"\n{'='*80}")
        print(f"ANALYZING Z={target_z}mm (±{window}mm)")
        print(f"{'='*80}\n")
        
        # Find Z heights in range
        z_in_range = [z for z in self.z_heights if abs(z - target_z) <= window]
        
        if not z_in_range:
            print(f"WARNING: No layers found near Z={target_z}mm")
            closest_z = min(self.z_heights, key=lambda z: abs(z - target_z))
            print(f"Closest Z-height is {closest_z}mm")
            return None
        
        print(f"Found {len(z_in_range)} layers in range: {z_in_range}\n")
        
        analysis = {
            'target_z': target_z,
            'z_range': z_in_range,
            'layers': {},
            'anomalies': [],
        }
        
        # Analyze each layer in range
        for z in z_in_range:
            layer_data = self.layers[z]
            
            # Extract commands (without line numbers)
            commands = [cmd for _, cmd in layer_data]
            
            # Command statistics
            cmd_counter = Counter()
            movements = []
            extrusions = []
            arcs = []
            temperatures = []
            pauses = []
            fans = []
            
            prev_x, prev_y, prev_e = None, None, None
            
            for line_num, cmd in layer_data:
                cmd_type = cmd.split()[0] if cmd else ""
                cmd_counter[cmd_type] += 1
                
                # Track movements
                if cmd_type in ['G0', 'G1']:
                    x_match = re.search(r'X([-+]?\d*\.?\d+)', cmd)
                    y_match = re.search(r'Y([-+]?\d*\.?\d+)', cmd)
                    e_match = re.search(r'E([-+]?\d*\.?\d+)', cmd)
                    f_match = re.search(r'F([-+]?\d*\.?\d+)', cmd)
                    
                    x = float(x_match.group(1)) if x_match else prev_x
                    y = float(y_match.group(1)) if y_match else prev_y
                    e = float(e_match.group(1)) if e_match else prev_e
                    f = float(f_match.group(1)) if f_match else None
                    
                    # Check for large jumps
                    if prev_x is not None and x is not None and prev_y is not None and y is not None:
                        dist = ((x - prev_x)**2 + (y - prev_y)**2)**0.5
                        if dist > 50:  # Large movement > 50mm
                            movements.append({
                                'line': line_num,
                                'distance': dist,
                                'from': (prev_x, prev_y),
                                'to': (x, y),
                                'command': cmd
                            })
                    
                    # Check for extrusion
                    if e is not None and prev_e is not None:
                        e_diff = e - prev_e
                        if abs(e_diff) > 5:  # Large extrusion/retraction
                            extrusions.append({
                                'line': line_num,
                                'amount': e_diff,
                                'command': cmd
                            })
                    
                    prev_x, prev_y, prev_e = x, y, e
                
                # Track arcs (buffer-heavy)
                elif cmd_type in ['G2', 'G3']:
                    arcs.append((line_num, cmd))
                
                # Track temperature changes
                elif cmd_type in ['M104', 'M109', 'M140', 'M190']:
                    temp_match = re.search(r'S(\d+)', cmd)
                    temp = int(temp_match.group(1)) if temp_match else None
                    temperatures.append((line_num, cmd_type, temp))
                
                # Track pauses
                elif cmd_type in ['M0', 'M1', 'M25', 'M226']:
                    pauses.append((line_num, cmd))
                
                # Track fan changes
                elif cmd_type in ['M106', 'M107']:
                    fans.append((line_num, cmd))
            
            analysis['layers'][z] = {
                'line_range': (layer_data[0][0], layer_data[-1][0]) if layer_data else (0, 0),
                'command_count': len(commands),
                'command_types': dict(cmd_counter),
                'large_movements': movements,
                'large_extrusions': extrusions,
                'arcs': arcs,
                'temperature_changes': temperatures,
                'pauses': pauses,
                'fan_changes': fans,
            }
        
        # Identify anomalies
        self._identify_anomalies(analysis)
        
        return analysis
    
    def _identify_anomalies(self, analysis):
        """Identify suspicious patterns in the analysis"""
        target_z = analysis['target_z']
        
        # Check each layer for anomalies
        for z, layer in analysis['layers'].items():
            # Check for pause commands
            if layer['pauses']:
                analysis['anomalies'].append({
                    'type': 'PAUSE_COMMAND',
                    'z': z,
                    'severity': 'CRITICAL',
                    'description': f"Found {len(layer['pauses'])} pause command(s) at Z={z}mm",
                    'details': layer['pauses']
                })
            
            # Check for excessive arcs
            if len(layer['arcs']) > 100:
                analysis['anomalies'].append({
                    'type': 'EXCESSIVE_ARCS',
                    'z': z,
                    'severity': 'HIGH',
                    'description': f"Found {len(layer['arcs'])} arc commands at Z={z}mm (buffer-intensive)",
                    'details': f"First few: {layer['arcs'][:5]}"
                })
            
            # Check for large movements
            if layer['large_movements']:
                analysis['anomalies'].append({
                    'type': 'LARGE_MOVEMENT',
                    'z': z,
                    'severity': 'MEDIUM',
                    'description': f"Found {len(layer['large_movements'])} large movement(s) >50mm at Z={z}mm",
                    'details': layer['large_movements']
                })
            
            # Check for temperature changes mid-layer
            if layer['temperature_changes']:
                analysis['anomalies'].append({
                    'type': 'TEMPERATURE_CHANGE',
                    'z': z,
                    'severity': 'MEDIUM',
                    'description': f"Found {len(layer['temperature_changes'])} temperature change(s) at Z={z}mm",
                    'details': layer['temperature_changes']
                })
            
            # Check for excessive commands (buffer issues)
            if layer['command_count'] > 10000:
                analysis['anomalies'].append({
                    'type': 'EXCESSIVE_COMMANDS',
                    'z': z,
                    'severity': 'HIGH',
                    'description': f"Layer has {layer['command_count']} commands (potential buffer issue)",
                    'details': layer['command_types']
                })
        
        # Compare with neighboring layers
        z_list = sorted(analysis['layers'].keys())
        if len(z_list) > 1:
            # Find the target Z or closest
            target_idx = min(range(len(z_list)), key=lambda i: abs(z_list[i] - target_z))
            
            if target_idx > 0 and target_idx < len(z_list) - 1:
                prev_z = z_list[target_idx - 1]
                curr_z = z_list[target_idx]
                next_z = z_list[target_idx + 1]
                
                prev_count = analysis['layers'][prev_z]['command_count']
                curr_count = analysis['layers'][curr_z]['command_count']
                next_count = analysis['layers'][next_z]['command_count']
                
                avg_neighbor = (prev_count + next_count) / 2
                
                # If current layer has significantly more commands
                if curr_count > avg_neighbor * 2:
                    analysis['anomalies'].append({
                        'type': 'COMMAND_COUNT_SPIKE',
                        'z': curr_z,
                        'severity': 'HIGH',
                        'description': f"Layer at Z={curr_z}mm has {curr_count} commands vs avg {avg_neighbor:.0f} in neighbors",
                        'details': f"Prev: {prev_count}, Curr: {curr_count}, Next: {next_count}"
                    })
    
    def generate_report(self, analysis, output_file='gcode_analysis_report.txt'):
        """Generate detailed text report"""
        print(f"\nGenerating detailed report: {output_file}")
        
        with open(output_file, 'w') as f:
            # Header
            f.write("="*80 + "\n")
            f.write("G-CODE ANALYSIS REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"File: {self.gcode_file}\n")
            f.write("="*80 + "\n\n")
            
            # Overall statistics
            f.write("OVERALL STATISTICS\n")
            f.write("-"*80 + "\n")
            f.write(f"Total lines: {self.stats['total_lines']:,}\n")
            f.write(f"Total layers: {self.stats['total_layers']}\n")
            f.write(f"Z range: {min(self.z_heights):.3f}mm to {max(self.z_heights):.3f}mm\n")
            f.write(f"\nCommand types:\n")
            for cmd, count in self.stats['commands'].most_common(20):
                f.write(f"  {cmd:10s}: {count:,}\n")
            
            f.write(f"\nTemperature changes: {len(self.stats['temperature_changes'])}\n")
            f.write(f"Tool changes: {len(self.stats['tool_changes'])}\n")
            f.write(f"Pause commands: {len(self.stats['pauses'])}\n")
            f.write(f"Fan changes: {len(self.stats['fan_changes'])}\n")
            
            if not analysis:
                f.write("\nNo analysis data available.\n")
                return
            
            # Target Z analysis
            f.write(f"\n{'='*80}\n")
            f.write(f"DETAILED ANALYSIS: Z={analysis['target_z']}mm REGION\n")
            f.write(f"{'='*80}\n\n")
            
            f.write(f"Layers analyzed: {len(analysis['z_range'])}\n")
            f.write(f"Z-heights in range: {', '.join(f'{z:.3f}mm' for z in analysis['z_range'])}\n\n")
            
            # Layer-by-layer details
            for z in sorted(analysis['layers'].keys()):
                layer = analysis['layers'][z]
                f.write(f"\n{'-'*80}\n")
                f.write(f"Layer at Z={z:.3f}mm\n")
                f.write(f"{'-'*80}\n")
                f.write(f"Line range: {layer['line_range'][0]:,} - {layer['line_range'][1]:,}\n")
                f.write(f"Total commands: {layer['command_count']:,}\n")
                
                f.write(f"\nCommand breakdown:\n")
                for cmd, count in sorted(layer['command_types'].items(), key=lambda x: -x[1])[:15]:
                    f.write(f"  {cmd:10s}: {count:,}\n")
                
                if layer['arcs']:
                    f.write(f"\nArc commands (G2/G3): {len(layer['arcs'])}\n")
                    if len(layer['arcs']) <= 5:
                        for line_num, cmd in layer['arcs']:
                            f.write(f"  Line {line_num}: {cmd}\n")
                    else:
                        for line_num, cmd in layer['arcs'][:3]:
                            f.write(f"  Line {line_num}: {cmd}\n")
                        f.write(f"  ... and {len(layer['arcs']) - 3} more\n")
                
                if layer['large_movements']:
                    f.write(f"\nLarge movements (>50mm): {len(layer['large_movements'])}\n")
                    for mv in layer['large_movements'][:5]:
                        f.write(f"  Line {mv['line']}: {mv['distance']:.2f}mm - {mv['command']}\n")
                
                if layer['large_extrusions']:
                    f.write(f"\nLarge extrusions/retractions: {len(layer['large_extrusions'])}\n")
                    for ex in layer['large_extrusions'][:5]:
                        f.write(f"  Line {ex['line']}: {ex['amount']:.3f}mm - {ex['command']}\n")
                
                if layer['temperature_changes']:
                    f.write(f"\nTemperature changes:\n")
                    for line_num, cmd_type, temp in layer['temperature_changes']:
                        f.write(f"  Line {line_num}: {cmd_type} S{temp}\n")
                
                if layer['pauses']:
                    f.write(f"\nPAUSE COMMANDS FOUND:\n")
                    for line_num, cmd in layer['pauses']:
                        f.write(f"  Line {line_num}: {cmd}\n")
                
                if layer['fan_changes']:
                    f.write(f"\nFan changes:\n")
                    for line_num, cmd in layer['fan_changes'][:10]:
                        f.write(f"  Line {line_num}: {cmd}\n")
            
            # Anomalies section
            f.write(f"\n{'='*80}\n")
            f.write("ANOMALIES DETECTED\n")
            f.write(f"{'='*80}\n\n")
            
            if analysis['anomalies']:
                # Sort by severity
                severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
                sorted_anomalies = sorted(analysis['anomalies'], 
                                         key=lambda x: severity_order.get(x['severity'], 99))
                
                for anom in sorted_anomalies:
                    f.write(f"\n[{anom['severity']}] {anom['type']}\n")
                    f.write(f"Z-height: {anom['z']:.3f}mm\n")
                    f.write(f"Description: {anom['description']}\n")
                    f.write(f"Details: {anom['details']}\n")
            else:
                f.write("No significant anomalies detected.\n")
            
            # Recommendations
            f.write(f"\n{'='*80}\n")
            f.write("RECOMMENDATIONS\n")
            f.write(f"{'='*80}\n\n")
            
            if analysis['anomalies']:
                critical = [a for a in analysis['anomalies'] if a['severity'] == 'CRITICAL']
                high = [a for a in analysis['anomalies'] if a['severity'] == 'HIGH']
                
                if critical:
                    f.write("CRITICAL ISSUES:\n")
                    for anom in critical:
                        if anom['type'] == 'PAUSE_COMMAND':
                            f.write(f"- Pause command found at Z={anom['z']:.3f}mm - This likely causes the freeze!\n")
                            f.write(f"  Remove or comment out the pause command(s) in the G-code.\n")
                
                if high:
                    f.write("\nHIGH PRIORITY:\n")
                    for anom in high:
                        if anom['type'] == 'EXCESSIVE_ARCS':
                            f.write(f"- Excessive arc commands at Z={anom['z']:.3f}mm may cause buffer issues\n")
                            f.write(f"  Consider adjusting slicer settings to reduce arc resolution.\n")
                        elif anom['type'] == 'EXCESSIVE_COMMANDS':
                            f.write(f"- Very high command count at Z={anom['z']:.3f}mm\n")
                            f.write(f"  May overwhelm printer buffer. Check slicer resolution settings.\n")
                        elif anom['type'] == 'COMMAND_COUNT_SPIKE':
                            f.write(f"- Command count spike at Z={anom['z']:.3f}mm\n")
                            f.write(f"  Check for complex geometry or slicer artifacts.\n")
                
                # If no critical or high issues found
                if not critical and not high:
                    f.write("No critical or high-priority issues found at Z={:.1f}mm.\n\n".format(analysis['target_z']))
                    f.write("The detected medium-priority items (large travel movements) are normal\n")
                    f.write("for this print and should not cause freezing.\n\n")
                    f.write("Since no G-code anomalies were found, consider:\n")
                    f.write("- Checking printer firmware logs for errors\n")
                    f.write("- Verifying SD card integrity (try a different card)\n")
                    f.write("- Testing with a different G-code file at the same height\n")
                    f.write("- Updating printer firmware to the latest version\n")
                    f.write("- Checking for hardware issues (thermistor, power supply, stepper drivers)\n")
                    f.write("- Monitoring printer temperature - overheating can cause freezes\n")
                    f.write("- Checking if the issue occurs at the exact same Z-height consistently\n")
            else:
                f.write("No obvious issues found. Consider:\n")
                f.write("- Checking printer firmware logs\n")
                f.write("- Verifying SD card integrity\n")
                f.write("- Testing with a different G-code file at same height\n")
                f.write("- Updating printer firmware\n")
        
        print(f"Report saved to: {output_file}")
    
    def print_summary(self, analysis):
        """Print summary to console"""
        print(f"\n{'='*80}")
        print("ANALYSIS SUMMARY")
        print(f"{'='*80}\n")
        
        print(f"File: {self.gcode_file}")
        print(f"Total lines: {self.stats['total_lines']:,}")
        print(f"Total layers: {self.stats['total_layers']}")
        print(f"Z range: {min(self.z_heights):.3f}mm to {max(self.z_heights):.3f}mm\n")
        
        if not analysis:
            print("No analysis data available.")
            return
        
        print(f"Target Z: {analysis['target_z']}mm")
        print(f"Layers analyzed: {len(analysis['z_range'])}")
        print(f"Z-heights in range: {', '.join(f'{z:.3f}mm' for z in analysis['z_range'])}\n")
        
        # Show anomalies
        if analysis['anomalies']:
            print(f"ANOMALIES FOUND: {len(analysis['anomalies'])}\n")
            
            # Group by severity
            by_severity = defaultdict(list)
            for anom in analysis['anomalies']:
                by_severity[anom['severity']].append(anom)
            
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if severity in by_severity:
                    print(f"{severity}:")
                    for anom in by_severity[severity]:
                        print(f"  - {anom['description']}")
                    print()
            
            # Highlight critical issues
            critical = [a for a in analysis['anomalies'] if a['severity'] == 'CRITICAL']
            if critical:
                print("⚠️  CRITICAL: " + critical[0]['description'])
                print("   This is likely the cause of the printer freeze!\n")
        else:
            print("No significant anomalies detected.\n")
        
        # Show layer statistics
        print("LAYER STATISTICS:")
        for z in sorted(analysis['layers'].keys()):
            layer = analysis['layers'][z]
            print(f"  Z={z:.3f}mm: Lines {layer['line_range'][0]:,}-{layer['line_range'][1]:,}, "
                  f"{layer['command_count']:,} commands")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze G-code for 3D printer freezing issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s file.gcode.zip -z 31.8
  %(prog)s file.gcode -z 31.8 -w 1.0 -o report.txt
        """
    )
    parser.add_argument('gcode_file', help='G-code file or .zip file containing G-code')
    parser.add_argument('-z', '--target-z', type=float, default=31.8,
                       help='Target Z-height to analyze (default: 31.8mm)')
    parser.add_argument('-w', '--window', type=float, default=0.5,
                       help='Analysis window around target Z (default: ±0.5mm)')
    parser.add_argument('-o', '--output', default='gcode_analysis_report.txt',
                       help='Output report file (default: gcode_analysis_report.txt)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.gcode_file):
        print(f"ERROR: File not found: {args.gcode_file}")
        sys.exit(1)
    
    print("G-CODE ANALYZER")
    print("="*80)
    print()
    
    try:
        # Create analyzer
        analyzer = GCodeAnalyzer(args.gcode_file)
        
        # Extract and parse
        analyzer.extract_gcode()
        analyzer.parse_gcode()
        
        # Analyze target region
        analysis = analyzer.analyze_z_region(args.target_z, args.window)
        
        # Generate outputs
        analyzer.print_summary(analysis)
        analyzer.generate_report(analysis, args.output)
        
        print(f"\n{'='*80}")
        print("Analysis complete!")
        print(f"Detailed report saved to: {args.output}")
        print("="*80)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
