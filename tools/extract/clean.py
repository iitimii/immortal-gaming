import asyncio
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.utils.llm import call_llm_json

INPUT_CSV_PATH = project_root / "tools" / "extract" / "res.csv"
OUTPUT_CSV_PATH = project_root / "tools" / "extract" / "cleaned_res.csv"
CONCURRENCY_LIMIT = 5

TEXT_FIELDS = ["style", "headquarters"]
LIST_FIELDS = ["members", "techniques", "treasures"]
CSV_FIELDNAMES = ["sect_name", *TEXT_FIELDS, *LIST_FIELDS]

CLEAN_PROMPT_TEMPLATE = """
You are an expert at curating data extracted from xianxia (cultivation) novels.
Clean up the sect information below by removing redundant and duplicated content.

Raw information:
{sect_info}

Requirements:
1. **Deduplicate**: remove duplicate entries from the members, techniques and treasures lists.
2. **Condense**: if the style or headquarters descriptions are repetitive or wordy, merge and condense them while keeping the core information.
3. **Format**: return standard JSON with the structure below.
4. **Preserve**: keep all meaningful information.

Response format:
{
  "Sect Name": {
    "style": "condensed description",
    "headquarters": "condensed description",
    "members": ["member 1", "member 2"],
    "techniques": ["technique 1", "technique 2"],
    "treasures": ["treasure 1"]
  }
}

Notes:
- If a field is empty in the raw information, keep it empty.
- Do not invent information that was not provided.
- The sect name must match the input "sect_name" exactly.
"""


async def process_row(row: Dict[str, str], semaphore: asyncio.Semaphore) -> Dict[str, Any]:
    """Process a single CSV row using LLM."""
    async with semaphore:
        # Pass the row as a JSON string to preserve structure for the LLM
        sect_info_str = json.dumps(row, ensure_ascii=False, indent=2)

        prompt = CLEAN_PROMPT_TEMPLATE.replace("{sect_info}", sect_info_str)

        try:
            print(f"Processing: {row.get('sect_name', 'Unknown')}")
            result = await call_llm_json(prompt)
            return result
        except Exception as e:
            print(f"Error processing {row.get('sect_name', 'Unknown')}: {e}")
            return {}


def merge_cleaned_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge the cleaned results."""
    final_data = {}

    for result in results:
        if not result:
            continue

        # Check if it's a flat structure (e.g. { "sect_name": "SectName", "style": ... })
        if "sect_name" in result and isinstance(result["sect_name"], str):
            sect_name = result["sect_name"]
            # Treat the whole result as data, minus the name
            data = {k: v for k, v in result.items() if k != "sect_name"}
            # Normalize to the expected iteration structure
            items_to_process = {sect_name: data}
        else:
            items_to_process = result

        for sect_name, data in items_to_process.items():
            if not isinstance(data, dict):
                # This might happen if the result was oddly structured
                # or the flat structure was not detected (e.g. "sect_name" missing)
                print(f"Warning: Unexpected data format for sect {sect_name}, skipping. Data type: {type(data)}, Value: {data}")
                continue

            if sect_name not in final_data:
                entry = {key: data.get(key, "") for key in TEXT_FIELDS}
                for key in LIST_FIELDS:
                    entry[key] = data.get(key, []) if isinstance(data.get(key), list) else []
                final_data[sect_name] = entry
            else:
                # Same sect seen again (shouldn't happen if input is unique, but good for safety)
                existing = final_data[sect_name]

                # Merge text fields
                for key in TEXT_FIELDS:
                    new_val = data.get(key, "")
                    if new_val and new_val not in existing[key]:
                        existing[key] = existing[key] + " | " + new_val if existing[key] else new_val

                # Merge lists
                for key in LIST_FIELDS:
                    new_list = data.get(key, [])
                    if isinstance(new_list, list):
                        current_set = set(existing[key])
                        for item in new_list:
                            item_str = str(item)
                            if item_str not in current_set:
                                existing[key].append(item)
                                current_set.add(item_str)
    return final_data


def save_to_csv(data: Dict[str, Any], output_path: Path):
    """Save cleaned data to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()

        for sect_name, details in data.items():
            row = {"sect_name": sect_name}
            for key in TEXT_FIELDS:
                row[key] = details.get(key, "")
            for key in LIST_FIELDS:
                row[key] = ", ".join(map(str, details.get(key, [])))
            writer.writerow(row)
    print(f"Results saved to: {output_path}")


async def main():
    if not INPUT_CSV_PATH.exists():
        print(f"Input file not found: {INPUT_CSV_PATH}")
        return

    print(f"Reading from {INPUT_CSV_PATH}")
    with open(INPUT_CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("No data found in CSV.")
        return

    print(f"Found {len(rows)} rows. Starting processing...")

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = [process_row(row, semaphore) for row in rows]

    results = await asyncio.gather(*tasks)

    print("Merging and saving results...")
    final_data = merge_cleaned_results(results)
    save_to_csv(final_data, OUTPUT_CSV_PATH)
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
