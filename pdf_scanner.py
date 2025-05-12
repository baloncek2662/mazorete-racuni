import fitz  # PyMuPDF
from pathlib import Path


def extract_trr_name(pdf_path):
    """
    Extract the name that follows the TRR line from a PDF file.
    Returns None if TRR line is not found.
    """
    try:
        # Open the PDF
        doc = fitz.open(pdf_path)

        # Get the first page
        page = doc[0]

        # Extract text
        text = page.get_text()

        # Split into lines
        lines = text.split('\n')

        # Find the line with TRR
        for i, line in enumerate(lines):
            if line.startswith('TRR:'):
                # Return the next line if it exists
                if i + 1 < len(lines):
                    return lines[i + 1].strip()
                break

        return None

    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        return None
    finally:
        if 'doc' in locals():
            doc.close()


def get_unique_filename(base_path, new_name):
    """
    Generate a unique filename by adding a suffix if the file already exists.
    Returns the path with a unique filename.
    """
    counter = 1
    base_name = new_name.stem
    extension = new_name.suffix
    new_path = new_name

    while new_path.exists():
        new_path = base_path / f"{base_name}_{counter}{extension}"
        counter += 1

    return new_path


def rename_pdfs():
    """
    Process all PDFs in the download folder and rename them based on TRR information.
    """
    # Get the download directory
    download_dir = Path('download')
    print(download_dir)

    # Process each PDF file
    for pdf_file in download_dir.glob('*.pdf'):
        print(f"Processing {pdf_file.name}...")

        # Extract the name from the PDF
        new_name = extract_trr_name(pdf_file)

        if new_name:
            # Create new filename
            new_filename = f"{new_name}.pdf"
            new_path = get_unique_filename(download_dir, pdf_file.parent / new_filename)

            # Rename the file
            try:
                pdf_file.rename(new_path)
                print(f"Renamed to: {new_path.name}")
            except Exception as e:
                msg = f"Error renaming {pdf_file.name}: {str(e)}"
                print(msg)
        else:
            print(f"Could not find TRR information in {pdf_file.name}")


if __name__ == "__main__":
    rename_pdfs()
