# -*- coding: utf-8 -*-
"""
"""
from sphinx.errors import ExtensionError
from sphinx.locale import _
from sphinx.transforms.post_transforms.images import ImageConverter
from sphinx.util import logging
from sphinx.util.osutil import ENOENT, EPIPE, EINVAL
from cairosvg import svg2pdf

logger = logging.getLogger(__name__)

class CairoSvgConverter(ImageConverter):
    conversion_rules = [
        ('image/svg+xml', 'application/pdf'),
    ]

    def is_available(self):
        # type: () -> bool
        return True

    def convert(self, _from, _to):
        # type: (unicode, unicode) -> bool
        """Converts the image to expected one."""
        svg2pdf(url=_from, write_to=_to)

        return True


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_post_transform(CairoSvgConverter)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
