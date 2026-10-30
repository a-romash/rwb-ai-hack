import re


def lint(source, ac, params=()):
    errors=[]
    if ac not in source: errors.append('TEST_NO_AC')
    forbidden=r'\bSkip\b|DateTime(?:Offset)?\.(?:Now|UtcNow)|Thread\.Sleep|Task\.Delay|\bcatch\s*\(|\btry\s*\{'
    if re.search(forbidden,source) or not re.search(r'\bAssert\.|\bexpect\(',source): errors.append('TEST_FORBIDDEN')
    for value in params:
        if isinstance(value,(int,float)) and not isinstance(value,bool) and re.search(r'(?<![\w.])'+re.escape(str(value))+r'(?![\w.])',source):
            errors.append('TEST_FORBIDDEN')
    return sorted(set(errors))
