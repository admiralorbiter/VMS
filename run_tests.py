#!/usr/bin/env python3
"""
Test runner script for VMS application.
Provides easy commands to run different types of tests.
"""

import sys
import subprocess
import argparse

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False

def main():
    parser = argparse.ArgumentParser(description='VMS Test Runner')
    parser.add_argument('--type', choices=['unit', 'integration', 'all', 'fast', 'salesforce'], 
                       default='fast', help='Type of tests to run')
    parser.add_argument('--file', help='Specific test file to run')
    parser.add_argument('--function', help='Specific test function to run')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage report')
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Add verbosity
    if args.verbose:
        cmd.extend(['-v', '-s'])
    else:
        cmd.extend(['-q'])
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend(['--cov=.', '--cov-report=term-missing'])
    
    # Determine what to run based on type
    description = ""
    if args.type == 'unit':
        cmd.append('tests/unit/')
        description = "Unit Tests"
    elif args.type == 'integration':
        cmd.extend(['-m', 'integration'])
        cmd.append('tests/')  # Add tests directory
        description = "Integration Tests"
    elif args.type == 'all':
        cmd.append('tests/')
        description = "All Tests"
    elif args.type == 'fast':
        cmd.extend(['-m', 'not slow'])
        cmd.append('tests/')  # Add tests directory
        description = "Fast Tests (excluding slow tests)"
    elif args.type == 'salesforce':
        cmd.extend(['-m', 'salesforce'])
        cmd.append('tests/')  # Add tests directory
        description = "Salesforce Integration Tests"
    
    # Add specific file if provided
    if args.file:
        cmd.append(args.file)
        description = f"{description} - {args.file}"
    
    # Add specific function if provided
    if args.function:
        if args.file:
            cmd.append(f"::{args.function}")
        else:
            cmd.extend(['-k', args.function])
        description = f"{description} - {args.function}"
    
    # Run the tests
    success = run_command(cmd, description)
    
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main() 