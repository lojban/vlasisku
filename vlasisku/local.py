# local settings

import os

# Allow docker-compose to control debug flag, default to False.
DEBUG = os.getenv('DEBUG', '').lower() in ('1', 'true', 'yes', 'on')
# Prefer an environment-provided host (e.g. from docker-compose), fallback to production host.
WEBSITE = os.getenv('WEBSITE', 'vlasisku.lojban.org')
BOT_KEY = ''

