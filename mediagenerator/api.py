import logging
import os
import shutil
from collections import OrderedDict, defaultdict
from urllib.parse import quote

# from django.utils.http import urlquote
from . import utils  # settings
from .settings import (
    GENERATED_MEDIA_DIR,
    GENERATED_MEDIA_NAMES_FILE,
    MEDIA_GENERATORS,
)
from .utils import load_backend

# HACK: by Hybird (we should pass it as argument -- & modify all the API)
global_errors = defaultdict(OrderedDict)
# logger = logging.getLogger(__name__)
logger = logging.getLogger('mediagenerator')


def generate_media():
    if os.path.exists(GENERATED_MEDIA_DIR):
        shutil.rmtree(GENERATED_MEDIA_DIR)

    utils.NAMES = {}

    for backend_name in MEDIA_GENERATORS:
        backend = load_backend(backend_name)()

        for key, url, content in backend.get_output():
            version = backend.generate_version(key, url, content)
            if version:
                base, ext = os.path.splitext(url)
                url = f'{base}-{version}{ext}'

            path = os.path.join(GENERATED_MEDIA_DIR, url)

            parent = os.path.dirname(path)
            if not os.path.exists(parent):
                os.makedirs(parent)

            if isinstance(content, str):
                content = content.encode('utf8')

            with open(path, 'wb') as fp:
                fp.write(content)

            # utils.NAMES[key] = urlquote(url)
            utils.NAMES[key] = quote(url)

    # Generate a module with media file name mappings
    with open(GENERATED_MEDIA_NAMES_FILE, 'w') as fp:
        fp.write('NAMES = %r' % utils.NAMES)

    for category, errors in global_errors.items():
        for error in errors.values():
            logger.warning('%s - %s', category, error)
