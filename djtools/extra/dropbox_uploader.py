# -*- coding: utf-8 -*-

# Credits: https://github.com/jncraton/PythonDropboxUploader

"""
Copyright (c) 2010, Jon Craton
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer. Redistributions in
binary form must reproduce the above copyright notice, this list of
conditions and the following disclaimer in the documentation and/or other
materials provided with the distribution. Neither the name of Jon Craton
nor the names of its contributors may be used to endorse or promote
products derived from this software without specific prior written
permission. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


def upload_file(local_file, remote_dir, remote_file, email, password):
    """ Upload a local file to Dropbox """

    try:
        import mechanize
    except ImportError:
        raise ImportError('No module named mechanize. Try run: sudo apt-get install python-mechanize.')

    # Fire up a browser using mechanize
    br = mechanize.Browser()

    # Browse to the login page
    br.open('https://www.dropbox.com/login')

    # Enter the username and password into the login form
    def is_login_form(lista):
        return lista.action == "https://www.dropbox.com/login" and lista.method == "POST"

    try:
        br.select_form(predicate=is_login_form)
    except Exception:
        print("Unable to find login form.")
        exit(1)

    br['login_email'] = email
    br['login_password'] = password

    # Send the form
    br.submit()

    # Add our file upload to the upload form once logged in
    def is_upload_form(u):
        return u.action == "https://dl-web.dropbox.com/upload" and u.method == "POST"

    try:
        br.select_form(predicate=is_upload_form)
    except Exception:
        print("Unable to find upload form.")
        print("Make sure that your login information is correct.")
        exit(1)

    br.form.find_control("dest").readonly = False
    br.form.set_value(remote_dir, "dest")
    br.form.add_file(open(local_file, "rb"), "", remote_file)

    # Submit the form with the file
    br.submit()
