#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# shellcheck disable=all
source /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        if [ -z ${TMT_SOURCE_DIR} ]; then
          tmt_root=${TMT_TREE}
        else
          tmt_root=${TMT_SOURCE_DIR}/scikit_build_core-*
        fi
		    rlRun "rsync -r ${tmt_root}$TMT_TEST_NAME/ $tmp" 0 "Copy example project"
		    rlRun "rsync -r ${tmt_root}/docs/examples/getting_started/test.py $tmp" 0 "Copy test.py file"
        rlRun "pushd $tmp"
        rlRun "tree" 0 "Show directory tree"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "pip install . --config-settings=cmake.verbose=true --no-index --no-build-isolation" 0 "Build the python project"
        rlRun "python3 test.py" 0 "Test project is installed correctly"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
