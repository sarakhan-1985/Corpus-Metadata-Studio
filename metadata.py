"""Metadata validation and Excel export (no network or user sessions)."""
from io import BytesIO
import pandas as pd

FIELDS = ['File_ID', 'Student_ID', 'Student_Name', 'Roll_No', 'Course',
          'Semester', 'Institution', 'Text_Type', 'Essay_Topic', 'Language',
          'Collection_Status', 'Notes']
GUIDE = [
    'Exact corpus filename, e.g. RAW_01.txt', 'Anonymous participant code, e.g. S01',
    'Optional; retain only with permission', 'Optional identifying roll number',
    'Course represented by the corpus', 'Collection term, e.g. Fall 2026',
    'Source institution', 'Essay, interview, article, etc.', 'Topic or writing prompt',
    'Language of the text', 'Raw, Cleaned, Annotated, or Reviewed',
    'Relevant collection or processing notes']

def normalize(row):
    return {f: '' if pd.isna(row.get(f)) else str(row.get(f)).strip() for f in FIELDS}

def validate(rows):
    seen = set()
    for i, row in enumerate(rows, 1):
        if not row['File_ID']:
            raise ValueError(f'Row {i}: File_ID is required.')
        if row['File_ID'] in seen:
            raise ValueError(f"Duplicate File_ID: {row['File_ID']}")
        seen.add(row['File_ID'])
        if any(len(v) > 10000 for v in row.values()):
            raise ValueError(f'Row {i}: a field exceeds 10,000 characters.')

def excel_bytes(rows, anonymize=False):
    """Write strings literally, so metadata cannot become Excel formulas."""
    data = [{f: row.get(f, '') for f in FIELDS} for row in rows]
    if anonymize:
        for row in data:
            row['Student_Name'] = ''
            row['Roll_No'] = ''
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={
        'options': {'strings_to_formulas': False, 'strings_to_urls': False}}) as writer:
        pd.DataFrame(data, columns=FIELDS).to_excel(writer, index=False, sheet_name='Student Metadata')
        pd.DataFrame({'Field': FIELDS, 'What to enter': GUIDE}).to_excel(
            writer, index=False, sheet_name='Field Guide')
        book = writer.book
        header = book.add_format({'bold': True, 'bg_color': '#243B53', 'font_color': 'white', 'text_wrap': True})
        for name, columns in [('Student Metadata', FIELDS), ('Field Guide', ['Field', 'What to enter'])]:
            sheet = writer.sheets[name]
            sheet.freeze_panes(1, 0)
            sheet.set_row(0, 32)
            for j, field in enumerate(columns):
                sheet.write(0, j, field, header)
            sheet.set_column(0, len(columns)-1, 23)
        writer.sheets['Student Metadata'].autofilter(0, 0, len(data), len(FIELDS)-1)
        writer.sheets['Student Metadata'].set_column(8, 8, 38)
        writer.sheets['Student Metadata'].set_column(11, 11, 45)
        writer.sheets['Field Guide'].set_column(1, 1, 55)
    return output.getvalue()
