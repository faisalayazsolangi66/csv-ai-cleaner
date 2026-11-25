# csv-ai-cleaner

Use the OpenAI API to clean and normalize a CSV column. It sends only
the distinct values of one column to the API, asks for a cleaned version
of each, and writes a new CSV with a `<column>_cleaned` column added
(or replaces the original with `--replace`).

## Requirements

- Python 3.8+
- No third-party packages (standard library only; API calls use `urllib`)
- An OpenAI account with API access

## API key

The API key is read **only** from the `OPENAI_API_KEY` environment
variable. Never hardcode a key in a file, and never share it.

```bash
export OPENAI_API_KEY='sk-...'
```

If the variable is not set, the tool exits with a clear error and does
not call the API.

## Usage

```bash
python3 main.py customers.csv city
python3 main.py customers.csv city --replace -o customers_clean.csv
python3 main.py customers.csv city --instruction "Standardize to Title Case and expand abbreviations."
python3 main.py customers.csv city --dry-run
```

Options:

- `csv_file` — input CSV file
- `column` — column to clean
- `-o, --output` — output CSV file (default: `<input>_cleaned.csv`)
- `--replace` — replace the column instead of adding `<column>_cleaned`
- `--instruction` — extra cleaning instruction for the model
- `-m, --model` — model to use (default: gpt-4o-mini)
- `--dry-run` — show the value mapping without writing a file

## Example

```bash
$ export OPENAI_API_KEY='sk-...'
$ python3 main.py customers.csv city
```

Sample output:

```
Cleaning 3 distinct values in 'city'...
  'new york!!' -> 'New York'
  'LAHORE ' -> 'Lahore'
  'london' -> 'London'
Wrote 3 rows to customers_cleaned.csv
```

## License

MIT — see [LICENSE](LICENSE).
