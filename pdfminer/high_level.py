"""Functions that can be used for the most common use-cases for pdfminer.six"""

import sys
import logging

from .pdfinterp import PDFResourceManager, PDFPageInterpreter
from .pdfdevice import TagExtractor
from .pdfpage import PDFPage
from .converter import XMLConverter, HTMLConverter, TextConverter
from .image import ImageWriter
from .layout import LAParams
from io import StringIO


def extract_text_to_fp(inf, outfp, output_type='text', codec='utf-8',
                       laparams=None, maxpages=0, page_numbers=None,
                       password="", scale=1.0, rotation=0, layoutmode='normal',
                       output_dir=None, strip_control=False, debug=False,
                       disable_caching=False, **kwargs):
    """Parses text from inf-file and writes to outfp file-like object.

    Takes loads of optional arguments but the defaults are somewhat sane.
    Beware laparams: Including an empty LAParams is not the same as passing
        None!

    :param inf: a file-like object to read PDF structure from, such as a
        file handler (using the builtin `open()` function) or a `BytesIO`.
    :param outfp: a file-like object to write the text to.
    :param output_type: May be 'text', 'xml', 'html', 'tag'. Only 'text' works
        properly.
    :param codec: Text decoding codec
    :param laparams: An LAParams object from pdfminer.layout. Default is None
        but may not layout correctly.
    :param maxpages: How many pages to stop parsing after
    :param page_numbers: zero-indexed page numbers to operate on.
    :param password: For encrypted PDFs, the password to decrypt.
    :param scale: Scale factor
    :param rotation: Rotation factor
    :param layoutmode: Default is 'normal', see
        pdfminer.converter.HTMLConverter
    :param output_dir: If given, creates an ImageWriter for extracted images.
    :param strip_control: Does what it says on the tin
    :param debug: Output more logging data
    :param disable_caching: Does what it says on the tin
    :param other:
    :return: nothing, acting as it does on two streams. Use StringIO to get
        strings.
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    imagewriter = None
    if output_dir:
        imagewriter = ImageWriter(output_dir)

    rsrcmgr = PDFResourceManager(caching=not disable_caching)

    if output_type == 'text':
        device = TextConverter(rsrcmgr, outfp, codec=codec, laparams=laparams,
                               imagewriter=imagewriter)

    if outfp == sys.stdout:
        outfp = sys.stdout.buffer

    if output_type == 'xml':
        device = XMLConverter(rsrcmgr, outfp, codec=codec, laparams=laparams,
                              imagewriter=imagewriter,
                              stripcontrol=strip_control)
    elif output_type == 'html':
        device = HTMLConverter(rsrcmgr, outfp, codec=codec, scale=scale,
                               layoutmode=layoutmode, laparams=laparams,
                               imagewriter=imagewriter)
    elif output_type == 'tag':
        device = TagExtractor(rsrcmgr, outfp, codec=codec)

    interpreter = PDFPageInterpreter(rsrcmgr, device)
    for page in PDFPage.get_pages(inf,
                                  page_numbers,
                                  maxpages=maxpages,
                                  password=password,
                                  caching=not disable_caching,
                                  check_extractable=True):
        page.rotate = (page.rotate + rotation) % 360
        interpreter.process_page(page)

    device.close()


def extract_text(pdf_file, password='', page_numbers=None, maxpages=0,
                 caching=True, codec='utf-8', laparams=None):
    """
    Parses and returns the text contained in a PDF file.
    Takes loads of optional arguments but the defaults are somewhat sane.
    Returns a string containing all of the text extracted.

    :param pdf_file: Path to the PDF file to be worked on
    :param password: For encrypted PDFs, the password to decrypt.
    :param page_numbers: List of zero-indexed page numbers to extract.
    :param maxpages: The maximum number of pages to parse
    :param caching: If resources should be cached
    :param codec: Text decoding codec
    :param laparams: LAParams object from pdfminer.layout.
    """
    if laparams is None:
        laparams = LAParams()

    with open(pdf_file, "rb") as fp, StringIO() as output_string:
        rsrcmgr = PDFResourceManager()
        device = TextConverter(rsrcmgr, output_string, codec=codec,
                               laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        for page in PDFPage.get_pages(
                fp,
                page_numbers,
                maxpages=maxpages,
                password=password,
                caching=caching,
                check_extractable=True,
        ):
            interpreter.process_page(page)

        return output_string.getvalue()
