import re
from typing import List, Dict, Any

# Set of common abbreviations that shouldn't end a sentence
ABBREVIATIONS = {
    "mr",
    "mrs",
    "ms",
    "dr",
    "jr",
    "sr",
    "vs",
    "prof",
    "st",
    "co",
    "corp",
    "inc",
    "ltd",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
    "e.g",
    "i.e",
}


class ChunkingService:
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Splits text into sentences, handling abbreviations and initials correctly.
        """
        # Normalize whitespace
        cleaned_text = re.sub(r"\s+", " ", text).strip()
        if not cleaned_text:
            return []

        # Split on standard sentence punctuation followed by spaces
        raw_splits = re.split(r"(?<=[.!?])\s+", cleaned_text)

        sentences = []
        temp_sentence = []

        for split in raw_splits:
            temp_sentence.append(split)

            # Extract the last word to see if it is an abbreviation
            words = split.split()
            if not words:
                continue

            # Strip outer punctuation/brackets (like parentheses in "(e.g.")
            last_word = words[-1].lower().strip("()[]{}'\"").rstrip(".!?")

            # Check if it is a single-letter initial (e.g. "J." in "J. P. Morgan")
            is_initial = len(last_word) == 1 and last_word.isalpha()

            # If the last word is an abbreviation or an initial, do not close the sentence yet
            if last_word in ABBREVIATIONS or is_initial:
                continue
            else:
                sentences.append(" ".join(temp_sentence))
                temp_sentence = []

        # Append any remaining segments
        if temp_sentence:
            sentences.append(" ".join(temp_sentence))

        return sentences

    def chunk_document(
        self,
        pages: List[Dict[str, Any]],
        document_id: str,
        source_filename: str,
        target_words: int = 300,
        overlap_sentences: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Groups sentences of each page into chunks of approximately target_words.
        Tracks page numbers, document IDs, filenames, and sequential chunk indices.
        """
        chunks = []
        chunk_index = 0

        for page in pages:
            page_num = page["page_number"]
            text = page["text"]

            # Split the page's text into discrete sentences
            sentences = self.split_into_sentences(text)
            if not sentences:
                continue

            current_chunk_sentences = []
            current_word_count = 0

            for sentence in sentences:
                sentence_words = len(sentence.split())

                # If adding this sentence exceeds our target size, and we already have content,
                # we close the current chunk.
                if (
                    current_word_count + sentence_words > target_words
                    and current_chunk_sentences
                ):
                    chunk_text = " ".join(current_chunk_sentences)
                    chunks.append(
                        {
                            "text": chunk_text,
                            "page_number": page_num,
                            "chunk_index": chunk_index,
                            "document_id": document_id,
                            "source_filename": source_filename,
                            "word_count": len(chunk_text.split()),
                            "char_count": len(chunk_text),
                        }
                    )
                    chunk_index += 1

                    # Sliding window overlap: keep the last N sentences for context in the next chunk
                    if (
                        overlap_sentences > 0
                        and len(current_chunk_sentences) > overlap_sentences
                    ):
                        current_chunk_sentences = current_chunk_sentences[
                            -overlap_sentences:
                        ]
                        current_word_count = sum(
                            len(s.split()) for s in current_chunk_sentences
                        )
                    else:
                        current_chunk_sentences = []
                        current_word_count = 0

                current_chunk_sentences.append(sentence)
                current_word_count += sentence_words

            # Add any remaining text on the page as the final chunk
            if current_chunk_sentences:
                chunk_text = " ".join(current_chunk_sentences)
                chunks.append(
                    {
                        "text": chunk_text,
                        "page_number": page_num,
                        "chunk_index": chunk_index,
                        "document_id": document_id,
                        "source_filename": source_filename,
                        "word_count": len(chunk_text.split()),
                        "char_count": len(chunk_text),
                    }
                )
                chunk_index += 1

        return chunks


chunking_service = ChunkingService()
