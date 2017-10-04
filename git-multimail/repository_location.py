#
# This Python module returns back a list of GitHub repository names and
# the location of a local clone for that repository.
#

# edit this list as appropriate
repository_location = {
  # 'git-multimail/git-multimail': '/Users/rubys/git/git-multimail'
}

# either instead of, or in addition to the enumerated list above, provide
# a list of file paths (including wild cards) containing git repositories
paths = [
  # '/home/rubys/git/*'
]

#
# Do not edit below this line
#

if paths:
  from glob import glob
  import os
  import re

  try:
    from StringIO import StringIO
  except ImportError:
    from io import StringIO

  try:
    from configparser import ConfigParser
    from configparser import Error as ConfigParserError
  except ImportError:
    from ConfigParser import ConfigParser
    from ConfigParser import Error as ConfigParserError

  for path in paths:
    for source in glob(path):
      # expand path
      if not source.endswith('.git'): source += '/.git'
      source = os.path.abspath(source)

      # skip if config not found
      if not os.path.isfile(source + '/config'): continue

      # parse config (note: Python's ConfigParser doesn't support whitespace)
      try:
        with open(source + '/config') as file: config = file.readlines()
        parser = ConfigParser()
        parser.readfp(StringIO(''.join([line.lstrip() for line in config])))

        url = parser.get('remote "origin"', 'url')
      except ConfigParserError:
        continue

      # extract repository name (support both SSH and HTTP(S) formatted git names)
      repo = None
      for pat in ['git@[^:]+:(.+)\.git', 'https?://[^/]+/(.+)\.git']:
        obj = re.match(pat, url)
        if obj:
          repo = obj.group(1)
          break

      # add repository to repository_location
      if repo:
        if source.endswith('/.git'): source = source[:-5]
        repository_location[repo] = source

if __name__ == '__main__':
  # for debugging purposes, dump repository_location
  import pprint
  pp = pprint.PrettyPrinter(indent=4)
  pp.pprint(repository_location)
