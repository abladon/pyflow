#!/usr/bin/env python
#
# pyFlow - a lightweight parallel task engine
#
# Copyright (c) 2012-2015 Illumina, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

"""
This demonstrates a run of a prototype BCL to BWA BAM workflow
created as a production-scale proof of concept for pyflow.

The bwa workflow is written into the BWAWorkflow object. See
bwaworkflow.py for implementation details of this class.

Finally, make sure configuration settings in BWAWorkflowConfig
are appropriate before running.
"""

import os, sys

scriptDir = os.path.abspath(os.path.dirname(__file__))
scriptName = os.path.basename(__file__)


runScript1 = """#!/usr/bin/env python
# BWAWorkflow run script auto-generated by command: %s

import os.path, sys

scriptDir=os.path.abspath(os.path.dirname(__file__))
sys.path.append('%s')
from bwaworkflow import BWAWorkflow

class WorkflowOptions(object) :
""" % (" ".join(sys.argv), scriptDir)

runScript2 = """
def get_run_options() :
    from optparse import OptionParser
    import textwrap

    epilog=\"""Note this script can be re-run to continue the workflow run in case of interuption.
Also note that dryRun option has limited utility when task definition depends on upstream task results,
in which case the dry run will not cover the full 'live' run task set)\"""

    # no epilog in py 2.4! hack-in the feature instead:
    class MyOptionParser(OptionParser) :
        def __init__(self, *args, **kwargs):
            self.myepilog = None
            try:
                self.myepilog = kwargs.pop('epilog')
            except KeyError:
                pass
            OptionParser.__init__(self,*args, **kwargs)

        def print_help(self,*args,**kwargs) :
            OptionParser.print_help(self,*args, **kwargs)
            if self.myepilog != None :
                sys.stdout.write("%s\\n" % (textwrap.fill(self.myepilog)))

    parser = MyOptionParser(epilog=epilog)


    parser.add_option("-m", "--mode", type="string",dest="mode",
                      help="select run mode (local|sge)")
    parser.add_option("-j", "--jobs", type="string",dest="jobs",
	              help="number of jobs (default: 1 for local mode, 'unlimited' for sge mode)")
    parser.add_option("-e","--mailTo", type="string",dest="mailTo",action="append",
	              help="send email notification of job completion status to this address (may be provided multiple times for more than one email address)")
    parser.add_option("-d","--dryRun", dest="isDryRUn",action="store_true",
                      help="dryRun workflow code without actually running command-tasks")


    (options,args) = parser.parse_args()

    if len(args) :
        parser.print_help()
	sys.exit(2)

    if options.mode == None :
        parser.print_help()
	sys.exit(2)
    elif options.mode not in ["local","sge"] :
        parser.error("Invalid mode. Available modes are: local, sge")

    if options.jobs == None :
        if options.mode == "sge" :
	    options.jobs == "unlimited"
	else :
	    options.jobs == "1"
    elif (options.jobs != "unlimited") and (int(options.jobs) <= 0) :
        parser.error("Jobs must be 'unlimited' or an integer greater than 1")

    return options

runOptions=get_run_options()
flowOptions=WorkflowOptions()
flowOptions.outputDir=scriptDir
wflow = BWAWorkflow(flowOptions)
retval=wflow.run(mode=runOptions.mode,
                 nCores=runOptions.jobs,
                 dataDirRoot=scriptDir,
                 mailTo=runOptions.mailTo,
		 isContinue="Auto",
                 isForceContinue=True,
                 isDryRun=runOptions.isDryRUn)
sys.exit(retval)
"""




def checkArg(x, label, checkfunc) :
    if x != None:
        x = os.path.abspath(x)
        if not checkfunc(x) :
            raise Exception("Can't find %s: '%s'" % (label, x))
    return x

def checkDirArg(dir, label) :
    return checkArg(dir, label, os.path.isdir)

def checkFileArg(file, label) :
    return checkArg(file, label, os.path.isfile)



def get_option_parser(defaults, configFileName, isAllHelp=False) :
    from optparse import OptionGroup, OptionParser, SUPPRESS_HELP
    import textwrap

    description = """This script configures a bcl to BWA alignmed BAM workflow.
Given a bcl basecalls directory the workflow will create fastq's using CASAVA's
bcl to fastq converter, then align each fastq using bwa, and finally consolidate
the output into a single BAM file for for each Project/Sample combination.

The configuration process will produce a workflow run script, which can be used to
execute the workflow on a single node or through sge with a specific job limit.
"""

    epilog = """Default parameters will always be read from the file '%s' if it exists.
This file is searched for in the current working directory first -- if
it is not found then the directory containing this script is searched as well.
The current set of default parameters may be written to this file using the --writeConfig switch,
which takes all current defaults and arguments, writes these to the
configuration file and exits without setting up a workflow run script as usual.
""" % (configFileName)

    # no epilog in py 2.4! hack-in the feature instead:
    class MyOptionParser(OptionParser) :
        def __init__(self, *args, **kwargs):
            self.myepilog = None
            try:
                self.myepilog = kwargs.pop('epilog')
            except KeyError:
                pass
            OptionParser.__init__(self, *args, **kwargs)

        def print_help(self, *args, **kwargs) :
            OptionParser.print_help(self, *args, **kwargs)
            if self.myepilog != None :
                sys.stdout.write("%s\n" % (textwrap.fill(self.myepilog)))


    parser = MyOptionParser(description=description, epilog=epilog)

    parser.set_defaults(**defaults)

    parser.add_option("--allHelp", action="store_true", dest="isAllHelp",
                      help="show all extended/hidden options")

    group = OptionGroup(parser, "Workflow options")
    group.add_option("--bclBasecallsDir", type="string", dest="bclBasecallsDirList", metavar="DIR", action="append",
                      help="BCL basecalls directory. Call this option multiple times to specify multiple bcl directories, samples with the same name will be combined over all flowcells after alignmnet. [required] (default: %default)")
    group.add_option("--bclTilePattern", type="string", dest="bclTilePatternList", metavar="PATTERN", action="append",
                      help="BCL converter tiles expression used to select a subsset of tiles (eg. 's_1') call this option either once for each basecalls dir or not at all (default: %default)")
    group.add_option("--genomeFasta", type="string", dest="genomeFasta",
	              help="Genome fasta file which includes BWA index in the same directory [required] (default: %default)")
    group.add_option("--outputDir", type="string", dest="outputDir",
                      help="BCL basecalls directory [required] (default: %default)")
    group.add_option("--sampleName", type="string", dest="sampleNameList", metavar="sampleName", action="append",
                     help="Restrict analysis to given sampleName. This option can be provided more than once for multiple sample names. If no names are provided all samples are analyzed (default: %default)")
    parser.add_option_group(group)

    secgroup = OptionGroup(parser, "Extended options",
                                  "These options are not likely to be reset after initial configuration in a new site, they will not be printed here if a default exists from the configuration file or otherwise, unless --allHelp is specified")

    # used to access isAnyHelp from the maybeHelp function
    class Hack : isAnyHelp = False

    def maybeDefHelp(key, msg) :
        if isAllHelp or (key not in defaults) :
            Hack.isAnyHelp = True
            return msg
        return SUPPRESS_HELP

    secgroup.add_option("--casavaDir", type="string", dest="casavaDir",
                     help=maybeDefHelp("casavaDir", "casava 1.8.2+ installation directory [required] (default: %default)"))
    secgroup.add_option("--bwaBin", type="string", dest="bwaBin",
                     help=maybeDefHelp("bwaBin", "bwa binary [required] (default: %default)"))
    secgroup.add_option("--samtoolsBin", type="string", dest="samtoolsBin",
                     help=maybeDefHelp("samtoolsBin", "samtools binary [required] (default: %default)"))
    secgroup.add_option("--picardDir", type="string", dest="picardDir",
                     help=maybeDefHelp("picardDir", "casava 1.8.2+ installation directory [required] (default: %default)"))
    if not Hack.isAnyHelp:
        secgroup.description = "hidden"
    parser.add_option_group(secgroup)

    def maybeHelp(key, msg) :
        if isAllHelp : return msg
        return SUPPRESS_HELP

    configgroup = OptionGroup(parser, "Config options")
    configgroup.add_option("--writeConfig", action="store_true", dest="isWriteConfig",
                           help=maybeHelp("writeConfig", "Write new default configuration file based on current defaults and agruments. Defaults written to: '%s'" % (configFileName)))
    if not isAllHelp :
        configgroup.description = "hidden"
    parser.add_option_group(configgroup)

    return parser



def get_run_options() :
    from ConfigParser import SafeConfigParser

    configFileName = scriptName + ".ini"
    if not os.path.isfile(configFileName) :
        configPath = os.path.join(scriptDir, configFileName)
    else :
        configPath = os.path.join('.', configFileName)

    configSectionName = scriptName

    config = SafeConfigParser()
    config.optionxform = str
    config.read(configPath)

    configOptions = {}
    if config.has_section(configSectionName) :
        for (k, v) in config.items(configSectionName) :
            if v == "" : continue
            configOptions[k] = v

    defaults = { 'outputDir' : './results',
                 'bclToFastqMaxCores' : 12,
                 'samtoolsSortMemPerCore' : 1000000000,  # samtools sort uses about 2x what you tell it to...
                 'alnMaxCores' : 8,  # presumably bwa aln will become increasingly inefficient per core, so we don't want to let this go forever...
                 'isKeepFastq' : True,  # important to keep these during testing, but not for production
               }

    defaults.update(configOptions)

    parser = get_option_parser(defaults, configFileName)
    (options, args) = parser.parse_args()

    if options.isAllHelp :
        parser = get_option_parser(defaults, configFileName, True)
        parser.print_help()
        sys.exit(2)

    if len(args) :  # or (len(sys.argv) == 1):
        parser.print_help()
	sys.exit(2)

    # sanitize arguments before writing defaults, check for missing arguments after:
    #
    def checkListRepeats(list, itemLabel) :
        if list == None : return
        if len(set(list)) != len(list) :
            parser.error("Repeated %s entries" % (itemLabel))

    if options.bclBasecallsDirList != None :
        for i, bclDir in enumerate(options.bclBasecallsDirList) :
            options.bclBasecallsDirList[i] = checkDirArg(bclDir, "bcl basecalls directory")
    # tmp for testing:
    # checkListRepeats(options.bclBasecallsDirList,"bcl basecalls directory")
    if (options.bclTilePatternList != None) and \
       (len(options.bclBasecallsDirList) != len(options.bclTilePatternList)) :
        parser.error("Unexpected number of bclTilPattern entries")
    checkListRepeats(options.sampleNameList, "sample name")

    options.casavaDir = checkDirArg(options.casavaDir, "casava directory")

    options.genomeFasta = checkFileArg(options.genomeFasta, "genome fasta file")
    options.bwaBin = checkFileArg(options.bwaBin, "bwa binary")
    options.samtoolsBin = checkFileArg(options.samtoolsBin, "samtools binary")

    if options.isWriteConfig == True :
        if not config.has_section(configSectionName) :
            config.add_section(configSectionName)
        for k, v in vars(options).iteritems() :
            if k == "isWriteConfig" : continue
            if v == None : v = ""
            config.set(configSectionName, k, str(v))
        configfp = open(configFileName, "w")
        config.write(configfp)
        configfp.close()
        sys.exit(0)

    def noArgOrError(msg) :
        if len(sys.argv) <= 1 :
            parser.print_help()
            sys.exit(2)
        else :
            parser.error(msg)

    def assertOption(arg, label) :
        if arg == None:
            noArgOrError("No %s specified" % (label))

    def assertList(list, itemLabel) :
        if (list == None) or (len(list) == 0) :
            noArgOrError("List containing %s (s) is empty or missing" % (itemLabel))
        else :
            for item in list :
                assertOption(item, itemLabel)

    assertList(options.bclBasecallsDirList, "bcl basecalls directory")
    assertList(options.sampleNameList, "sample name")
    assertOption(options.genomeFasta, "genome fasta file")
    assertOption(options.outputDir, "output directory")
    assertOption(options.casavaDir, "casava directory")
    assertOption(options.picardDir, "picard directory")
    assertOption(options.bwaBin, "bwa binary")
    assertOption(options.samtoolsBin, "samtools binary")

    return options



from bwaworkflow import BWAWorkflow, ensureDir


def main() :

    options = get_run_options()

    # instantiate workflow object to trigger parameter validation only
    #
    wflow = BWAWorkflow(options)

    # generate runscript:
    #
    scriptFile = os.path.join(options.outputDir, "runWorkflow.py")
    ensureDir(options.outputDir)

    sfp = open(scriptFile, "w")
    sfp.write(runScript1)
    # there must be a nicer way to reverse eval() an object -- maybe human readable pickle is what we want here?
    for k, v in vars(options).iteritems() :
        if isinstance(v, basestring) :
            sfp.write("    %s = '%s'\n" % (k, v))
        else:
            sfp.write("    %s = %s\n" % (k, v))
    sfp.write("\n")
    sfp.write(runScript2)
    sfp.close()
    os.chmod(scriptFile, 0o755)

    notefp = sys.stdout
    notefp.write("""
Successfully created workflow run script. To execute the workflow, run the following script and set appropriate options:

%s
""" % (scriptFile))


if __name__ == "__main__" :
    main()

