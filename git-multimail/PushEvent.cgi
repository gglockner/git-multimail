#!/usr/bin/python

#
# A CGI script that handles PushEvent GitHub web hooks by:
#  * validating and optionally logging the request
#  * locating the associated local clone of the repository
#  * fetching the change
#  * storing event information into environment variables
#  * invoking the local repository's post-receive hook
#
# This script should work on both Python 2.7 and 3.x.
#

from __future__ import print_function
import hashlib, hmac, json, os, sys, traceback
from subprocess import Popen, PIPE, STDOUT

try:
  from html import escape # Python >= 3.2
except ImportError:
  from cgi import escape

try:
  from urllib.parse import unquote_plus # Python 3
except ImportError:
  from urllib import unquote_plus

enc = os.environ.get('LANG', 'utf-8').split(".")[-1]
########################################################################

# Shared secret with GitHub.  Should NOT be encoded in this script.  See:
# https://developer.github.com/webhooks/securing/
token = bytes(os.environ.get('UNIQUE_ID', ''), enc)

########################################################################

class Failure(Exception): pass

try:
  # get map of repositories
  from repository_location import repository_location

  # process request
  if os.environ.get('REQUEST_METHOD', '').upper() == 'POST':

    # read and decode event payload
    payload = sys.stdin.read()
    if payload.startswith('payload='): payload=unquote_plus(payload[8:])

    # compute signature
    signature = 'sha1=' + hmac.new(token, bytes(payload, enc), hashlib.sha1).hexdigest()

    # if logs directory present, open log, otherwise open devnull
    if os.path.isdir('logs'):
      log = open('logs/' + signature[5:], 'w')
    else:
      log = open(os.devnull, 'w')

    # write log
    log.write(json.dumps(dict(os.environ), indent=2, sort_keys=True))
    log.write("\n\nSignature expected: %s\n\n" % repr(signature))
    log.write(payload)

    # validate signature
    if token and os.environ.get('HTTP_X_HUB_SIGNATURE', '') != signature:
      log.write("\n\nBAD Signature")
      raise Failure(422, 'Bad Signature', 'Signature does not match')
    log.write("\n\nSignature OK")

    # parse payload as JSON
    event = json.loads(payload)

    # log parsed results
    log.write("\n\nParsed event:\n")
    log.write(json.dumps(event, indent=2))

    # look up path to repository
    repository = repository_location[event['repository']['full_name']]
    if not repository:
      raise Failure(422, 'No repository', 'Repository not found')

    # quick exit for ping requests
    if 'zen' in event and not 'ref' in event:
      raise Failure(202, 'Accepted', 'Pong')

    # fetch updates from commit
    cmd = ['git', '-C', repository, 'fetch', 'origin', event['ref']]
    if event.get('forced', False): cmd.insert(4, '--force')
    process = Popen(cmd, stdout=PIPE, stderr=PIPE)
    responses = process.communicate()

    # log response
    log.write("\n\Exit code: %s\n" % process.returncode)
    log.write("\nFetch response:\n%s\n" % "\n".join(responses[-2:]))

    # stop if fetch failed
    if process.returncode != 0:
      raise Failure(500, 'Internal error',
        "git fetch rc=%d\n%s" % (process.returncode, "\n".join(responses)))

    # locate hook
    hook = repository
    if not hook.endswith('.git'): hook += '/.git'
    hook += '/hooks/post-receive'

    if os.path.exists(hook):
      # gather and log input for post-receive hook
      update = "%(before)s %(after)s %(ref)s\n" % event
      log.write("\n\nData to be passed to post-receive hook:\n")
      log.write(update)

      # copy event information into environment variables
      for key, value in event.items():
        os.environ['WEBHOOK_%s' % key.upper()] = json.dumps(value)

      log.write("\nEnvironment variables passed to webhook\n")
      for key, value in os.environ.items():
        if key.startswith('WEBHOOK_'):
           log.write("%s=%s\n" % (key, value))

      # invoke post-receive hook
      # NOTE: stderr will show up in the web server's error log
      cwd = os.getcwd()
      try:
        os.chdir(repository)
        process = Popen([hook], stdin=PIPE, stdout=PIPE, stderr=PIPE)
      finally:
        os.chdir(cwd)
      responses += process.communicate(input=update)

      # log response
      log.write("\n\nExit code: %s\n" % process.returncode)
      log.write("\nHook response:\n%s\n" % "\n".join(responses[-2:]))

    print("Status: 200 OK\r\nContent-Type: text/plain\r\n\r\n%s" %
      "\n".join(responses))

  elif not token:

    # Produce an HTML form useful for debugging purposes
    # NOTE: only shown if a secure token is NOT configured
    print("""Status: 200 OK\r\nContent-Type: text/html\r\n\r\n<!DOCTYPE html>
      <html><head><title>GitHub WebHook Test Form</title></head><body>
      <h1>GitHub WebHook Test Form</h1><p>Payload:</p>
      <form method=POST><textarea name=payload cols=80 rows=20></textarea>
      <p><input type=submit value='submit payload'></p>
      <hr><h2>Repositories</h2><table>""")

    # Add a list of repositories
    print("<thead><tr><th>GitHub</td><th>Local file path</th></tr></thead>")
    for name, value in sorted(repository_location.items()):
      print("<tr><td>%s</td><td>%s</td></tr>" % (escape(name), escape(value)))
    
    print("</table><br><hr><h2>Environtment Variables</h2><table>")
    print("<thead><tr><th>Name</td><th>Value</th></tr></thead>")

    # Add a dump of CGI environment variables
    for name, value in sorted(os.environ.items()):
      print("<tr><td>%s</td><td>%s</td></tr>" % (escape(name), escape(value)))
    
    print("</table></body></html>")

  else:

    print("Status: 405 Method Not Allowed\r\nAllow: POST\r\n" +
      "Content-Type: text/plain\r\n\r\n" +
      "HTTP %s Method not allowed" % os.environ['REQUEST_METHOD'])

except Failure as failure:
  print("Status: %d %s\r\nContent-Type: text/plain\r\n\r\n%s" % failure.args)

except:
  print("Status: 500 Internal error\r\nContent-Type: text/plain\r\n\r")
  traceback.print_exc(file=sys.stdout)
