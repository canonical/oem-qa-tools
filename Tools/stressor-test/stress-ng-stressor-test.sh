#!/bin/bash

STRESSORS_FILE="stressors-list.log"
TEMP_RESULT="tmp-stress-ng-test.csv"

dump_stressors() {
    ./capture-stressor.py | tee $STRESSORS_FILE 
}

run_stress-ng() {
    # to capture the exit code of stres-ng (with tee command) test result
    # need to enable pipefail
    # https://www.gnu.org/savannah-checkouts/gnu/bash/manual/bash.html#The-Set-Builtin
    if [[ ! -e $TEMP_RESULT ]]; then
        echo "STRESSOR,RESULT" > $TEMP_RESULT
    fi

    echo "## Start stress-ng test..." 
    count=$(wc -l $STRESSORS_FILE | awk -F ' ' '{ print $1}')
    echo "Remaing stressors: $count"
    stressor=$(head -n 1 $STRESSORS_FILE)
    
    read -p "Is this stressor $stressor test failed?"$'\n\t'"input [yes] to skip it."$'\n\t'"Or"$'\n\t'"press [Enter] to run" awnser
    if [[ "$awnser" == "yes" ]]; then
        # Remove stressor from config file 
        sed -i '1d' $STRESSORS_FILE
	echo "$stressor,fail" >> $TEMP_RESULT
    fi
    
    while [[ $count > 0 ]];
    do
	stressor=$(head -n 1 $STRESSORS_FILE)
	echo "# Running stress-ng with this $stressor stressor.."
	cmd="stress-ng --$stressor 0 --timeout 30 --skip-silent --verbose"
	echo "command: $cmd"
        set -o pipefail
	$cmd 2>&1 | tee "$stressor"_test-result.log
        RET=$?
	set +o pipefail
        if [[ $RET == 0 || $RET == 3 || $RET == 4 ]]; then
            echo "$stressor,pass" >> $TEMP_RESULT
        else
            echo "$stressor,fail" >> $TEMP_RESULT
	fi
        # Remove stressor from config file 
	sed -i '1d' $STRESSORS_FILE
	sleep 5 
        count=$(wc -l $STRESSORS_FILE | awk -F ' ' '{ print $1}')
    done
    echo "stress-ng test completed"
    date=$(date +"%Y-%m-%dT%H%M")
    mv $TEMP_RESULT stress-ng_test-result_"$date".csv 
    rm $STRESSORS_FILE
}


main() {
    if [[ ! -e $STRESSORS_FILE ]]; then
        dump_stressors
    fi
    run_stress-ng
}

main
