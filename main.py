#!/usr/bin/env python3
"""Use the OpenAI API to clean and normalize a CSV column.

Sends the distinct values of one column to the API, asks for a cleaned
version of each, and writes a new CSV with the cleaned column added
(or replacing the original with --replace).

The API key is read ONLY from the OPENAI_API_KEY environment variable.
Never hardcode a key. Uses urllib from the standard library only.
"""
import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = "https://api.openai.com/v1/chat/completions"


def get_api_key():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("Error: OPENAI_API_KEY is not set.", file=sys.stderr)
        print("Set it before running this tool, for example:", file=sys.stderr)
        print("  export OPENAI_API_KEY='sk-...'", file=sys.stderr)
        print("Never paste your key into a file or share it.", file=sys.stderr)
        return None
    return key


def clean_values(api_key, values, column, instruction, model):
    """Ask the API to clean each distinct value; return {old: new}."""
    prompt = (
        f"Clean and normalize each value in this list from the CSV column "
        f"'{column}'. {instruction}\n"
        "Return ONLY a JSON object mapping each original value to its "
        "cleaned value, with no other text. Example: "
        '{"New York!!": "New York"}.\n\n'
        + json.dumps(values, indent=2)
    )
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system",
             "content": "You clean tabular data. Reply with JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 2000,
    }).encode("utf-8")
    request = urllib.request.Request(
        API_URL, data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Error: OpenAI API returned HTTP {exc.code}: {body}",
              file=sys.stderr)
        return None
    except urllib.error.URLError as exc:
        print(f"Error: could not reach the OpenAI API: {exc}", file=sys.stderr)
        return None
    try:
        content = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        print(f"Error: unexpected API response: {data}", file=sys.stderr)
        return None
    # Tolerate a fenced code block around the JSON.
    if content.startswith("```"):
        content = content.strip("`").strip()
        if content.lower().startswith("json"):
            content = content[4:].strip()
    try:
        mapping = json.loads(content)
    except json.JSONDecodeError:
        print(f"Error: API did not return valid JSON:\n{content}",
              file=sys.stderr)
        return None
    return {str(k): str(v) for k, v in mapping.items()}


def main():
    parser = argparse.ArgumentParser(
        description="Use the OpenAI API to clean and normalize a CSV column. "
                    "The API key comes from the OPENAI_API_KEY environment "
                    "variable only.")
    parser.add_argument("csv_file", help="Input CSV file.")
    parser.add_argument("column", help="Column to clean.")
    parser.add_argument("-o", "--output", help="Output CSV file "
                        "(default: <input>_cleaned.csv).")
    parser.add_argument("--replace", action="store_true",
                        help="Replace the column in place instead of adding "
                             "a '<column>_cleaned' column.")
    parser.add_argument("--instruction", default="Fix capitalization, "
                        "trim extra whitespace, remove stray punctuation, "
                        "and make equivalent values identical.",
                        help="Extra cleaning instruction for the model.")
    parser.add_argument("-m", "--model", default="gpt-4o-mini",
                        help="Model to use (default: gpt-4o-mini).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show the value mapping without writing a file "
                             "(still calls the API).")
    args = parser.parse_args()

    api_key = get_api_key()
    if api_key is None:
        return 1

    try:
        with open(args.csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                print(f"Error: {args.csv_file} has no header row.",
                      file=sys.stderr)
                return 1
            if args.column not in reader.fieldnames:
                print(f"Error: column '{args.column}' not found. "
                      f"Columns: {', '.join(reader.fieldnames)}",
                      file=sys.stderr)
                return 1
            rows = list(reader)
    except OSError as exc:
        print(f"Error: cannot read {args.csv_file}: {exc}", file=sys.stderr)
        return 1

    values = sorted({row[args.column] for row in rows if row[args.column]})
    if not values:
        print(f"Error: column '{args.column}' has no non-empty values.",
              file=sys.stderr)
        return 1
    print(f"Cleaning {len(values)} distinct values in '{args.column}'...",
          file=sys.stderr)
    mapping = clean_values(api_key, values, args.column,
                           args.instruction, args.model)
    if mapping is None:
        return 1
    for old, new in mapping.items():
        print(f"  {old!r} -> {new!r}")

    if args.dry_run:
        return 0
    out_column = args.column if args.replace else f"{args.column}_cleaned"
    fieldnames = list(reader.fieldnames)
    if not args.replace:
        fieldnames.append(out_column)
    output = args.output or args.csv_file.replace(".csv", "_cleaned.csv")
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row[out_column] = mapping.get(row[args.column], row[args.column])
            writer.writerow(row)
    print(f"Wrote {len(rows)} rows to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
