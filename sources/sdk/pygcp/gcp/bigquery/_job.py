# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Implements BigQuery Job functionality."""

import collections
from time import sleep as _sleep

JobError = collections.namedtuple('JobError', ['location', 'message', 'reason'])


class Job(object):
  """Represents a BigQuery Job.
  """

  def __init__(self, api, job_id):
    """Initializes an instance of a Job.

    Args:
      api: the BigQuery API object to use to issue requests. The project ID will be inferred from
          this.
      job_id: the BigQuery job ID corresponding to this job.
    """
    self._api = api
    self._job_id = job_id
    self._is_complete = False
    self._errors = None
    self._fatal_error = None

  @property
  def id(self):
    """ Get the Job ID.

    Returns:
      The ID of the job.
    """
    return self._job_id

  @property
  def iscomplete(self):
    """ Get the completion state of the job.

    Returns:
      True if the job is complete; False if it is still running.
    """
    self._refresh_state()
    return self._is_complete

  @property
  def failed(self):
    """ Get the success state of the job.

    Returns:
      True if the job failed; False if it is still running or succeeded (possibly with partial
      failure).
    """
    self._refresh_state()
    return self._is_complete and self._fatal_error

  @property
  def fatal_error(self):
    """ Get the job error.

    Returns:
      None if the job succeeded or is still running, else the error tuple for the failure.
    """
    self._refresh_state()
    return self._fatal_error

  @property
  def errors(self):
    """ Get the errors in the job.

    Returns:
      None if the job is still running, else the list of errors that occurred.
    """
    self._refresh_state()
    return self._errors

  def _refresh_state(self):
    """ Get the state of a job. If the job is complete this does nothing
        otherwise it gets a refreshed copy of the job resource.
    """
    # TODO(gram): should we put a choke on refreshes? E.g. if the last call was less than
    # a second ago should we return the cached value?
    if self._is_complete:
      return

    response = self._api.jobs_get(self._job_id)

    if 'status' in response:
      status = response['status']
      if 'state' in status and status['state'] == 'DONE':
        self._is_complete = True
        if 'errorResult' in status:
          error_result = status['errorResult']
          location = error_result.get('location', None)
          message = error_result.get('message', None)
          reason = error_result.get('reason', None)
          self._fatal_error = JobError(location, message, reason)
        if 'errors' in status:
          self._errors = []
          for error in status['errors']:
            location = error.get('location', None)
            message = error.get('message', None)
            reason = error.get('reason', None)
            self._errors.append(JobError(location, message, reason))

  def wait(self, timeout=None, poll=5):
    """ Wait for the job to complete, or a timeout to happen.

    Args:
      timeout: how long to poll before giving up; default None which means no timeout.
      poll: interval in seconds between polls (default 5)

    Returns:
      True if job completed; False if wait timed out.
    """
    while not self.iscomplete:
      if timeout is not None:
        if timeout <= 0:
          return False
        timeout -= poll
      _sleep(poll)
    return True

  def __repr__(self):
    """ Get the notebook representation for the job.
    """
    return 'Job %s' % str(self._job_id)

