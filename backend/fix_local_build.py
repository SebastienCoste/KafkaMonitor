#!/usr/bin/env python3
"""
Post-build fix for local development
This script ensures the built frontend works with run_local.py
"""
import os
import shutil
from pathlib import Path

def fix_local_build():
    """Fix the built frontend for local development"""
    print("🔧 Fixing frontend build for local development...")
    
    # Paths
    frontend_dir = Path("../frontend")
    build_dir = frontend_dir / "build"
    index_file = build_dir / "index.html"
    
    if not build_dir.exists():
        print("❌ Frontend build directory not found. Run 'npm run build' first.")
        return False
    
    if not index_file.exists():
        print("❌ index.html not found in build directory.")
        return False
    
    # Read the current index.html
    with open(index_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    print("📄 Current index.html preview:")
    # Show static file references
    for line in html_content.split('\n'):
        if 'static/' in line:
            print(f"   {line.strip()}")
    
    # Ensure static paths use /static/ (not /api/static/)
    original_content = html_content
    html_content = html_content.replace('src="/api/static/', 'src="/static/')
    html_content = html_content.replace('href="/api/static/', 'href="/static/')
    
    if html_content != original_content:
        # Write the fixed content back
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("✅ Fixed static file paths for local development")
    else:
        print("✅ Static file paths are already correct for local development")
    
    # Check if static files exist
    static_dir = build_dir / "static"
    if static_dir.exists():
        js_files = list((static_dir / "js").glob("*.js"))
        css_files = list((static_dir / "css").glob("*.css"))
        print(f"📁 Found {len(js_files)} JS files and {len(css_files)} CSS files")
    else:
        print("❌ Static directory not found in build")
        return False
    
    print("🎉 Frontend build is ready for local development!")
    print("\n💡 Usage:")
    print("   cd backend")
    print("   python run_local.py")
    print("   # Then open http://localhost:8001 in your browser")
    
    return True

if __name__ == "__main__":
    fix_local_build()