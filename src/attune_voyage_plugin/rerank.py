"""Signed rerank entry."""

from .common import request, result
from .provider import rerank


if __name__ == '__main__':
    data = request()
    if data['paths']:
        raise ValueError('Paid rerank may not receive index paths')
    result(rerank(**data['arguments']))
