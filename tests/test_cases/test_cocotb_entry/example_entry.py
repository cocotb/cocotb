import os
from cocotb.xunit_reporter import XUnitReporter


class EntryClass():

    def __init__(self):
        self.file = open('results.txt', 'w')
        print("Created entry_object")

    def entry_func(self, argv):
        print("Ran entry_func: {}".format(argv), file=self.file)

    def event_func(self, level, message):
        print("Ran event_func: {}, {}".format(level, message), file=self.file)

    def __del__(self):
        print("Shutting down", file=self.file)
        self.file.close()


entry_object = EntryClass()

_sim_event = entry_object.event_func

# horrible hack around the fact the makefiles expect a results.xml from every test
results_filename = os.getenv('COCOTB_RESULTS_FILE', "results.xml")
XUnitReporter(filename=results_filename).write()
