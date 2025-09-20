# Test Management — Importing Test Cases (CSV and BDD)

## Summary
- Bulk‑create test cases by importing a single CSV or multiple `.feature` files.
- Great for rapidly completing Step 1 (document cases) and sharing a Public Link.

## Prerequisites
- You have a Test Management account and a selected project (or create one).

## Import from CSV
1. Go to Test Cases and click Import (icon or button).
2. Upload a `.csv` file (one file per import).
3. Choose destination folder (or upload to root).
4. Configure options under “Show More Fields” if needed:
   - Import inline images (public URLs only)
   - CSV Separator (`,`, `;`, `:`, `|`, `\t`)
   - First Row (header row index)
   - File Encoding (UTF‑8 default)
5. Map CSV columns to system fields (verify carefully).
6. Preview → Import Test Cases.

CSV tips
- Include columns like: Title, Description, Preconditions, Priority, Component/Area, Steps, Expected Result, Tags.
- To link Asana, include full Asana task URLs in a column and map it to the Asana issues field.

## CSV file conditions (limits)
- One `.csv` per import, up to 10 MB;
- Up to 5000 test cases per CSV (split if larger);
- If stuck at 99%, split and retry; if stuck elsewhere, restart the import.
- Inline images supported only via public URLs (not file attachments).

## Import BDD test cases from `.feature` files
1. Go to Test Cases → Import.
2. Upload one or more `.feature` files (up to 20; each ≤ 10 MB).
3. Optionally enable automatic folder creation to mirror file structure.
4. Preview extracted Features/Scenarios/Steps → Import Test Cases.
5. On failure, download the system‑generated error report and retry.

### BDD via CSV (special mapping)
- Ensure Feature and Scenario columns are present and non‑empty.
- Add a “template” column per row with value set to “Test Case BDD” (or similar) and map it to the system “Test Case BDD” field.
- Map your Feature/Scenario/Background columns to the system’s Scenario field as guided.

## Why this helps our hackathon
- Rapidly seed a structured test suite (critical flows, edge/negative cases).
- Easier to organize by folders per feature/flow.
- Immediately share a Public Link to your test case folders in the README.

## Gotchas
- Use public URLs for images referenced in CSV (e.g., GitHub raw links after pushing the repo).
- Keep imports within size/count limits; split large files.
- Double‑check field mapping before importing.

## Where in the product
- Test Management → Projects → Test Cases → Import (CSV/Feature).
- Related docs: Test Management “Import test cases from CSV or Feature file”.
