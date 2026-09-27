"""Signed embed entry."""

from .common import request, result
from .provider import embed


if __name__ == '__main__':
    data = request()
    if data['paths']:
        raise ValueError('Paid embed may not receive index paths')
    result(embed(**data['arguments']))
