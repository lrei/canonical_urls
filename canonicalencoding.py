'''
A bunch of tricks to get a page encoding
It's probably better to fall back on UnicodeDammit before going deep into this
'''

import re
try:
    import cchardet as chardet
except:
    import chardet


RE_CHARSET = re.compile(br'<meta.*?charset=["\']*(.+?)["\'>]', flags=re.I)
RE_PRAGMA = re.compile(br'<meta.*?content=["\']*;?charset=(.+?)["\'>]', flags=re.I)
RE_XML = re.compile(br'^<\?xml.*?encoding=["\']*(.+?)["\'>]')

CHARSETS = {
    'big5': 'big5hkscs',
    'gb2312': 'gb18030',
    'ascii': 'utf-8',
    'maccyrillic': 'cp1251',
    'win1251': 'cp1251',
    'win-1251': 'cp1251',
    'windows-1251': 'cp1251',
}

def fix_charset(encoding):
    '''Overrides encoding when charset declaration or charset determination is 
    a subset of a larger charset. Created because of issues with Chinese 
    websites - lifted from python-readability
    '''
    encoding = encoding.lower()
    return CHARSETS.get(encoding, encoding)


def get_header_encoding(headers):
    '''Get content from headers provided by urllib
    '''
    if not headers:
        return None

    content_type = headers.get('content-type')
    if content_type:
        # check for charset
        if 'charset' in content_type:
            try:
                enc = content_type.split('charset=')[-1]
                return fix_charset(enc)
            except:
                return None
    return None


def get_declared_encodings(page):
    '''Returns a list Encodings found in the content
    Based on code from python-readability
    '''
    # Regex for XML and HTML Meta charset declaration
    declared_encodings = (RE_CHARSET.findall(page) +
                          RE_PRAGMA.findall(page) +
                          RE_XML.findall(page))

    # fix
    declared_encodings = [fix_charset(x) for x in declared_encodings]

    return declared_encodings


def detect_encoding(page):
    '''Get an encoding from chardet
    '''
    # Remove all HTML tags, and leave only text for chardet
    text = re.sub(b'(\s*</?[^>]*>)+\s*', b' ', page).strip()

    # if content is too small
    if len(text) < 10:
        return None # can't guess

    # detect
    res = chardet.detect(text)
    if 'encoding' in res:
        enc = fix_charset(enc)
        return res

    return enc


def try_encoding(page, encoding):
    '''Tries to decode a page using an encoding (strict - no errors)
    '''
    try:
        ucontent = unicode(page, encoding, 'strict')
        return ucontent
    except:
        return None


def try_encoding_force(page, encoding):
    '''Tries to decode a page using an encoding (replace errors)
    '''
    try:
        ucontent = unicode(html, encoding, 'replace')
        return ucontent
    except:
        return None
