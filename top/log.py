
import os

from lithoxyl import Logger, SensibleSink, SensibleFilter, SensibleFormatter, StreamEmitter

tlog = Logger('toplog')

stderr_fmt = SensibleFormatter('{status_char}{iso_end_local_noms_notz} - {duration_s}s - {action_name} - {end_message}')
stderr_emt = StreamEmitter('stderr')
stderr_filter = SensibleFilter(success='debug',
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
            raise exc_obj.with_traceback(exc_tb)


tlog.add_sink(DevDebugSink(post_mortem=os.getenv('TOP_PDB')))
