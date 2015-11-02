Setting up a GitHub webhook with git-multimail
==============================================

This isn't particularly difficult, but given the number of moving parts, it is
important to plan accordingly.  This guide will take you step by step through
the process.  What you will need to complete this guide:

* `sendmail` installed and configured
* `git` installed and configured
* A web server installed and configured to be able to run CGI scripts.  This
  web server needs to be on the public web.

Note: a single webhook can route requests for multiple repositories.  The
instructions below will identify what parts of the configuration are
per-repository and what parts are common.

Verifying sendmail and git configuration
----------------------------------------

The following command, when run on Mac OSX or Linux hosts, should verify that
you have these tools set up correctly::

  echo "Subject: sendmail test" | sendmail $(git config --global user.email)

Getting the above working is beyond the scope of this guide.  However
everything that follows depends on this working.  `git-multimail` supports
alternatives to sendmail, but again that is beyond the scope of this guide.

Configuring git-multimail on a local repository
-----------------------------------------------

This is documented elsewhere, but included in abreviated form here to help
people who start here to get up and running quickly.  Copy and paste the
following commands::

    #!/bin/bash -x

    # create a directory for demo purposes
    rm -rf mmdemo
    mkdir mmdemo
    cd mmdemo

    # create a bare clone of a Git repository (repository #1)
    git clone --bare https://github.com/git-multimail/git-multimail.git

    # create a full clone of that repository (repository #2)
    git clone git-multimail.git

    # copy multimail hook into repository #1
    ln -s $(pwd)/git-multimail/git-multimail/git_multimail.py \
      git-multimail.git/hooks/git_multimail.py
    ln -s $(pwd)/git-multimail/git-multimail/post-receive.example \
      git-multimail.git/hooks/post-receive

    # configure multimail hook to send email to you
    git -C git-multimail.git config multimailhook.mailingList \
      $(git config --global user.email)

    # create a new file in repository #2
    echo 'It worked!' > git-multimail/mmdemo

    # add it
    git -C git-multimail add mmdemo

    # commit it
    git -C git-multimail commit -a -m 'multimail demo'

    # push it to repository #1
    git -C git-multimail push

Notes:

* You will need a single local copy (ideally ``--bare``) for each GitHub
  repository that you want to monitor for push requests.
* ``git config`` commands are used to configure repository specific information
  (such as who to notify).  See `Configuration
  <https://github.com/git-multimail/git-multimail#configuration>`_
  for more information.
* You will need to link a copy of ``git_multimail.py`` into each repository.
  You will not need to modify this file.
* You will need to link a copy of ``post-receive`` into each repository.
  You are welcome to tailor this file.  In fact, this is a convenient place to
  place common configuration that spans multiple repositories.  It may make
  sense to copy this example to another location before making changes.
  
Installing a PushEvent webhook as CGI
-------------------------------------

This is the step that is likely to take the longest.  If everything is set up
correctly, all you should need to do is copy the ``PushEvent.cgi`` and
``repository_location.py`` files into some place in the DocumentRoot of your
web server and navigate to the page using your web server.  If all goes well,
you should see a simple form, a dump of CGI environment variables, and an
empty list of repositories.

If things go wrong, check file permissions, check your server's error log,
and check the docs:

* https://httpd.apache.org/docs/2.4/howto/cgi.html
* https://www.nginx.com/resources/wiki/start/topics/examples/simplecgi/

Once that is working, create a ``logs`` directory in the same place you pub
the CGI script, and set its owner to the user id that your web server runs
scripts under.  Enter some random data in the web form and submit it.  You
will likely see some error (most commonly that the data you submitted wasn't
syntactically correct JSON).  Review the file created in the logs directory.

Next update the ``repository_location.py`` file to indicate where your
repositories are.  You can either individually white list repositories, or
wholesale use wildcards.  Change the file system owner of these repositories
to be that of the web server.  Visit the CGI page in your web browser and
verify the list of repositories is correct.

As a final step, create a secure secret to use as a web token.  GitHub
suggests you use the following command::

  ruby -rsecurerandom -e 'puts SecureRandom.hex(20)'

Set this as an environment variable for you CGI script:

  https://httpd.apache.org/docs/2.4/mod/mod_env.html#setenv

Verify that this is complete, verify this step by once again visiting the CGI
script in a web browser.  If done correctly, the CGI script will no longer
respond to GET requests.

Set up your Webhook
-------------------

This should be the easiest step.  All you should need is the URL of your CGI
script and the shared secret.  Follow these instructions, and set the content
type to JSON:

  https://developer.github.com/webhooks/creating/#setting-up-a-webhook

A ping will be sent, and you can see the response from your GitHub page:

  https://developer.github.com/webhooks/testing/

Failure responses will indicate what failed, including a stack traceback when
appropriate.  Success responses will include the output from git fetch and the
post-receive hook.  Requests can be redelivered using this interface.

Pushing changes to your GitHub repository should now result in email being sent
out.

Should you be comfortable with the data provided in responses, you can now
delete the ``logs`` directory used by the CGI script.  You can recreate it at
any time to resume capturing of logs.
