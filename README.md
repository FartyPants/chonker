# chonker

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/Q5Q5MOB4M)


# Smart Text Chunker

A "sophisticated" Python command-line tool for splitting large text files into smaller, more manageable chunks of, shall we say, semantic relevance. It's designed for preparing TEXT datasets for training and fine-tuning Large Language Models (LLMs).

Instead of naively splitting text by a fixed character count, this tool uses the inherent structure of a document (chapters, paragraphs, sentences) to create chunks that preserve context and meaning.

## Features

-   **Hierarchical Splitting**: Intelligently splits text using a multi-level fallback system:
    1.  **Chapters/Sections**: Respects major breaks (triple newlines).
    2.  **Paragraphs**: Combines whole paragraphs without exceeding the size limit.
    3.  **Sentences**: If a paragraph is too large, it splits it by sentences, avoiding splits on abbreviations like "Mr." or "Dr.".
    4.  **Lines**: As a final fallback, splits oversized sentences by line breaks.
-   **Flexible Sizing**: Define chunk size by either:
    -   `--chunk_size`: Maximum character count.
    -   `--max_tokens`: Maximum *estimated* token count.
-   **Quality Control**:
    -   `--min_tokens` / `--min_size`: Filter out insignificant chunks (e.g., lone titles or short lines) by setting a minimum size.
    -   `--remove_title`: Automatically detect and remove short chapter/section titles (e.g., "CHAPTER 1") from the beginning of chunks.
-   **Multiple Output Formats**:
    -   **JSONL (`.jsonl`)**: The default format, with one JSON object per line (`{"text": "..."}`). Ideal for streaming and large datasets.
    -   **Alpaca (`.json`)**: A single JSON file formatted for fine-tuning with the popular Alpaca-LoRA library (`[{"instruction": "", "input": "", "output": "..."}, ...]`).
-   **Debug Mode**:
    -   `--debug`: Generates a human-readable `.txt` file showing exactly how the text was chunked, complete with separators and size info for easy validation.

## Requirements

-   Python 3.6+
-   No external libraries required.

## Installation

1.  Clone the repository or download the `chonker.py` script.
    ```sh
    git clone https://github.com/FartyPants/chonker.git
    cd chonker
    ```
2.  The script is ready to use. You can run it directly with `python`.

## Usage

The script is run from the command line.

```sh
python chonker.py [INPUT_FILE] [OPTIONS]
```

### Basic Examples

**1. Chunk by Character Count**

Split `my_book.txt` into chunks of roughly 2000 characters each. The output will be `my_book.jsonl`.

```sh
python chonker.py my_book.txt --chunk_size 2000
```

**2. Chunk by Estimated Tokens**

Split `my_book.txt` into chunks of roughly 500 estimated tokens. This is often more useful for LLM applications.

```sh
python chonker.py my_book.txt --max_tokens 500
```

### Advanced Examples

**1. Creating an Alpaca Dataset**

Create a high-quality dataset for fine-tuning. This command will:
-   Chunk by a maximum of 400 tokens.
-   Discard any resulting chunk smaller than 30 tokens.
-   Automatically remove chapter titles that are shorter than 10 tokens.
-   Format the output as a single `my_book.alpaca.json` file.

```sh
python chonker.py my_book.txt --max_tokens 400 --min_tokens 30 --remove_title 10 --format alpaca
```

**2. Debugging the Chunking Logic**

If you want to verify how the text is being split, use the `--debug` flag. This will:
-   Split the text into chunks of max 1500 characters.
-   Create the standard `my_book.jsonl` output.
-   **Also create `my_book.debug.txt`** for easy inspection.

```sh
python chonker.py my_book.txt --chunk_size 1500 --debug
```

An entry in the `.debug.txt` file will look like this:

```
--- CHUNK 1 / 152 | SIZE: 1488 characters ---
This is the first chunk of text from the book. It contains the first paragraph.

And it also contains the second paragraph, because both together fit within the 1500 character limit.

#####

--- CHUNK 2 / 152 | SIZE: 1390 characters ---
This is the third paragraph. It was too long to be combined with the previous chunk, so it starts a new one.
```

### Command-Line Arguments

| Argument               | Description                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------------- |
| `input_file`           | **Required.** Path to the input text file.                                                              |
| `--chunk_size` / `-s`  | **Required** (or `--max_tokens`). Maximum character size for each chunk.                                |
| `--max_tokens` / `-t`  | **Required** (or `--chunk_size`). Maximum estimated token count for each chunk.                         |
| `--min_size`           | Minimum character size. Chunks smaller than this are discarded. Use with `--chunk_size`.                |
| `--min_tokens`         | Minimum estimated token count. Chunks smaller than this are discarded. Use with `--max_tokens`.         |
| `--remove_title N`     | If a chunk starts with a line shorter than `N` tokens followed by a double newline, remove it.          |
| `--format` / `-f`      | Output format. Choices: `json` (default), `jsonl`, `alpaca`.                                            |
| `--output_file` / `-o` | Path to the output file. If not set, it's auto-generated based on the input file name and format.       |
| `--debug`              | If set, also saves a human-readable `.txt` file with separators for easy inspection.                    |

added
--remove_line_start "prefix"  removes any line that start with the string in "prefix"  Ex: --remove_line_start "[" 

---
