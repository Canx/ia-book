#!/usr/bin/env python3
"""
Script to combine markdown chapters and convert them to PDF
"""

import os
import re
import subprocess
import sys
from pathlib import Path


def get_chapters_in_order(directory):
    """Get all markdown files in the directory ordered by their numeric prefix."""
    chapter_dir = Path(directory)
    markdown_files = [f for f in chapter_dir.glob("*.md") if f.is_file()]
    
    # Sort by the numeric prefix (the part before the first dash)
    def extract_number(file_path):
        match = re.match(r'^(\d+)', file_path.name)
        return int(match.group(1)) if match else float('inf')
    
    sorted_files = sorted(markdown_files, key=extract_number)
    return sorted_files


def combine_chapters(chapter_files, output_file):
    """Combine all chapter files into a single markdown file with proper formatting."""
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Create a clear cover page using HTML to ensure separation
        if os.path.exists("assets/portada-libro.png"):
            # Use HTML for better control over the cover page
            outfile.write("<div style=\"text-align: center; page-break-after: always;\">\n\n")
            outfile.write("![Portada del Libro](assets/portada-libro.png)\n\n")
            outfile.write("<h1>Inteligencia Artificial: Tu Guía Práctica</h1>\n\n")
            outfile.write("<h2>Ruben Cancho Gasulla</h2>\n\n")
            outfile.write("</div>\n\n")
        else:
            # If no cover image, just add the title and ensure page break
            outfile.write("# Inteligencia Artificial: Tu Guía Práctica\n\n")
            outfile.write("## Ruben Cancho Gasulla\n\n")
            outfile.write("\\newpage\n\n")  # LaTeX
            outfile.write("<div style=\"page-break-before: always;\"></div>\n\n")  # HTML/CSS for other engines

        # Write each chapter content
        for i, file_path in enumerate(chapter_files, 1):
            with open(file_path, 'r', encoding='utf-8') as infile:
                content = infile.read()

                # Fix image paths: change ../assets/ to assets/ since combined file is in root
                content = content.replace('../assets/', 'assets/')

                # Resize images and remove alt text, keeping only the image reference with size attributes
                import re
                # This regex finds markdown image references and adds size attributes to make them smaller
                # Convert ![alt text](path) to ![](path){width=50% height=50%} to make them smaller
                content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'![](\2){width=60%}', content)

                # Move the image after the first heading (chapter title)
                # Find the first markdown heading pattern (## or # or ###)
                lines = content.split('\n')
                new_lines = []
                image_found = False
                image_line = ""

                for line in lines:
                    # If it's an image line, save it but don't add it yet
                    if line.strip().startswith('![](') and ('.png' in line or '.jpg' in line or '.jpeg' in line or '.gif' in line or '.svg' in line):
                        image_line = line
                        image_found = True
                    else:
                        # Otherwise, add the line to the new content
                        new_lines.append(line)

                # Rebuild content: put the image after the first heading
                rebuilt_content = "\n".join(new_lines)
                if image_found:
                    # Find the first heading and insert image after it
                    rebuilt_content = re.sub(r'(^[#]+.*$\n)', r'\1\n' + image_line + '\n', rebuilt_content, count=1, flags=re.MULTILINE)

                # Add page break between chapters (except for the first one)
                if i > 1:
                    outfile.write("\n\\newpage\n\n")  # LaTeX
                    outfile.write("\n<div style=\"page-break-before: always;\"></div>\n\n")  # HTML/CSS for other engines

                # Write the content
                outfile.write(rebuilt_content)
                outfile.write("\n\n")  # Add some spacing between chapters


def convert_to_pdf(input_md, output_pdf, title="Inteligencia Artificial: Tu Guía Práctica"):
    """Convert markdown file to PDF using Pandoc."""
    try:
        # First try with pdflatex if available
        result = subprocess.run(['which', 'pdflatex'], capture_output=True, text=True)
        has_latex = result.returncode == 0

        if has_latex:
            # Prepare pandoc command with LaTeX styling options
            cmd = [
                'pandoc',
                input_md,
                '-o', output_pdf,
                '--pdf-engine=pdflatex',  # Use LaTeX to generate PDF
                '--toc',  # Include table of contents
                '--toc-depth=2',  # Include up to level 2 headers in TOC
                '--highlight-style=pygments',  # Syntax highlighting style
                '--variable', 'geometry:margin=1in',  # Set page margins
                '--variable', f'title:{title}',  # Set document title
                '--variable', 'author:Ruben Cancho Gasulla',  # Set author
                '--variable', 'date:\\today',  # Add today's date
                '--variable', 'classoption=oneside',  # Remove blank pages in print
            ]
        else:
            # Check for alternative PDF engines
            pdf_engine = None
            for engine in ['wkhtmltopdf', 'weasyprint']:
                result = subprocess.run(['which', engine], capture_output=True, text=True)
                if result.returncode == 0:
                    pdf_engine = engine
                    break

            if pdf_engine:
                print(f"LaTeX not found, using {pdf_engine} for PDF conversion...")
                cmd = [
                    'pandoc',
                    input_md,
                    '-o', output_pdf,
                    f'--pdf-engine={pdf_engine}',
                    '--toc',  # Include table of contents
                    '--toc-depth=2',  # Include up to level 2 headers in TOC
                    '--highlight-style=pygments',  # Syntax highlighting style
                    '--variable', f'title:{title}',  # Set document title
                    '--variable', 'author:Ruben Cancho Gasulla',  # Set author
                    '--variable', 'date:' + subprocess.check_output(['date', '+%d/%m/%Y'], text=True).strip(),  # Add current date
                ]
            else:
                # No advanced PDF engine available, try basic standalone
                print("No advanced PDF engine found, using basic conversion...")
                cmd = [
                    'pandoc',
                    input_md,
                    '-o', output_pdf,
                    '--standalone',  # Just basic standalone document
                    '--variable', f'title:{title}',  # Set document title
                    '--variable', 'author:Ruben Cancho Gasulla',  # Set author
                ]

        # Add resource path for images (assets directory)
        cmd.extend(['--resource-path', '.'])  # Look for resources in current directory and subdirectories

        # Try to run the selected command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Successfully converted {input_md} to {output_pdf}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Pandoc conversion failed: {e}")
        print(f"Error output: {e.stderr}")

        # Try a simpler approach without table of contents or complex formatting
        print("Attempting simpler conversion...")
        try:
            cmd_simple = [
                'pandoc',
                input_md,
                '-o', output_pdf,
                '--standalone',  # Just basic standalone document
                '--variable', f'title:{title}',  # Set document title
                '--variable', 'author:Ruben Cancho Gasulla',  # Set author
            ]
            # Add resource path for images (assets directory)
            cmd_simple.extend(['--resource-path', '.'])  # Look for resources in current directory and subdirectories
            result = subprocess.run(cmd_simple, capture_output=True, text=True, check=True)
            print(f"Successfully converted {input_md} to {output_pdf} using simple method")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Simple conversion also failed: {e}")
            return False
    except FileNotFoundError:
        print("Pandoc is not installed or not in PATH")
        return False


def main():
    """Main function to process the book conversion."""
    chapter_dir = "./chapters"
    temp_combined = "./book_temp.md"
    output_pdf = "./libro_IA.pdf"
    
    print("Gathering chapters...")
    chapter_files = get_chapters_in_order(chapter_dir)
    
    if not chapter_files:
        print(f"No markdown files found in {chapter_dir}")
        sys.exit(1)
    
    print(f"Found {len(chapter_files)} chapters:")
    for f in chapter_files:
        print(f"  - {f.name}")
    
    print("\nCombining chapters...")
    combine_chapters(chapter_files, temp_combined)
    print(f"Combined chapters into {temp_combined}")
    
    print("\nConverting to PDF...")
    success = convert_to_pdf(temp_combined, output_pdf)
    
    if success:
        print(f"\n✅ PDF created successfully: {output_pdf}")
    else:
        print(f"\n❌ Failed to create PDF: {output_pdf}")
        sys.exit(1)
    
    # Clean up temporary file
    try:
        os.remove(temp_combined)
        print(f"Cleaned up temporary file: {temp_combined}")
    except OSError as e:
        print(f"Could not remove temporary file {temp_combined}: {e}")


if __name__ == "__main__":
    main()
