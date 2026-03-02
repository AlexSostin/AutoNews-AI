#!/usr/bin/env python
"""
Test Analytics — Find duplicate tests, coverage gaps, and prioritize tests.

Usage:
    python scripts/analyze_tests.py              # Full report
    python scripts/analyze_tests.py --duplicates # Only duplicate tests
    python scripts/analyze_tests.py --gaps       # Only coverage gaps
    python scripts/analyze_tests.py --priority   # Priority based on recent changes

Run from backend/ directory:
    cd backend && python scripts/analyze_tests.py
"""

import os
import sys
import ast
import subprocess
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

TESTS_DIR = Path(__file__).parent.parent / 'tests'
BACKEND_DIR = Path(__file__).parent.parent


def collect_test_functions():
    """Parse all test files and extract test function info."""
    tests = []
    
    if not TESTS_DIR.exists():
        print(f"  ⚠️  Tests directory not found: {TESTS_DIR}")
        return tests
    
    for test_file in sorted(TESTS_DIR.glob('test_*.py')):
        try:
            source = test_file.read_text()
            tree = ast.parse(source)
        except SyntaxError:
            continue
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith('test_'):
                    # Get docstring
                    docstring = ast.get_docstring(node) or ''
                    
                    # Get function body as text
                    start = node.lineno - 1
                    end = node.end_lineno or start + 1
                    lines = source.split('\n')[start:end]
                    body = '\n'.join(lines)
                    
                    # Find parent class
                    parent_class = ''
                    for parent_node in ast.walk(tree):
                        if isinstance(parent_node, ast.ClassDef):
                            for child in ast.walk(parent_node):
                                if child is node:
                                    parent_class = parent_node.name
                                    break
                    
                    tests.append({
                        'file': test_file.name,
                        'class': parent_class,
                        'name': node.name,
                        'docstring': docstring,
                        'body': body,
                        'line': node.lineno,
                        'full_name': f"{test_file.name}::{parent_class}::{node.name}" if parent_class else f"{test_file.name}::{node.name}",
                    })
    
    return tests


def find_duplicate_tests(tests):
    """Find tests with very similar bodies using basic text comparison."""
    print('\n' + '═' * 60)
    print('  🔍 Duplicate Test Detection')
    print('═' * 60 + '\n')
    
    if not tests:
        print('  No tests found.')
        return
    
    # Normalize test bodies for comparison
    def normalize(body):
        lines = body.strip().split('\n')
        # Remove docstrings, comments, blank lines
        clean = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                clean.append(stripped)
        return '\n'.join(clean)
    
    duplicates = []
    
    for i in range(len(tests)):
        body_i = normalize(tests[i]['body'])
        if len(body_i) < 30:  # Skip very short tests
            continue
            
        for j in range(i + 1, len(tests)):
            body_j = normalize(tests[j]['body'])
            if len(body_j) < 30:
                continue
            
            # Simple similarity: Jaccard coefficient on line sets
            lines_i = set(body_i.split('\n'))
            lines_j = set(body_j.split('\n'))
            
            if not lines_i or not lines_j:
                continue
            
            intersection = lines_i & lines_j
            union = lines_i | lines_j
            similarity = len(intersection) / len(union) if union else 0
            
            if similarity > 0.80:
                duplicates.append({
                    'test_a': tests[i]['full_name'],
                    'test_b': tests[j]['full_name'],
                    'similarity': round(similarity * 100, 1),
                })
    
    if duplicates:
        for d in sorted(duplicates, key=lambda x: x['similarity'], reverse=True):
            print(f"  ⚠️  {d['similarity']}% similar:")
            print(f"      {d['test_a']}")
            print(f"      {d['test_b']}")
            print()
        print(f"  Total: {len(duplicates)} potential duplicates\n")
    else:
        print('  ✅ No duplicate tests found\n')


def find_coverage_gaps():
    """Find Python source files without corresponding tests."""
    print('\n' + '═' * 60)
    print('  📊 Coverage Gaps — Files Without Tests')
    print('═' * 60 + '\n')
    
    # Source files to check
    source_dirs = [
        BACKEND_DIR / 'news',
        BACKEND_DIR / 'ai_engine',
    ]
    
    source_files = set()
    for src_dir in source_dirs:
        if src_dir.exists():
            for f in src_dir.rglob('*.py'):
                if '__pycache__' in str(f) or f.name.startswith('__'):
                    continue
                if 'migrations' in str(f):
                    continue
                rel = f.relative_to(BACKEND_DIR)
                source_files.add(str(rel))
    
    # Test files
    test_files = set()
    if TESTS_DIR.exists():
        for f in TESTS_DIR.glob('test_*.py'):
            test_files.add(f.name)
    
    # Read test files to find imports
    tested_modules = set()
    for tf in test_files:
        try:
            content = (TESTS_DIR / tf).read_text()
            # Find imports
            for line in content.split('\n'):
                if 'from news' in line or 'from ai_engine' in line:
                    # Extract module path
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        module = parts[1]
                        tested_modules.add(module.replace('.', '/') + '.py')
        except Exception:
            continue
    
    # Find gaps
    gaps = []
    for src in sorted(source_files):
        module_path = src
        is_tested = any(m in module_path for m in tested_modules)
        if not is_tested:
            gaps.append(src)
    
    if gaps:
        for g in gaps:
            print(f"  📋 {g}")
        print(f"\n  Total: {len(gaps)} files without direct test imports")
        print(f"  Tested: {len(source_files) - len(gaps)}/{len(source_files)}\n")
    else:
        print('  ✅ All source files have corresponding tests\n')


def test_prioritization():
    """Suggest tests to run based on recently changed files."""
    print('\n' + '═' * 60)
    print('  🎯 Test Prioritization — Based on Recent Changes')
    print('═' * 60 + '\n')
    
    # Get recently changed files
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD~5', 'HEAD'],
            capture_output=True, text=True, cwd=str(BACKEND_DIR),
            timeout=10
        )
        changed_files = [f for f in result.stdout.strip().split('\n') if f.endswith('.py')]
    except Exception:
        print('  ⚠️  Could not read git history')
        return
    
    if not changed_files:
        print('  No Python files changed in last 5 commits\n')
        return
    
    # Map changed files to relevant tests
    file_to_tests = defaultdict(list)
    
    if TESTS_DIR.exists():
        for test_file in TESTS_DIR.glob('test_*.py'):
            content = test_file.read_text()
            for changed in changed_files:
                basename = Path(changed).stem
                if basename in content:
                    file_to_tests[changed].append(test_file.name)
    
    print(f"  Changed files (last 5 commits): {len(changed_files)}\n")
    
    priority_tests = set()
    for changed, tests in sorted(file_to_tests.items()):
        print(f"  📁 {changed}")
        for t in tests:
            print(f"      → {t}")
            priority_tests.add(t)
        print()
    
    untested_changes = [f for f in changed_files if f not in file_to_tests]
    if untested_changes:
        print(f"  ⚠️  Changed files with NO matching tests:")
        for f in untested_changes:
            print(f"      {f}")
    
    if priority_tests:
        print(f"\n  🏃 Priority test command:")
        tests_str = ' '.join(f'tests/{t}' for t in sorted(priority_tests))
        print(f"      pytest {tests_str} -v\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Test Analytics')
    parser.add_argument('--duplicates', action='store_true', help='Only duplicate tests')
    parser.add_argument('--gaps', action='store_true', help='Only coverage gaps')
    parser.add_argument('--priority', action='store_true', help='Only test prioritization')
    args = parser.parse_args()
    
    run_all = not any([args.duplicates, args.gaps, args.priority])
    
    print('\n🧪 Test Analytics Report')
    print('=' * 60)
    
    tests = collect_test_functions()
    print(f"  Found {len(tests)} test functions\n")
    
    if run_all or args.duplicates:
        find_duplicate_tests(tests)
    
    if run_all or args.gaps:
        find_coverage_gaps()
    
    if run_all or args.priority:
        test_prioritization()
    
    print('✅ Analysis complete!\n')


if __name__ == '__main__':
    main()
