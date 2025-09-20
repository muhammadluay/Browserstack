#!/usr/bin/env python3
import os
import sys
import zipfile
import xml.etree.ElementTree as ET


NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'v': 'urn:schemas-microsoft-com:vml',
}


def load_relationships(zf):
    """Return mapping of rId -> zip path for media targets in document.xml.rels."""
    rels_path = 'word/_rels/document.xml.rels'
    rels = {}
    if rels_path in zf.namelist():
        rels_xml = ET.fromstring(zf.read(rels_path))
        for rel in rels_xml.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
            rId = rel.get('Id')
            target = rel.get('Target')  # typically 'media/image1.png'
            if rId and target:
                # Targets are relative to 'word/'
                zip_target = target
                if not zip_target.startswith('word/'):
                    zip_target = 'word/' + zip_target
                rels[rId] = zip_target
    return rels


def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def extract_image(zf, zip_member, media_dir):
    """Extract a single image from the zip to media_dir, return relative output path."""
    data = zf.read(zip_member)
    name = os.path.basename(zip_member)
    out_path = os.path.join(media_dir, name)
    with open(out_path, 'wb') as f:
        f.write(data)
    # Return path relative to CWD for readability
    return out_path


def get_text_with_images(zf, media_dir):
    doc_path = 'word/document.xml'
    if doc_path not in zf.namelist():
        raise FileNotFoundError('word/document.xml not found in DOCX')

    rels = load_relationships(zf)
    rel_to_output = {}

    def process_run(run):
        parts = []
        # text nodes
        for t in run.findall('.//w:t', NS):
            parts.append(t.text or '')
        # tabs and line breaks
        for _ in run.findall('.//w:tab', NS):
            parts.append('\t')
        for _ in run.findall('.//w:br', NS):
            parts.append('\n')
        # drawings (images)
        for drawing in run.findall('.//w:drawing', NS):
            for blip in drawing.findall('.//a:blip', NS):
                rid = blip.get('{%s}embed' % NS['r'])
                if rid and rid in rels:
                    zip_member = rels[rid]
                    # extract if not already
                    if rid not in rel_to_output:
                        rel_to_output[rid] = extract_image(zf, zip_member, media_dir)
                    parts.append(f"[Image: {rel_to_output[rid]}]")
        # legacy vml image
        for imagedata in run.findall('.//v:imagedata', NS):
            rid = imagedata.get('{%s}id' % NS['r'])
            if rid and rid in rels:
                zip_member = rels[rid]
                if rid not in rel_to_output:
                    rel_to_output[rid] = extract_image(zf, zip_member, media_dir)
                parts.append(f"[Image: {rel_to_output[rid]}]")
        return ''.join(parts)

    def process_paragraph(p):
        texts = []
        for run in p.findall('.//w:r', NS):
            texts.append(process_run(run))
        line = ''.join(texts).strip()
        return line

    def process_table(tbl):
        lines = []
        for tr in tbl.findall('w:tr', NS):
            cells = []
            for tc in tr.findall('w:tc', NS):
                cell_parts = []
                for p in tc.findall('w:p', NS):
                    cell_parts.append(process_paragraph(p))
                cells.append(' '.join([c for c in cell_parts if c]))
            lines.append('\t'.join(cells).rstrip())
        return '\n'.join(lines)

    root = ET.fromstring(zf.read(doc_path))
    body = root.find('w:body', NS)
    if body is None:
        return ''

    out_lines = []
    for child in list(body):
        tag = child.tag
        if tag == '{%s}p' % NS['w']:
            line = process_paragraph(child)
            out_lines.append(line)
        elif tag == '{%s}tbl' % NS['w']:
            out_lines.append(process_table(child))
        # separate blocks
        if out_lines and out_lines[-1] != '':
            out_lines.append('')

    # join, ensuring single newlines between blocks
    text = '\n'.join(out_lines).rstrip() + '\n'
    return text


def main():
    if len(sys.argv) < 2:
        print('Usage: docx_to_txt.py <input.docx>')
        sys.exit(2)
    in_path = sys.argv[1]
    if not os.path.isfile(in_path):
        print(f'Input not found: {in_path}')
        sys.exit(1)

    base, _ = os.path.splitext(os.path.basename(in_path))
    out_txt = base + '.txt'
    media_dir = base + '_media'
    ensure_dir(media_dir)

    with zipfile.ZipFile(in_path, 'r') as zf:
        text = get_text_with_images(zf, media_dir)

    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(text)

    print(f'Wrote text: {out_txt}')
    print(f'Extracted images (if any) to: {media_dir}/')


if __name__ == '__main__':
    main()

