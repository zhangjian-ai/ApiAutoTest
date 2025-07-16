import os
import sys
import pytest


if __name__ == '__main__':

    from framework.logger import log
    from framework.assists import Prepare

    pp = Prepare()

    try:
        args = pp.build_args()
        log.info(f"running arguments: {args}")
        code = pytest.main(args).value
    except SystemExit as exc:
        code = exc.code

    # done
    sys.exit(code)
