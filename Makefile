.PHONY: help shunit2 pyunit all docs
.DEFAULT_GOAL := all

help:  ## Display this help
	@awk -F':.*##' 'BEGIN {bl = "\033[0m"; cy = "\033[36m"; printf "\nUsage:\n  make %s<target>%s\n\nTargets:\n", cy, bl} /^[a-zA-Z0-9_-]+:.*?##/ {printf "  %s%-10s%s %s\n", cy, $$1, bl, $$2}' $(MAKEFILE_LIST)

shunit2 = shunit2/encrypt_ami.sh \
					shunit2/share_ami.sh

shunit2:  ## Run the shunit2 tests for the Bash code
	for i in $(shunit2) ; do \
    printf "\n%s:\n" $$i ; \
    bash $$i ; \
    done

pyunit = pyunit/encrypt_ami.py
pyunit:  ## Run the Python Unittest tests for the Python code
	for i in $(pyunit) ; do \
		printf "\n%s:\n" $$i ; \
		python $$i ; \
		done

all: shunit2 pyunit  ## Run everything

docs:  ## Regenerate the README
	ruby docs.rb
