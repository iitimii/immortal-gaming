import asyncio
import argparse
import csv
from pathlib import Path
from typing import Dict, List, Any
import sys

# Add project root to python path to ensure imports work
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.utils.llm import call_llm_json
from src.utils.io import read_txt

CHUNK_SIZE = 12000
CSV_OUTPUT_PATH = project_root / "tools" / "extract" / "res.csv"

TEXT_FIELDS = ["style", "headquarters"]
LIST_FIELDS = ["members", "techniques", "treasures"]
CSV_FIELDNAMES = ["sect_name", *TEXT_FIELDS, *LIST_FIELDS]

PROMPT_TEMPLATE = """
You are an expert analyst of xianxia (cultivation) novels.
Extract all information related to "sects" from the text below.
For every sect you find, extract:
- Sect name (used as the JSON key)
- style: how the sect conducts itself
- headquarters: where the sect is based
- members: known members
- techniques: cultivation techniques / methods
- treasures: treasures and artifacts

Return the result as JSON:
{
  "Sect Name": {
    "style": "description...",
    "headquarters": "description...",
    "members": ["member 1", "member 2"],
    "techniques": ["technique 1", "technique 2"],
    "treasures": ["treasure 1"]
  }
}

If no sect information is found, return an empty JSON object {}.
If the information about a sect is incomplete, record only what was found and leave the other fields as an empty string or empty list. Never make anything up.
Make sure the response is valid JSON.

Text excerpt:
{text_chunk}
"""


def split_text(text: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    """Split text into chunks of approximately chunk_size."""
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


async def process_chunk(chunk: str, index: int, total: int) -> Dict[str, Any]:
    """Process a single chunk using LLM."""
    print(f"Processing chunk {index + 1}/{total}...")
    prompt = PROMPT_TEMPLATE.replace("{text_chunk}", chunk)
    try:
        # call_llm_json already handles retries.
        result = await call_llm_json(prompt)
        return result
    except Exception as e:
        print(f"Error processing chunk {index + 1}: {e}")
        return {}


def merge_results(all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge results from multiple chunks."""
    final_data = {}

    for result in all_results:
        if not result:
            continue

        for sect_name, data in result.items():
            if sect_name not in final_data:
                entry = {key: data.get(key, "") for key in TEXT_FIELDS}
                for key in LIST_FIELDS:
                    entry[key] = data.get(key, []) if isinstance(data.get(key), list) else []
                final_data[sect_name] = entry
            else:
                existing = final_data[sect_name]

                # Merge text fields (append if different and not empty)
                for key in TEXT_FIELDS:
                    new_val = data.get(key, "")
                    if new_val and new_val not in existing[key]:
                        if existing[key]:
                            existing[key] += " | " + new_val
                        else:
                            existing[key] = new_val

                # Merge lists (deduplicate)
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
    """Save extracted data to CSV."""
    # Ensure directory exists
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
    parser = argparse.ArgumentParser(description="Extract sect info from a novel.")
    parser.add_argument("file", help="Path to the novel .txt file")
    parser.add_argument("--test", action="store_true", help="Run in test mode (process the first 3 chunks only)")
    args = parser.parse_args()

    novel_path = Path(args.file)
    if not novel_path.exists():
        print(f"File not found: {novel_path}")
        print("Usage: python extract.py <path_to_novel.txt> [--test]")
        return

    print(f"Reading novel from: {novel_path}")
    try:
        text = read_txt(novel_path)
    except Exception:
        print("UTF-8 read failed, trying GB18030...")
        try:
            with open(novel_path, "r", encoding="gb18030") as f:
                text = f.read()
        except Exception as e:
            print(f"Failed to read file: {e}")
            return

    chunks = split_text(text)
    print(f"Total text length: {len(text)}. Split into {len(chunks)} chunks.")

    if not chunks:
        print("No text to process.")
        return

    # Test mode logic
    if args.test:
        print("\n=== TEST MODE: Processing first 3 chunks only ===")
        chunks = chunks[:3]

    # Process chunks
    semaphore = asyncio.Semaphore(5)  # Allow 5 concurrent requests

    async def sem_task(chunk, idx):
        async with semaphore:
            return await process_chunk(chunk, idx, len(chunks))

    tasks = [sem_task(chunk, i) for i, chunk in enumerate(chunks)]
    results = await asyncio.gather(*tasks)

    print("Merging results...")
    final_results = merge_results(results)
    print("Done!")

    save_to_csv(final_results, CSV_OUTPUT_PATH)


if __name__ == "__main__":
    asyncio.run(main())
