#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# shellcheck disable=all
source /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
		    rlRun "rsync -r $TMT_TREE$TMT_TEST_NAME/ $tmp" 0 "Copy example project"
		    rlRun "rsync -r $TMT_TREE$TMT_TEST_NAME/../test.py $tmp" 0 "Copy test.py file"
        rlRun "pushd $tmp"
        rlRun "tree" 0 "Show directory tree"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "pip install . --config-settings=cmake.verbose=true" 0 "Build the python project"
        rlRun "python3 test.py" 0 "Test project is installed correctly"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
