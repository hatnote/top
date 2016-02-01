
import os

from lithoxyl import Logger, SensibleSink, Formatter, StreamEmitter
from lithoxyl.filters import ThresholdFilter

tlog = Logger('toplog')

stderr_fmt = Formatter('{status_char}{end_local_iso8601_noms_notz} - {duration_secs}s - {record_name} - {message}')
stderr_emt = StreamEmitter('stderr')
stderr_filter = ThresholdFilter(success='debug',
                                failure='debug',
                                exception='debug')
stderr_sink = SensibleSink(formatter=stderr_fmt,
                           emitter=stderr_emt,
                           filters=[stderr_filter])
#                           on=['begin', 'complete'])  # TODO: clunk
tlog.add_sink(stderr_sink)


class DevDebugSink(object):
    # TODO: configurable max number of traceback signatures, after
    #       which exit/ignore?

    def __init__(self, reraise=False, post_mortem=False):
        self.reraise = reraise
        self.post_mortem = post_mortem

    #def on_complete(self, record):
    #    some conditions and a pdb perhaps

    def on_exception(self, record, exc_type, exc_obj, exc_tb):
        if self.post_mortem:
            import pdb; pdb.post_mortem()
        if self.reraise:
            raise exc_type, exc_obj, exc_tb


tlog.add_sink(DevDebugSink(post_mortem=os.getenv('TOP_PDB')))
