#!/usr/bin/env bash
if [ "${TRAVIS_BRANCH}" = "master" ]; then
  pip install -r package/requirements.txt  --index-url https://pypi.python.org/simple
  pip install cloudshell-shell-core  --index-url https://pypi.python.org/simple
else
  pip install -r package/requirements.txt  --index-url https://testpypi.python.org/pypi
  pip install cloudshell-shell-core  --index-url https://testpypi.python.org/pypi
fi

pip install -r test_requirements.txt
pip install coveralls