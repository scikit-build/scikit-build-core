#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# shellcheck disable=all
source /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
		    rlRun "rsync -r .$TMT_TEST_NAME/ $tmp" 0 "Copy example project"
        if [ "${HAS_PYTEST}" != True ]; then
		      rlRun "rsync -r ./docs/examples/getting_started/test.py $tmp" 0 "Copy test.py file"
        fi
        rlRun "pushd $tmp"
        rlRun "tree" 0 "Show directory tree"
        rlRun "python3 -m venv .venv --system-site-packages" 0 "Create venv with system packages"
        rlRun "source .venv/bin/activate" 0 "Activate venv"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "pip install . -v --no-index --no-build-isolation" 0 "Build the python project"
        if [ "${HAS_PYTEST}" == True ]; then
          rlRun "python3 -m pytest" 0 "Run built-in pytest"
        else
          rlRun "python3 test.py" 0 "Test project is installed correctly"
        fi
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
