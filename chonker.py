#!/usr/bin/env python
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable, List

# --- Sizing, Splitting, and Formatting Logic (mostly unchanged) ---

def estimate_token_count(text: str) -> int:
    """Estimates the token count of a string using a word- and punctuation-based heuristic."""
    if not text: return 0
    token_count, in_word = 0, False
    for ch in text:
        if not ch.isalnum():
            if in_word: in_word = False
            if not ch.isspace(): token_count += 1
        else:
            if not in_word: in_word, token_count = True, token_count + 1
    return int(token_count * 1.08)

def split_into_sentences(text: str) -> list[str]:
    """Splits text into sentences using a regex that handles common abbreviations."""
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s', text)
    return [s.strip() for s in sentences if s.strip()]

def remove_leading_title(chunk: str, max_title_tokens: int, size_func: Callable[[str], int]) -> str:
    """
    If a chunk starts with a short line followed by a double newline,
    and that line is smaller than max_title_tokens, it's considered a title
    and removed.
    """
    if max_title_tokens <= 0:
        return chunk

    # Find the position of the first double newline
    try:
        split_pos = chunk.index('\n\n')
        
        # The potential title is the text before this position
        potential_title = chunk[:split_pos].strip()
        
        # Check if the title is short enough and doesn't contain sentence-ending punctuation
        # (real titles usually don't end with a period).
        if potential_title and size_func(potential_title) <= max_title_tokens and '.' not in potential_title and '?' not in potential_title:
            # Return the rest of the chunk, stripping leading whitespace
            return chunk[split_pos:].lstrip()
            
    except ValueError:
        # No double newline found, so no title to strip
        pass

    return chunk

def smart_chunker(text: str, max_size: int, min_size: int, size_func: Callable[[str], int], title_token_limit: int) -> list[str]:
    """Splits text into semantically meaningful chunks, respecting size limits and removing titles."""
    CHAPTER_DELIMITER, PARAGRAPH_DELIMITER = "\n\n\n", "\n\n"
    final_chunks = []
    text = text.replace('\r\n', '\n').strip()
    chapters = text.split(CHAPTER_DELIMITER)

    def finalize_chunk(chunk: str):
        """Helper to process and add a chunk to the final list."""
        if chunk:
            # Apply title removal before size check
            processed_chunk = remove_leading_title(chunk, title_token_limit, size_func)
            if size_func(processed_chunk) >= min_size:
                final_chunks.append(processed_chunk)

    for chapter in chapters:
        chapter = chapter.strip()
        if not chapter: continue
        paragraphs, current_chunk = chapter.split(PARAGRAPH_DELIMITER), ""
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph: continue
            prospective_chunk = paragraph if not current_chunk else f"{current_chunk}{PARAGRAPH_DELIMITER}{paragraph}"
            if size_func(prospective_chunk) <= max_size:
                current_chunk = prospective_chunk
            else:
                finalize_chunk(current_chunk)
                if size_func(paragraph) > max_size:
                    sub_chunks = split_oversized_text_block(paragraph, max_size, min_size, size_func, title_token_limit)
                    # Sub-chunks are already processed, so just extend
                    final_chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
        finalize_chunk(current_chunk)
            
    return final_chunks

def split_oversized_text_block(text: str, max_size: int, min_size: int, size_func: Callable[[str], int], title_token_limit: int) -> list[str]:
    """Handles a block of text that is too large, splitting by sentences or lines."""
    sentences = split_into_sentences(text)
    sub_chunks, current_sub_chunk = [], ""

    def finalize_sub_chunk(chunk: str):
        if chunk:
            processed_chunk = remove_leading_title(chunk, title_token_limit, size_func)
            if size_func(processed_chunk) >= min_size:
                sub_chunks.append(processed_chunk)

    for sentence in sentences:
        prospective_chunk = sentence if not current_sub_chunk else f"{current_sub_chunk} {sentence}"
        if size_func(prospective_chunk) <= max_size:
            current_sub_chunk = prospective_chunk
        else:
            finalize_sub_chunk(current_sub_chunk)
            if size_func(sentence) > max_size:
                line_chunks = split_by_lines(sentence, max_size, min_size, size_func, title_token_limit)
                sub_chunks.extend(line_chunks)
                current_sub_chunk = ""
            else:
                current_sub_chunk = sentence
    finalize_sub_chunk(current_sub_chunk)
    return sub_chunks

def split_by_lines(text: str, max_size: int, min_size: int, size_func: Callable[[str], int], title_token_limit: int) -> list[str]:
    """Absolute last resort: split a text block by lines."""
    lines, line_chunks, current_line_chunk = text.split('\n'), [], ""

    def finalize_line_chunk(chunk: str):
        if chunk:
            processed_chunk = remove_leading_title(chunk, title_token_limit, size_func)
            if size_func(processed_chunk) >= min_size:
                line_chunks.append(processed_chunk)

    for line in lines:
        line = line.strip()
        if not line: continue
        prospective_chunk = line if not current_line_chunk else f"{current_line_chunk}\n{line}"
        if size_func(prospective_chunk) <= max_size:
            current_line_chunk = prospective_chunk
        else:
            finalize_line_chunk(current_line_chunk)
            current_line_chunk = line
    finalize_line_chunk(current_line_chunk)
    return line_chunks

def format_as_jsonl(chunks: List[str]):
    for chunk in chunks: yield json.dumps({"text": chunk}) + '\n'

def format_as_alpaca(chunks: List[str]):
    alpaca_data = [{"instruction": "", "input": "", "output": chunk} for chunk in chunks]
    return json.dumps(alpaca_data, indent=4)

# --- Main Application Logic ---

def main():
    parser = argparse.ArgumentParser(
        description="A smart text chunker for creating ML datasets.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # ... (parser setup remains the same, with one addition)
    parser.add_argument("input_file", type=Path, help="Path to the input text file.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--chunk_size", type=int, help="Maximum character size for each chunk.")
    group.add_argument("-t", "--max_tokens", type=int, help="Maximum estimated token count for each chunk.")
    
    parser.add_argument("--min_size", type=int, default=0, help="Minimum character size. Chunks smaller than this are skipped.")
    parser.add_argument("--min_tokens", type=int, default=0, help="Minimum estimated token count. Chunks smaller than this are skipped.")
    parser.add_argument(
        "--remove_title", type=int, default=0, metavar='MAX_TOKENS',
        help="If a chunk starts with a line shorter than MAX_TOKENS followed by a double newline, remove it. Default: 0 (disabled)."
    )
    
    parser.add_argument("-o", "--output_file", type=Path, default=None, help="Path to the output file (extension will be set by format).")
    parser.add_argument("-f", "--format", choices=['jsonl', 'alpaca'], default='jsonl', help="Output format.")
    parser.add_argument("--debug", action="store_true", help="If set, also save a human-readable .txt file for inspection.")
    
    args = parser.parse_args()

    # --- Initial Setup ---
    if not args.input_file.is_file():
        print(f"Error: Input file not found at '{args.input_file}'", file=sys.stderr); sys.exit(1)

    if args.max_tokens:
        size_func, max_size, min_size, size_unit = estimate_token_count, args.max_tokens, args.min_tokens, "tokens (est.)"
    else:
        size_func, max_size, min_size, size_unit = len, args.chunk_size, args.min_size, "characters"

    print(f"Using {size_unit}. Max size: {max_size}, Min size: {min_size}", file=sys.stderr)
    if args.remove_title > 0:
        print(f"Removing titles shorter than {args.remove_title} tokens.", file=sys.stderr)
    
    output_path = args.output_file.with_suffix('.json' if args.format == 'alpaca' else '.jsonl') if args.output_file else \
                  args.input_file.with_suffix('.alpaca.json' if args.format == 'alpaca' else '.jsonl')

    # --- Main Processing Block ---
    try:
        input_text = args.input_file.read_text(encoding='utf-8')
        chunks = smart_chunker(input_text, max_size, min_size, size_func, args.remove_title)

        print(f"Formatting {len(chunks)} chunks for output...", file=sys.stderr)
        with open(output_path, 'w', encoding='utf-8') as f:
            if args.format == 'alpaca': f.write(format_as_alpaca(chunks))
            else:
                for line in format_as_jsonl(chunks): f.write(line)

        print(f"\nSuccess! Output saved to '{output_path}'", file=sys.stderr)

        if args.debug:
            output_path_debug = args.input_file.with_suffix('.debug.txt')
            with open(output_path_debug, 'w', encoding='utf-8') as f:
                for i, chunk in enumerate(chunks):
                    chunk_size = size_func(chunk)
                    header = f"--- CHUNK {i+1} / {len(chunks)} | SIZE: {chunk_size} {size_unit} ---\n"
                    f.write(header + chunk)
                    if i < len(chunks) - 1: f.write("\n\n#####\n\n")
            print(f"Debug output saved to '{output_path_debug}'", file=sys.stderr)

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr); sys.exit(1)

if __name__ == "__main__":
    main()