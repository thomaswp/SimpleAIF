
def __find_all(a_str, sub):
    start = 0
    while True:
        start = a_str.find(sub, start)
        if start == -1: return
        yield start
        start += 1

def __highlight_to_start_end(highlight, code_lines):
    hl_line = highlight["line"]
    hl_column_start = highlight["columnStart"]
    text = highlight["text"]
    start_index = sum(map(lambda x: len(x) + 1, code_lines[:hl_line])) + hl_column_start
    end_index = start_index + len(text)
    return start_index, end_index

def __is_subgoal_relevant(code, subgoal_highlights, ngram):
    for start_index in __find_all(code, ngram):
        end_index = start_index + len(ngram)
        for highlight in subgoal_highlights:
            hl_start, hl_end = highlight
            # If the two substrings overlap at all
            # if ngram == "for":
            #     print(start_index, end_index, hl_start, hl_end)
            if not (start_index >= hl_end or end_index <= hl_start):
                return True
    return False

def __are_ngrams_relevant(code, subgoal_highlights, ngrams):
    return [__is_subgoal_relevant(code, subgoal_highlights, ngram) for ngram in ngrams]

def __get_highlights_start_end_for_subgoal_index(highlights, subgoal_index, code_lines):
    return [__highlight_to_start_end(highlight, code_lines) for highlight in highlights if highlight["subgoalIndex"] == subgoal_index]

def are_ngrams_relevant_for_subgoal_index(subgoal_data, ngrams, subgoal_index):
    code_lines = subgoal_data["codeLines"]
    highlights = subgoal_data["highlights"]
    code = "\n".join(code_lines)
    subgoal_highlights = __get_highlights_start_end_for_subgoal_index(highlights, subgoal_index, code_lines)
    return __are_ngrams_relevant(code, subgoal_highlights, ngrams)