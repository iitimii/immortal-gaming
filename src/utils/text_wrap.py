import re
from typing import Optional

def wrap_text_by_pixels(font, text: str, max_width_px: int, first_line_max_width_px: Optional[int] = None) -> list[str]:
    """
    Word-wrap text by pixel width.
    Supports <color:R,G,B>...</color> tags and keeps them intact across line breaks.
    
    Args:
        font: object with a .size(text) -> (w, h) method (e.g. pygame.font.Font)
        text: input text
        max_width_px: maximum pixel width of a regular line
        first_line_max_width_px: (optional) maximum pixel width of the first line, for first-line indents or prefixes.
                                 Defaults to max_width_px if not provided.
    
    Returns:
        list[str]: wrapped lines, each a self-contained rich-text string
    """
    if not text:
        return []

    normalized_text = text.replace('\\n', '\n')
    paragraphs = normalized_text.split('\n')
    
    wrapped_lines = []
    
    # Whether we are on the very first line of the text (for first_line_max_width_px)
    is_absolute_first_line = True

    # Regex matching color tags: opening or closing tag
    tag_pattern = re.compile(r'(<color:\d+,\d+,\d+>)|(</color>)')

    for paragraph in paragraphs:
        if not paragraph:
            wrapped_lines.append("")
            # An empty line counts as a line; later lines are no longer the absolute first line
            is_absolute_first_line = False
            continue

        # Tokenize logic including tags
        parts = tag_pattern.split(paragraph)
        raw_tokens = [p for p in parts if p]

        tokens = []
        for rt in raw_tokens:
            if tag_pattern.match(rt):
                tokens.append({'type': 'tag', 'content': rt})
            else:
                current_word = ""
                for char in rt:
                    if char.isascii() and not char.isspace():
                        current_word += char
                    else:
                        if current_word:
                            tokens.append({'type': 'text', 'content': current_word})
                            current_word = ""
                        tokens.append({'type': 'text', 'content': char})
                if current_word:
                    tokens.append({'type': 'text', 'content': current_word})

        # Layout
        current_line_str = ""
        current_width = 0
        active_color_tag = None 

        for token in tokens:
            if token['type'] == 'tag':
                tag_content = token['content']
                current_line_str += tag_content
                if tag_content.startswith('<color'):
                    active_color_tag = tag_content
                else:
                    active_color_tag = None
            else:
                # Text token
                word = token['content']
                w, _ = font.size(word)
                
                # Determine current limit
                current_limit = first_line_max_width_px if (is_absolute_first_line and first_line_max_width_px is not None) else max_width_px
                
                if current_width + w <= current_limit:
                    current_line_str += word
                    current_width += w
                else:
                    # Need to wrap
                    if active_color_tag:
                        current_line_str += "</color>"
                    
                    if current_line_str:
                        wrapped_lines.append(current_line_str)
                        # A line break happened, so the next line is no longer the first
                        is_absolute_first_line = False
                    
                    # Start new line
                    current_line_str = ""
                    current_width = 0
                    if active_color_tag:
                        current_line_str += active_color_tag
                    
                    # Check limit again for the new line (which is definitely not first line)
                    # Note: is_absolute_first_line is already False above
                    line_limit = max_width_px
                    
                    if w > line_limit:
                        # Super long word handling
                        temp_word = word
                        while True:
                             w_temp, _ = font.size(temp_word)
                             # Ensure we use the correct limit for the chunk
                             # If we just wrapped, we are on a new line, so use max_width_px
                             current_chunk_limit = max_width_px 
                             
                             if w_temp <= current_chunk_limit:
                                 # Remaining part fits
                                 current_line_str += temp_word
                                 current_width += w_temp
                                 break
                             
                             # Find cut index
                             cut_idx = 1
                             while cut_idx <= len(temp_word):
                                 sub = temp_word[:cut_idx]
                                 sw, _ = font.size(sub)
                                 if sw > current_chunk_limit:
                                     break
                                 cut_idx += 1
                             cut_idx -= 1
                             if cut_idx == 0: cut_idx = 1
                             
                             chunk = temp_word[:cut_idx]
                             current_line_str += chunk
                             if active_color_tag:
                                 current_line_str += "</color>"
                             wrapped_lines.append(current_line_str)
                             is_absolute_first_line = False
                             
                             temp_word = temp_word[cut_idx:]
                             current_line_str = ""
                             if active_color_tag:
                                 current_line_str += active_color_tag
                                 current_width = 0
                    else:
                        if word.isspace():
                            pass
                        else:
                            current_line_str += word
                            current_width += w

        if current_line_str:
            wrapped_lines.append(current_line_str)
            is_absolute_first_line = False

    return wrapped_lines
