from fpdf import FPDF
import os
import argparse
script_name = os.path.basename(__file__)


def txt_to_pdf(input_file):
    output_file = os.path.splitext(input_file)[0] + '.pdf'
    pdf = FPDF(orientation='P', unit='mm', format='A4')  # Set orientation to Portrait
    pdf.set_page_background((0,0,0))
    pdf.set_margin(1)
    pdf.set_text_color(255, 255, 255)  # RGB for white
    pdf.add_font("DejaVuSansMono", style="", fname="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    pdf.set_font("DejaVuSansMono", size=5)
    pdf.add_page()

    with open(input_file, 'r', encoding='utf-8') as file:
        for line in file:
            pdf.cell(0, 2.5, txt=line, ln=True)
    pdf.output(output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a single .PDF from a single .TXT")
    parser.add_argument("txt_file", type=str, help="txt_file full_path")
    args = parser.parse_args()
    print(f"{script_name}: txt_file is {args.txt_file}")
    txt_to_pdf(args.txt_file)
