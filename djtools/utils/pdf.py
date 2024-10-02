import os
import subprocess
import sys
import tempfile
import traceback

from PyPDF2 import PdfFileReader
from django.conf import settings

__all__ = ['check_pdf_with_gs', 'check_pdf_with_pypdf', 'pdf_valido', 'fix_tmp_pdf']


def check_pdf_with_gs(content_pdf):
    # write the data to a temp file
    handle, filepath = tempfile.mkstemp()  # make a tmp file
    f = os.fdopen(handle, "wb")  # open the tmp file for writing
    f.write(content_pdf.read())  # write the tmp file
    f.close()
    gs = getattr(settings, 'GHOSTSCRIPT_CMD', None)
    cmd = [gs, "-dQUIET", "-dBATCH", "-dNOPAUSE", "-sDEVICE=nullpage", filepath]
    try:
        dict_env = {'TMPDIR': settings.TEMP_DIR, 'TEMP': settings.TEMP_DIR}
        rc = subprocess.call(cmd, stdout=subprocess.PIPE, env=dict_env)
        # Consuming the output
        return rc == 0
    except OSError:
        sys.exit("Error executing Ghostscript ({0}). Is it in your PATH?".format(gs))
    # removing
    finally:
        os.remove(filepath)


def check_pdf_with_pypdf(content_pdf):
    try:
        PdfFileReader(content_pdf, strict=True)
        return True
    except Exception:
        return False


def pdf_valido(arquivo):
    return arquivo.name.lower().endswith('.pdf') and (check_pdf_with_pypdf(arquivo) or check_pdf_with_gs(arquivo))


def fix_tmp_pdf(input_pdf, outfile):
    gs = getattr(settings, 'GHOSTSCRIPT_CMD', None)
    with tempfile.NamedTemporaryFile(suffix=".pdf") as fp:
        fp.write(input_pdf)
        fp.seek(0)
        directory = tempfile.mkdtemp()
        cmd = [gs, "-dPDF=1", "-dQUIET", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite", "-sOutputFile=" + outfile.name, fp.name]
        try:
            dict_env = {'TMPDIR': settings.TEMP_DIR, 'TEMP': settings.TEMP_DIR}
            subprocess.call(cmd, stderr=sys.stdout, cwd=directory, env=dict_env)
            output_pdf = outfile.read()
            return output_pdf
        except OSError:
            raise Exception("Error executing Ghostscript ({0}). Is it in your PATH?".format(gs))
        except Exception:
            raise Exception("Error while running Ghostscript subprocess. Traceback: \n {0}".format(traceback.format_exc()))
