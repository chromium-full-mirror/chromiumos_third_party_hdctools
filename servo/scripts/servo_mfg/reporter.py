# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Module to help write clean mfg reports to text."""

import datetime
import glob
import logging
import os
import shutil
import sys
import tarfile
import tempfile
import textwrap

# Format string to use for info level logging.
INFO_FMT_STRING = '%(asctime)s - %(message)s'
# Format string to use for debug level logging.
DEBUG_FMT_STRING = ('%(asctime)s - %(name)s - %(levelname)s - '
                    '%(filename)s:%(lineno)d - %(message)s')

INFO_FMT = logging.Formatter(INFO_FMT_STRING)
DEBUG_FMT = logging.Formatter(DEBUG_FMT_STRING)


# The base directory under which new servo mfg folders are created.
OUTDIR_BASE = '/var/log/'


# The prefix for each new servo_mfg_ folder.
OUTDIR_PREFIX = 'servo_mfg_'


def clear_all():
  """API to clean up all logs."""
  # Clearing all should only skip the large .tbz bundles. This glob makes sure
  # that all smaller (per session) bundles are also deleted.
  logs = glob.glob(os.path.join(OUTDIR_BASE, OUTDIR_PREFIX + '*'))
  for l in logs:
    if os.path.isdir(l):
      shutil.rmtree(l)
    else:
      os.remove(l)


def bundle_all():
  """API to bundle all logs into a tar-archive."""
  # This avoids us compressing any compressed logs if they are around.
  dirs = [d for d in glob.glob(os.path.join(OUTDIR_BASE, OUTDIR_PREFIX + '*'))
          if os.path.isdir(d)]
  return bundle(dirs)


def bundle(paths):
  """bundle up all dirs in |paths|.

  If paths only has one member, it will create a tar of that one member as the
  root. It will be named the same as that member.
  Otherwise, it will create a tar of all the members, and be named after
  timestamp when the file was generated.

  Args:
    paths: a list of paths to servo mfg log directories

  Returns:
    path to compressed logs archive
  """
  single_mode = True if len(paths) == 1 else False
  if single_mode:
    on = os.path.basename(paths[0])
  else:
    on = '%s.%s' % (OUTDIR_PREFIX[:-1],
                    datetime.datetime.today().strftime('%Y-%m-%d.%H.%M.%f'))
  outpath = os.path.join(OUTDIR_BASE, '%s.tbz2' % on)
  with tarfile.open(outpath, 'w:bz2') as tar:
    for d in paths:
      arcname = '.' if single_mode else os.path.basename(d)
      if not d or not os.path.exists(d):
        logging.error('Cannot tar up non-existant outdir %r', d)
      else:
        tar.add(d, arcname=arcname)
  # Again, make sure this is all access
  os.chmod(outpath, 0o666)
  return outpath


def setup_logging_and_reporting(debug=False):
  """This function will setup the right files, directories, and formats.

  Args:
    debug: whether the stdout logs should be in DEBUG or INFO

  Returns:
    outdir, the directory in which all the logs and reports will be for this
    session
  """
  root_logger = logging.getLogger()
  # Handle filtering of messages in the handlers, but pass all along.
  root_logger.setLevel(logging.DEBUG)
  # setup temp directory here
  outdir = tempfile.mkdtemp(dir=OUTDIR_BASE, prefix=OUTDIR_PREFIX)
  for loglevel in [logging.INFO, logging.WARNING, logging.DEBUG]:
    levelname = logging.getLevelName(loglevel)
    path = os.path.join(outdir, 'log.%s' % levelname)
    handler = logging.FileHandler(path)
    handler.setLevel(loglevel)
    if loglevel == logging.DEBUG:
      handler.setFormatter(DEBUG_FMT)
    else:
      handler.setFormatter(INFO_FMT)
    root_logger.addHandler(handler)
  # A handler for stdout as well.
  console_handler = logging.StreamHandler(sys.stdout)
  if debug:
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(DEBUG_FMT)
  else:
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(INFO_FMT)
  root_logger.addHandler(console_handler)
  # return the directory
  return outdir


# pylint: disable=g-bad-exception-name
class ReporterError(Exception):
  """Reporter error class."""


class Reporter(object):
  """Class to encompass a full reporter.

  A reporter keeps track of all the reports (one per device manufacturing)
  and then prints additional metadata at the end.
  """

  # The filename for the report produced
  FNAME = 'report.txt'

  # The Reporter title needs to be # as it's the main headline of the report.
  # This is in case the user renders the output in .md
  REPORTER_TITLE_PREFIX = '#'

  def __init__(self, board, outdir):
    """Setup the reporter.

    Args:
      board: servo board being manufactured
      outdir: directory to write the logs and reports to

    Raises:
      ReporterError: if |outdir| does not exist
    """
    self._logger = logging.getLogger(type(self).__name__)
    if not os.path.exists(outdir):
      raise ReporterError('Outdir %r not found' % outdir)
    self._path = os.path.join(outdir, self.FNAME)
    self._failed_path = os.path.join(outdir, self.FNAME)
    self._current_report = None
    self._results = []
    self._cover_report = Report(self._path, self._failed_path, dev_report=False,
                                topic=board,
                                date=str(datetime.datetime.today()))
    # This report as it bookbinds the entire reporter is a bit special.
    # We need to change the prefix, to highlight it's a title.
    # pylint: disable=invalid-name
    # |REPORT_PREFIX| is the constant used in the report to generate the title.
    self._cover_report.REPORT_PREFIX = self.REPORTER_TITLE_PREFIX
    self._cover_report.gen_topic()

  def finish(self):
    """Wrap up the report by generating some statistics."""
    # generate statistics for the run, and write them out
    summary = self.new_report(dev_report=False, topic='summary')
    # Report statistic per section that each device went through.
    # pylint: disable=g-complex-comprehension
    # comprehension is to extract all sections from all results.
    known_sections = set([k for r in self._results for k in r])
    for section in known_sections:
      total = sum([1 for r in self._results if section in r])
      success = sum([1 for r in self._results if section in r and r[section]])
      failure = total - success
      summary.report_task('Devices %s' % section, str(total))
      summary.report_task('Devices %s success' % section, str(success))
      summary.report_task('Devices %s failure' % section, str(failure))
    # Report overall run statistics.
    total_devices = len(self._results)
    any_sort_of_failures = sum([1 for r in self._results if not
                                all(r.values())])
    summary.report_task('Devices with any failure', str(any_sort_of_failures))
    summary.report_task('Devices total', str(total_devices))
    # finish the file
    summary.finish(skip_space=True)
    # TODO(coconutruben): check if failed_path has some entries - if it does,
    # add a title to
    # it as well.

  def new_report(self, **kwargs):
    """Generate a new report.

    Args:
      **kwargs: k/v pairs to attach to the new report header

    Returns:
      Report, a Report object of the newly generated report
    """
    new_report = Report(self._path, self._failed_path, **kwargs)
    if self._current_report:
      # Close out the current report, and keep around
      # the outcome to generate stats later.
      self._current_report.finish()
      self._results.append(self._current_report.section_outcomes)
      self._current_report.finish()
    self._current_report = new_report
    # Start off the report with the topic correctly.
    self._current_report.gen_topic()
    return self._current_report


class Report(object):
  """Individual report for one device programming/flashing cycle."""

  # The following class variables are all the formatting bits for the
  # report.txt entries.

  LINE_WIDTH = 80

  LOGLINE_WIDTH = 80

  STATUS_PAD = '.'

  FINISHED_LINE = '-' * LINE_WIDTH

  REPORT_PREFIX = '##'

  SECTION_PREFIX = '###'

  SPACE_TO_NEXT_REPORT = 3

  SPACE_TO_SECTIONS = 2

  SPACE_TO_PREV_SECTION = 2

  SPACE_TO_SECTION_BODY = 1

  # Prefix to print before a comment line.
  COMMENT_PREFIX = '// '

  # Map to lookup the string meaning for a task result. A task result e.g.
  # programming the serialname can have three outcomes:
  # - success
  # - failure
  # - it was skipped
  TASK_FAILED_STRINGS = {
      False: 'FAILED',
      True: 'SUCCESS',
      None: 'SKIPPED'
  }

  # A section can have multiple outcomes as well. A section is for example all
  # programming, or all testing.
  SECTION_OUTCOME_STRINGS = {
      True: 'SUCCESS',
      False: 'FAILED',
      None: 'UNKNOWN'
  }

  def __init__(self, path, failed_path, dev_report=True, topic='device',
               **kwargs):
    """Setup the report.

    Args:
      path: path to the report.txt
      failed_path: path to the report only containing failures
      dev_report: if True, also write a copy for only this device specific
                  report
      topic: topic of the section. This is to allow the main report to have
             sections that are for statistics and not about a specific device
      **kwargs: k/v pairs to print into the header with topic

    Raises:
      ReporterError: if either |path| or |failed_path| do not exist
    """
    self._logger = logging.getLogger(type(self).__name__)
    for p in [path, failed_path]:
      d = os.path.dirname(p)
      if not os.path.exists(d):
        raise ReporterError('Invalid path %r provided. Directory not found.')
    self._dir = os.path.dirname(path)
    self._rpath = path
    self._serial = kwargs.get('serial', 'unknown')
    self._path = None
    if dev_report:
      # Only write your 'own' device report if requested to do so.
      self._path = os.path.join(self._dir, '%s.0.txt' % self._serial)
      # Shift is only relevant if we're also storing dev reports.
      self._shift()
    self._lines = []
    pieces = ['|%s:%s|' % (arg, val) for arg, val in kwargs.items()]
    self.header_line = '%s: %s' % (topic, ' '.join(pieces))
    # Helper to avoid printing after the report is marked finished.
    self._finished = False
    self._current_section = None
    # Map section names to their outcome to generate stats, and report lines
    # This can be 'True' 'False' or 'None' mapping to the constants above.
    self.section_outcomes = {}

  def _shift(self):
    """Shift any existing reports with |self._serial| if necessary."""
    # Generate all existing reports with the current serial. The wildcard
    # removes the number suffix and the type extension.
    wildcard = self._path.split('.')[0] + '*'
    paths = glob.glob(wildcard)
    if self._path in paths:
      self._logger.debug('Shifting older reports for %r', self._serial)
    paths.sort(reverse=True)
    for path in paths:
      src = path
      p, num, ftype = path.split('.')
      # Move the path up by one identifier.
      dst = '%s.%d.%s' % (p, int(num) + 1, ftype)
      os.rename(src, dst)

  def gen_topic(self):
    """Write the topic into the document."""
    report_title = '%s %s' % (self.REPORT_PREFIX, self.header_line)
    self.write_line(report_title)
    self.add_space(self.SPACE_TO_SECTIONS)

  def add_space(self, space, skip_dev_report=False):
    """Add blank lines to the document.

    Args:
      space: number of spaces to add
      skip_dev_report: whether to skip writing to |self._path|
    """
    for _ in range(space):
      self.write_line('\n', skip_dev_report=skip_dev_report)

  def _mark_section(self, outcome):
    """Mark the current section as |outcome|.

    Args:
      outcome: one of True, False, None to mark the section as described in
               |self.SECTION_OUTCOME_STRINGS|
    """
    if self._current_section:
      self.section_outcomes[self._current_section] = outcome
      self.write_line(self.FINISHED_LINE)
      # _mark_section is only called through a boolean, or None. These
      # keys always exist.
      self.report_task(self._current_section,
                       self.SECTION_OUTCOME_STRINGS[outcome])
      self._current_section = None

  def add_section(self, title):
    """Add a new section to this report.

    Note: if a section is not currently finished when this is called, it will
    close out the previous section with the result 'UNKNOWN'

    Args:
      title: title of the new section
    """
    if self._current_section is not None:
      # The user failed to mark the section as finished. Log about it, but
      # proceed.
      self._logger.debug('User never marked outcome of section %r',
                         self._current_section)
      self._mark_section(None)
    self._current_section = title
    self.add_space(self.SPACE_TO_PREV_SECTION)
    line = '%s %s - %s' % (self.SECTION_PREFIX, title, self.header_line)
    self.write_line(line)
    self.add_space(self.SPACE_TO_SECTION_BODY)

  def add_comment(self, comment):
    """Add a comment to the report.

    Args:
      comment: comment to add
    """
    file_comment = textwrap.wrap(comment,
                                 self.LINE_WIDTH - len(self.COMMENT_PREFIX))
    for line in file_comment:
      self.write_line('%s%s' % (self.COMMENT_PREFIX, line))
    console_comment = textwrap.wrap(comment, self.LOGLINE_WIDTH)
    for line in console_comment:
      self._logger.info(line)

  def report_task(self, task, status):
    """Report a task with its status.

    Args:
      task: name of the task performed
      status: status at the end. See |self.TASK_FAILED_STRINGS| for the logic
              but this supports shorthands, or if none are used, just uses
              |status| itself
    """
    # This allows for a short cut to report a common three way status of
    # a task failing, succeeding or being skipped.
    status = self.TASK_FAILED_STRINGS.get(status, status)
    # Make sure the status is a string.
    status = str(status)
    padding = self.LINE_WIDTH - len(status)
    logpadding = self.LOGLINE_WIDTH - len(status)
    line = '%s%s' % (task.ljust(padding, self.STATUS_PAD), status)
    self.write_line(line)
    self._logger.info('%s%s', task.ljust(logpadding, self.STATUS_PAD), status)

  def write_line(self, line, skip_dev_report=False):
    """Helper to write a line to file.

    Args:
      line: line to write
      skip_dev_report: whether to skip writing to |self._path|
    """
    if self._finished:
      self._logger.error('Report already finished. Will not print more lines.')
    if not line.endswith('\n'):
      line = '%s\n' % line
    # Write to device specific report only if enabled.
    if self._path is not None and not skip_dev_report:
      with open(self._path, 'a') as f:
        f.write(line)
    # Write to global report
    with open(self._rpath, 'a') as f:
      f.write(line)
    self._lines.append(line)

  def finish(self, skip_space=False):
    """Finish the current report up.

    Args:
      skip_space: whether to add space as a new report is expected after this
      or not.
    """
    if self._finished: return
    self.write_line(self.FINISHED_LINE)
    self.write_line(self.FINISHED_LINE)
    if not skip_space:
      self.add_space(self.SPACE_TO_NEXT_REPORT, skip_dev_report=True)
    self._finished = True
    # TODO(coconutruben): add here the failed ones.

  def mark(self, result):
    """Mark the currently active section as |result|.

    Args:
      result: the result of the section
    """
    self._mark_section(bool(result))
