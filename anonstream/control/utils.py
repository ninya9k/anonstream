import json

def json_dumps_contiguous(obj, **kwargs):
    return json.dumps(obj, **kwargs).replace(' ', r'\u0020')
