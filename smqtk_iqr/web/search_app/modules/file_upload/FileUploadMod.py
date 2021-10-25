import flask
from io import BytesIO
import multiprocessing
import os
import tempfile
from typing import Dict, Optional, Callable, TYPE_CHECKING

from smqtk_dataprovider.utils.file import safe_create_dir
import logging
from werkzeug.datastructures import FileStorage

# Without this if-statement there is an import cycle and a runtime error,
# but we only need this import during type checking so this checks for that.
if TYPE_CHECKING:
    from smqtk_iqr.web.search_app import IqrSearchDispatcher


LOG = logging.getLogger(__name__)
script_dir = os.path.dirname(os.path.abspath(__file__))


class FileUploadMod (flask.Blueprint):
    """
    Flask blueprint for file uploading.
    """

    def __init__(
        self, name: str, parent_app: 'IqrSearchDispatcher',
        working_directory: str, url_prefix: Optional[str] = None
    ):
        """
        Initialize uploading module

        :param parent_app: Parent Flask app

        :param working_directory: Directory for temporary file storage during
            upload up to the time a user takes control of the file.

        """
        super(FileUploadMod, self).__init__(
            name, __name__,
            static_folder=os.path.join(script_dir, 'static'),
            url_prefix=url_prefix
        )
        # TODO: Thread safety

        self.parent_app = parent_app
        self.working_dir = working_directory

        # TODO: Move chunk storage to database for APACHE multiprocessing
        # File chunk aggregation
        #   Top level key is the file ID of the upload. The dictionary
        #   underneath that is the index ID'd chunks. When all chunks are
        #   present, the file is written and the entry in this map is removed.
        self._file_chunks: Dict[
            str, Dict[int, BytesIO]
        ] = {}
        # Lock per file ID so as to not collide when uploading multiple chunks
        self._fid_locks: Dict[str, multiprocessing.synchronize.RLock] = {}

        # FileID to temporary path that a completed file is located at.
        self._completed_files: Dict[str, str] = {}

        #
        # Routing
        #

        @self.route('/upload_chunk', methods=["POST"])
        @self.parent_app.module_login.login_required
        def upload_file() -> str:
            """
            Handle arbitrary file upload to OS temporary file storage, recording
            file upload completions.

            """
            form = flask.request.form
            LOG.debug("POST form contents: %s" % str(flask.request.form))

            fid = form['flowIdentifier']
            current_chunk = int(form['flowChunkNumber'])
            total_chunks = int(form['flowTotalChunks'])
            filename = form['flowFilename']

            chunk_data: FileStorage = flask.request.files['file']

            with self._fid_locks.setdefault(fid, multiprocessing.RLock()):
                # Create new entry in chunk map / add to existing entry
                # - Need to explicitly copy the buffered data as the file object
                #   closes between chunk messages.
                self._file_chunks.setdefault(fid, {})[current_chunk] \
                    = BytesIO(chunk_data.read())  # type: ignore
                message = "Uploaded chunk #%d of %d for file '%s'" \
                    % (current_chunk, total_chunks, filename)

                if total_chunks == len(self._file_chunks[fid]):
                    LOG.debug("[%s] Final chunk uploaded", filename+"::"+fid)
                    # have all chucks in memory now
                    try:
                        # Combine chunks into single file
                        file_ext = os.path.splitext(filename)[1]
                        file_saved_path = self._write_file_chunks(
                            self._file_chunks[fid], file_ext
                        )
                        LOG.debug("[%s] saved from chunks: %s",
                                  filename+"::"+fid, file_saved_path)
                        # now in file, free up dict memory

                        self._completed_files[fid] = file_saved_path
                        message = "[%s] Completed upload" % (filename+"::"+fid)

                    except IOError as ex:
                        LOG.debug("[%s] Failed to write combined chunks",
                                  filename+"::"+fid)
                        message = "Failed to write out combined chunks for " \
                                  "file %s: %s" % (filename, str(ex))
                        raise RuntimeError(message)

                    except NotImplementedError as ex:
                        message = "Encountered non-implemented code path: %s" \
                                  % str(ex)
                        raise RuntimeError(message)

                    finally:
                        # remove chunk map entries
                        del self._file_chunks[fid]
                        del self._fid_locks[fid]

            # Flow only displays return as a string, so just returning the
            # message component.
            return message

        @self.route("/completed_uploads")
        @self.parent_app.module_login.login_required
        def completed_uploads() -> Callable:
            return flask.jsonify(self._completed_files)

    def upload_post_url(self) -> str:
        """
        :return: The url string to give to the JS upload zone for POSTing file
            chunks.
        """
        return (self.url_prefix and self.url_prefix+"/" or "") + 'upload_chunk'

    def get_path_for_id(self, file_unique_id: str) -> str:
        """
        Get the path to the temp file that was uploaded.

        It is the user's responsibility to remove this file when it is done
        being used, or move it else where.

        :param file_unique_id: Unique ID of the uploaded file

        :return: The path to the complete uploaded file.

        """
        return self._completed_files[file_unique_id]

    def clear_completed(self, file_unique_id: str) -> None:
        """
        Clear the completed file entry in our cache. This should be called after
        taking responsibility for an uploaded file.

        This does NOT delete the file.

        :raises KeyError: If the given unique ID does not correspond to an
            entry in our completed cache.

        :param file_unique_id: Unique ID of an uploaded file to clear from the
            completed cache.

        """
        del self._completed_files[file_unique_id]

    # noinspection PyMethodMayBeStatic
    def _write_file_chunks(
        self, chunk_map: Dict[int, BytesIO],
        file_extension: str = ''
    ) -> str:
        """
        Given a mapping of chunks, write their contents to a temporary file,
        returning the path to that file.

        Returned file path should be manually removed by the user.

        :param chunk_map: Mapping of integer index to file-like chunk
        :param file_extension: String extension to suffix the temporary file
            with

        :raises OSError: OS problems creating temporary file or writing it out.

        :return: Path to temporary combined file

        """
        # Make sure write dir exists...
        if not os.path.isdir(self.working_dir):
            safe_create_dir(self.working_dir)
        tmp_fd, tmp_path = tempfile.mkstemp(file_extension,
                                            dir=self.working_dir)
        LOG.debug("Combining chunks into temporary file: %s", tmp_path)
        tmp_file = open(tmp_path, 'wb')
        for idx, chunk in sorted(chunk_map.items(), key=lambda p: p[0]):
            data = chunk.read()
            tmp_file.write(data)
        tmp_file.close()
        return tmp_path
