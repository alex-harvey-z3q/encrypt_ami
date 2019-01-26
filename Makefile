.PHONY: help shunit2 pyunit all docs
.DEFAULT_GOAL := all

help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

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
